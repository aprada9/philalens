"""Conservative collection evaluation skeleton.

This module creates a durable evaluation run before AI vision, source adapters,
or pricing logic are connected. It records crop readiness and explicit
"not enough evidence" valuation buckets so the browser can exercise the
evaluation workflow without pretending identification has happened.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import replace

from .costing import (
    estimate_openai_vision_run_cost,
    non_openai_cost_estimate,
    summarize_observation_costs,
)
from .models import (
    EVALUATION_STATUS_COMPLETED,
    EVALUATION_STATUS_INTERRUPTED,
    EVALUATION_STATUS_RUNNING,
    REVIEW_NEEDS_CROP_REVIEW,
    EvaluationRunRecord,
    StampCrop,
    StampObservationRecord,
    StampValuationRecord,
)
from .observation_schema import DEFAULT_UNOBSERVABLE_FACTORS, VisionAnalysisResult
from .similarity import group_duplicate_crops
from .storage import PhilalensStore, new_id, utc_now
from .triage import triage_observation
from .vision import VisionObservationAdapter, VisionObservationError

CROP_READINESS_PIPELINE_VERSION = "tier1-identification-v2"


class EvaluationCancelledError(Exception):
    """Raised by a progress callback to stop a run gracefully.

    Crops processed before the cancellation keep their records (each crop's
    valuation is its checkpoint), the run is marked ``interrupted``, and it can
    be resumed later without repeating completed crops.
    """

# Backoff before each retry of a failed vision call. The long final step
# rides out rate-limit bursts under concurrent calls. Tests may monkeypatch
# this to () to avoid sleeping.
VISION_RETRY_BACKOFF_SECONDS: tuple[float, ...] = (2.0, 5.0, 15.0)

_PRIOR_BUCKET_ACTIONS = {
    "likely_common": "no individual review needed; spot-check only",
    "possibly_interesting": "gather market evidence",
    "investigate": "gather market evidence and consider expert review",
}


def evaluate_collection_readiness(
    store: PhilalensStore,
    collection_id: str,
    vision_adapter: VisionObservationAdapter | None = None,
    crop_ids: list[str] | None = None,
    progress_callback: Callable[[int, int, StampCrop], None] | None = None,
    resume_run_id: str | None = None,
    vision_concurrency: int = 1,
) -> EvaluationRunRecord | None:
    collection = store.get_collection(collection_id)
    if collection is None:
        return None

    vision_mode = vision_adapter.adapter_name if vision_adapter else "not_connected"

    if resume_run_id is not None:
        run = store.get_evaluation_run(resume_run_id)
        if run is None or run.collection_id != collection.collection_id:
            return None
        if run.settings.get("crop_scope") == "selected":
            selected = run.settings.get("selected_crop_ids") or []
            crop_id_filter: set[str] | None = {str(crop_id) for crop_id in selected}
        else:
            crop_id_filter = None
    else:
        crop_id_filter = set(crop_ids) if crop_ids is not None else None

    crops = [
        crop
        for page in store.list_pages(collection.collection_id)
        for crop in store.list_crops_for_page(page.page_id)
        if crop_id_filter is None or crop.crop_id in crop_id_filter
    ]

    if resume_run_id is not None:
        # A valuation record is the last write for a crop in a run, so crops
        # with one are already fully processed and are not repeated.
        pending_crops = [
            crop
            for crop in crops
            if store.get_stamp_valuation_for_crop(run.run_id, crop.crop_id) is None
        ]
        errors: list[str] = list(run.errors)
        run = store.update_evaluation_run(
            replace(run, status=EVALUATION_STATUS_RUNNING, finished_at=None)
        )
    else:
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
        pending_crops = crops
        errors = []

    skipped_vision_for_crop_review = False
    successful_vision_count = 0
    vision_api_call_count = 0

    # Near-duplicate crops share one vision call: the representative (first
    # member) is analyzed and the result is fanned out to the other members.
    duplicate_of: dict[str, str] = {}
    representative_ids: set[str] = set()
    if vision_adapter is not None:
        eligible = [
            crop for crop in pending_crops if crop.review_state != REVIEW_NEEDS_CROP_REVIEW
        ]
        for group in group_duplicate_crops(eligible):
            if len(group) < 2:
                continue
            representative_ids.add(group[0].crop_id)
            for member in group[1:]:
                duplicate_of[member.crop_id] = group[0].crop_id

    # Split the work: crops that need an API call (representatives and
    # singletons), duplicate members waiting on their representative, and
    # crops recorded without vision.
    call_crops: list[StampCrop] = []
    skip_crops: list[StampCrop] = []
    members_by_representative: dict[str, list[StampCrop]] = {}
    for crop in pending_crops:
        if vision_adapter and crop.review_state != REVIEW_NEEDS_CROP_REVIEW:
            representative_id = duplicate_of.get(crop.crop_id)
            if representative_id is not None:
                members_by_representative.setdefault(representative_id, []).append(crop)
            else:
                call_crops.append(crop)
        else:
            skip_crops.append(crop)

    cancelled = False
    completed_count = 0
    total_crops = len(pending_crops)

    def report_done(crop: StampCrop) -> None:
        # Called on the main thread only; a cancel raised by the callback
        # stops new dispatches while in-flight (already paid) calls finish
        # and are saved.
        nonlocal cancelled, completed_count
        completed_count += 1
        if progress_callback is None or cancelled:
            return
        try:
            progress_callback(completed_count, total_crops, crop)
        except EvaluationCancelledError:
            cancelled = True

    def record_success(crop: StampCrop, analysis: VisionAnalysisResult) -> None:
        nonlocal successful_vision_count
        _store_analysis(store, analysis)
        store.add_stamp_valuation(
            _readiness_valuation(
                run.run_id, crop, vision_observation_status="available", analysis=analysis
            )
        )
        successful_vision_count += 1
        report_done(crop)
        for member in members_by_representative.get(crop.crop_id, []):
            derived = _derived_analysis(analysis, member, crop.crop_id)
            _store_analysis(store, derived)
            store.add_stamp_valuation(
                _readiness_valuation(
                    run.run_id,
                    member,
                    vision_observation_status="available",
                    analysis=derived,
                    derived_from=crop.crop_id,
                )
            )
            successful_vision_count += 1
            report_done(member)

    def record_failure(crop: StampCrop, message: str) -> None:
        errors.append(f"{crop.crop_id}: {message}")
        store.add_stamp_observation(
            _readiness_observation(run.run_id, crop, extra_warnings=["ai_vision_failed"])
        )
        store.add_stamp_valuation(
            _readiness_valuation(run.run_id, crop, vision_observation_status="failed")
        )
        report_done(crop)
        for member in members_by_representative.get(crop.crop_id, []):
            errors.append(
                f"{member.crop_id}: vision failed on duplicate representative {crop.crop_id}"
            )
            store.add_stamp_observation(
                _readiness_observation(
                    run.run_id,
                    member,
                    extra_warnings=["ai_vision_failed", "derived_from_duplicate_failed"],
                )
            )
            store.add_stamp_valuation(
                _readiness_valuation(run.run_id, member, vision_observation_status="failed")
            )
            report_done(member)

    for crop in skip_crops:
        if cancelled:
            break
        vision_observation_status = "not_connected"
        if vision_adapter and crop.review_state == REVIEW_NEEDS_CROP_REVIEW:
            vision_observation_status = "skipped_crop_review"
            skipped_vision_for_crop_review = True
        store.add_stamp_observation(_readiness_observation(run.run_id, crop))
        store.add_stamp_valuation(
            _readiness_valuation(
                run.run_id, crop, vision_observation_status=vision_observation_status
            )
        )
        report_done(crop)

    # Vision calls run concurrently in a sliding window; all database writes
    # and progress callbacks stay on this thread. Each crop's valuation is
    # its checkpoint, so a crash or stop mid-run resumes without re-billing.
    if vision_adapter is not None and call_crops and not cancelled:
        adapter = vision_adapter
        with ThreadPoolExecutor(max_workers=max(1, vision_concurrency)) as executor:
            crop_iter = iter(call_crops)
            in_flight: dict[Future[VisionAnalysisResult], StampCrop] = {}

            def submit_next() -> None:
                if cancelled:
                    return
                next_crop = next(crop_iter, None)
                if next_crop is not None:
                    in_flight[
                        executor.submit(_observe_with_retries, adapter, next_crop, run.run_id)
                    ] = next_crop

            for _ in range(max(1, vision_concurrency)):
                submit_next()

            while in_flight:
                done, _pending = wait(list(in_flight), return_when=FIRST_COMPLETED)
                for future in done:
                    crop = in_flight.pop(future)
                    error = future.exception()
                    if error is None:
                        vision_api_call_count += 1
                        record_success(crop, future.result())
                    else:
                        record_failure(crop, str(error))
                    submit_next()

    warnings = [
        "source_matching_not_connected",
        "market_pricing_not_connected",
    ]
    if vision_adapter is None:
        warnings.append("ai_vision_not_connected")
    elif successful_vision_count == 0 and pending_crops:
        warnings.append("ai_vision_produced_no_observations")
    if errors:
        warnings.append("ai_vision_failed_on_some_crops")
    if skipped_vision_for_crop_review:
        warnings.append("ai_vision_skipped_for_crop_review")
    if not crops:
        warnings.append("no_crops_available")
    if collection.needs_crop_review_count:
        warnings.append("crop_review_remaining")
    if resume_run_id is not None:
        warnings.append("run_resumed_after_interruption")
    if duplicate_of:
        warnings.append("duplicate_crops_shared_vision_results")
    if cancelled:
        warnings.append("run_cancelled_by_user")

    completed = replace(
        run,
        status=EVALUATION_STATUS_INTERRUPTED if cancelled else EVALUATION_STATUS_COMPLETED,
        finished_at=utc_now(),
        settings={
            **run.settings,
            "vision_api_call_count": vision_api_call_count,
            "duplicate_group_count": len(representative_ids),
            "duplicate_derived_count": len(duplicate_of),
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


def _store_analysis(store: PhilalensStore, analysis: VisionAnalysisResult) -> None:
    store.add_stamp_observation(analysis.observation)
    for candidate in analysis.candidates:
        store.add_catalog_candidate(candidate)


def _derived_analysis(
    analysis: VisionAnalysisResult,
    crop: StampCrop,
    representative_crop_id: str,
) -> VisionAnalysisResult:
    """Fan a representative's analysis out to a near-duplicate crop."""

    observation = replace(
        analysis.observation,
        observation_id=new_id("obs"),
        crop_id=crop.crop_id,
        created_at=None,
        model_metadata={
            **analysis.observation.model_metadata,
            "derived_from_duplicate": representative_crop_id,
        },
    )
    candidates = [
        replace(
            candidate,
            candidate_id=new_id("cand"),
            crop_id=crop.crop_id,
            contradiction_warnings=[
                *candidate.contradiction_warnings,
                "derived_from_duplicate_crop",
            ],
        )
        for candidate in analysis.candidates
    ]
    return VisionAnalysisResult(
        observation=observation,
        candidates=candidates,
        prior_value_bucket=analysis.prior_value_bucket,
        prior_value_rationale=analysis.prior_value_rationale,
    )


def _observe_with_retries(
    vision_adapter: VisionObservationAdapter,
    crop: StampCrop,
    run_id: str,
) -> VisionAnalysisResult:
    attempts = len(VISION_RETRY_BACKOFF_SECONDS) + 1
    for attempt in range(attempts):
        try:
            return vision_adapter.observe_crop(crop, run_id)
        except VisionObservationError:
            if attempt == attempts - 1:
                raise
            time.sleep(VISION_RETRY_BACKOFF_SECONDS[attempt])
    raise VisionObservationError("unreachable retry state")


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
    analysis: VisionAnalysisResult | None = None,
    derived_from: str | None = None,
) -> StampValuationRecord:
    observation = analysis.observation if analysis is not None else None
    identity_confidence = 0.0
    candidate_id: str | None = None

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
    elif (
        vision_observation_status == "available"
        and analysis is not None
        and observation is not None
        and analysis.prior_value_bucket
    ):
        # V2 path: the vision model proposed identity candidates and a
        # value-triage bucket. These are priors, never source-backed facts.
        value_bucket = analysis.prior_value_bucket
        recommended_next_action = _PRIOR_BUCKET_ACTIONS.get(
            analysis.prior_value_bucket, "review manually"
        )
        identity_confidence = max(
            (candidate.match_score for candidate in analysis.candidates), default=0.0
        )
        top_candidate = min(
            analysis.candidates, key=lambda candidate: candidate.rank, default=None
        )
        candidate_id = top_candidate.candidate_id if top_candidate else None
        uncertainty_warnings = [
            "ai_prior_identity_unverified",
            "market_evidence_not_checked",
            "unobservable_variants_may_change_value",
        ]
        assumptions = [
            "AI prior from the front photo only; no source or market evidence attached.",
        ]
        if analysis.prior_value_rationale:
            assumptions.append(f"Model rationale: {analysis.prior_value_rationale}")
        if derived_from:
            assumptions.append(
                f"Result copied from visually near-duplicate crop {derived_from}."
            )
            uncertainty_warnings.append("derived_from_duplicate_crop")
        valuation_confidence = round(min(observation.confidence, identity_confidence) * 0.75, 2)
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
        candidate_id=candidate_id,
        estimated_value_low=None,
        estimated_value_high=None,
        currency="USD",
        identity_confidence=identity_confidence,
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
