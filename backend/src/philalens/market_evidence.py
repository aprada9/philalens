"""Tier 2 market-evidence pass over flagged outlier crops.

Evidence gathering enriches an existing completed Tier 1 evaluation run: it
stores ``source_evidence`` rows and appends an updated valuation record per
crop (the newest valuation per crop wins in exports). Value ranges are only
computed from realized-sale evidence with sufficient identity confidence;
otherwise the valuation states explicitly why there is no range.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .models import (
    CatalogCandidateRecord,
    EvaluationRunRecord,
    SourceEvidenceRecord,
    StampCrop,
    StampValuationRecord,
)
from .sources import (
    TIER_ACTIVE_LISTING_WEAK,
    TIER_REALIZED_SALE,
    EvidenceItem,
    EvidenceQuery,
    SourceAdapter,
    SourceAdapterError,
)
from .storage import PhilalensStore, new_id, utc_now

# Buckets whose crops are Tier 2 targets when no explicit selection is given.
ATTENTION_BUCKETS = {"possibly_interesting", "investigate", "needs_expert_check"}

# A value range requires this many realized-sale price points and at least
# this much identity confidence. Asking prices never count toward a range.
MIN_REALIZED_SALE_PRICES = 2
MIN_IDENTITY_CONFIDENCE_FOR_RANGE = 0.5

_CATALOG_HINT_PREFIX = "catalog_hint (unverified):"


class MarketEvidenceError(RuntimeError):
    """Raised when an evidence pass cannot start."""


def gather_market_evidence(
    store: PhilalensStore,
    collection_id: str,
    adapters: list[SourceAdapter],
    crop_ids: list[str] | None = None,
    progress_callback: Callable[[int, int, StampCrop], None] | None = None,
) -> EvaluationRunRecord | None:
    collection = store.get_collection(collection_id)
    if collection is None:
        return None

    run = store.get_latest_evaluation_run(collection_id)
    if run is None or run.status != "completed":
        raise MarketEvidenceError(
            "Run a Tier 1 evaluation first: market evidence attaches to the latest "
            "completed evaluation run."
        )

    crops = {
        crop.crop_id: crop
        for page in store.list_pages(collection_id)
        for crop in store.list_crops_for_page(page.page_id)
    }
    if crop_ids is not None:
        missing = [crop_id for crop_id in crop_ids if crop_id not in crops]
        if missing:
            raise MarketEvidenceError(f"Crop not found in collection: {missing[0]}")
        targets = [crops[crop_id] for crop_id in crop_ids]
    else:
        targets = [
            crops[valuation.crop_id]
            for valuation in _latest_valuations_per_crop(store, run.run_id)
            if valuation.value_bucket in ATTENTION_BUCKETS and valuation.crop_id in crops
        ]

    errors: list[str] = list(run.errors)
    evidence_total = 0
    for index, crop in enumerate(targets, start=1):
        if progress_callback is not None:
            progress_callback(index, len(targets), crop)
        evidence_total += _gather_for_crop(store, run, crop, adapters, errors)

    enabled_sources = sorted(
        {*run.enabled_sources, *(adapter.source_name for adapter in adapters)}
    )
    warnings = [
        warning
        for warning in run.warnings
        if warning not in {"source_matching_not_connected", "market_pricing_not_connected"}
    ]
    if "market_evidence_gathered" not in warnings:
        warnings.append("market_evidence_gathered")

    updated = replace(
        run,
        enabled_sources=enabled_sources,
        settings={
            **run.settings,
            "source_matching": "connected",
            "market_pricing": "evidence_only",
            "market_evidence": {
                "sources": [adapter.source_name for adapter in adapters],
                "crops_processed": len(targets),
                "evidence_record_count": evidence_total,
                "last_gathered_at": utc_now(),
            },
        },
        warnings=warnings,
        errors=errors,
    )
    return store.update_evaluation_run(updated)


def _gather_for_crop(
    store: PhilalensStore,
    run: EvaluationRunRecord,
    crop: StampCrop,
    adapters: list[SourceAdapter],
    errors: list[str],
) -> int:
    previous = store.get_stamp_valuation_for_crop(run.run_id, crop.crop_id)
    candidates = store.list_catalog_candidates_for_crop(run.run_id, crop.crop_id)
    top_candidate = min(candidates, key=lambda candidate: candidate.rank, default=None)
    query = _query_from_candidate(top_candidate)

    if not query.has_identity():
        store.add_stamp_valuation(
            _updated_valuation(
                run.run_id,
                crop,
                previous,
                evidence_records=[],
                no_range_reason=(
                    "No identity candidate to search with; run Tier 1 identification "
                    "or review the crop first."
                ),
            )
        )
        return 0

    evidence_records: list[SourceEvidenceRecord] = []
    failed_sources: list[str] = []
    for adapter in adapters:
        try:
            items = adapter.fetch_evidence(query)
        except SourceAdapterError as exc:
            errors.append(f"{crop.crop_id}: {exc}")
            failed_sources.append(adapter.source_name)
            continue
        for item in items:
            evidence_records.append(
                store.add_source_evidence(
                    _evidence_record(run.run_id, crop.crop_id, top_candidate, item)
                )
            )

    store.add_stamp_valuation(
        _updated_valuation(
            run.run_id,
            crop,
            previous,
            evidence_records=evidence_records,
            failed_sources=failed_sources,
        )
    )
    return len(evidence_records)


def _latest_valuations_per_crop(
    store: PhilalensStore, run_id: str
) -> list[StampValuationRecord]:
    latest: dict[str, StampValuationRecord] = {}
    for valuation in store.list_stamp_valuations_for_run(run_id):
        latest[valuation.crop_id] = valuation
    return list(latest.values())


def _query_from_candidate(candidate: CatalogCandidateRecord | None) -> EvidenceQuery:
    if candidate is None:
        return EvidenceQuery()
    catalog_hint = next(
        (
            note.removeprefix(_CATALOG_HINT_PREFIX).strip()
            for note in candidate.variant_notes
            if note.startswith(_CATALOG_HINT_PREFIX)
        ),
        None,
    )
    return EvidenceQuery(
        issuer=candidate.issuer,
        series_title=candidate.title,
        year=candidate.year,
        denomination=candidate.denomination,
        catalog_hint=catalog_hint,
    )


def _evidence_record(
    run_id: str,
    crop_id: str,
    candidate: CatalogCandidateRecord | None,
    item: EvidenceItem,
) -> SourceEvidenceRecord:
    return SourceEvidenceRecord(
        evidence_id=new_id("evid"),
        run_id=run_id,
        crop_id=crop_id,
        candidate_id=candidate.candidate_id if candidate else None,
        source_name=item.source_name,
        source_type=item.source_type,
        source_url=item.source_url,
        local_reference_id=item.local_reference_id,
        matched_fields=item.matched_fields,
        price=item.price,
        price_low=item.price_low,
        price_high=item.price_high,
        currency=item.currency,
        condition_assumptions=item.condition_assumptions,
        evidence_tier=item.evidence_tier,
        confidence=item.confidence,
        license_notes=item.license_notes,
        raw_payload=item.raw_payload,
    )


def _updated_valuation(
    run_id: str,
    crop: StampCrop,
    previous: StampValuationRecord | None,
    evidence_records: list[SourceEvidenceRecord],
    no_range_reason: str | None = None,
    failed_sources: list[str] | None = None,
) -> StampValuationRecord:
    realized_prices = _prices(evidence_records, TIER_REALIZED_SALE)
    asking_prices = _prices(evidence_records, TIER_ACTIVE_LISTING_WEAK)
    identity_confidence = previous.identity_confidence if previous else 0.0

    value_low: float | None = None
    value_high: float | None = None
    currency = previous.currency if previous else "USD"
    if no_range_reason is None:
        if len(realized_prices) >= MIN_REALIZED_SALE_PRICES:
            if identity_confidence >= MIN_IDENTITY_CONFIDENCE_FOR_RANGE:
                prices = [price for price, _ in realized_prices]
                value_low = min(prices)
                value_high = max(prices)
                currency = realized_prices[0][1] or currency
            else:
                no_range_reason = (
                    "Realized-sale prices found, but identity confidence "
                    f"({identity_confidence:.2f}) is below "
                    f"{MIN_IDENTITY_CONFIDENCE_FOR_RANGE:.2f}; confirm the identification "
                    "before trusting a range."
                )
        elif asking_prices:
            no_range_reason = (
                "Only active-listing asking prices were found. Asking prices are weak "
                "evidence and never set a value range on their own."
            )
        elif evidence_records:
            no_range_reason = (
                "Only reference metadata was found; no sale or listing prices to "
                "support a range."
            )
        else:
            no_range_reason = "No market or reference evidence was found for this identity."

    assumptions = [
        assumption
        for assumption in (previous.assumptions if previous else [])
        if not assumption.startswith(("Value range:", "No value range:", "Asking-price context:"))
    ]
    if value_low is not None and value_high is not None:
        assumptions.append(
            f"Value range: from {len(realized_prices)} realized-sale price points; "
            "condition and variant assumptions remain unverified."
        )
    else:
        assumptions.append(f"No value range: {no_range_reason}")
    if asking_prices:
        low = min(price for price, _ in asking_prices)
        high = max(price for price, _ in asking_prices)
        asking_currency = asking_prices[0][1] or "?"
        assumptions.append(
            f"Asking-price context: {len(asking_prices)} active listings asking "
            f"{low:g}-{high:g} {asking_currency}; weak evidence, not an estimate."
        )
    if failed_sources:
        assumptions.append(
            f"Evidence sources unavailable during this pass: {', '.join(failed_sources)}."
        )

    uncertainty_warnings = [
        warning
        for warning in (previous.uncertainty_warnings if previous else [])
        if warning != "market_evidence_not_checked"
    ]
    if value_low is None:
        uncertainty_warnings.append("no_evidence_backed_value_range")
    if asking_prices and not realized_prices:
        uncertainty_warnings.append("asking_prices_only_weak_evidence")

    if value_low is not None:
        market_confidence = 0.6
        next_action = "review evidence; consider expert review before acting on the range"
    elif asking_prices:
        market_confidence = 0.2
        next_action = "review listings; seek realized-sale evidence or expert review"
    elif evidence_records:
        market_confidence = 0.1
        next_action = "review reference matches; identity needs confirmation"
    else:
        market_confidence = 0.0
        next_action = (
            previous.recommended_next_action if previous else None
        ) or "gather market evidence"

    return StampValuationRecord(
        valuation_id=new_id("val"),
        run_id=run_id,
        crop_id=crop.crop_id,
        candidate_id=previous.candidate_id if previous else None,
        estimated_value_low=value_low,
        estimated_value_high=value_high,
        currency=currency,
        identity_confidence=identity_confidence,
        condition_confidence=previous.condition_confidence if previous else 0.0,
        market_evidence_confidence=market_confidence,
        valuation_confidence=round(
            min(identity_confidence, market_confidence) if value_low is not None else
            (previous.valuation_confidence if previous else 0.0),
            2,
        ),
        value_bucket=previous.value_bucket if previous else "not_enough_evidence",
        assumptions=assumptions,
        uncertainty_warnings=uncertainty_warnings,
        recommended_next_action=next_action,
        evidence_ids=[record.evidence_id for record in evidence_records],
    )


def _prices(
    evidence_records: list[SourceEvidenceRecord], tier: str
) -> list[tuple[float, str | None]]:
    return [
        (record.price, record.currency)
        for record in evidence_records
        if record.evidence_tier == tier and record.price is not None
    ]
