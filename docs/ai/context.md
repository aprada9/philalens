# Philalens Agent Context

Last updated: 2026-06-29

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

- a minimal Python/FastAPI backend under `backend/`
- dataclass-based initial domain models in `backend/src/philalens/models.py`
- placeholder pipeline functions in `backend/src/philalens/pipeline.py`
- an intake-shaped API endpoint in `backend/src/philalens/api.py`
- product, architecture, data, and roadmap docs under `docs/`
- product workflow and research notes under `docs/product-workflow.md` and
  `docs/research/`
- agent context infrastructure through `AGENTS.md` and `docs/ai/`

The following are not implemented yet:

- real image upload persistence
- page preprocessing
- stamp detection and cropping
- OCR
- AI vision extraction
- catalog/reference matching
- market evidence retrieval
- valuation logic
- review UI
- export workflow

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

- Backend-first foundation using Python and FastAPI.
- Structured data models before UI complexity.
- Evidence-first analysis pipeline.
- Manual review should be part of the product, not an afterthought.
- Segmentation-first workflow: detect page regions, crop stamps, review crops,
  then perform OCR/vision, candidate matching, and valuation.
- Valuation should use low/high ranges with identity confidence, condition
  confidence, source evidence, and recommended next action.

## Open Product Questions

- Should the first UI be a local web app, desktop-like app, or hosted web app?
- What image quality and formats should the MVP assume?
- Which catalog/reference sources are legally usable for the first version, and
  should the MVP begin with user-imported catalog data?
- Should the first matching strategy rely on user-provided catalog data, public
  references, or API-backed providers?
- What export formats matter first: CSV, JSON, PDF report, or spreadsheet?
- How much manual correction is needed for stamp crops in the MVP?

## Next Likely Work

1. Define the product workflow in more detail with the user.
2. Decide first UI and deployment target.
3. Decide initial source policy: user-imported data first, API-backed providers,
   or hybrid.
4. Design the persistent data model for pages, crops, observations, candidates,
   evidence, valuations, and review status.
5. Implement image upload persistence and page records.
6. Add first stamp segmentation prototype.
