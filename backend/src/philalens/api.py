"""FastAPI entrypoint for Philalens."""

from __future__ import annotations

import shutil
from dataclasses import asdict, replace
from os import environ
from pathlib import Path
from threading import Lock, Thread

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import PROJECT_ROOT, get_settings
from .costing import estimate_openai_vision_run_cost, non_openai_cost_estimate
from .evaluation import evaluate_collection_readiness
from .exports import build_collection_csv, build_collection_export, build_evaluation_run_export
from .imaging import normalize_image, safe_filename, supported_image_extension
from .models import REVIEW_NEEDS_CROP_REVIEW, REVIEW_UNREVIEWED, PageImageRecord, StampCrop
from .segmentation import detect_stamp_crops, recrop_stamp
from .storage import PhilalensStore, new_id
from .vision import VisionObservationError, build_vision_adapter_from_settings


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


class CropSelection(BaseModel):
    crop_ids: list[str] = Field(default_factory=list)


class AppSettingsUpdate(BaseModel):
    vision_provider: str = Field(default="none")
    openai_api_key: str | None = Field(default=None)
    openai_vision_model: str = Field(default="gpt-4.1-mini")
    openai_vision_detail: str = Field(default="high")


_startup_settings = get_settings()
app = FastAPI(
    title=_startup_settings.app_name,
    version="0.2.0",
    description="Local stamp collection intake, segmentation, review, and export API.",
)
store = PhilalensStore(_startup_settings.database_path)
store.initialize()
store.mark_interrupted_evaluation_runs()
evaluation_jobs: dict[str, dict[str, object]] = {}
evaluation_jobs_lock = Lock()
_MAX_TRACKED_EVALUATION_JOBS = 50


FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/")
def frontend_index() -> Response:
    index_path = FRONTEND_DIST / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)
    return HTMLResponse(
        "<h1>Philalens</h1><p>Frontend is not built. Run "
        "<code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code> "
        "and restart the server.</p>",
        status_code=503,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/collections")
def list_collections() -> list[dict[str, object]]:
    return [asdict(collection) for collection in store.list_collections()]


@app.post("/api/collections")
async def create_collection(files: list[UploadFile] = File(...)) -> dict[str, object]:
    settings = get_settings()
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


@app.get("/api/collections/{collection_id}/evaluation-runs")
def list_evaluation_runs(collection_id: str) -> list[dict[str, object]]:
    if store.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found.")
    return [asdict(run) for run in store.list_evaluation_runs(collection_id)]


@app.post("/api/collections/{collection_id}/evaluate")
def evaluate_collection(
    collection_id: str, selection: CropSelection | None = None
) -> dict[str, object]:
    try:
        vision_adapter = build_vision_adapter_from_settings(get_settings())
    except VisionObservationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    crop_ids = selection.crop_ids if selection and selection.crop_ids else None
    run = evaluate_collection_readiness(
        store,
        collection_id,
        vision_adapter=vision_adapter,
        crop_ids=crop_ids,
    )
    if run is None:
        raise HTTPException(status_code=404, detail="Collection not found.")
    export = build_collection_export(store, collection_id)
    if export is None:
        raise HTTPException(status_code=500, detail="Collection was not found after evaluation.")
    return export


@app.post("/api/collections/{collection_id}/evaluate/start")
def start_evaluation_job(
    collection_id: str, selection: CropSelection | None = None
) -> dict[str, object]:
    if store.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found.")

    crop_ids = selection.crop_ids if selection and selection.crop_ids else None
    cost_estimate = _build_evaluation_cost_estimate(collection_id, crop_ids)
    job_id = new_id("evaljob")
    _set_evaluation_job(
        job_id,
        {
            "job_id": job_id,
            "collection_id": collection_id,
            "status": "queued",
            "current": 0,
            "total": 0,
            "current_crop_id": None,
            "current_crop_label": None,
            "current_crop_image_url": None,
            "message": "Queued evaluation",
            "error": None,
            "cost_estimate": cost_estimate,
            "cost_actual": None,
        },
    )
    thread = Thread(
        target=_run_evaluation_job,
        args=(job_id, collection_id, crop_ids),
        daemon=True,
    )
    thread.start()
    return _get_evaluation_job_or_404(job_id)


@app.get("/api/evaluation-jobs/{job_id}")
def get_evaluation_job(job_id: str) -> dict[str, object]:
    return _get_evaluation_job_or_404(job_id)


@app.post("/api/evaluation-runs/{run_id}/resume")
def resume_evaluation_run(run_id: str) -> dict[str, object]:
    run = store.get_evaluation_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    if run.status not in {"interrupted", "failed"}:
        raise HTTPException(
            status_code=400,
            detail=f"Only interrupted or failed runs can be resumed (status: {run.status}).",
        )

    job_id = new_id("evaljob")
    _set_evaluation_job(
        job_id,
        {
            "job_id": job_id,
            "collection_id": run.collection_id,
            "status": "queued",
            "current": 0,
            "total": 0,
            "current_crop_id": None,
            "current_crop_label": None,
            "current_crop_image_url": None,
            "message": "Queued evaluation resume",
            "error": None,
            "cost_estimate": run.settings.get("cost_estimate"),
            "cost_actual": None,
            "resumed_run_id": run.run_id,
        },
    )
    thread = Thread(
        target=_run_evaluation_job,
        args=(job_id, run.collection_id, None),
        kwargs={"resume_run_id": run.run_id},
        daemon=True,
    )
    thread.start()
    return _get_evaluation_job_or_404(job_id)


@app.post("/api/collections/{collection_id}/evaluation-cost-estimate")
def estimate_collection_evaluation_cost(
    collection_id: str, selection: CropSelection | None = None
) -> dict[str, object]:
    if store.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found.")
    crop_ids = selection.crop_ids if selection and selection.crop_ids else None
    return _build_evaluation_cost_estimate(collection_id, crop_ids)


@app.get("/api/settings")
def get_app_settings() -> dict[str, object]:
    settings = get_settings()
    return {
        "vision_provider": settings.vision_provider,
        "openai_api_key_set": bool(settings.openai_api_key),
        "openai_vision_model": settings.openai_vision_model,
        "openai_vision_detail": settings.openai_vision_detail,
    }


@app.post("/api/settings")
def update_app_settings(update: AppSettingsUpdate) -> dict[str, object]:
    provider = update.vision_provider.strip().lower() or "none"
    if provider not in {"none", "openai"}:
        raise HTTPException(status_code=400, detail="Vision provider must be none or openai.")

    values = {
        "PHILALENS_VISION_PROVIDER": provider,
        "PHILALENS_OPENAI_VISION_MODEL": update.openai_vision_model.strip() or "gpt-4.1-mini",
        "PHILALENS_OPENAI_VISION_DETAIL": update.openai_vision_detail.strip() or "high",
    }
    if update.openai_api_key is not None and update.openai_api_key.strip():
        values["OPENAI_API_KEY"] = update.openai_api_key.strip()

    _write_env_values(PROJECT_ROOT / ".env", values)
    for key, value in values.items():
        environ[key] = value
    return get_app_settings()


@app.get("/api/collections/{collection_id}/evaluation-runs/latest")
def get_latest_evaluation_run(collection_id: str) -> dict[str, object]:
    if store.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found.")
    run = store.get_latest_evaluation_run(collection_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    export = build_evaluation_run_export(store, run.run_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return export


@app.get("/api/evaluation-runs/{run_id}")
def get_evaluation_run(run_id: str) -> dict[str, object]:
    export = build_evaluation_run_export(store, run_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return export


@app.get("/api/collections/{collection_id}/export.json")
def export_collection_json(collection_id: str) -> JSONResponse:
    export = build_collection_export(store, collection_id)
    if export is None:
        raise HTTPException(status_code=404, detail="Collection not found.")

    return JSONResponse(
        content=export,
        headers={"Content-Disposition": f'attachment; filename="philalens-{collection_id}.json"'},
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


@app.post("/api/crops/delete")
def delete_crops(selection: CropSelection) -> dict[str, object]:
    if not selection.crop_ids:
        raise HTTPException(status_code=400, detail="Select at least one crop.")

    crops = []
    for crop_id in selection.crop_ids:
        crop = store.get_crop(crop_id)
        if crop is None:
            raise HTTPException(status_code=404, detail=f"Crop not found: {crop_id}")
        crops.append(crop)

    pages = [store.get_page(crop.page_id) for crop in crops]
    if any(page is None for page in pages):
        raise HTTPException(status_code=404, detail="Page not found for one or more crops.")

    collection_ids = {page.collection_id for page in pages if page is not None}
    if len(collection_ids) != 1:
        raise HTTPException(status_code=400, detail="Selected crops must belong to one collection.")
    collection_id = next(iter(collection_ids))

    for crop in crops:
        store.delete_crop(crop.crop_id)
        Path(crop.crop_path).unlink(missing_ok=True)

    export = build_collection_export(store, collection_id)
    if export is None:
        raise HTTPException(status_code=500, detail="Collection was not found after crop deletion.")
    return export


@app.post("/api/crops/mark-ready")
def mark_crops_ready(selection: CropSelection) -> dict[str, object]:
    if not selection.crop_ids:
        raise HTTPException(status_code=400, detail="Select at least one crop.")

    crops = []
    for crop_id in selection.crop_ids:
        crop = store.get_crop(crop_id)
        if crop is None:
            raise HTTPException(status_code=404, detail=f"Crop not found: {crop_id}")
        crops.append(crop)

    pages = [store.get_page(crop.page_id) for crop in crops]
    if any(page is None for page in pages):
        raise HTTPException(status_code=404, detail="Page not found for one or more crops.")

    collection_ids = {page.collection_id for page in pages if page is not None}
    if len(collection_ids) != 1:
        raise HTTPException(status_code=400, detail="Selected crops must belong to one collection.")
    collection_id = next(iter(collection_ids))

    for crop in crops:
        store.update_crop(replace(crop, review_state=REVIEW_UNREVIEWED, warnings=[]))

    export = build_collection_export(store, collection_id)
    if export is None:
        raise HTTPException(status_code=500, detail="Collection was not found after crop update.")
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
    settings = get_settings()
    page = store.get_page(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found.")

    old_crop_paths = {Path(crop.crop_path) for crop in store.list_crops_for_page(page.page_id)}

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

    new_crop_paths = {Path(crop.crop_path) for crop in segmentation.crops}
    for orphaned in old_crop_paths - new_crop_paths:
        orphaned.unlink(missing_ok=True)

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


@app.delete("/api/collections/{collection_id}")
def delete_collection(collection_id: str) -> dict[str, object]:
    if store.get_collection(collection_id) is None:
        raise HTTPException(status_code=404, detail="Collection not found.")

    store.delete_collection(collection_id)
    collection_dir = get_settings().collections_dir / collection_id
    shutil.rmtree(collection_dir, ignore_errors=True)
    return {"deleted": collection_id}


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


def _write_env_values(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    updated: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in values:
            updated.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            updated.append(line)
    for key, value in values.items():
        if key not in seen:
            updated.append(f"{key}={value}")
    path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def _build_evaluation_cost_estimate(
    collection_id: str,
    crop_ids: list[str] | None = None,
) -> dict[str, object]:
    settings = get_settings()
    crops = _evaluation_crops(collection_id, crop_ids)
    billable_crops = [crop for crop in crops if crop.review_state != REVIEW_NEEDS_CROP_REVIEW]
    skipped_crop_review_count = len(crops) - len(billable_crops)
    provider = settings.vision_provider.strip().lower() or "none"
    if provider != "openai":
        return non_openai_cost_estimate(
            provider=provider,
            crop_count=len(crops),
            billable_api_call_count=0,
            skipped_crop_review_count=skipped_crop_review_count,
        )

    return estimate_openai_vision_run_cost(
        model=settings.openai_vision_model,
        image_detail=settings.openai_vision_detail,
        crop_count=len(crops),
        billable_api_call_count=len(billable_crops),
        skipped_crop_review_count=skipped_crop_review_count,
    )


def _evaluation_crops(collection_id: str, crop_ids: list[str] | None = None) -> list[StampCrop]:
    selected_ids = set(crop_ids) if crop_ids else None
    crops = [
        crop
        for page in store.list_pages(collection_id)
        for crop in store.list_crops_for_page(page.page_id)
        if selected_ids is None or crop.crop_id in selected_ids
    ]
    if selected_ids is not None:
        found_ids = {crop.crop_id for crop in crops}
        missing_ids = sorted(selected_ids - found_ids)
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Selected crop not found in collection: {missing_ids[0]}",
            )
    return crops


def _evaluation_complete_message(evaluated_count: int, cost_actual: object) -> str:
    cost_label = _api_cost_label(cost_actual)
    if cost_label:
        return f"Evaluation complete: {evaluated_count} stamps checked, API cost {cost_label}"
    return f"Evaluation complete: {evaluated_count} stamps checked"


def _api_cost_label(cost_payload: object) -> str | None:
    if not isinstance(cost_payload, dict):
        return None
    api_call_count = cost_payload.get("api_call_count")
    if not isinstance(api_call_count, int | float) or int(api_call_count) <= 0:
        return None
    cost = cost_payload.get("total_cost_usd")
    if not isinstance(cost, int | float):
        cost = cost_payload.get("known_total_cost_usd")
    if not isinstance(cost, int | float):
        return None
    return f"${cost:.4f}" if float(cost) < 0.01 else f"${cost:.2f}"


def _run_evaluation_job(
    job_id: str,
    collection_id: str,
    crop_ids: list[str] | None,
    resume_run_id: str | None = None,
) -> None:
    _update_evaluation_job(job_id, status="running", message="Starting evaluation")
    try:
        vision_adapter = build_vision_adapter_from_settings(get_settings())

        def report_progress(current: int, total: int, crop) -> None:
            _update_evaluation_job(
                job_id,
                status="running",
                current=current,
                total=total,
                current_crop_id=crop.crop_id,
                current_crop_label=f"Stamp {crop.crop_index}",
                current_crop_image_url=f"/media/crops/{crop.crop_id}",
                message=f"Analyzing Stamp {crop.crop_index}",
            )

        run = evaluate_collection_readiness(
            store,
            collection_id,
            vision_adapter=vision_adapter,
            crop_ids=crop_ids,
            progress_callback=report_progress,
            resume_run_id=resume_run_id,
        )
        if run is None:
            _update_evaluation_job(
                job_id,
                status="failed",
                message="Collection not found",
                error="Collection not found.",
            )
            return
        export = build_collection_export(store, collection_id)
        evaluated_count = 0
        if export and export.get("latest_evaluation_summary"):
            summary = export["latest_evaluation_summary"]
            if isinstance(summary, dict):
                evaluated_count = int(summary.get("evaluated_stamp_count") or 0)
        _update_evaluation_job(
            job_id,
            status="completed",
            current=evaluated_count,
            total=evaluated_count,
            message=_evaluation_complete_message(evaluated_count, run.settings.get("cost_actual")),
            run_id=run.run_id,
            cost_actual=run.settings.get("cost_actual"),
        )
    except Exception as exc:
        _update_evaluation_job(
            job_id,
            status="failed",
            message="Evaluation failed",
            error=str(exc),
        )


def _set_evaluation_job(job_id: str, payload: dict[str, object]) -> None:
    with evaluation_jobs_lock:
        evaluation_jobs[job_id] = payload
        # Bound the in-memory progress map: drop the oldest finished jobs.
        if len(evaluation_jobs) > _MAX_TRACKED_EVALUATION_JOBS:
            finished = [
                tracked_id
                for tracked_id, job in evaluation_jobs.items()
                if job.get("status") in {"completed", "failed"}
            ]
            for tracked_id in finished[: len(evaluation_jobs) - _MAX_TRACKED_EVALUATION_JOBS]:
                evaluation_jobs.pop(tracked_id, None)


def _update_evaluation_job(job_id: str, **updates: object) -> None:
    with evaluation_jobs_lock:
        job = dict(evaluation_jobs.get(job_id, {"job_id": job_id}))
        job.update(updates)
        evaluation_jobs[job_id] = job


def _get_evaluation_job_or_404(job_id: str) -> dict[str, object]:
    with evaluation_jobs_lock:
        job = evaluation_jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Evaluation job not found.")
        return dict(job)
