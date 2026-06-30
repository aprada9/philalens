"""FastAPI entrypoint for Philalens."""

from __future__ import annotations

import shutil
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from .config import settings
from .exports import build_collection_csv, build_collection_export
from .imaging import normalize_image, safe_filename, supported_image_extension
from .models import PageImageRecord
from .pipeline import build_empty_page_analysis, summarize_collection
from .segmentation import detect_stamp_crops, recrop_stamp
from .storage import PhilalensStore, new_id
from .visualizer import VISUALIZER_HTML


class CropUpdate(BaseModel):
    bbox_xywh: tuple[int, int, int, int] = Field(
        description="Crop box as x, y, width, height in normalized page-image pixels."
    )
    rotation_degrees: float | None = Field(
        default=None,
        description="Clockwise crop rotation in degrees. Omitted updates preserve current rotation.",
    )


class CropCreate(BaseModel):
    bbox_xywh: tuple[int, int, int, int] = Field(
        description="Manual crop box as x, y, width, height in normalized page-image pixels."
    )
    rotation_degrees: float = Field(
        default=0.0,
        description="Clockwise crop rotation in degrees.",
    )


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="Local stamp collection intake, segmentation, review, and export API.",
)
store = PhilalensStore(settings.database_path)
store.initialize()


@app.get("/", response_class=HTMLResponse)
def visualizer() -> str:
    return VISUALIZER_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/collections")
def list_collections() -> list[dict[str, object]]:
    return [asdict(collection) for collection in store.list_collections()]


@app.post("/api/collections")
async def create_collection(files: list[UploadFile] = File(...)) -> dict[str, object]:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one image.")
    if len(files) > settings.max_upload_files:
        raise HTTPException(
            status_code=400,
            detail=f"Upload at most {settings.max_upload_files} images per batch.",
        )

    for index, upload in enumerate(files, start=1):
        filename = safe_filename(upload.filename, f"page-{index}.jpg")
        if not supported_image_extension(filename):
            raise HTTPException(status_code=400, detail=f"Unsupported image format: {filename}")

    collection = store.create_collection(title=f"{len(files)} page batch")
    collection_dir = settings.collections_dir / collection.collection_id

    for index, upload in enumerate(files, start=1):
        page_id = new_id("page")
        page_dir = collection_dir / page_id
        original_filename = safe_filename(upload.filename, f"page-{index}.jpg")
        original_path = page_dir / original_filename
        normalized_path = page_dir / "normalized.jpg"
        crops_dir = page_dir / "crops"

        await _persist_upload(upload, original_path)

        try:
            normalized = normalize_image(original_path, normalized_path)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        segmentation = detect_stamp_crops(
            page_id=page_id,
            normalized_image_path=normalized.normalized_path,
            crop_dir=crops_dir,
            detector=settings.stamp_detector,
            yolo_model_path=settings.stamp_yolo_model_path,
            yolo_confidence=settings.stamp_yolo_confidence,
            margin_percent=settings.stamp_crop_margin_percent,
        )
        notes = [
            f"Automatic crop detection completed with {segmentation.detector}.",
            "Catalog matching, descriptions, and valuation are not enabled yet.",
        ]
        notes.extend(segmentation.warnings)

        page = PageImageRecord(
            page_id=page_id,
            collection_id=collection.collection_id,
            page_order=index,
            original_filename=original_filename,
            original_path=str(normalized.original_path),
            normalized_path=str(normalized.normalized_path),
            image_format=normalized.image_format,
            width=normalized.width,
            height=normalized.height,
            quality_warnings=normalized.warnings,
            notes=notes,
        )
        store.add_page(page)
        store.replace_page_crops(page_id, segmentation.crops)

    export = build_collection_export(store, collection.collection_id)
    if export is None:
        raise HTTPException(status_code=500, detail="Collection was not saved.")
    return export


@app.get("/api/collections/{collection_id}")
def get_collection(collection_id: str) -> dict[str, object]:
    export = build_collection_export(store, collection_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Collection not found.")
    return export


@app.get("/api/collections/{collection_id}/export.json")
def export_collection_json(collection_id: str) -> JSONResponse:
    export = build_collection_export(store, collection_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Collection not found.")

    return JSONResponse(
        content=export,
        headers={
            "Content-Disposition": f'attachment; filename="philalens-{collection_id}.json"'
        },
    )


@app.get("/api/collections/{collection_id}/export.csv")
def export_collection_csv(collection_id: str) -> Response:
    csv_payload = build_collection_csv(store, collection_id)
    if csv_payload is None:
        raise HTTPException(status_code=404, detail="Collection not found.")

    return Response(
        content=csv_payload,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="philalens-{collection_id}.csv"'},
    )


@app.patch("/api/crops/{crop_id}")
def update_crop(crop_id: str, update: CropUpdate) -> dict[str, object]:
    crop = store.get_crop(crop_id)
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found.")

    page = store.get_page(crop.page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")

    if update.bbox_xywh[2] <= 0 or update.bbox_xywh[3] <= 0:
        raise HTTPException(status_code=400, detail="Crop width and height must be positive.")

    rotation_degrees = (
        crop.rotation_degrees if update.rotation_degrees is None else update.rotation_degrees
    )
    updated = recrop_stamp(
        page_id=page.page_id,
        crop_id=crop.crop_id,
        crop_index=crop.crop_index,
        normalized_image_path=Path(page.normalized_path),
        crop_dir=Path(crop.crop_path).parent,
        bbox_xywh=update.bbox_xywh,
        rotation_degrees=rotation_degrees,
    )
    store.update_crop(updated)
    return {"crop": asdict(updated)}


@app.delete("/api/crops/{crop_id}")
def delete_crop(crop_id: str) -> dict[str, object]:
    crop = store.get_crop(crop_id)
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found.")

    page = store.get_page(crop.page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")

    store.delete_crop(crop.crop_id)
    Path(crop.crop_path).unlink(missing_ok=True)

    export = build_collection_export(store, page.collection_id)
    if export is None:
        raise HTTPException(status_code=500, detail="Collection was not found after crop deletion.")
    return export


@app.post("/api/pages/{page_id}/crops")
def create_manual_crop(page_id: str, create: CropCreate) -> dict[str, object]:
    page = store.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")

    if create.bbox_xywh[2] <= 0 or create.bbox_xywh[3] <= 0:
        raise HTTPException(status_code=400, detail="Crop width and height must be positive.")

    crop_index = store.next_crop_index(page.page_id)
    crop = recrop_stamp(
        page_id=page.page_id,
        crop_id=new_id("crop"),
        crop_index=crop_index,
        normalized_image_path=Path(page.normalized_path),
        crop_dir=Path(page.normalized_path).parent / "crops",
        bbox_xywh=create.bbox_xywh,
        rotation_degrees=create.rotation_degrees,
    )
    store.add_crop(crop)

    export = build_collection_export(store, page.collection_id)
    if export is None:
        raise HTTPException(status_code=500, detail="Collection was not found after crop creation.")
    return export


@app.post("/api/pages/{page_id}/redetect")
def redetect_page(page_id: str) -> dict[str, object]:
    page = store.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")

    segmentation = detect_stamp_crops(
        page_id=page.page_id,
        normalized_image_path=Path(page.normalized_path),
        crop_dir=Path(page.normalized_path).parent / "crops",
        detector=settings.stamp_detector,
        yolo_model_path=settings.stamp_yolo_model_path,
        yolo_confidence=settings.stamp_yolo_confidence,
        margin_percent=settings.stamp_crop_margin_percent,
    )
    store.replace_page_crops(page.page_id, segmentation.crops)

    export = build_collection_export(store, page.collection_id)
    if export is None:
        raise HTTPException(status_code=500, detail="Collection was not found after re-detection.")
    return export


@app.delete("/api/pages/{page_id}")
def delete_page(page_id: str) -> dict[str, object]:
    page = store.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")

    collection_id = page.collection_id
    page_dir = Path(page.normalized_path).parent
    store.delete_page(page.page_id)
    shutil.rmtree(page_dir, ignore_errors=True)

    export = build_collection_export(store, collection_id)
    if export is None:
        raise HTTPException(status_code=500, detail="Collection was not found after page deletion.")
    return export


@app.get("/media/pages/{page_id}/normalized")
def get_normalized_page(page_id: str) -> FileResponse:
    page = store.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")
    return _file_response(Path(page.normalized_path), page.original_filename)


@app.get("/media/crops/{crop_id}")
def get_crop_image(crop_id: str) -> FileResponse:
    crop = store.get_crop(crop_id)
    if crop is None:
        raise HTTPException(status_code=404, detail="Crop not found.")
    return _file_response(Path(crop.crop_path), f"{crop.crop_id}.jpg")


@app.post("/analyze/pages")
async def analyze_pages(files: list[UploadFile] = File(...)) -> dict[str, object]:
    """Backward-compatible placeholder endpoint from the initial skeleton."""
    pages = [
        build_empty_page_analysis(
            page_id=f"page-{index + 1}",
            image_filename=file.filename or f"page-{index + 1}.jpg",
        )
        for index, file in enumerate(files)
    ]
    summary = summarize_collection(pages)

    return {
        "pages": [asdict(page) for page in pages],
        "summary": asdict(summary),
        "note": "Use /api/collections for persisted local intake and segmentation.",
    }


async def _persist_upload(upload: UploadFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)


def _file_response(path: Path, filename: str) -> FileResponse:
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path=path, filename=filename)
