# Session Handoff

Last updated: 2026-06-30

## Current State

Philalens has moved from placeholder foundation to a first local MVP foundation:

- Python/FastAPI backend.
- Local SQLite/filesystem persistence under `data/local/` by default.
- HEIC/HEIF-aware image intake through `pillow-heif`.
- Batch upload endpoint for album page images.
- Normalized JPEG page derivatives for browser display and segmentation.
- Classical OpenCV stamp-region segmentation prototype.
- Optional Ultralytics YOLO stamp detector path, plus
  `scripts/download_stamp_detector.py` to download the Apache-2.0 model from
  `code2k13/philately-tool` into ignored local storage.
- Stored crop images, bounding boxes, confidence, warnings, and review state.
- Crop boxes flagged as `needs_crop_review` when confidence or geometry is
  suspicious.
- Browser visualizer at `/` for upload, page review, crop inspection, selected
  stamp highlighting on the full page, inspector-based crop-box resizing with
  drag handles or numeric fields, no-selection coverage shading for spotting
  missed crops, manual crop drawing for missed stamps, inspector-based crop
  rotation with a drag handle, a pending-review stamp filter, crop deletion,
  page deletion, page re-detection, independently scrolling side lists, and
  CSV/JSON exports.
- API endpoints for collection listing/detail, media serving, crop updates,
  manual crop creation, crop deletion, page deletion, and exports.
- Initial pipeline placeholder remains for backward-compatible smoke checks.
- Product, architecture, data strategy, and roadmap docs.
- Agent operating guide and context infrastructure.
- Context guard script and GitHub Actions workflow.
- Product workflow and research notes for segmentation, valuation, and data
  sources.

## What The User Has Explained

The user owns many stamp album photos. Each page contains multiple stamps. The
target product should upload those photos, identify and analyze individual
stamps, cross-check against available sources, estimate individual stamp values,
and summarize full collection value.

The user specifically wants the repo to be easy for AI agents to develop,
maintain, and improve. New sessions should learn context from repo files rather
than requiring repeated chat history.

The user uploaded `ALBUM2_0659.HEIC` as the first real example. It is a
4032 x 3024 HEIC photo of a black album page with many mostly French used
stamps. The image confirms the workflow must isolate each stamp on a page before
analysis and must handle rotated, overlapping, partial, and tightly spaced
stamps.

The user clarified:

- the first app should be local
- storage should use SQLite plus filesystem storage
- the real batch format is mostly HEIC, about 80 page images
- first exports should be CSV and JSON
- the tool should include a visualizer for stamp-by-stamp review
- crop correction should be automatic-first, with manual review requested for
  suspicious crops
- the first OpenCV cropper was not good enough, so an open-source YOLO detector
  path was reviewed and integrated as optional local tooling
- after testing, the YOLO cropper was good but missed whole rows on the sample
  page: 41 detected out of about 68 stamps
- numeric-only crop correction was not pragmatic; crop boxes need draggable
  corner handles
- the left stamp list must scroll independently so the main image and selected
  stamp remain visible
- crop resizing should happen in the per-stamp inspector, not directly on the
  full-page view
- selecting a stamp in the list should highlight its location in the full page
- no-selection page review should make missed stamps easier to spot by shading
  areas outside detected crop boxes
- false-positive crop boxes and uploaded pages should be removable from the
  visualizer so the user can clean up or re-upload from scratch
- a quick filter should show crops pending crop review
- missed stamps should be addable with a manual full-page drag crop
- rotated stamps should be correctable dynamically in the selected-stamp
  inspector, without adding numeric rotation inputs

## What Is Not Built Yet

- OCR or AI vision extraction.
- Catalog matching.
- Market evidence retrieval.
- Value estimation.
- Durable observation, candidate, source evidence, and valuation tables.
- Candidate/valuation review workflow beyond crop review.
- Empirical tuning of YOLO confidence/margins against more of the user's real
  HEIC pages.

## Research Conclusions

- Valuation must be evidence-weighted and expressed as ranges.
- A front album photo is useful for issuer, denomination, design, cancellation,
  centering, visible faults, and rough condition.
- A front album photo usually cannot determine gum, watermark, paper, hidden
  thins, regumming, repairs, or expertized authenticity.
- Start with user-imported/source-adapter data; avoid unlicensed catalog bundling.
- eBay Browse API may help with active listing evidence, including image search,
  but active asking prices are weaker than realized sales.

## Recommended Next Session Start

1. Read `AGENTS.md`.
2. Read `docs/ai/context.md`.
3. Read `docs/product-brief.md`, `docs/product-workflow.md`,
   `docs/architecture.md`, `docs/data-strategy.md`, and `docs/research/`.
4. Check `git status --short --branch`.
5. Run the backend tests if dependencies are installed:
   `cd backend && .venv/bin/python -m pytest -q`.
6. To enable the better cropper, install `.[yolo]` and run
   `python3 scripts/download_stamp_detector.py`.
7. Start the local app with `cd backend && .venv/bin/uvicorn philalens.api:app --reload`.

## Next Good Tasks

- Run a real HEIC batch through the local visualizer and inspect segmentation
  failure cases using the optional YOLO detector.
- Compare results across more pages and tune detector confidence, crop margins,
  and review flags beyond the first sample page.
- Improve segmentation for rotated, overlapping, partial, and tightly spaced
  stamps.
- Improve drag-handle crop editing based on hands-on use.
- Add persistent tables for stamp observations, candidates, evidence,
  valuations, and recommended next actions.
- Add AI vision extraction for individual crop observations with schema tests.
- Define the source adapter schema and first catalog/reference import path.
