"""Collection export builders."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any, cast

from .storage import PhilalensStore


def build_collection_export(store: PhilalensStore, collection_id: str) -> dict[str, object] | None:
    collection = store.get_collection(collection_id)
    if collection is None:
        return None

    pages_payload: list[dict[str, object]] = []
    for page in store.list_pages(collection_id):
        crops_payload = []
        for crop in store.list_crops_for_page(page.page_id):
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
                    "description": "Pending vision extraction.",
                    "identification": {
                        "status": "not_started",
                        "candidates": [],
                        "note": "Catalog matching is not connected yet.",
                    },
                    "valuation": {
                        "status": "not_available",
                        "estimated_value_low": None,
                        "estimated_value_high": None,
                        "currency": "USD",
                        "confidence": 0.0,
                        "note": "Valuation requires candidate identity and market evidence.",
                    },
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
        "pages": pages_payload,
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
            "valuation_status",
            "estimated_value_low",
            "estimated_value_high",
            "currency",
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
                    "valuation_status": valuation["status"],
                    "estimated_value_low": valuation["estimated_value_low"],
                    "estimated_value_high": valuation["estimated_value_high"],
                    "currency": valuation["currency"],
                }
            )

    return output.getvalue()
