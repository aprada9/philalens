# Philalens Rebuild Plan V2

Last updated: 2026-08-06

This plan supersedes `docs/final-tool-build-plan.md` as the execution plan. It
follows a full code audit (2026-08-06) and explicit user decisions. The
northstar in `docs/project-northstar.md` remains valid; this plan changes the
route, not the destination.

## User Decisions (2026-08-06)

- Vision provider: **OpenAI** (existing adapter path; fix it, do not add a
  second provider now).
- Scope: **primarily the user's own ~80-page collection**. Optimize for getting
  the user's answer, not for a generalized product.
- The user **has physical access to the albums**: the recapture loop (backs,
  watermarks, close-ups for shortlisted stamps) is a real feature, not
  hypothetical.
- UI: **rewrite as a Vite + React SPA** served by FastAPI. The inline-HTML
  visualizer is deprecated.

## Audit Verdict (2026-08-06)

Roughly 35-40% of the codebase is kept. Full details in the session that
produced this plan; the durable conclusions:

Keep as-is:

- `storage.py` (durable SQLite schema already anticipates candidates,
  evidence, valuations)
- `observation_schema.py` (strict, uncertainty-preserving; best module)
- `imaging.py`, `exports.py`
- Most meaningful tests (`test_observation_schema.py`, `test_vision.py`,
  `test_evaluation.py`, `test_storage_exports.py`, `test_api.py`)

Keep with rework:

- `api.py`: fix settings bug, remove global mutable state, dedupe validation
  blocks, make evaluation resumable
- `evaluation.py`: keep run bookkeeping, replace skeleton logic with the real
  Tier 1 pass
- `segmentation.py`: keep crop I/O and review-loop plumbing; cache the YOLO
  model; treat OpenCV fallback as last resort

Rewrite:

- `visualizer.py` (1,906-line inline HTML/JS string) → React SPA under
  `frontend/`

Delete:

- `pipeline.py`, `/analyze/pages` endpoint, and the placeholder dataclass
  family in `models.py` (lines ~22-87)
- `embedding_index` table until something actually uses it
- Most of `costing.py`'s dashboard machinery (keep simple per-run token/cost
  recording)
- `test_pipeline.py`, `test_visualizer.py`

Known bugs to fix (audit findings):

1. Settings written via the UI never take effect: `config.py` evaluates env
   vars at import time and nothing reloads `.env`. The UI reports "saved" but
   lies. Fix by making `Settings` read env lazily (or reconstruct from a
   loaded `.env`) and loading `.env` at startup.
2. Crop bbox/image mismatch: `_write_crop` saves the padded box but stores the
   unpadded bbox. Store what the crop image actually contains.
3. YOLO model reloaded from disk per page — cache it.
4. Stored XSS: model output interpolated into `innerHTML` (goes away with the
   React rewrite; do not reintroduce).
5. `evaluation_jobs` is in-memory only and the sync `/evaluate` endpoint
   blocks; runs must be durable and resumable (a 3,500-crop run will crash at
   least once).
6. Orphaned crop files on re-detect; no collection deletion.

## Valuation Approach: Three-Tier Funnel

Reality check from the sample pages (Netherlands definitives, Spain 1958-59
commemoratives, Uruguay/Venezuela mid-century): 95%+ of the collection is
common used material worth EUR 0.05-0.50. Catalog prices overstate; common
used stamps trade in bulk lots at 5-20% of catalog. The tool's job is triage.

Expert workflow replicated: identify → variant → condition → catalog value →
discount to real market → realized-sales check for anything promising.

### Tier 1 — every curated crop (cheap, ~$0.01-0.03/crop)

One OpenAI vision call per crop (after duplicate grouping) returning an
extended structured observation:

- everything in `stamp-observation-v1` (visible text, issuer, denomination,
  date hints, cancellation, centering, faults, unobservable factors)
- candidate identity: country, series/issue name, approximate year, likely
  catalog family/range where the model is confident (e.g. "Spain 1959
  Velazquez set, Edifil ~1238-1247"), each with confidence
- a prior value bucket: `likely_common` / `possibly_interesting` /
  `investigate`, with a one-line rationale

Modern multimodal models encode substantial catalog knowledge for common
material; the schema must still force uncertainty (no invented exact catalog
numbers at high confidence). Full collection ≈ 3,500 crops ≈ $40-120 one-off,
less after duplicate grouping.

### Tier 2 — flagged outliers only (~5%)

Attach real market evidence:

- web search for the candidate issue (catalog references, dealer pages)
- eBay Browse keyword/image search; active listings stored as weak evidence,
  sold/completed as stronger where available
- open sources (Wikidata/Commons, Smithsonian) for reference images/metadata

Output: low/high value range with cited evidence records, or an explicit
`not_enough_evidence` state.

### Tier 3 — the shortlist (~10-30 stamps)

The tool generates a per-stamp "recapture kit": which stamps to re-photograph
(back, watermark area, perforation edge, close-up), what each new photo would
resolve, and whether expert review is warranted. The user has the albums, so
this loop closes: recaptured images attach to the stamp and upgrade condition
or variant confidence.

Guardrails carried over from the previous plan (still binding):

- No formal appraisals; ranges + confidence + evidence only.
- Asking prices never become standalone value estimates.
- No scraping of restricted catalogs (Colnect, StampWorld, Scott/Michel/Yvert
  data) without permission.
- Preserve uncertainty for watermark, paper, gum, hidden faults, authenticity.
- Calibrate on 2-4 representative pages before any full-collection run.
- External API calls only on explicit user action with visible cost.

## Build Phases

### Phase 0: Cleanup + foundations — DONE (2026-08-06)

- Delete dead code (pipeline, placeholder models, embedding table, costing
  dashboard surplus, trivial tests).
- Fix bugs 1-3, 5, 6 above.
- Make evaluation runs durable and resumable (persist job state; retries with
  backoff; batch checkpointing).
- Acceptance: tests pass; settings changes take effect without restart; a
  killed evaluation run resumes without repeating completed crops.

Completed 2026-08-06. Notes:

- Deleted: `pipeline.py`, `/analyze/pages`, the placeholder dataclass family,
  the `embedding_index` table/CRUD, `test_pipeline.py`, `test_visualizer.py`.
- Deferred to Phase 1: removing `costing.py`'s dashboard machinery — the
  current visualizer's settings dialog renders `cost_dashboard`, so it stays
  until the React SPA replaces that UI.
- Settings fix: `Settings` fields are now `default_factory`-based (read env at
  instantiation), `.env` loads at import without overriding set vars, and
  `api.py` builds settings per request via `get_settings()`. Covered by
  `test_settings_update_takes_effect_without_restart`.
- Segmentation: detected crops store the padded box as `bbox_xywh` (bbox now
  always matches saved crop pixels); manual recrops write exactly the drawn
  box; YOLO model cached per path.
- Evaluation: runs left `running`/`pending` are marked `interrupted` at API
  startup; `POST /api/evaluation-runs/{run_id}/resume` resumes interrupted or
  failed runs, skipping crops that already have a valuation in the run
  (per-crop checkpoint marker); vision calls retry with backoff
  (`VISION_RETRY_BACKOFF_SECONDS`); the in-memory job map is bounded.
- Cleanup: redetect unlinks replaced crop files;
  `DELETE /api/collections/{id}` removes rows (FK cascade) and the collection
  directory.

### Phase 1: React SPA — DONE (2026-08-06)

- `frontend/` with Vite + React + TypeScript; FastAPI serves the built assets
  and stays the API.
- Re-implement the proven review interactions: page list, coverage mode
  (shading outside crops), selected-stamp highlight, crop drag/resize/rotate,
  manual crop drawing, pending-review filter, batch select/delete/ready.
- Add what the old UI lacked: triage queues by bucket, stamp detail panel with
  observations/candidates/evidence, collection dashboard (counts by bucket,
  coverage, cost), evaluation progress.
- Escape/render all model output safely.
- Acceptance: full crop-curation workflow works in the SPA; old visualizer
  removed.

Completed 2026-08-06. Notes:

- `frontend/` is Vite + React 19 + TypeScript (strict), no other runtime
  dependencies. `npm run build` outputs `frontend/dist`, which FastAPI mounts
  at `/assets` and serves at `/` (with a build-instructions page when dist is
  missing). Vite dev mode proxies `/api` and `/media` to `127.0.0.1:8000`.
- Components: App (state + layout), PageViewer (SVG page with coverage
  shading, selection highlight, click-select, manual crop drawing), StampList
  (thumbnails, review/bucket badges, filter chips, multi-select batch
  actions), Inspector (crop preview, zoomed SVG crop editor with corner
  drag-resize, move, rotation handle, numeric fields, observation/valuation/
  candidate/evidence detail), EvaluationPanel (summary chips, cost estimate,
  job progress with live crop thumbnail, resume buttons for
  interrupted/failed runs), SettingsDialog.
- All model output rendered through React (no innerHTML) — the old XSS is
  gone. `visualizer.py` deleted; `costing.py` dashboard machinery removed
  (`/api/settings` no longer returns `cost_dashboard`; per-run cost recording
  kept).
- Verified in the browser against a real 4032x3024 HEIC album page: upload,
  YOLO re-detect (2 OpenCV crops → 54 YOLO crops), select from list and from
  page, drag-resize commit with crop image cache-busting, evaluate-all job
  with progress polling and bucket chips, settings dialog.

### Phase 2: Tier 1 identification pass

- Extend the observation schema (as `stamp-observation-v2`) with candidate
  identity + prior value bucket; update the prompt.
- Duplicate grouping first: perceptual hash (e.g. dHash) over curated crops;
  near-duplicate groups share one Tier 1 call and fan results out with a
  `derived_from_duplicate` marker.
- Run on the 2-4 calibration pages; iterate prompt until identification of
  known stamps is reliable; record per-run cost.
- Acceptance: calibration pages produce correct country/series for the clear
  majority of crops, honest uncertainty for the rest, and a bucket
  distribution that matches eyeball reality (mostly `likely_common`).

### Phase 3: Tier 2 evidence for outliers

- Source adapter interface (kept from the old plan, narrowed): web search,
  eBay Browse (keyword + image), Wikidata/Commons.
- Evidence records stored with URL, price, currency, status, tier, retrieved
  date, rationale — the existing `source_evidence` table fits.
- Value ranges computed only when identity confidence and evidence support
  them; otherwise explicit gaps.
- Acceptance: each `investigate` stamp shows cited evidence and either a range
  or a stated reason there is none.

### Phase 4: Shortlist + recapture loop

- Recapture kit generation (per-stamp photo instructions).
- Attach recaptured images to existing stamps; re-run Tier 1/2 on upgraded
  evidence.
- Collection report: summary ranges, outlier list, per-stamp inventory,
  CSV/JSON export (existing exporter extended).
- Acceptance: the user can print/follow the recapture list at the physical
  albums and feed photos back in.

### Phase 5: Full collection run

- Only after calibration pages prove the funnel: upload all ~80 pages, curate
  crops, run Tier 1 broadly, Tier 2 on flags, produce the final report.
- Acceptance: conservative inventory, clearly listed outliers, exports with
  full evidence trails.

## Non-Goals For This Rebuild

- Second vision provider (revisit only if OpenAI quality blocks calibration).
- Multi-user/product polish beyond what the single-user workflow needs.
- Embedding-based similarity search (perceptual hashing first; add embeddings
  only if duplicate grouping proves insufficient).
- Licensed catalog integration (user has no catalog export; LLM priors + web
  evidence instead).
