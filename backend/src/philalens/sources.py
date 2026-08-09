"""Tier 2 evidence source adapters.

Adapters retrieve external reference or market evidence for a stamp identity
candidate. They are storage-agnostic: each returns lightweight ``EvidenceItem``
values that the market-evidence orchestrator converts into durable
``SourceEvidenceRecord`` rows.

Evidence strength is explicit and conservative:

- ``reference_metadata``: open reference entries (Wikidata) with no prices.
- ``active_listing_weak``: live marketplace asking prices. Asking prices never
  become standalone value estimates.
- ``realized_sale``: completed sale prices. Only this tier can support a value
  range. No current adapter produces it; the tier exists so future sold-price
  sources plug in without changing the range policy.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from .config import Settings

TIER_REFERENCE_METADATA = "reference_metadata"
TIER_ACTIVE_LISTING_WEAK = "active_listing_weak"
TIER_REALIZED_SALE = "realized_sale"

SOURCE_TYPE_OPEN_REFERENCE = "open_reference"
SOURCE_TYPE_MARKETPLACE_LISTING = "marketplace_listing"

_HTTP_TIMEOUT_SECONDS = 15.0
# Wikimedia's user-agent policy requires a contact URL; generic UAs get 403.
_USER_AGENT = "Philalens/0.2 (https://github.com/aprada9/philalens; personal stamp research tool)"

_EBAY_ENDPOINTS = {
    "production": {
        "token": "https://api.ebay.com/identity/v1/oauth2/token",
        "browse": "https://api.ebay.com/buy/browse/v1",
    },
    "sandbox": {
        "token": "https://api.sandbox.ebay.com/identity/v1/oauth2/token",
        "browse": "https://api.sandbox.ebay.com/buy/browse/v1",
    },
}
_EBAY_STAMPS_CATEGORY_ID = "260"


class SourceAdapterError(RuntimeError):
    """Raised when an evidence source cannot be queried."""


@dataclass(frozen=True)
class EvidenceQuery:
    """Search input built from a stamp's top identity candidate."""

    issuer: str | None = None
    series_title: str | None = None
    year: int | None = None
    denomination: str | None = None
    catalog_hint: str | None = None

    def search_terms(self) -> str:
        parts = [
            self.issuer,
            self.series_title,
            str(self.year) if self.year else None,
            self.denomination,
        ]
        return " ".join(part for part in parts if part)

    def has_identity(self) -> bool:
        return bool(self.issuer or self.series_title or self.catalog_hint)


@dataclass(frozen=True)
class EvidenceItem:
    source_name: str
    source_type: str
    evidence_tier: str
    confidence: float
    source_url: str | None = None
    local_reference_id: str | None = None
    matched_fields: dict[str, Any] = field(default_factory=dict)
    price: float | None = None
    price_low: float | None = None
    price_high: float | None = None
    currency: str | None = None
    condition_assumptions: str | None = None
    license_notes: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class SourceAdapter(Protocol):
    @property
    def source_name(self) -> str: ...

    def fetch_evidence(self, query: EvidenceQuery) -> list[EvidenceItem]: ...


class WikidataStampAdapter:
    """Open reference lookup against the Wikidata search API (CC0, no key)."""

    source_name = "wikidata"

    def __init__(self, http_client: httpx.Client | None = None, max_results: int = 3) -> None:
        self._client = http_client
        self._max_results = max_results

    def fetch_evidence(self, query: EvidenceQuery) -> list[EvidenceItem]:
        terms = query.search_terms()
        if not terms:
            return []
        # Wikidata search ANDs every term, so a full issue query often matches
        # nothing; fall back to country-level philatelic reference items.
        hits, used_query = self._search(f"{terms} postage stamp")
        confidence = 0.3
        if not hits and query.issuer:
            hits, used_query = self._search(f"postage stamps of {query.issuer}")
            confidence = 0.15  # country-level context only, not an issue match

        items: list[EvidenceItem] = []
        for hit in hits[: self._max_results]:
            if not isinstance(hit, dict) or not hit.get("title"):
                continue
            entity_id = str(hit["title"])
            items.append(
                EvidenceItem(
                    source_name=self.source_name,
                    source_type=SOURCE_TYPE_OPEN_REFERENCE,
                    evidence_tier=TIER_REFERENCE_METADATA,
                    # Keyword-matched reference entry, not a confirmed identity.
                    confidence=confidence,
                    source_url=f"https://www.wikidata.org/wiki/{entity_id}",
                    local_reference_id=entity_id,
                    matched_fields={
                        "query": used_query,
                        "snippet": _strip_html(str(hit.get("snippet", ""))),
                    },
                    license_notes="Wikidata content is CC0.",
                    raw_payload={"search_hit": hit},
                )
            )
        return items

    def _search(self, search_query: str) -> tuple[list[dict[str, Any]], str]:
        payload = _get_json(
            self._client,
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": search_query,
                "srlimit": str(self._max_results),
                "format": "json",
            },
            source_name=self.source_name,
        )
        hits = payload.get("query", {}).get("search", [])
        if not isinstance(hits, list):
            return [], search_query
        return [hit for hit in hits if isinstance(hit, dict)], search_query


class EbayBrowseAdapter:
    """eBay Browse API keyword search over the Stamps category.

    Returns active listings only. Asking prices are stored as weak evidence and
    never become standalone value estimates. Credentials come from settings/env
    and are never written to the repository.
    """

    source_name = "ebay_browse"

    def __init__(
        self,
        app_id: str,
        cert_id: str,
        marketplace: str = "EBAY_US",
        environment: str = "production",
        http_client: httpx.Client | None = None,
        max_results: int = 10,
    ) -> None:
        endpoints = _EBAY_ENDPOINTS.get(environment)
        if endpoints is None:
            raise SourceAdapterError(
                f"Unknown eBay environment: {environment} (use production or sandbox)."
            )
        self._app_id = app_id
        self._cert_id = cert_id
        self._marketplace = marketplace
        self._token_url = endpoints["token"]
        self._browse_url = endpoints["browse"]
        self._client = http_client
        self._max_results = max_results
        self._token: str | None = None
        self._token_expires_at = 0.0

    def fetch_evidence(self, query: EvidenceQuery) -> list[EvidenceItem]:
        terms = query.search_terms()
        if not terms:
            return []
        payload = _get_json(
            self._client,
            f"{self._browse_url}/item_summary/search",
            params={
                "q": f"{terms} stamp",
                "category_ids": _EBAY_STAMPS_CATEGORY_ID,
                "limit": str(self._max_results),
            },
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "X-EBAY-C-MARKETPLACE-ID": self._marketplace,
            },
            source_name=self.source_name,
        )
        summaries = payload.get("itemSummaries", [])
        if not isinstance(summaries, list):
            return []

        items: list[EvidenceItem] = []
        for summary in summaries[: self._max_results]:
            if not isinstance(summary, dict):
                continue
            price_value, currency = _ebay_price(summary)
            items.append(
                EvidenceItem(
                    source_name=self.source_name,
                    source_type=SOURCE_TYPE_MARKETPLACE_LISTING,
                    evidence_tier=TIER_ACTIVE_LISTING_WEAK,
                    # Keyword-matched active listing: weak on both identity
                    # and price.
                    confidence=0.25,
                    source_url=summary.get("itemWebUrl"),
                    local_reference_id=summary.get("itemId"),
                    matched_fields={
                        "query": terms,
                        "listing_title": summary.get("title"),
                        "condition": summary.get("condition"),
                    },
                    price=price_value,
                    currency=currency,
                    condition_assumptions=(
                        "Listing condition as described by the seller; unverified."
                    ),
                    license_notes=(
                        "Active eBay listing. Asking price only; weaker than realized sales."
                    ),
                    raw_payload={"item_summary": summary},
                )
            )
        return items

    def _access_token(self) -> str:
        if self._token is not None and time.monotonic() < self._token_expires_at:
            return self._token

        basic = base64.b64encode(f"{self._app_id}:{self._cert_id}".encode()).decode()
        try:
            response = _request(
                self._client,
                "POST",
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "scope": "https://api.ebay.com/oauth/api_scope",
                },
                headers={
                    "Authorization": f"Basic {basic}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise SourceAdapterError(f"ebay_browse: token request failed: {exc}") from exc

        token = payload.get("access_token")
        if not token:
            raise SourceAdapterError("ebay_browse: token response had no access_token.")
        self._token = str(token)
        # Refresh one minute before the reported expiry.
        expires_in = float(payload.get("expires_in", 7200))
        self._token_expires_at = time.monotonic() + max(expires_in - 60.0, 60.0)
        return self._token


class HipStampAdapter:
    """HipStamp marketplace keyword search (stamps-only marketplace).

    Active listings only — asking prices, stored as weak evidence like eBay.
    The material is better identified than general marketplaces (dealer and
    APS-store listings), so keyword matches skew more relevant. API key is
    free via app registration at hipstamp.com; 10k requests/day.
    """

    source_name = "hipstamp"

    def __init__(
        self,
        api_key: str,
        http_client: httpx.Client | None = None,
        max_results: int = 10,
    ) -> None:
        self._api_key = api_key
        self._client = http_client
        self._max_results = max_results

    def fetch_evidence(self, query: EvidenceQuery) -> list[EvidenceItem]:
        terms = query.search_terms()
        if not terms:
            return []
        payload = _get_json(
            self._client,
            "https://www.hipstamp.com/api/listings",
            params={
                "keywords": terms,
                "limit": str(self._max_results),
                "api_key": self._api_key,
            },
            source_name=self.source_name,
        )
        results = payload.get("results", [])
        if not isinstance(results, list):
            return []

        items: list[EvidenceItem] = []
        for listing in results[: self._max_results]:
            if not isinstance(listing, dict):
                continue
            try:
                price = float(listing.get("current_price"))
            except (TypeError, ValueError):
                price = None
            items.append(
                EvidenceItem(
                    source_name=self.source_name,
                    source_type=SOURCE_TYPE_MARKETPLACE_LISTING,
                    evidence_tier=TIER_ACTIVE_LISTING_WEAK,
                    confidence=0.25,
                    source_url=listing.get("url"),
                    local_reference_id=str(listing.get("id", "")) or None,
                    matched_fields={
                        "query": terms,
                        "listing_title": listing.get("name"),
                        "seller": listing.get("username"),
                    },
                    price=price,
                    currency=str(listing.get("currency")) if listing.get("currency") else None,
                    condition_assumptions=(
                        "Listing condition as described by the seller; unverified."
                    ),
                    license_notes=(
                        "Active HipStamp listing. Asking price only; weaker than realized sales."
                    ),
                    raw_payload={"listing": listing},
                )
            )
        return items


def build_source_adapters_from_settings(settings: Settings) -> list[SourceAdapter]:
    adapters: list[SourceAdapter] = [WikidataStampAdapter()]
    if settings.ebay_app_id and settings.ebay_cert_id:
        adapters.append(
            EbayBrowseAdapter(
                app_id=settings.ebay_app_id,
                cert_id=settings.ebay_cert_id,
                marketplace=settings.ebay_marketplace,
                environment=settings.ebay_environment,
            )
        )
    if settings.hipstamp_api_key:
        adapters.append(HipStampAdapter(api_key=settings.hipstamp_api_key))
    return adapters


def market_source_status(settings: Settings) -> dict[str, str]:
    return {
        "wikidata": "available",
        "ebay_browse": (
            "configured" if settings.ebay_app_id and settings.ebay_cert_id else "not_configured"
        ),
        "hipstamp": "configured" if settings.hipstamp_api_key else "not_configured",
    }


def _request(
    client: httpx.Client | None,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    headers = {"User-Agent": _USER_AGENT, **kwargs.pop("headers", {})}
    if client is not None:
        return client.request(method, url, headers=headers, **kwargs)
    with httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS) as owned:
        return owned.request(method, url, headers=headers, **kwargs)


def _get_json(
    client: httpx.Client | None,
    url: str,
    *,
    params: dict[str, str],
    source_name: str,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        response = _request(client, "GET", url, params=params, headers=headers or {})
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise SourceAdapterError(f"{source_name}: request failed: {exc}") from exc
    except ValueError as exc:
        raise SourceAdapterError(f"{source_name}: response was not JSON.") from exc
    if not isinstance(payload, dict):
        raise SourceAdapterError(f"{source_name}: unexpected response shape.")
    return payload


def _ebay_price(summary: dict[str, Any]) -> tuple[float | None, str | None]:
    price = summary.get("price")
    if not isinstance(price, dict):
        return None, None
    try:
        value = float(price.get("value"))
    except (TypeError, ValueError):
        return None, None
    currency = price.get("currency")
    return value, str(currency) if currency else None


def _strip_html(text: str) -> str:
    result: list[str] = []
    in_tag = False
    for char in text:
        if char == "<":
            in_tag = True
        elif char == ">":
            in_tag = False
        elif not in_tag:
            result.append(char)
    return "".join(result)
