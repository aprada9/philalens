# Philalens Agent Context

Last updated: 2026-06-30

## User Intent

The user has many stamp album page photos, around 80 or more images for a
collection. Each page contains multiple stamps. The desired tool should let the
user upload page photos, analyze each stamp, cross-check against existing
databases, philatelic knowledge, and available market evidence, then estimate
the potential value of each stamp and the whole collection.

The chosen repository and product name is Philalens.

The first reviewed example image is `ALBUM2_0659.HEIC`, a 4032 x 3024 HEIC album
page photo with many mostly French used stamps on dark album stock. It includes
regular rows, rotated stamps, overlapping stamps, cancellations, album rings,
page edges, and partial crops. This confirms the first hard problem is robust
page-to-stamp segmentation with manual correction, not isolated single-stamp
classification.

## Product Posture

Philalens should behave like an AI-assisted research, inventory, and valuation
triage tool. It should not present estimates as formal appraisals.

The product should optimize for evidence-backed triage: quickly classify likely
common material, surface possible outliers, and recommend better images or expert
review where value depends on unobservable factors.

The product must preserve:

- evidence behind identifications
- confidence for each candidate
- uncertainty and missing observations
- source attribution
- human review status

## Current Implementation

The repository contains:

- a Python/FastAPI backend under `backend/`
- dataclass-based domain models in `backend/src/philalens/models.py`
- local SQLite/filesystem persistence in `backend/src/philalens/storage.py`
- HEIC-aware image normalization in `backend/src/philalens/imaging.py`
- optional YOLO stamp segmentation plus OpenCV fallback in
  `backend/src/philalens/segmentation.py`
- CSV/JSON export shaping in `backend/src/philalens/exports.py`
- a local browser visualizer in `backend/src/philalens/visualizer.py`
- a downloader for the optional Apache-2.0 detector model in
  `scripts/download_stamp_detector.py`
- API endpoints in `backend/src/philalens/api.py` for collection upload,
  collection review, media serving, crop correction, and exports
- product, architecture, data, and roadmap docs under `docs/`
- product workflow and research notes under `docs/product-workflow.md` and
  `docs/research/`
- agent context infrastructure through `AGENTS.md` and `docs/ai/`

The current local app can:

- upload batches of page images
- support HEIC/HEIF via `pillow-heif`
- store originals under `data/local/`
- create normalized JPEG page images
- detect likely stamp crop regions with YOLO when the optional model/dependency
  are present, otherwise with OpenCV fallback
- flag suspicious crops as `needs_crop_review`
- let the user inspect pages and crops in a local browser visualizer
- locate the selected stamp through a strong full-page highlight
- show a no-selection coverage mode that shades non-cropped page areas so
  missed stamps are easier to spot
- update crop boxes in the selected-stamp inspector with drag handles or numeric
  fields
- create manual crop boxes on the full-page view for stamps missed by automatic
  detection
- rotate selected crop boxes in the inspector with a drag handle; rotation is
  persisted as `rotation_degrees` and reflected in crop images and exports
- re-detect an existing page with current detector settings
- remove false-positive crop boxes and remove uploaded pages for clean re-upload
- filter the stamp list to crops pending crop review
- export collection data as CSV and JSON

The following are not implemented yet:

- OCR
- AI vision extraction
- catalog/reference matching
- market evidence retrieval
- valuation logic
- durable stamp observation/candidate/valuation tables
- reviewed valuation workflow

## Important Constraints

- Stamp identity often depends on subtle differences: watermark, perforation,
  paper, overprint, color shade, cancellation, gum, and condition.
- Catalog data may be copyrighted or licensed. Do not bundle restricted data
  without explicit permission.
- Asking prices are weaker evidence than realized sale prices.
- AI output must be reviewable and should carry confidence and rationale.
- Future agents must update durable context when they alter project direction.
- A single front-side album photo cannot reliably prove watermark, paper, gum,
  regumming, hidden thins, hidden repairs, or expertized authenticity.
- Active marketplace listings are weaker evidence than realized sale prices.

## Current Technical Direction

- Local-first foundation using Python, FastAPI, SQLite, and filesystem storage.
- Structured data models before UI complexity.
- Evidence-first analysis pipeline.
- Manual review should be part of the product, not an afterthought.
- Segmentation-first workflow: detect page regions, crop stamps, review crops,
  then perform OCR/vision, candidate matching, and valuation.
- Valuation should use low/high ranges with identity confidence, condition
  confidence, source evidence, and recommended next action.
- Batch HEIC image intake is part of the MVP because the user's collection is
  mostly HEIC album page photos.
- Automatic segmentation should be attempted first; manual crop correction
  should be requested for low-confidence or suspicious crops.
- The OpenCV cropper is known to be weak. The better local detector path is an
  optional Ultralytics YOLO model from the Apache-2.0 `code2k13/philately-tool`
  repository. The model is downloaded into `data/local/models/`, not committed.
- On the sample HEIC page, the previous YOLO threshold found 41 crops while the
  lower review-mode threshold finds 68 candidates. Low-confidence detections
  are flagged with `low_detector_confidence` and `needs_crop_review`.
- The visualizer keeps the left page/stamp lists scrolling independently from
  the main image and inspector.
- The visualizer treats no selected stamp as coverage-review mode: detected
  crops remain outlined and areas outside crop boxes are shaded to expose
  possible missed stamps.
- Crop records include `rotation_degrees`. Manual crop creation is done from the
  full-page view; crop resizing and rotation are done from the selected-stamp
  inspector.
- The second Reddit tool link supplied by the user was blocked by Reddit network
  security and no public source/license was found.

## Open Product Questions

- Which catalog/reference sources are legally usable for the first version, and
  should the MVP begin with user-imported catalog data?
- Should the first matching strategy rely on user-provided catalog data, public
  references, or API-backed providers?
- What minimum image quality warnings should block or defer AI analysis?
- What fields should be in the durable stamp observation, candidate, evidence,
  valuation, and review tables?
- What valuation confidence and escalation rules should be applied before
  showing collection-level ranges?

Resolved for now:

- First UI/deployment shape: local browser web app.
- Initial storage: SQLite plus filesystem under `data/local/`.
- Initial image format assumption: batch upload of mostly HEIC/HEIF photos,
  normalized to JPEG working images.
- First exports: CSV and JSON.
- Crop correction policy: automatic segmentation first, manual correction for
  suspicious/low-confidence crops while keeping all crops editable.
- First crop correction UX: full-page overlays are for selection/location, while
  crop resizing lives in the selected-stamp inspector with drag handles plus
  numeric bbox fields.
- First crop cleanup UX: false-positive crop boxes and uploaded pages can be
  deleted from the local visualizer, and pending review crops can be filtered.
- First manual crop UX: missed stamps can be added by drawing a crop rectangle
  on the full-page image, then adjusted and rotated in the inspector.

## Next Likely Work

1. Run the local visualizer against a larger real HEIC batch and collect
   segmentation failure cases with the optional YOLO detector enabled.
2. Tune confidence, margins, and review flags across more pages, not only the
   first sample page.
3. Improve segmentation for rotated, overlapping, partial, and tightly spaced
   stamps.
4. Improve crop review ergonomics after real drag-handle use.
5. Design durable tables for observations, candidates, evidence, valuations,
   and recommended next actions.
6. Add AI vision extraction for stamp crops with schema tests.
7. Decide initial catalog/source policy for matching and valuation.
