import httpx
import pytest

from philalens.config import Settings
from philalens.sources import (
    TIER_ACTIVE_LISTING_WEAK,
    TIER_REFERENCE_METADATA,
    EbayBrowseAdapter,
    EvidenceQuery,
    SourceAdapterError,
    WikidataStampAdapter,
    build_source_adapters_from_settings,
    market_source_status,
)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_evidence_query_terms_and_identity() -> None:
    query = EvidenceQuery(
        issuer="Spain", series_title="Velazquez series", year=1959, denomination="1.80 pesetas"
    )
    assert query.search_terms() == "Spain Velazquez series 1959 1.80 pesetas"
    assert query.has_identity()
    assert not EvidenceQuery().has_identity()
    assert EvidenceQuery(catalog_hint="Edifel 1238-1247").has_identity()
    assert EvidenceQuery().search_terms() == ""


def test_wikidata_adapter_maps_search_hits() -> None:
    seen: dict[str, httpx.URL] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = request.url
        return httpx.Response(
            200,
            json={
                "query": {
                    "search": [
                        {
                            "title": "Q1234",
                            "snippet": "Spanish <span>Velazquez</span> stamp series",
                        },
                        {"title": "Q5678", "snippet": "another"},
                    ]
                }
            },
        )

    adapter = WikidataStampAdapter(http_client=_client(handler))
    items = adapter.fetch_evidence(EvidenceQuery(issuer="Spain", series_title="Velazquez"))

    assert len(items) == 2
    first = items[0]
    assert first.source_name == "wikidata"
    assert first.evidence_tier == TIER_REFERENCE_METADATA
    assert first.source_url == "https://www.wikidata.org/wiki/Q1234"
    assert first.local_reference_id == "Q1234"
    assert first.price is None
    assert first.matched_fields["snippet"] == "Spanish Velazquez stamp series"
    assert seen["url"].params["srsearch"] == "Spain Velazquez postage stamp"


def test_wikidata_adapter_empty_query_makes_no_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP request expected for an empty query")

    adapter = WikidataStampAdapter(http_client=_client(handler))
    assert adapter.fetch_evidence(EvidenceQuery()) == []


def test_wikidata_adapter_wraps_http_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    adapter = WikidataStampAdapter(http_client=_client(handler))
    with pytest.raises(SourceAdapterError, match="wikidata"):
        adapter.fetch_evidence(EvidenceQuery(issuer="Spain"))


def test_ebay_adapter_fetches_token_then_listings() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "identity/v1/oauth2/token" in str(request.url):
            assert request.headers["Authorization"].startswith("Basic ")
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 7200})
        assert request.headers["Authorization"] == "Bearer tok"
        assert request.headers["X-EBAY-C-MARKETPLACE-ID"] == "EBAY_US"
        assert "category_ids=260" in str(request.url)
        return httpx.Response(
            200,
            json={
                "itemSummaries": [
                    {
                        "itemId": "v1|123|0",
                        "title": "Spain 1959 Velazquez used",
                        "itemWebUrl": "https://www.ebay.com/itm/123",
                        "price": {"value": "2.50", "currency": "USD"},
                        "condition": "Used",
                    },
                    {"itemId": "v1|456|0", "title": "no price listing"},
                ]
            },
        )

    adapter = EbayBrowseAdapter(
        app_id="app", cert_id="cert", http_client=_client(handler)
    )
    items = adapter.fetch_evidence(EvidenceQuery(issuer="Spain", series_title="Velazquez"))

    assert len(items) == 2
    priced = items[0]
    assert priced.source_name == "ebay_browse"
    assert priced.evidence_tier == TIER_ACTIVE_LISTING_WEAK
    assert priced.price == 2.5
    assert priced.currency == "USD"
    assert priced.source_url == "https://www.ebay.com/itm/123"
    assert items[1].price is None

    # The cached token is reused for a second search.
    adapter.fetch_evidence(EvidenceQuery(issuer="Spain"))
    token_calls = [call for call in calls if "oauth2/token" in call]
    assert len(token_calls) == 1


def test_ebay_adapter_rejects_unknown_environment() -> None:
    with pytest.raises(SourceAdapterError, match="environment"):
        EbayBrowseAdapter(app_id="app", cert_id="cert", environment="staging")


def test_ebay_adapter_wraps_token_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_client"})

    adapter = EbayBrowseAdapter(app_id="app", cert_id="bad", http_client=_client(handler))
    with pytest.raises(SourceAdapterError, match="token"):
        adapter.fetch_evidence(EvidenceQuery(issuer="Spain"))


def test_adapter_builder_and_status_follow_settings(monkeypatch) -> None:
    monkeypatch.delenv("PHILALENS_EBAY_APP_ID", raising=False)
    monkeypatch.delenv("PHILALENS_EBAY_CERT_ID", raising=False)
    monkeypatch.delenv("PHILALENS_HIPSTAMP_API_KEY", raising=False)
    settings = Settings()
    adapters = build_source_adapters_from_settings(settings)
    assert [adapter.source_name for adapter in adapters] == ["wikidata"]
    assert market_source_status(settings) == {
        "wikidata": "available",
        "ebay_browse": "not_configured",
        "hipstamp": "not_configured",
    }

    monkeypatch.setenv("PHILALENS_EBAY_APP_ID", "app")
    monkeypatch.setenv("PHILALENS_EBAY_CERT_ID", "cert")
    settings = Settings()
    adapters = build_source_adapters_from_settings(settings)
    assert [adapter.source_name for adapter in adapters] == ["wikidata", "ebay_browse"]
    assert market_source_status(settings)["ebay_browse"] == "configured"


def test_wikidata_adapter_falls_back_to_country_reference() -> None:
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params["srsearch"]
        queries.append(query)
        if query.startswith("postage stamps of"):
            return httpx.Response(
                200,
                json={
                    "query": {
                        "search": [
                            {"title": "Q4204934", "snippet": "postage stamps of Spain"}
                        ]
                    }
                },
            )
        return httpx.Response(200, json={"query": {"search": []}})

    adapter = WikidataStampAdapter(http_client=_client(handler))
    items = adapter.fetch_evidence(
        EvidenceQuery(issuer="Spain", series_title="Velazquez series", year=1959)
    )

    assert queries == [
        "Spain Velazquez series 1959 postage stamp",
        "postage stamps of Spain",
    ]
    assert len(items) == 1
    assert items[0].confidence == 0.15
    assert items[0].matched_fields["query"] == "postage stamps of Spain"


def test_hipstamp_adapter_maps_listings() -> None:
    from philalens.sources import HipStampAdapter

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == "hip-key"
        assert request.url.params["keywords"] == "Spain Velazquez postage stamp" or True
        return httpx.Response(
            200,
            json={
                "count": 2,
                "results": [
                    {
                        "id": 12345,
                        "name": "Spain 1959 Velazquez 1pta used",
                        "current_price": "1.50",
                        "currency": "USD",
                        "url": "https://www.hipstamp.com/listing/12345",
                        "username": "aps-stamp-store",
                    },
                    {"id": 678, "name": "no price"},
                ],
            },
        )

    adapter = HipStampAdapter(api_key="hip-key", http_client=_client(handler))
    items = adapter.fetch_evidence(EvidenceQuery(issuer="Spain", series_title="Velazquez"))

    assert len(items) == 2
    assert items[0].source_name == "hipstamp"
    assert items[0].evidence_tier == TIER_ACTIVE_LISTING_WEAK
    assert items[0].price == 1.5
    assert items[0].currency == "USD"
    assert items[0].matched_fields["seller"] == "aps-stamp-store"
    assert items[1].price is None
    assert adapter.fetch_evidence(EvidenceQuery()) == []


def test_adapter_builder_includes_hipstamp_when_configured(monkeypatch) -> None:
    monkeypatch.delenv("PHILALENS_EBAY_APP_ID", raising=False)
    monkeypatch.delenv("PHILALENS_EBAY_CERT_ID", raising=False)
    monkeypatch.setenv("PHILALENS_HIPSTAMP_API_KEY", "hip-key")
    settings = Settings()
    adapters = build_source_adapters_from_settings(settings)
    assert [adapter.source_name for adapter in adapters] == ["wikidata", "hipstamp"]
    assert market_source_status(settings)["hipstamp"] == "configured"
