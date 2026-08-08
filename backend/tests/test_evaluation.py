from pathlib import Path
from typing import Any, cast

import pytest

import philalens.evaluation
from philalens.evaluation import evaluate_collection_readiness
from philalens.exports import build_collection_export, build_evaluation_run_export
from philalens.models import (
    EVALUATION_STATUS_RUNNING,
    REVIEW_NEEDS_CROP_REVIEW,
    CatalogCandidateRecord,
    PageImageRecord,
    StampCrop,
    StampObservationRecord,
)
from philalens.observation_schema import VisionAnalysisResult
from philalens.storage import PhilalensStore
from philalens.vision import VisionObservationError


@pytest.fixture(autouse=True)
def _no_retry_backoff(monkeypatch) -> None:
    monkeypatch.setattr(philalens.evaluation, "VISION_RETRY_BACKOFF_SECONDS", ())


class FakeVisionAdapter:
    adapter_name = "fake_vision"
    model_name: str | None = "fake-vision-model"

    def __init__(self) -> None:
        self.seen_crop_ids: list[str] = []

    def observe_crop(self, crop: StampCrop, run_id: str) -> VisionAnalysisResult:
        self.seen_crop_ids.append(crop.crop_id)
        return VisionAnalysisResult(
            observation=StampObservationRecord(
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
        )


class FakeV2VisionAdapter(FakeVisionAdapter):
    adapter_name = "fake_vision_v2"

    def __init__(self, bucket: str = "possibly_interesting") -> None:
        super().__init__()
        self.bucket = bucket

    def observe_crop(self, crop: StampCrop, run_id: str) -> VisionAnalysisResult:
        base = super().observe_crop(crop, run_id)
        candidate = CatalogCandidateRecord(
            candidate_id=f"cand_{crop.crop_id}",
            run_id=run_id,
            crop_id=crop.crop_id,
            source_name="ai_vision_prior",
            issuer="France",
            title="Sower definitives",
            year=1907,
            denomination="25c",
            variant_notes=["catalog_hint (unverified): Yvert Sower range"],
            match_score=0.8,
            rank=1,
            contradiction_warnings=["ai_prior_without_source_evidence"],
        )
        return VisionAnalysisResult(
            observation=base.observation,
            candidates=[candidate],
            prior_value_bucket=self.bucket,
            prior_value_rationale="Early period issue with light cancel.",
        )


class FailingVisionAdapter:
    adapter_name = "failing_vision"
    model_name: str | None = "failing-vision-model"

    def observe_crop(self, crop: StampCrop, run_id: str) -> VisionAnalysisResult:
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
    assert run.pipeline_version == "tier1-identification-v2"
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


class FlakyVisionAdapter(FakeVisionAdapter):
    adapter_name = "flaky_vision"

    def __init__(self, failures_before_success: int) -> None:
        super().__init__()
        self.remaining_failures = failures_before_success

    def observe_crop(self, crop: StampCrop, run_id: str) -> VisionAnalysisResult:
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise VisionObservationError("transient provider error")
        return super().observe_crop(crop, run_id)


def _collection_with_clean_crops(store: PhilalensStore, tmp_path: Path, crop_ids: list[str]):
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
                crop_id=crop_id,
                page_id=page.page_id,
                crop_index=index,
                bbox_xywh=(10 + 130 * index, 20, 100, 120),
                crop_path=str(tmp_path / f"{crop_id}.jpg"),
                segmentation_confidence=0.88,
            )
            for index, crop_id in enumerate(crop_ids, start=1)
        ],
    )
    return collection


def test_vision_calls_retry_transient_failures(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(philalens.evaluation, "VISION_RETRY_BACKOFF_SECONDS", (0.0, 0.0))
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = _collection_with_clean_crops(store, tmp_path, ["crop_clean"])
    adapter = FlakyVisionAdapter(failures_before_success=2)

    run = evaluate_collection_readiness(store, collection.collection_id, vision_adapter=adapter)

    assert run is not None
    assert run.errors == []
    assert adapter.seen_crop_ids == ["crop_clean"]
    observations = store.list_stamp_observations_for_run(run.run_id)
    assert observations[0].issuer_hint == "France"


def test_resume_skips_crops_already_processed_in_run(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = _collection_with_clean_crops(store, tmp_path, ["crop_done", "crop_pending"])

    interrupted = store.create_evaluation_run(
        collection_id=collection.collection_id,
        pipeline_version="crop-readiness-skeleton-v1",
        status=EVALUATION_STATUS_RUNNING,
        enabled_sources=[],
        settings={"crop_scope": "collection", "selected_crop_ids": []},
        vision_model="fake-vision-model",
    )
    adapter = FakeVisionAdapter()
    # Simulate the checkpoint left by a killed run: crop_done fully processed.
    done_analysis = adapter.observe_crop(_crop(store, "crop_done"), interrupted.run_id)
    store.add_stamp_observation(done_analysis.observation)
    store.add_stamp_valuation(
        philalens.evaluation._readiness_valuation(
            interrupted.run_id,
            _crop(store, "crop_done"),
            vision_observation_status="available",
            analysis=done_analysis,
        )
    )
    adapter.seen_crop_ids.clear()

    assert store.mark_interrupted_evaluation_runs() == 1
    assert store.get_evaluation_run(interrupted.run_id).status == "interrupted"

    run = evaluate_collection_readiness(
        store,
        collection.collection_id,
        vision_adapter=adapter,
        resume_run_id=interrupted.run_id,
    )

    assert run is not None
    assert run.run_id == interrupted.run_id
    assert run.status == "completed"
    assert adapter.seen_crop_ids == ["crop_pending"]
    assert "run_resumed_after_interruption" in run.warnings
    valuations = store.list_stamp_valuations_for_run(run.run_id)
    assert {valuation.crop_id for valuation in valuations} == {"crop_done", "crop_pending"}


def _crop(store: PhilalensStore, crop_id: str) -> StampCrop:
    crop = store.get_crop(crop_id)
    assert crop is not None
    return crop


def test_v2_adapter_stores_candidates_and_prior_bucket(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = _collection_with_clean_crops(store, tmp_path, ["crop_clean"])
    adapter = FakeV2VisionAdapter(bucket="investigate")

    run = evaluate_collection_readiness(store, collection.collection_id, vision_adapter=adapter)

    assert run is not None
    candidates = store.list_catalog_candidates_for_crop(run.run_id, "crop_clean")
    assert len(candidates) == 1
    assert candidates[0].source_name == "ai_vision_prior"
    assert candidates[0].issuer == "France"

    valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_clean")
    assert valuation is not None
    assert valuation.value_bucket == "investigate"
    assert valuation.identity_confidence == 0.8
    assert valuation.candidate_id == candidates[0].candidate_id
    assert valuation.recommended_next_action == (
        "gather market evidence and consider expert review"
    )
    assert "ai_prior_identity_unverified" in valuation.uncertainty_warnings
    assert any("Model rationale" in assumption for assumption in valuation.assumptions)
    assert valuation.estimated_value_low is None
    assert run.settings["vision_api_call_count"] == 1


def _write_test_image(path: Path, color: tuple[int, int, int], seed: int = 0) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (80, 100), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle([10 + seed, 10, 60, 50], fill=(255 - color[0], 120, 90))
    draw.rectangle([20, 60 + seed, 70, 90], fill=(30, 30, 30))
    image.save(path, "JPEG", quality=92)


def test_duplicate_crops_share_one_vision_call(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = _collection_with_clean_crops(
        store, tmp_path, ["crop_a", "crop_a_dup", "crop_b"]
    )
    # crop_a and crop_a_dup are pixel-identical; crop_b is clearly different.
    _write_test_image(tmp_path / "crop_a.jpg", (200, 40, 40))
    _write_test_image(tmp_path / "crop_a_dup.jpg", (200, 40, 40))
    _write_test_image(tmp_path / "crop_b.jpg", (40, 60, 210), seed=8)

    adapter = FakeV2VisionAdapter(bucket="likely_common")
    run = evaluate_collection_readiness(store, collection.collection_id, vision_adapter=adapter)

    assert run is not None
    assert adapter.seen_crop_ids == ["crop_a", "crop_b"]
    assert run.settings["vision_api_call_count"] == 2
    assert run.settings["duplicate_derived_count"] == 1
    assert "duplicate_crops_shared_vision_results" in run.warnings

    observations = {
        observation.crop_id: observation
        for observation in store.list_stamp_observations_for_run(run.run_id)
    }
    assert observations["crop_a_dup"].issuer_hint == "France"
    assert observations["crop_a_dup"].model_metadata["derived_from_duplicate"] == "crop_a"
    assert "derived_from_duplicate" not in observations["crop_a"].model_metadata

    derived_candidates = store.list_catalog_candidates_for_crop(run.run_id, "crop_a_dup")
    assert len(derived_candidates) == 1
    assert "derived_from_duplicate_crop" in derived_candidates[0].contradiction_warnings

    derived_valuation = store.get_stamp_valuation_for_crop(run.run_id, "crop_a_dup")
    assert derived_valuation is not None
    assert derived_valuation.value_bucket == "likely_common"
    assert "derived_from_duplicate_crop" in derived_valuation.uncertainty_warnings


def test_cancelled_run_saves_progress_and_resumes(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = _collection_with_clean_crops(
        store, tmp_path, ["crop_one", "crop_two", "crop_three"]
    )
    adapter = FakeVisionAdapter()

    def cancel_after_first(current: int, total: int, crop: StampCrop) -> None:
        if current > 1:
            raise philalens.evaluation.EvaluationCancelledError()

    run = evaluate_collection_readiness(
        store,
        collection.collection_id,
        vision_adapter=adapter,
        progress_callback=cancel_after_first,
    )

    assert run is not None
    assert run.status == "interrupted"
    assert "run_cancelled_by_user" in run.warnings
    # The first crop was fully processed and checkpointed before the stop.
    assert adapter.seen_crop_ids == ["crop_one"]
    valuations = store.list_stamp_valuations_for_run(run.run_id)
    assert {valuation.crop_id for valuation in valuations} == {"crop_one"}

    adapter.seen_crop_ids.clear()
    resumed = evaluate_collection_readiness(
        store,
        collection.collection_id,
        vision_adapter=adapter,
        resume_run_id=run.run_id,
    )

    assert resumed is not None
    assert resumed.status == "completed"
    assert adapter.seen_crop_ids == ["crop_two", "crop_three"]
    valuations = store.list_stamp_valuations_for_run(resumed.run_id)
    assert {valuation.crop_id for valuation in valuations} == {
        "crop_one",
        "crop_two",
        "crop_three",
    }
