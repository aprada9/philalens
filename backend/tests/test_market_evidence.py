from pathlib import Path

import pytest

from philalens.exports import build_evaluation_summary
from philalens.market_evidence import (
    MarketEvidenceError,
    gather_market_evidence,
)
from philalens.models import (
    CatalogCandidateRecord,
    PageImageRecord,
    StampCrop,
    StampValuationRecord,
)
from philalens.sources import (
    TIER_ACTIVE_LISTING_WEAK,
    TIER_REALIZED_SALE,
    TIER_REFERENCE_METADATA,
    EvidenceItem,
    EvidenceQuery,
    SourceAdapterError,
)
from philalens.storage import PhilalensStore


class FakeAdapter:
    def __init__(self, source_name: str, items: list[EvidenceItem]) -> None:
        self.source_name = source_name
        self.items = items
        self.queries: list[EvidenceQuery] = []

    def fetch_evidence(self, query: EvidenceQuery) -> list[EvidenceItem]:
        self.queries.append(query)
        return self.items


class FailingAdapter:
    source_name = "broken_source"

    def fetch_evidence(self, query: EvidenceQuery) -> list[EvidenceItem]:
        raise SourceAdapterError("broken_source: request failed")


def _reference_item() -> EvidenceItem:
    return EvidenceItem(
        source_name="wikidata",
        source_type="open_reference",
        evidence_tier=TIER_REFERENCE_METADATA,
        confidence=0.3,
        source_url="https://www.wikidata.org/wiki/Q1",
    )


def _listing_item(price: float) -> EvidenceItem:
    return EvidenceItem(
        source_name="ebay_browse",
        source_type="marketplace_listing",
        evidence_tier=TIER_ACTIVE_LISTING_WEAK,
        confidence=0.25,
        price=price,
        currency="USD",
        source_url="https://www.ebay.com/itm/1",
    )


def _sale_item(price: float) -> EvidenceItem:
    return EvidenceItem(
        source_name="future_sales_source",
        source_type="marketplace_sale",
        evidence_tier=TIER_REALIZED_SALE,
        confidence=0.5,
        price=price,
        currency="EUR",
    )


def _setup_collection(tmp_path: Path, buckets: dict[str, str], identity_confidence: float = 0.8):
    """Create a collection with one crop per bucket and a completed Tier 1 run."""
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = store.create_collection(title="evidence fixture")
    page = PageImageRecord(
        page_id="page_1",
        collection_id=collection.collection_id,
        page_order=1,
        original_filename="album.jpg",
        original_path=str(tmp_path / "album.jpg"),
        normalized_path=str(tmp_path / "normalized.jpg"),
        image_format="JPEG",
        width=1200,
        height=900,
    )
    store.add_page(page)
    crops = [
        StampCrop(
            crop_id=crop_id,
            page_id=page.page_id,
            crop_index=index,
            bbox_xywh=(10 + index * 100, 10, 90, 110),
            crop_path=str(tmp_path / f"{crop_id}.jpg"),
            segmentation_confidence=0.9,
        )
        for index, crop_id in enumerate(buckets, start=1)
    ]
    store.replace_page_crops(page.page_id, crops)

    run = store.create_evaluation_run(
        collection_id=collection.collection_id,
        pipeline_version="tier1-identification-v2",
        status="completed",
        enabled_sources=[],
        settings={"mode": "crop_readiness_only"},
    )
    for crop_id, bucket in buckets.items():
        candidate = store.add_catalog_candidate(
            CatalogCandidateRecord(
                candidate_id=f"cand_{crop_id}",
                run_id=run.run_id,
                crop_id=crop_id,
                source_name="ai_vision_prior",
                issuer="Spain",
                title="Velazquez series",
                year=1959,
                denomination="1 peseta",
                variant_notes=["catalog_hint (unverified): Edifil ~1238-1247"],
                match_score=identity_confidence,
                rank=1,
            )
        )
        store.add_stamp_valuation(
            StampValuationRecord(
                valuation_id=f"val_{crop_id}",
                run_id=run.run_id,
                crop_id=crop_id,
                candidate_id=candidate.candidate_id,
                identity_confidence=identity_confidence,
                valuation_confidence=0.5,
                value_bucket=bucket,
                uncertainty_warnings=["market_evidence_not_checked"],
                recommended_next_action="gather market evidence",
            )
        )
    return store, collection, run


def test_targets_only_attention_buckets_by_default(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(
        tmp_path,
        {"crop_a": "likely_common", "crop_b": "investigate", "crop_c": "possibly_interesting"},
    )
    adapter = FakeAdapter("wikidata", [_reference_item()])

    updated = gather_market_evidence(store, collection.collection_id, [adapter])

    assert updated is not None
    assert len(adapter.queries) == 2
    assert updated.settings["market_evidence"]["crops_processed"] == 2
    assert updated.settings["market_evidence"]["evidence_record_count"] == 2
    assert "wikidata" in updated.enabled_sources
    assert "market_evidence_gathered" in updated.warnings
    # The common crop keeps its single Tier 1 valuation.
    assert store.get_stamp_valuation_for_crop(run.run_id, "crop_a").valuation_id == "val_crop_a"


def test_asking_prices_never_set_a_range(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(tmp_path, {"crop_b": "investigate"})
    adapter = FakeAdapter("ebay_browse", [_listing_item(2.5), _listing_item(15.0)])

    gather_market_evidence(store, collection.collection_id, [adapter])

    valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_b")
    assert valuation.estimated_value_low is None
    assert valuation.estimated_value_high is None
    assert valuation.value_bucket == "investigate"
    assert len(valuation.evidence_ids) == 2
    assert "asking_prices_only_weak_evidence" in valuation.uncertainty_warnings
    assert "market_evidence_not_checked" not in valuation.uncertainty_warnings
    assert any(item.startswith("No value range:") for item in valuation.assumptions)
    assert any(item.startswith("Asking-price context:") for item in valuation.assumptions)
    evidence = store.list_source_evidence_for_crop(run.run_id, "crop_b")
    assert {record.price for record in evidence} == {2.5, 15.0}
    assert all(record.candidate_id == "cand_crop_b" for record in evidence)


def test_realized_sales_with_confident_identity_produce_a_range(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(tmp_path, {"crop_b": "investigate"})
    adapter = FakeAdapter("future_sales_source", [_sale_item(4.0), _sale_item(9.0)])

    gather_market_evidence(store, collection.collection_id, [adapter])

    valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_b")
    assert valuation.estimated_value_low == 4.0
    assert valuation.estimated_value_high == 9.0
    assert valuation.currency == "EUR"
    assert valuation.market_evidence_confidence == 0.6
    assert "no_evidence_backed_value_range" not in valuation.uncertainty_warnings


def test_low_identity_confidence_withholds_the_range(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(
        tmp_path, {"crop_b": "investigate"}, identity_confidence=0.3
    )
    adapter = FakeAdapter("future_sales_source", [_sale_item(4.0), _sale_item(9.0)])

    gather_market_evidence(store, collection.collection_id, [adapter])

    valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_b")
    assert valuation.estimated_value_low is None
    assert any("identity confidence" in item for item in valuation.assumptions)


def test_crop_without_candidates_gets_explicit_gap(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(tmp_path, {"crop_b": "investigate"})
    # Strip the candidate rows so the crop has no identity to search with.
    with store._connect() as connection:
        connection.execute("DELETE FROM catalog_candidates")
    adapter = FakeAdapter("wikidata", [_reference_item()])

    gather_market_evidence(store, collection.collection_id, [adapter])

    assert adapter.queries == []
    valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_b")
    assert valuation.estimated_value_low is None
    assert any("No identity candidate" in item for item in valuation.assumptions)


def test_failed_source_is_recorded_and_others_continue(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(tmp_path, {"crop_b": "investigate"})
    good = FakeAdapter("wikidata", [_reference_item()])

    updated = gather_market_evidence(
        store, collection.collection_id, [FailingAdapter(), good]
    )

    assert any("broken_source" in error for error in updated.errors)
    valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_b")
    assert len(valuation.evidence_ids) == 1
    assert any("broken_source" in item for item in valuation.assumptions)


def test_requires_a_completed_run(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = store.create_collection(title="no runs yet")

    with pytest.raises(MarketEvidenceError, match="Tier 1"):
        gather_market_evidence(store, collection.collection_id, [])


def test_unknown_crop_selection_fails(tmp_path: Path) -> None:
    store, collection, _run = _setup_collection(tmp_path, {"crop_b": "investigate"})

    with pytest.raises(MarketEvidenceError, match="missing_crop"):
        gather_market_evidence(
            store, collection.collection_id, [], crop_ids=["missing_crop"]
        )


def test_summary_counts_latest_valuation_per_crop(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(
        tmp_path, {"crop_a": "likely_common", "crop_b": "investigate"}
    )
    adapter = FakeAdapter("wikidata", [_reference_item()])
    gather_market_evidence(store, collection.collection_id, [adapter])

    summary = build_evaluation_summary(store, run.run_id)
    assert summary is not None
    # crop_b now has two valuation records in the run; the summary must not
    # double count it.
    assert summary["evaluated_stamp_count"] == 2
    assert summary["value_bucket_counts"] == {"investigate": 1, "likely_common": 1}


def test_regathering_replaces_previous_evidence(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(tmp_path, {"crop_b": "investigate"})
    adapter = FakeAdapter("ebay_browse", [_listing_item(2.5), _listing_item(15.0)])

    gather_market_evidence(store, collection.collection_id, [adapter], crop_ids=["crop_b"])
    gather_market_evidence(store, collection.collection_id, [adapter], crop_ids=["crop_b"])

    evidence = store.list_source_evidence_for_crop(run.run_id, "crop_b")
    assert len(evidence) == 2  # replaced, not accumulated
    valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_b")
    assert len(valuation.evidence_ids) == 2
    assert (
        sum(1 for item in valuation.assumptions if item.startswith("No value range:")) == 1
    )

    # A failed pass must not wipe evidence gathered earlier.
    gather_market_evidence(
        store, collection.collection_id, [FailingAdapter()], crop_ids=["crop_b"]
    )
    assert len(store.list_source_evidence_for_crop(run.run_id, "crop_b")) == 2
