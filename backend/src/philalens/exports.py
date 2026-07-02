"""Collection export builders."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import asdict
from io import StringIO
from typing import Any, cast

from .storage import PhilalensStore


def build_collection_export(store: PhilalensStore, collection_id: str) -> dict[str, object] | None:
    collection = store.get_collection(collection_id)
    if collection is None:
        return None

    evaluation_runs = store.list_evaluation_runs(collection_id)
    latest_run = evaluation_runs[0] if evaluation_runs else None
    latest_evaluation_summary = (
        build_evaluation_summary(store, latest_run.run_id) if latest_run else None
    )
    pages_payload: list[dict[str, object]] = []
    for page in store.list_pages(collection_id):
        crops_payload = []
        for crop in store.list_crops_for_page(page.page_id):
            observation = (
                store.get_stamp_observation_for_crop(latest_run.run_id, crop.crop_id)
                if latest_run
                else None
            )
            candidates = (
                store.list_catalog_candidates_for_crop(latest_run.run_id, crop.crop_id)
                if latest_run
                else []
            )
            evidence = (
                store.list_source_evidence_for_crop(latest_run.run_id, crop.crop_id)
                if latest_run
                else []
            )
            valuation = (
                store.get_stamp_valuation_for_crop(latest_run.run_id, crop.crop_id)
                if latest_run
                else None
            )

            observation_payload: dict[str, object]
            if observation is None:
                observation_payload = {
                    "status": "not_started",
                    "note": "No observation has been recorded for this crop yet.",
                }
            else:
                observation_payload = {"status": "available", **asdict(observation)}

            identification_payload: dict[str, object]
            if latest_run is None:
                identification_payload = {
                    "status": "not_started",
                    "candidates": [],
                    "note": "Catalog matching is not connected yet.",
                }
            else:
                identification_payload = {
                    "status": "available" if candidates else "no_candidates",
                    "run_id": latest_run.run_id,
                    "candidates": [asdict(candidate) for candidate in candidates],
                }

            valuation_payload: dict[str, object]
            if valuation is None:
                valuation_payload = {
                    "status": "not_available",
                    "estimated_value_low": None,
                    "estimated_value_high": None,
                    "currency": "USD",
                    "confidence": 0.0,
                    "note": "Valuation requires candidate identity and market evidence.",
                }
            else:
                valuation_payload = {
                    "status": "available",
                    **asdict(valuation),
                    "confidence": valuation.valuation_confidence,
                }

            crops_payload.append(
                {
                    "crop_id": crop.crop_id,
                    "crop_index": crop.crop_index,
                    "bbox_xywh": list(crop.bbox_xywh),
                    "rotation_degrees": crop.rotation_degrees,
                    "crop_image_url": f"/media/crops/{crop.crop_id}",
                    "segmentation_confidence": crop.segmentation_confidence,
                    "review_state": crop.review_state,
                    "warnings": crop.warnings,
                    "description": observation.design_subject
                    if observation and observation.design_subject
                    else "Pending vision extraction.",
                    "evaluation_run_id": latest_run.run_id if latest_run else None,
                    "observation": observation_payload,
                    "identification": identification_payload,
                    "evidence": [asdict(item) for item in evidence],
                    "valuation": valuation_payload,
                }
            )

        pages_payload.append(
            {
                "page_id": page.page_id,
                "page_order": page.page_order,
                "original_filename": page.original_filename,
                "image_format": page.image_format,
                "width": page.width,
                "height": page.height,
                "quality_warnings": page.quality_warnings,
                "notes": page.notes,
                "normalized_image_url": f"/media/pages/{page.page_id}/normalized",
                "stamps": crops_payload,
            }
        )

    return {
        "collection": {
            "collection_id": collection.collection_id,
            "created_at": collection.created_at,
            "title": collection.title,
            "page_count": collection.page_count,
            "stamp_count": collection.stamp_count,
            "needs_crop_review_count": collection.needs_crop_review_count,
        },
        "evaluation_runs": [asdict(run) for run in evaluation_runs],
        "latest_evaluation_run_id": latest_run.run_id if latest_run else None,
        "latest_evaluation_summary": latest_evaluation_summary,
        "pages": pages_payload,
    }


def build_evaluation_summary(store: PhilalensStore, run_id: str) -> dict[str, object] | None:
    run = store.get_evaluation_run(run_id)
    if run is None:
        return None
    collection = store.get_collection(run.collection_id)
    if collection is None:
        return None

    valuations = store.list_stamp_valuations_for_run(run_id)
    bucket_counts = Counter(valuation.value_bucket for valuation in valuations)
    attention_buckets = {"possibly_interesting", "needs_expert_check"}
    attention_count = sum(bucket_counts[bucket] for bucket in attention_buckets)
    return {
        "run_id": run.run_id,
        "status": run.status,
        "pipeline_version": run.pipeline_version,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "evaluated_stamp_count": len(valuations),
        "unevaluated_stamp_count": max(0, collection.stamp_count - len(valuations)),
        "crop_review_remaining": collection.needs_crop_review_count,
        "attention_recommended_count": attention_count,
        "value_bucket_counts": dict(sorted(bucket_counts.items())),
        "warnings": run.warnings,
        "errors": run.errors,
    }


def build_evaluation_run_export(store: PhilalensStore, run_id: str) -> dict[str, object] | None:
    run = store.get_evaluation_run(run_id)
    if run is None:
        return None

    collection = store.get_collection(run.collection_id)
    if collection is None:
        return None

    return {
        "run": asdict(run),
        "collection": asdict(collection),
        "summary": build_evaluation_summary(store, run_id),
        "observations": [
            asdict(observation) for observation in store.list_stamp_observations_for_run(run_id)
        ],
        "candidates": [
            asdict(candidate) for candidate in store.list_catalog_candidates_for_run(run_id)
        ],
        "evidence": [asdict(evidence) for evidence in store.list_source_evidence_for_run(run_id)],
        "valuations": [
            asdict(valuation) for valuation in store.list_stamp_valuations_for_run(run_id)
        ],
    }


def build_collection_csv(store: PhilalensStore, collection_id: str) -> str | None:
    export = build_collection_export(store, collection_id)
    if export is None:
        return None

    output = StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "collection_id",
            "page_id",
            "page_order",
            "original_filename",
            "crop_id",
            "crop_index",
            "bbox_x",
            "bbox_y",
            "bbox_w",
            "bbox_h",
            "rotation_degrees",
            "segmentation_confidence",
            "review_state",
            "warnings",
            "description",
            "evaluation_run_id",
            "issuer_hint",
            "denomination_hint",
            "observation_confidence",
            "candidate_count",
            "top_candidate_title",
            "valuation_status",
            "estimated_value_low",
            "estimated_value_high",
            "currency",
            "value_bucket",
            "valuation_confidence",
            "recommended_next_action",
        ],
    )
    writer.writeheader()

    collection = cast(dict[str, Any], export["collection"])
    pages = cast(list[dict[str, Any]], export["pages"])
    for page in pages:
        stamps = cast(list[dict[str, Any]], page["stamps"])
        for stamp in stamps:
            bbox = cast(list[int], stamp["bbox_xywh"])
            valuation = cast(dict[str, Any], stamp["valuation"])
            observation = cast(dict[str, Any], stamp["observation"])
            identification = cast(dict[str, Any], stamp["identification"])
            candidates = cast(list[dict[str, Any]], identification["candidates"])
            top_candidate = candidates[0] if candidates else {}
            warnings = cast(list[str], stamp["warnings"])
            writer.writerow(
                {
                    "collection_id": collection["collection_id"],
                    "page_id": page["page_id"],
                    "page_order": page["page_order"],
                    "original_filename": page["original_filename"],
                    "crop_id": stamp["crop_id"],
                    "crop_index": stamp["crop_index"],
                    "bbox_x": bbox[0],
                    "bbox_y": bbox[1],
                    "bbox_w": bbox[2],
                    "bbox_h": bbox[3],
                    "rotation_degrees": stamp["rotation_degrees"],
                    "segmentation_confidence": stamp["segmentation_confidence"],
                    "review_state": stamp["review_state"],
                    "warnings": ";".join(warnings),
                    "description": stamp["description"],
                    "evaluation_run_id": stamp["evaluation_run_id"],
                    "issuer_hint": observation.get("issuer_hint"),
                    "denomination_hint": observation.get("denomination_hint"),
                    "observation_confidence": observation.get("confidence"),
                    "candidate_count": len(candidates),
                    "top_candidate_title": top_candidate.get("title"),
                    "valuation_status": valuation["status"],
                    "estimated_value_low": valuation["estimated_value_low"],
                    "estimated_value_high": valuation["estimated_value_high"],
                    "currency": valuation["currency"],
                    "value_bucket": valuation.get("value_bucket"),
                    "valuation_confidence": valuation.get("confidence"),
                    "recommended_next_action": valuation.get("recommended_next_action"),
                }
            )

    return output.getvalue()
