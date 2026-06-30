from pathlib import Path

from philalens.exports import build_collection_csv, build_collection_export
from philalens.models import REVIEW_NEEDS_CROP_REVIEW, PageImageRecord, StampCrop
from philalens.storage import PhilalensStore


def test_storage_and_exports_round_trip_collection(tmp_path: Path) -> None:
    store = PhilalensStore(tmp_path / "philalens.sqlite")
    store.initialize()
    collection = store.create_collection(title="test batch")

    page = PageImageRecord(
        page_id="page_1",
        collection_id=collection.collection_id,
        page_order=1,
        original_filename="album.heic",
        original_path=str(tmp_path / "album.heic"),
        normalized_path=str(tmp_path / "normalized.jpg"),
        image_format="HEIF",
        width=1200,
        height=900,
        quality_warnings=[],
        notes=["Automatic crop detection completed."],
    )
    store.add_page(page)
    store.replace_page_crops(
        page.page_id,
        [
            StampCrop(
                crop_id="crop_1",
                page_id=page.page_id,
                crop_index=1,
                bbox_xywh=(10, 20, 100, 120),
                crop_path=str(tmp_path / "crop.jpg"),
                segmentation_confidence=0.62,
                rotation_degrees=12.5,
                review_state=REVIEW_NEEDS_CROP_REVIEW,
                warnings=["large_region_may_include_multiple_stamps"],
            )
        ],
    )

    export = build_collection_export(store, collection.collection_id)
    assert export is not None
    assert export["collection"]["page_count"] == 1
    assert export["collection"]["stamp_count"] == 1
    assert export["collection"]["needs_crop_review_count"] == 1
    assert export["pages"][0]["stamps"][0]["review_state"] == REVIEW_NEEDS_CROP_REVIEW
    assert export["pages"][0]["stamps"][0]["rotation_degrees"] == 12.5

    csv_payload = build_collection_csv(store, collection.collection_id)
    assert csv_payload is not None
    assert "crop_1" in csv_payload
    assert "rotation_degrees" in csv_payload
    assert "12.5" in csv_payload
    assert "large_region_may_include_multiple_stamps" in csv_payload

    assert store.delete_crop("crop_1") is True
    assert store.delete_crop("crop_missing") is False
    export = build_collection_export(store, collection.collection_id)
    assert export is not None
    assert export["collection"]["page_count"] == 1
    assert export["collection"]["stamp_count"] == 0
    assert export["pages"][0]["stamps"] == []

    assert store.delete_page(page.page_id) is True
    assert store.delete_page("page_missing") is False
    export = build_collection_export(store, collection.collection_id)
    assert export is not None
    assert export["collection"]["page_count"] == 0
    assert export["pages"] == []
