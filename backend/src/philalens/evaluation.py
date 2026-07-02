"""Conservative collection evaluation skeleton.

This module creates a durable evaluation run before AI vision, source adapters,
or pricing logic are connected. It records crop readiness and explicit
"not enough evidence" valuation buckets so the browser can exercise the
evaluation workflow without pretending identification has happened.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .costing import (
    estimate_openai_vision_run_cost,
    non_openai_cost_estimate,
    summarize_observation_costs,
)
from .models import (
    EVALUATION_STATUS_COMPLETED,
    EVALUATION_STATUS_RUNNING,
    REVIEW_NEEDS_CROP_REVIEW,
    EvaluationRunRecord,
    StampCrop,
    StampObservationRecord,
    StampValuationRecord,
)
from .observation_schema import DEFAULT_UNOBSERVABLE_FACTORS
from .storage import PhilalensStore, new_id, utc_now
from .triage import triage_observation
from .vision import VisionObservationAdapter, VisionObservationError


CROP_READINESS_PIPELINE_VERSION = "crop-readiness-skeleton-v1"


def evaluate_collection_readiness(
    store: PhilalensStore,
    collection_id: str,
    vision_adapter: VisionObservationAdapter | None = None,
    crop_ids: list[str] | None = None,
    progress_callback: Callable[[int, int, StampCrop], None] | None = None,
) -> EvaluationRunRecord | None:
    collection = store.get_collection(collection_id)
    if collection is None:
        return None

    vision_mode = vision_adapter.adapter_name if vision_adapter else "not_connected"
    crop_id_filter = set(crop_ids) if crop_ids is not None else None
    crops = [
        crop
        for page in store.list_pages(collection.collection_id)
        for crop in store.list_crops_for_page(page.page_id)
        if crop_id_filter is None or crop.crop_id in crop_id_filter
    ]
    run = store.create_evaluation_run(
        collection_id=collection.collection_id,
        pipeline_version=CROP_READINESS_PIPELINE_VERSION,
        status=EVALUATION_STATUS_RUNNING,
        enabled_sources=[],
        settings={
            "mode": "crop_readiness_only",
            "ai_vision": vision_mode,
            "vision_model": vision_adapter.model_name if vision_adapter else None,
            "crop_scope": "selected" if crop_id_filter is not None else "collection",
            "selected_crop_ids": sorted(crop_id_filter) if crop_id_filter is not None else [],
            "source_matching": "not_connected",
            "market_pricing": "not_connected",
            "cost_estimate": _estimate_cost_for_run(vision_adapter, crops),
        },
        vision_model=vision_adapter.model_name if vision_adapter else None,
    )

    errors: list[str] = []
    skipped_vision_for_crop_review = False
    successful_vision_count = 0

    total_crops = len(crops)
    for index, crop in enumerate(crops, start=1):
        if progress_callback is not None:
            progress_callback(index, total_crops, crop)
        vision_observation_status = "not_connected"
        observation: StampObservationRecord | None = None
        if vision_adapter and crop.review_state != REVIEW_NEEDS_CROP_REVIEW:
            try:
                observation = store.add_stamp_observation(
                    vision_adapter.observe_crop(crop, run.run_id)
                )
                vision_observation_status = "available"
                successful_vision_count += 1
            except VisionObservationError as exc:
                vision_observation_status = "failed"
                errors.append(f"{crop.crop_id}: {exc}")
                store.add_stamp_observation(
                    _readiness_observation(
                        run.run_id,
                        crop,
                        extra_warnings=["ai_vision_failed"],
                    )
                )
        else:
            if vision_adapter and crop.review_state == REVIEW_NEEDS_CROP_REVIEW:
                vision_observation_status = "skipped_crop_review"
                skipped_vision_for_crop_review = True
            store.add_stamp_observation(_readiness_observation(run.run_id, crop))

        store.add_stamp_valuation(
            _readiness_valuation(
                run.run_id,
                crop,
                vision_observation_status=vision_observation_status,
                observation=observation,
            )
        )

    warnings = [
        "source_matching_not_connected",
        "market_pricing_not_connected",
    ]
    if vision_adapter is None:
        warnings.append("ai_vision_not_connected")
    elif successful_vision_count == 0 and crops:
        warnings.append("ai_vision_produced_no_observations")
    if errors:
        warnings.append("ai_vision_failed_on_some_crops")
    if skipped_vision_for_crop_review:
        warnings.append("ai_vision_skipped_for_crop_review")
    if not crops:
        warnings.append("no_crops_available")
    if collection.needs_crop_review_count:
        warnings.append("crop_review_remaining")

    completed = replace(
        run,
        status=EVALUATION_STATUS_COMPLETED,
        finished_at=utc_now(),
        settings={
            **run.settings,
            "cost_actual": summarize_observation_costs(
                store.list_stamp_observations_for_run(run.run_id),
                provider=vision_mode,
                model=vision_adapter.model_name if vision_adapter else None,
            ),
        },
        warnings=warnings,
        errors=errors,
    )
    return store.update_evaluation_run(completed)


def _readiness_observation(
    run_id: str,
    crop: StampCrop,
    extra_warnings: list[str] | None = None,
) -> StampObservationRecord:
    image_quality_warnings = list(crop.warnings)
    image_quality_warnings.extend(extra_warnings or [])
    if crop.review_state == REVIEW_NEEDS_CROP_REVIEW:
        image_quality_warnings.append("crop_review_required")

    return StampObservationRecord(
        observation_id=new_id("obs"),
        run_id=run_id,
        crop_id=crop.crop_id,
        image_quality_warnings=image_quality_warnings,
        unobservable_factors=DEFAULT_UNOBSERVABLE_FACTORS,
        confidence=0.0,
        model_metadata={
            "adapter": "crop_readiness_skeleton",
            "vision_extraction": "not_started",
        },
    )


def _readiness_valuation(
    run_id: str,
    crop: StampCrop,
    *,
    vision_observation_status: str = "not_connected",
    observation: StampObservationRecord | None = None,
) -> StampValuationRecord:
    if crop.review_state == REVIEW_NEEDS_CROP_REVIEW:
        value_bucket = "needs_better_image"
        recommended_next_action = "review crop"
        uncertainty_warnings = [
            "crop_review_required",
            "identity_not_evaluated",
            "market_evidence_not_checked",
        ]
        assumptions = [
            "Crop requires review before reliable identification or valuation.",
            "Only the current front crop image is represented.",
        ]
        valuation_confidence = 0.0
    elif vision_observation_status == "available" and observation is not None:
        triage = triage_observation(observation)
        value_bucket = triage.value_bucket
        recommended_next_action = triage.recommended_next_action
        uncertainty_warnings = triage.uncertainty_warnings
        assumptions = triage.assumptions
        valuation_confidence = triage.valuation_confidence
    elif vision_observation_status == "failed":
        value_bucket = "not_enough_evidence"
        recommended_next_action = "rerun observation extraction"
        uncertainty_warnings = [
            "vision_extraction_failed",
            "identity_not_evaluated",
            "market_evidence_not_checked",
        ]
        assumptions = [
            "AI vision was configured but did not produce a valid observation for this crop.",
            "Catalog matching and market evidence have not run.",
        ]
        valuation_confidence = 0.0
    else:
        value_bucket = "not_enough_evidence"
        recommended_next_action = "run observation extraction and source matching"
        uncertainty_warnings = [
            "identity_not_evaluated",
            "market_evidence_not_checked",
            "vision_adapter_not_connected",
        ]
        assumptions = [
            "Crop-readiness skeleton only; no AI vision, catalog matching, or market evidence has run.",
            "Only the current front crop image is represented.",
        ]
        valuation_confidence = 0.0

    return StampValuationRecord(
        valuation_id=new_id("val"),
        run_id=run_id,
        crop_id=crop.crop_id,
        estimated_value_low=None,
        estimated_value_high=None,
        currency="USD",
        identity_confidence=0.0,
        condition_confidence=0.0,
        market_evidence_confidence=0.0,
        valuation_confidence=valuation_confidence,
        value_bucket=value_bucket,
        assumptions=assumptions,
        uncertainty_warnings=uncertainty_warnings,
        recommended_next_action=recommended_next_action,
        evidence_ids=[],
    )


def _estimate_cost_for_run(
    vision_adapter: VisionObservationAdapter | None,
    crops: list[StampCrop],
) -> dict[str, object]:
    billable_crops = [crop for crop in crops if crop.review_state != REVIEW_NEEDS_CROP_REVIEW]
    skipped_crop_review_count = len(crops) - len(billable_crops)
    if vision_adapter is None:
        return non_openai_cost_estimate(
            provider="none",
            crop_count=len(crops),
            billable_api_call_count=0,
            skipped_crop_review_count=skipped_crop_review_count,
        )

    if vision_adapter.adapter_name != "openai_responses_vision":
        return non_openai_cost_estimate(
            provider=vision_adapter.adapter_name,
            model=vision_adapter.model_name,
            crop_count=len(crops),
            billable_api_call_count=len(billable_crops),
            skipped_crop_review_count=skipped_crop_review_count,
        )

    image_detail = getattr(vision_adapter, "image_detail", None)
    return estimate_openai_vision_run_cost(
        model=vision_adapter.model_name,
        image_detail=image_detail if isinstance(image_detail, str) else None,
        crop_count=len(crops),
        billable_api_call_count=len(billable_crops),
        skipped_crop_review_count=skipped_crop_review_count,
    )
