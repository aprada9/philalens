# Session Handoff

Last updated: 2026-08-08

## Latest Session (2026-08-09, part 4): AI Value Estimation (Tier 2.5)

The user found per-stamp manual sold-comp checking too heavy for a
non-expert and asked whether the AI can estimate values and whether
specialized marketplaces/bibliography exist. Answered honestly: Delcampe/
Catawiki have sold data but no public APIs; catalogs are licensed; eBay
Marketplace Insights (real sold data) is a gated API worth applying for
with the existing dev account (the realized_sale tier is ready for it).
Built the automation that IS possible:

- `ai_estimate.py` (Tier 2.5): one structured model call per flagged stamp
  — crop image (detail low) + Tier 1 identity + observation + gathered
  evidence context — returning a conservative range, confidence, rationale,
  rarity notes (which varieties of the issue are valuable and what to
  check), and a recommended action (keep_common / check_sold_listings /
  expert_review). The prompt encodes dealer heuristics (bulk material at
  5-20% of catalog; realized ≈ 20-50% of median ask).
- Estimates are stored as valuations with an "AI-estimated range
  (unverified)" assumption marker, market_evidence_confidence capped at
  0.4, and stay separate everywhere: amber label + rationale + rarity
  notes in the drawer, separate report section with its own totals (never
  summed with owner-reviewed), CSV `ai_estimated` column.
- Endpoints: POST /api/crops/{id}/ai-estimate (single, sync) and
  POST /api/collections/{id}/ai-estimate/start (batch job over flagged).
  UI: drawer "🤖 AI estimate" button + Overview batch button.
- Live-verified on a real flagged stamp: $0.25-2 USD, confidence 0.34,
  honest "bulk material" verdict with watermark/perforation caveats.
- Owner-reviewed ranges remain the human-confirmed tier; the AI estimate
  triages which of the flagged stamps deserve that human minute.

## Earlier Session (2026-08-09, part 3): Job Re-Attach After Page Reload

The user finished Tier 1 on all currently-curated crops (51 flagged stamps
collection-wide now; ~2,600 crops still awaiting curation, deferred by
choice). Bug fix: reloading the page mid-run lost the progress panel — the
job id lived only in browser memory. `GET /api/evaluation-jobs` now lists
active (queued/running) jobs and the app re-attaches on load, restoring the
pill, detail popover, and Stop button. `startJobPolling` also uses the
job's own collection_id for the completion refresh instead of a possibly
stale closure. Next user step: the Overview batch "Gather market evidence
for all 51 flagged stamps", then sold-comp ranges per stamp.

## Earlier Session (2026-08-09, part 2): Phase 4 Implemented

75 backend tests pass; frontend builds; live-verified against the real
collection (kit lists the 6 flagged stamps; report shows 599 analyzed).
See `docs/rebuild-plan-v2.md` Phase 4 notes. Summary: owner-reviewed value
ranges (drawer form + sold-listings link, `POST /api/crops/{id}/valuation`,
"Owner-reviewed range" assumption marker, CSV `owner_reviewed` column),
printable recapture kit (photo checklist from unobservable factors),
recapture photo upload replacing the crop image (`POST
/api/crops/{id}/image` + drawer "Replace photo" + re-analyze), and the
printable collection report with per-currency owner-reviewed totals.

Correction from part 1: the "13 possibly_interesting" was a record count
(Tier 2 passes append valuations); the true stamp count is 6 — the UI was
right.

NEXT: the user runs the remaining Tier 1 batches (~4,700 stamps ready +
~2,600 crops still to curate), gathers evidence + sold-comp ranges for
flagged stamps, recaptures the shortlist, then the full report. Phase 5
(final full-collection pass) needs no new code.

## Earlier Session (2026-08-09, part 1): First Batch Run Reviewed + Evidence UX Fixes

First 500-stamp parallel batch: 14 min, $0.79, 0 errors, 494 likely_common
+ 13 possibly_interesting (2.6%), avg identity confidence 0.84. User judged
results good.

- Stamps view gained an analysis-status filter (All / Analyzed / Not
  analyzed yet).
- Re-gathering evidence now REPLACES the crop's previous evidence records
  (never wiping on a failed pass); the drawer button confirms before
  re-fetching; "Evidence sources unavailable" assumptions no longer
  accumulate. Existing duplicate evidence rows from double-gathers were
  deduped in the live DB (74 → 64 rows).
- The drawer's Market value section links to eBay SOLD listings for the
  stamp's identity (LH_Sold search URL) — realized prices are the evidence
  class that can set a range, and the public API only exposes active
  listings, so the human checks sold comps in the browser.
- User's open question: how to reach an estimated value range with
  confidence. Answered: the range policy requires realized-sale evidence;
  next build step is Phase 4's reviewed-valuation workflow (user-entered
  range from sold comps, marked human-reviewed) + recapture kit + report.

## Earlier Session (2026-08-08, part 10): Batch Evaluation

The user wants to run Tier 1 in sets (analyze a batch, check results,
run the next) rather than 5,251 stamps in one go. The Run evaluation panel
gained a batch-size select (first 100/250/500/1000/everything, default
250) that slices the scope's crop ids client-side in album page order.
Each batch is a normal completed run with its own cost record; the run
overlay (part 9) keeps every batch's results visible and the
"Not analyzed yet" count shrinking, so re-running the same scope+batch
walks through the collection without ever re-billing. Stop/resume remains
available inside any batch.

## Earlier Session (2026-08-08, part 9): Parallel Vision Calls + Run Overlay

Preparation for the user's first big Tier 1 run (~5,200 ready crops):

- Vision calls now run concurrently: sliding-window ThreadPoolExecutor in
  `evaluate_collection_readiness` (`vision_concurrency` param; API passes
  `PHILALENS_VISION_CONCURRENCY`, default 4). All DB writes and progress
  callbacks stay on the main thread; per-crop checkpoints, resume,
  duplicate fan-out (members written when their representative completes),
  and cancellation are preserved. Cancel semantics shifted slightly:
  in-flight (already paid) calls finish and are saved; no new dispatches.
  Expected wall-clock for 5,200 crops: ~10-13 h sequential → ~2.5-3.5 h at
  concurrency 4.
- `OpenAIStampVisionAdapter` now wraps transport/API errors (429s,
  timeouts, 5xx) as `VisionObservationError`, so per-crop retries with the
  new longer backoff (2/5/15 s) absorb rate-limit bursts instead of the
  whole run failing. Failures remain re-runnable via the "Failed
  extraction" scope.
- CRITICAL FIX for scoped runs: the collection export previously read only
  the latest run, so a second scoped run would have hidden the first run's
  results and re-offered those stamps as "not analyzed" (double billing
  risk). `build_collection_export` now overlays runs per crop: each crop
  shows all four record types from the newest run that evaluated it, and
  the collection summary counts the overlay. Verified: two scoped runs
  both remain visible; export latency unchanged (0.18 s live).

## Earlier Session (2026-08-08, part 8): Grid Triage for Page-Level Curation

Real curation feedback: most flagged crops are obvious Keeps, plus a batch
of obvious Deletes (album borders/bindings detected as stamps). One-at-a-
time queue review is the wrong shape for that, so Curate gained a grid
triage mode: the canvas-panel toggle ("▦ Grid triage (N)") shows all of the
current page's flagged crops as thumbnails; clicking marks a crop for
deletion (red ✕); one Apply button deletes the marked and accepts the rest
(single busy cycle via onGridApply → batch delete + batch mark-ready +
local state mirror), then the queue auto-advances to the next page with
flags. Each cell has a ⤢ shortcut to the crop editor for the few real
fixes and a tooltip with the crop's warnings. Browser-verified against the
live collection (2,606 flagged remained at the time; page grid rendered,
mark toggle and Apply counts correct — not applied, user data untouched).

## Earlier Session (2026-08-08, part 7): Queue Actions Made Fast at 8k Crops

The user reported multi-second Keep/Fix/Delete actions in the review queue.
Cause: every crop action returned the full collection export, and
`build_collection_export` ran 4 per-crop queries (each opening its own
SQLite connection) — ~32k queries plus a 6.3 MB JSON response per
keystroke at 7,956 crops. Fixes, measured against the live collection:

- `build_collection_export` now loads the latest run's observations,
  candidates, evidence, and valuations with 4 run-level queries grouped by
  crop (ordering semantics preserved: last-per-crop = newest). Full export:
  4.96 s → 0.19 s.
- Hot endpoints return light payloads instead of the export:
  DELETE /api/crops/{id} → {deleted_crop_id}, POST /api/crops/delete →
  {deleted_crop_ids}, POST /api/crops/mark-ready → {ready_crop_ids}
  (mark-ready measured at 19 ms). PATCH /api/crops/{id} already returned
  just the crop.
- The frontend mirrors these actions locally (`applyLocalPages` recomputes
  stamp/review counts client-side) instead of refetching; Fix box merges
  the PATCH response into the stamp and bumps the image version. Full
  refetches remain only where they're rare (upload, evaluate completion,
  redetect, page/collection deletion).
- Note: crop_aea8fa7fc7fb4e4f was mark-ready'd by a latency test and
  re-flagged afterwards; its warning chips were lost (state predates the
  only backup) but it is back in the review queue.

## Earlier Session (2026-08-08, part 6): Review-Bar Relaxation + Bulk Page Accept

The user uploaded all 241 pages: 7,956 crops, 3,733 flagged for review
(47%). Analysis of the flags showed the rule (`warnings OR confidence <
0.7`) was flooding the queue: for YOLO detections `segmentation_confidence`
is the raw YOLO score, which lands at 0.4-0.65 for correct detections, so
1,383 warning-free crops were flagged on score alone (calibration curation
kept ~87% of flagged crops unchanged).

- New rule: `warnings OR confidence < REVIEW_CONFIDENCE_BAR (0.45)`
  (`segmentation.py`); warned crops always stay flagged.
- `POST /api/collections/{id}/relax-crop-review` applies the current bar to
  crops flagged under the older stricter rule (no re-detection, curation
  preserved). Run live: 1,066 crops unflagged, 2,667 remain (all warned or
  genuinely low-confidence).
- Curate queue gained "Accept all N remaining on this page" (bulk
  mark-ready for the current page's flagged crops) — with ~11 flagged
  crops/page average, per-page acceptance makes the remaining queue
  tractable.

## Earlier Session (2026-08-08, part 5): Chunked Upload for the Real Collection Size

The user's full collection is 241 pages / ~685 MB (not ~80 pages as earlier
estimated; docs updated). A single upload request would exceed the 120-file
batch limit and be fragile at 685 MB, so the frontend now chunks uploads
client-side: any number of selected files is sent in sequential batches of
20 (each batch ingests + runs detection server-side), with live progress in
the notice bar and the page list growing as chunks land. A failure mid-way
keeps everything ingested so far; re-selecting the same files resumes via
the filename dedupe. Scale expectations: ~8,000 crops, Tier 1 at
gpt-4.1-mini ≈ $12-20; the crop-curation queue is the real bottleneck
(calibration flagged ~57% of crops — consider tuning
PHILALENS_STAMP_YOLO_CONFIDENCE after sampling flag rates on full pages).

## Earlier Session (2026-08-08, part 4): Backups + Year Slider (pre-full-run)

- Database backups: `PhilalensStore.create_backup` (SQLite online backup
  API, `data/local/backups/`, keep last 10) runs automatically after every
  completed/cancelled evaluation or evidence job; `GET /api/backup.sqlite`
  streams a fresh snapshot (Overview "Download backup" button + restore
  note). Verified live (860 KB snapshot of the calibration DB). Clarified
  to the user: per-crop checkpointing already made shutdowns safe; backups
  protect against database loss. The DB is the token-spend artifact —
  images are derivable from originals + stored crop boxes.
- Stamps view: the year from/to inputs became a dual-thumb range slider
  bounded by the collection's identified years (full span = no filter,
  narrowed range matches only stamps with a year, reset ×), and sorting
  gained "Year, oldest first" / "Year, newest first". Browser-verified.
- 70 backend tests pass; frontend typechecks and builds.
- The user is about to start the full ~80-page run.

## Earlier Session (2026-08-08, part 3): Incremental Upload + Stamps Filters

Preparation for the full ~80-page run:

- `POST /api/collections/{id}/pages` adds pages to an existing collection
  and skips files whose original filename is already present
  (case-insensitive), returning `added_page_count` and
  `skipped_duplicate_filenames`. The Upload pages button now extends the
  open collection (a notice bar reports added/skipped); it only creates a
  new collection when none exists. This lets the user re-select their whole
  photo folder without knowing which 3 pages were already uploaded, and
  without losing curation/evaluation work.
- Stamps view gained a country dropdown (distinct AI-identified issuers
  with counts) and year from/to filters (only stamps with an identified
  year match); browser-verified against the live 99-stamp collection.
- The user asked to filter by purchase value in EUR ("value when bought");
  this was NOT implemented because the data does not exist: a front photo
  gives only the printed face value in a historic currency (e.g. 1959
  pesetas), and actual purchase prices are unknown to the system.
  Explained to the user; denomination remains text-searchable.

## Earlier Session (2026-08-08, part 2): eBay Live + Vision Model Dropdown

- The user's eBay developer application was approved; the marketplace
  account deletion exemption was granted; App ID/Cert ID were entered in
  Settings. The user confirms eBay evidence gathering "works like a charm"
  (accuracy not yet judged).
- Settings now offers a curated vision-model dropdown built from
  `costing.vision_model_options()` (exposed via `GET /api/settings`):
  gpt-4.1-mini (default, ★), gpt-5.4-mini (★ value upgrade), gpt-4.1,
  gpt-5.4, gpt-5.5, gpt-4.1-nano — each with a rough $/100-stamps estimate
  from the existing token heuristic and an honest note (reasoning models
  under-estimate because hidden reasoning tokens bill as output). A
  "Custom model…" option keeps arbitrary model ids possible.
- Measured real cost reference: gpt-4.1-mini at high detail ≈ $0.0015 per
  stamp (46 calls / $0.069), so the full ~80-page collection (~2,600
  stamps) lands around $4-6 at the default model.
- Next: user proceeds to the full-collection workflow (upload in batches,
  curate via queue, evaluate with the "Not analyzed yet" scope, gather
  evidence on flagged); Phase 4 (recapture kit + collection report) is the
  next build phase.

## Earlier Session (2026-08-08, part 1): Evaluation Scopes, Run Progress Panel, Stop Button

User feedback session. 66 backend tests pass; frontend typechecks and builds.

- The 2026-08-07 discrepancy resolved itself: the user redid curation and ran
  a full evaluation (run_4bf9edfb2c414d4f, 99 crops, all `likely_common`,
  which the user confirms matches reality; 8 false-positive crops deleted,
  0 pending review).
- "Gather evidence → Not Found" bug root cause: the dev uvicorn (started
  without `--reload` before the Phase 3 commit) served the new frontend but
  had no evidence routes. No code bug. The server was restarted WITH
  `--reload` and the endpoint was verified live against a real crop
  (3 Wikidata reference items + explicit no-range reason). If the user
  starts the server manually again, `--reload` is recommended.
- Evaluation scopes: Overview has a "Run evaluation" panel with a scope
  select — Not analyzed yet / Re-analyze flagged / Failed extraction /
  All stamps — computing crop id sets client-side and passing them to the
  existing selected-crop evaluation path. The dynamic next-step card now
  evaluates only the remaining stamps instead of everything. All multi-crop
  runs (not just full runs) show the cost-estimate confirm dialog.
- Run progress detail: the top-bar pill shows "N/M" and is clickable — a
  popover shows analyzed/pending counts, a live progress bar, current stamp
  thumbnail, elapsed time, estimated cost, and a "Stop run" button.
- Graceful stop: `POST /api/evaluation-jobs/{job_id}/cancel` sets a flag;
  the progress callback raises `EvaluationCancelledError`; the run is marked
  `interrupted` with warning `run_cancelled_by_user`, every already-analyzed
  crop keeps its records (per-crop valuation checkpoints, unchanged), and
  the existing resume flow finishes the rest without re-billing. Covered by
  `test_cancelled_run_saves_progress_and_resumes`.
- Scale note re-confirmed with the user: the 3 pages are calibration only;
  the real collection is ~80 pages and the architecture (resumable runs,
  duplicate grouping, cost estimates) was built for that. Full-collection
  run remains Phase 5.

NEXT STEPS:

1. eBay keys into Settings when the developer application clears (may take
   days; nothing blocks on it).
2. All 99 calibration stamps are `likely_common`, so Tier 2 has no flagged
   targets. Consider adding 1-2 album pages with suspected-interesting
   material to exercise the investigate path, or proceed to Phase 4
   (recapture kit + shortlist + collection report), which does not depend
   on eBay.

## Earlier Session (2026-08-07, part 2): Phase 3 Implemented — Tier 2 Market Evidence

All 64 backend tests pass; frontend typechecks and builds. Implemented per
`docs/rebuild-plan-v2.md` Phase 3 (see its notes for full detail):

- `sources.py`: adapter interface + `WikidataStampAdapter` (live, verified —
  needs the contact-URL user agent, falls back to country-level reference
  items) + `EbayBrowseAdapter` (tested against mocked OAuth/Browse; inactive
  until eBay keys are set in Settings, stored in `.env` only).
- `market_evidence.py`: Tier 2 pass enriching the latest completed run;
  appends one updated valuation per crop; range only from >= 2 realized-sale
  prices with identity confidence >= 0.5; explicit "No value range:" reasons;
  asking prices are context only, never estimates.
- API: `POST /api/crops/{crop_id}/evidence`,
  `POST /api/collections/{id}/evidence/start` (job),
  settings expose `market_sources` and accept eBay keys.
- UI: drawer Gather evidence button live, Market value section (range or
  withheld reason + asking-price context), Overview batch evidence button,
  Settings eBay App ID/Cert ID fields.
- `build_evaluation_summary` now counts only the latest valuation per crop.

IMPORTANT DISCREPANCY (needs the user): the user reported having curated the
calibration crops and re-run Tier 1 before this session, but
`data/local/philalens.sqlite` shows neither — 61 crops still
`needs_crop_review`, and the newest evaluation run is still the 2026-08-06
16:39 UTC calibration (46 vision calls, $0.069, all 46 `likely_common`,
issuer split Netherlands 22 / Spain 17 / Uruguay 4 / other 3, which matches
the known pages). That run itself looks sane. Possibly the curation/re-run
happened against a different data dir or was not saved; the user should
verify in the UI (Curate queue should show 61 pending) and redo it if needed.

NEXT STEPS:

1. User: curate the 61 flagged crops and re-run Tier 1 (the previous re-run
   did not reach the database; see discrepancy note).
2. User: enter eBay App ID/Cert ID in Settings when the application clears —
   eBay evidence activates with no code change.
3. Judge Tier 2 evidence usefulness on flagged stamps (none exist yet — the
   calibration run flagged nothing), then Phase 4 (recapture kit).

## Earlier Session (2026-08-07, part 1): UI Redesign — Workflow-First, Light+Dark

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

Status updates from the user (2026-08-07, end of session):

- Calibration verdict: the user judged the Tier 1 identifications good. No
  prompt iteration needed before Phase 3.
- eBay: the user registered an eBay Developer account; the application is
  under review (~1 day). Phase 3 should build the marketplace adapter
  interface plus the open sources (Wikidata/Commons first) and leave the
  eBay Browse adapter ready to activate once the App ID/key arrives —
  configured via settings/env, never committed to the repo.

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
