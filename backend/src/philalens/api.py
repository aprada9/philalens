"""FastAPI entrypoint for Philalens."""

from dataclasses import asdict

from fastapi import FastAPI, File, UploadFile

from .config import settings
from .pipeline import build_empty_page_analysis, summarize_collection

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI-assisted stamp collection analysis and valuation research API.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze/pages")
async def analyze_pages(files: list[UploadFile] = File(...)) -> dict[str, object]:
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
        "note": "This endpoint currently validates intake and response shape only.",
    }

