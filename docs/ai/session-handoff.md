# Session Handoff

Last updated: 2026-08-07

## Latest Session (2026-08-07): UI Redesign — Workflow-First, Light+Dark

The user ran the first real OpenAI calibration (46 stamps, $0.07,
identifications judged good) and approved a full UI/UX redesign from an
interactive mockup. Implemented:

- Three workflow views replacing the single mega-screen: **Overview** (stat
  tiles, dynamic next-step card, clickable value-triage bar, attention shelf,
  country breakdown from AI candidates, exports), **Curate** (page cards with
  progress, page canvas, keyboard-first review queue: K keep / F fix /
  D delete / arrow skip, hands off to the crop-editor inspector with
  back-to-queue), **Stamps** (card gallery with search, bucket filter chips,
  attention-first sort, detail drawer with identity headline, bucket
  rationale, confidence bar, unverified-AI note, Escape to close).
- Light + dark themes via CSS variables and `data-theme` on the root;
  toggle in the top bar persisted to localStorage, default follows the OS.
  Bucket colors are semantic and CVD-validated per theme
  (common/interesting/investigate/fixcrop/none). Human-readable bucket
  labels ("Common", "Fix crop") via `frontend/src/buckets.ts`.
- Evaluation job progress lives in a top-bar pill (non-blocking);
  Evaluate-all shows a cost-estimate confirm dialog before spending.
- Removed `StampList.tsx`/`EvaluationPanel.tsx`; multi-select batch actions
  were replaced by the review queue (single-crop actions remain in the
  drawer/inspector).

All 44 backend tests pass; frontend typechecks. Browser-verified in both
themes against the live calibration collection, including a real keyboard
queue deletion of a false-positive crop.

Next: the user curates the remaining ~61 flagged crops (queue) and re-runs
evaluation on the fixed crops; then Phase 3 (market evidence adapters).

## Earlier Session (2026-08-06, part 4): Phase 2 Implemented — Tier 1 Identification

All 44 backend tests pass. Implemented per `docs/rebuild-plan-v2.md` Phase 2
notes: `stamp-observation-v2` (identity candidates + prior value bucket),
rewritten vision prompt, `VisionAnalysisResult` adapter contract,
perceptual-hash duplicate grouping (`similarity.py`) with one vision call per
group and `derived_from_duplicate` fan-out, valuation from model prior
buckets (pipeline `tier1-identification-v2`), candidates rendered in the
inspector. A 3-page calibration collection (108 crops) exists in
`data/local/`.

NEXT STEP (requires the user): curate calibration crops in the UI, set the
OpenAI API key in Settings, run selected-crop evaluation, and judge
identification quality; iterate the prompt if needed. Then Phase 3 (market
evidence adapters for flagged outliers).

## Earlier Session (2026-08-06, part 3): Phase 1 Complete — React SPA

The old inline-HTML visualizer is gone. The UI is now a Vite + React 19 +
TypeScript SPA under `frontend/`, served by FastAPI from `frontend/dist`
(build with `cd frontend && npm install && npm run build`). Backend: 33 tests
pass; `visualizer.py` deleted; costing dashboard machinery removed
(`/api/settings` no longer returns `cost_dashboard`).

SPA features: page list, coverage-mode shading, click-select on page and
list, stamp list with thumbnails/badges/filter chips (pending review +
value buckets), multi-select batch delete/mark-ready/evaluate, inspector
with zoomed crop editor (corner drag-resize, move, rotation handle, numeric
fields), observation/valuation/candidate/evidence detail, evaluation panel
with cost estimate, live job progress, resume buttons for interrupted runs,
settings dialog, JSON/CSV export buttons, collection deletion.

Browser-verified against a real HEIC album page (ALBUM2_0664.HEIC): upload,
YOLO re-detect (2 OpenCV crops → 54 YOLO crops after installing `.[yolo]`
and downloading the model), crop drag-resize with image cache-busting,
evaluate-all job to completion with bucket chips. The YOLO model now lives
in `data/local/models/` on this machine.

Next session: Phase 2 — extend `stamp-observation-v1` to v2 (candidate
identity + prior value bucket in one vision call), perceptual-hash duplicate
grouping, calibrate the prompt on 2-4 real pages with the OpenAI provider.

## Earlier Session (2026-08-06, part 2): Phase 0 Complete

Phase 0 of `docs/rebuild-plan-v2.md` was implemented. All 33 tests pass
(`cd backend && .venv/bin/python -m pytest -q`). Changes:

- Deleted dead code: `pipeline.py`, `/analyze/pages`, placeholder dataclass
  family in `models.py`, `embedding_index` table + CRUD, `test_pipeline.py`,
  `test_visualizer.py`.
- Fixed the settings bug: `Settings` fields use `default_factory` (env read at
  instantiation), `config.load_env_file` loads `.env` at import without
  overriding set vars, `api.py` uses `get_settings()` per request. Settings
  changes now take effect without restart (tested).
- Crop bbox now matches saved crop pixels: detection stores the padded box;
  manual recrops write exactly the drawn box (no hidden padding).
- YOLO model cached per resolved path (was reloaded per page).
- Evaluation durability: startup marks stale `running`/`pending` runs as
  `interrupted`; `POST /api/evaluation-runs/{run_id}/resume` resumes
  interrupted/failed runs skipping crops that already have a valuation record
  in the run; vision calls retry with `VISION_RETRY_BACKOFF_SECONDS` backoff;
  in-memory job map bounded to 50 entries.
- File hygiene: redetect unlinks replaced crop files (incl. `_manual.jpg`);
  new `DELETE /api/collections/{collection_id}` removes rows via FK cascade
  plus the collection directory.
- Deferred to Phase 1: costing-dashboard removal (old visualizer renders it)
  and the visualizer XSS (dies with the React rewrite).

Next session: Phase 1 — Vite + React + TypeScript SPA under `frontend/`,
served by FastAPI; port the crop-review interactions, add triage queues and
stamp detail views; then delete `visualizer.py` and trim `costing.py`.

## Earlier Session (2026-08-06, part 1): Audit + Rebuild Plan V2

A full code audit was performed and a new execution plan written to
`docs/rebuild-plan-v2.md` (supersedes `docs/final-tool-build-plan.md`).

User decisions: OpenAI-only vision provider, personal-collection scope,
Vite + React SPA rewrite of the visualizer, recapture loop enabled (user has
the physical albums). Valuation strategy: three-tier funnel (LLM
identification + value bucket for all crops → market evidence for outliers →
recapture kit/expert review for shortlist).

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
