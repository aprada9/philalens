from pathlib import Path

import pytest

from philalens.ai_estimate import (
    AI_ESTIMATE_PREFIX,
    ValueEstimationError,
    estimate_flagged_values,
)
from philalens.market_evidence import MarketEvidenceError
from philalens.storage import PhilalensStore

from test_market_evidence import _setup_collection


class FakeEstimator:
    model_name = "fake-estimator"

    def __init__(self, payload: dict | None = None, fail: bool = False) -> None:
        self.payload = payload or {
            "value_low": 2.0,
            "value_high": 12.0,
            "currency": "EUR",
            "confidence": 0.55,
            "rationale": "Common commemorative; bulk pricing applies.",
            "rarity_notes": "The 1959 set has no valuable varieties; color shades are minor.",
            "recommended_action": "check_sold_listings",
        }
        self.fail = fail
        self.contexts: list[str] = []

    def estimate(self, context: str, crop_image_path: Path) -> dict:
        if self.fail:
            raise ValueEstimationError("model unavailable")
        self.contexts.append(context)
        return dict(self.payload)


def test_ai_estimate_records_labeled_unverified_range(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(
        tmp_path, {"crop_a": "likely_common", "crop_b": "investigate"}
    )
    estimator = FakeEstimator()

    result = estimate_flagged_values(store, collection.collection_id, estimator)

    assert result == {"estimated_count": 1, "target_count": 1, "errors": []}
    # Context carries the identification for the model to reason over.
    assert "Velazquez series" in estimator.contexts[0]

    valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_b")
    assert valuation.estimated_value_low == 2.0
    assert valuation.estimated_value_high == 12.0
    assert valuation.currency == "EUR"
    assert valuation.value_bucket == "investigate"  # bucket unchanged
    assert valuation.market_evidence_confidence <= 0.4
    assert any(item.startswith(AI_ESTIMATE_PREFIX) for item in valuation.assumptions)
    assert any(item.startswith("Rarity check:") for item in valuation.assumptions)
    assert "ai_estimated_range_unverified" in valuation.uncertainty_warnings
    assert "sold listings" in (valuation.recommended_next_action or "")
    # The untouched common crop keeps its original valuation.
    assert (
        store.get_stamp_valuation_for_crop(run.run_id, "crop_a").valuation_id == "val_crop_a"
    )


def test_ai_estimate_failures_are_reported_not_fatal(tmp_path: Path) -> None:
    store, collection, run = _setup_collection(tmp_path, {"crop_b": "investigate"})
    result = estimate_flagged_values(
        store, collection.collection_id, FakeEstimator(fail=True)
    )
    assert result["estimated_count"] == 0
    assert len(result["errors"]) == 1
    # No half-written estimate: the previous valuation still stands.
    assert store.get_stamp_valuation_for_crop(run.run_id, "crop_b").valuation_id == "val_crop_b"


def test_ai_estimate_requires_completed_run(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = store.create_collection(title="no runs")
    with pytest.raises(MarketEvidenceError, match="Tier 1"):
        estimate_flagged_values(store, collection.collection_id, FakeEstimator())
