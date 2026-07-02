from pathlib import Path
from typing import Any, cast

from philalens.evaluation import evaluate_collection_readiness
from philalens.exports import build_collection_export, build_evaluation_run_export
from philalens.models import (
    REVIEW_NEEDS_CROP_REVIEW,
    PageImageRecord,
    StampCrop,
    StampObservationRecord,
)
from philalens.storage import PhilalensStore
from philalens.vision import VisionObservationError


class FakeVisionAdapter:
    adapter_name = "fake_vision"
    model_name: str | None = "fake-vision-model"

    def __init__(self) -> None:
        self.seen_crop_ids: list[str] = []

    def observe_crop(self, crop: StampCrop, run_id: str) -> StampObservationRecord:
        self.seen_crop_ids.append(crop.crop_id)
        return StampObservationRecord(
            observation_id=f"obs_{crop.crop_id}",
            run_id=run_id,
            crop_id=crop.crop_id,
            visible_text=["FRANCE", "25"],
            issuer_hint="France",
            denomination_hint="25c",
            design_subject="Sower",
            cancellation_state="used_light_cancel",
            condition_notes=["used"],
            confidence=0.74,
            model_metadata={
                "adapter": self.adapter_name,
                "model_name": self.model_name,
                "api_usage": {
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "cached_input_tokens": 0,
                    "total_tokens": 1500,
                },
                "api_cost": {"total_cost_usd": 0.0012},
            },
        )


class FailingVisionAdapter:
    adapter_name = "failing_vision"
    model_name: str | None = "failing-vision-model"

    def observe_crop(self, crop: StampCrop, run_id: str) -> StampObservationRecord:
        raise VisionObservationError("invalid structured output")


def test_evaluate_collection_readiness_creates_run_and_buckets(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = store.create_collection(title="evaluation fixture")
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
    store.replace_page_crops(
        page.page_id,
        [
            StampCrop(
                crop_id="crop_clean",
                page_id=page.page_id,
                crop_index=1,
                bbox_xywh=(10, 20, 100, 120),
                crop_path=str(tmp_path / "clean.jpg"),
                segmentation_confidence=0.88,
            ),
            StampCrop(
                crop_id="crop_review",
                page_id=page.page_id,
                crop_index=2,
                bbox_xywh=(140, 20, 100, 120),
                crop_path=str(tmp_path / "review.jpg"),
                segmentation_confidence=0.42,
                review_state=REVIEW_NEEDS_CROP_REVIEW,
                warnings=["low_detector_confidence"],
            ),
        ],
    )

    run = evaluate_collection_readiness(store, collection.collection_id)

    assert run is not None
    assert run.status == "completed"
    assert run.pipeline_version == "crop-readiness-skeleton-v1"
    assert "crop_review_remaining" in run.warnings

    valuations = store.list_stamp_valuations_for_run(run.run_id)
    buckets = {valuation.crop_id: valuation.value_bucket for valuation in valuations}
    actions = {valuation.crop_id: valuation.recommended_next_action for valuation in valuations}
    assert buckets == {
        "crop_clean": "not_enough_evidence",
        "crop_review": "needs_better_image",
    }
    assert actions["crop_review"] == "review crop"

    observations = store.list_stamp_observations_for_run(run.run_id)
    review_observation = next(item for item in observations if item.crop_id == "crop_review")
    assert "crop_review_required" in review_observation.image_quality_warnings
    assert "watermark" in review_observation.unobservable_factors

    collection_export = build_collection_export(store, collection.collection_id)
    assert collection_export is not None
    collection_summary = cast(dict[str, Any], collection_export["latest_evaluation_summary"])
    assert collection_summary["value_bucket_counts"] == {
        "needs_better_image": 1,
        "not_enough_evidence": 1,
    }

    run_export = build_evaluation_run_export(store, run.run_id)
    assert run_export is not None
    run_summary = cast(dict[str, Any], run_export["summary"])
    assert run_summary["crop_review_remaining"] == 1
    assert run_summary["attention_recommended_count"] == 0


def test_evaluate_collection_readiness_uses_optional_vision_adapter(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = store.create_collection(title="evaluation fixture")
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
    store.replace_page_crops(
        page.page_id,
        [
            StampCrop(
                crop_id="crop_clean",
                page_id=page.page_id,
                crop_index=1,
                bbox_xywh=(10, 20, 100, 120),
                crop_path=str(tmp_path / "clean.jpg"),
                segmentation_confidence=0.88,
            ),
            StampCrop(
                crop_id="crop_review",
                page_id=page.page_id,
                crop_index=2,
                bbox_xywh=(140, 20, 100, 120),
                crop_path=str(tmp_path / "review.jpg"),
                segmentation_confidence=0.42,
                review_state=REVIEW_NEEDS_CROP_REVIEW,
            ),
        ],
    )
    adapter = FakeVisionAdapter()

    run = evaluate_collection_readiness(store, collection.collection_id, vision_adapter=adapter)

    assert run is not None
    assert adapter.seen_crop_ids == ["crop_clean"]
    assert run.vision_model == "fake-vision-model"
    assert run.settings["ai_vision"] == "fake_vision"
    assert run.settings["cost_estimate"]["provider"] == "fake_vision"
    assert run.settings["cost_actual"]["api_call_count"] == 1
    assert run.settings["cost_actual"]["known_total_cost_usd"] == 0.0012
    assert "ai_vision_not_connected" not in run.warnings
    assert "ai_vision_skipped_for_crop_review" in run.warnings

    observations = {
        observation.crop_id: observation
        for observation in store.list_stamp_observations_for_run(run.run_id)
    }
    assert observations["crop_clean"].issuer_hint == "France"
    assert observations["crop_clean"].model_metadata["adapter"] == "fake_vision"
    assert "crop_review_required" in observations["crop_review"].image_quality_warnings

    valuations = {
        valuation.crop_id: valuation
        for valuation in store.list_stamp_valuations_for_run(run.run_id)
    }
    assert valuations["crop_clean"].value_bucket == "likely_common"
    assert valuations["crop_clean"].recommended_next_action == "spot-check with source matching"
    assert (
        "triage_cannot_rule_out_valuable_variants" in valuations["crop_clean"].uncertainty_warnings
    )
    assert valuations["crop_clean"].valuation_confidence > 0
    assert valuations["crop_review"].recommended_next_action == "review crop"


def test_evaluate_collection_readiness_records_vision_failures(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = store.create_collection(title="evaluation fixture")
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
    store.replace_page_crops(
        page.page_id,
        [
            StampCrop(
                crop_id="crop_clean",
                page_id=page.page_id,
                crop_index=1,
                bbox_xywh=(10, 20, 100, 120),
                crop_path=str(tmp_path / "clean.jpg"),
                segmentation_confidence=0.88,
            )
        ],
    )

    run = evaluate_collection_readiness(
        store,
        collection.collection_id,
        vision_adapter=FailingVisionAdapter(),
    )

    assert run is not None
    assert run.errors == ["crop_clean: invalid structured output"]
    assert "ai_vision_failed_on_some_crops" in run.warnings
    assert "ai_vision_produced_no_observations" in run.warnings

    observation = store.list_stamp_observations_for_run(run.run_id)[0]
    assert "ai_vision_failed" in observation.image_quality_warnings

    valuation = store.list_stamp_valuations_for_run(run.run_id)[0]
    assert valuation.recommended_next_action == "rerun observation extraction"
    assert "vision_extraction_failed" in valuation.uncertainty_warnings
    assert "vision_adapter_not_connected" not in valuation.uncertainty_warnings
