# Session Handoff

Last updated: 2026-07-02

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
- Durable evaluation foundation in SQLite: evaluation runs, stamp observations,
  catalog candidates, source evidence, stamp valuations, and embedding metadata.
- Browser `Evaluate` action and API endpoint for creating a completed
  crop-readiness evaluation run with placeholder observations and conservative
  buckets.
- Strict `stamp-observation-v1` schema, parser, JSON schema helper, prompt
  shape, and conversion helper for AI vision observations.
- Optional OpenAI vision adapter wired into evaluation runs. It is disabled by
  default and only sends crop images externally when
  `PHILALENS_VISION_PROVIDER=openai` and `OPENAI_API_KEY` are configured.
- Local value triage over AI-visible observations. It creates non-price buckets
  such as `likely_common`, `possibly_interesting`, `needs_expert_check`, and
  `needs_source_matching`.
- OpenAI evaluation cost tracking. The API can return a rough pre-run estimate
  for the current collection or selected crops, and completed runs summarize
  returned token usage plus local USD cost calculations when usage is present.
- Blank optional values copied from `.env.example` are treated as unset, so
  `PHILALENS_STAMP_YOLO_MODEL_PATH=` falls back to the default local model path
  instead of being interpreted as the current directory.
- Collection exports include latest evaluation-run fields and summary data when
  records exist.
- Browser visualizer at `/` for upload, page review, crop inspection, selected
  stamp highlighting on the full page, inspector-based crop-box resizing with
  drag handles or numeric fields, no-selection coverage shading for spotting
  missed crops, manual crop drawing for missed stamps, inspector-based crop
  rotation with a drag handle, a pending-review stamp filter, selected-crop
  deletion, selected-crop evaluation, selected-crop ready marking, topic-labeled
  crop/evaluation badges in the stamp list, crop deletion, page deletion, page
  re-detection, live evaluation progress with current crop thumbnail and API
  cost information when available, local OpenAI settings editing and a settings
  cost dashboard,
  independently scrolling side lists, and CSV/JSON exports.
- API endpoints for collection listing/detail, media serving, crop updates,
  manual crop creation, crop deletion, selected-crop deletion, selected-crop
  ready marking, page deletion, crop-readiness evaluation for full collections
  or selected crops, pollable evaluation jobs, evaluation cost estimates,
  evaluation-run reads, local settings with cost dashboard, and exports.
- Initial pipeline placeholder remains for backward-compatible smoke checks.
- Product, architecture, data strategy, and roadmap docs.
- `docs/project-northstar.md`, a consolidated final-tool northstar and staged
  specification for collection evaluation.
- `docs/final-tool-build-plan.md`, a detailed execution plan for heavy
  implementation sessions that keeps `/goal` prompts short while preserving the
  full plan in the repo.
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
- after crop detection and curation, the next phase should be automatic
  collection evaluation, guided by a durable northstar that future sessions can
  split into small steps
- the full 80-page collection should not be used as a development experiment;
  use 2-4 representative calibration pages until source-backed insights are
  trustworthy
- cropping is now considered mostly good, with only targeted crop/review
  adjustments needed unless calibration examples show concrete failures
- the user does not have a catalog CSV, so the first source-backed matching path
  should rely on open/permitted APIs and source adapters rather than assuming a
  user-provided catalog export

## What Is Not Built Yet

- OCR beyond the optional structured OpenAI vision observation adapter.
- Catalog matching.
- Market evidence retrieval.
- Value estimation.
- Source-backed processing for evaluation runs beyond optional observation
  triage.
- Candidate/valuation review workflow beyond crop review.
- Empirical tuning of YOLO confidence/margins against more of the user's real
  HEIC pages.
- Source adapters, local similarity search, duplicate grouping, real valuation
  buckets beyond the crop-readiness skeleton, marketplace evidence adapters, and
  collection evaluation dashboards beyond the settings cost summary.

## Research Conclusions

- Valuation must be evidence-weighted and expressed as ranges.
- A front album photo is useful for issuer, denomination, design, cancellation,
  centering, visible faults, and rough condition.
- A front album photo usually cannot determine gum, watermark, paper, hidden
  thins, regumming, repairs, or expertized authenticity.
- Start with user-imported/source-adapter data; avoid unlicensed catalog bundling.
- eBay Browse API may help with active listing evidence, including image search,
  but active asking prices are weaker than realized sales.
- Recent open-source scan did not find a mature end-to-end stamp valuation
  system. Reusable ideas come from `code2k13/philately-tool` for local vector
  search, structured catalogue projects such as Canadian Stamp Identifier, and
  adjacent inventory tools such as My Stamps and OpenNumismat.
- A deeper source investigation found no clean open worldwide stamp catalog API
  with authoritative catalog IDs, images, variants, and values. The recommended
  source order is Wikidata/Commons first, Smithsonian Open Access second,
  Europeana third, WNS/WADP only if usable access is confirmed, and eBay Browse
  only later as weak active-listing evidence.
- Evaluation should run as a durable, versioned process over curated crops and
  should produce observations, candidates, source evidence, valuation buckets,
  recommended next actions, and conservative collection summaries.

## Recommended Next Session Start

1. Read `AGENTS.md`.
2. Read `docs/ai/context.md`.
3. Read `docs/product-brief.md`, `docs/product-workflow.md`,
   `docs/project-northstar.md`, `docs/final-tool-build-plan.md`,
   `docs/architecture.md`,
   `docs/data-strategy.md`, and `docs/research/`.
4. Check `git status --short --branch`.
5. Run the backend tests if dependencies are installed:
   `cd backend && .venv/bin/python -m pytest -q`.
6. To enable the better cropper, install `.[yolo]` and run
   `python3 scripts/download_stamp_detector.py`.
7. Start the local app with `cd backend && .venv/bin/uvicorn philalens.api:app --reload`.

## Next Good Tasks

- Follow `docs/final-tool-build-plan.md` for the next heavy implementation
  session.
- Add the source adapter foundation and first Wikidata/Commons adapter slice.
- Wire candidate retrieval into selected-crop evaluation only.
- Add local similarity search and duplicate clustering as supporting retrieval.
- Calibrate the triage buckets against real pages and known examples.
- Harden the AI observation prompt and skip/downgrade policy against more real
  crops.
- Use 2-4 representative calibration pages rather than the full 80-page
  collection until source-backed insight quality is proven.
- Improve segmentation/crop review only when calibration examples show specific
  remaining failures.
- Improve drag-handle crop editing based on hands-on use.
