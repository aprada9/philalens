# Philalens Agent Context

Last updated: 2026-08-08

## Plan V2 (2026-08-06) — read this first

A full code audit (2026-08-06) concluded ~35-40% of the codebase is worth
keeping. The execution plan is now `docs/rebuild-plan-v2.md`, which supersedes
`docs/final-tool-build-plan.md`. Key user decisions locked in that plan:

- OpenAI stays the only vision provider (fix the existing path).
- Scope is the user's own ~80-page collection, not a general product.
- The user has physical album access: the recapture loop is real.
- The inline-HTML visualizer will be rewritten as a Vite + React SPA.
- Valuation uses a three-tier funnel: cheap LLM identification + prior value
  bucket for every crop, market evidence (web/eBay) for flagged outliers only,
  recapture kit + optional expert review for the shortlist.

Phase 0 of the plan was completed on 2026-08-06: dead code deleted
(`pipeline.py`, `/analyze/pages`, placeholder dataclasses, embedding table),
settings now read env lazily with `.env` loaded at startup (runtime settings
changes take effect immediately), crop `bbox_xywh` always matches the saved
crop image pixels, the YOLO model is cached per path, evaluation runs are
resumable (`interrupted` status at startup, resume endpoint, per-crop
valuation checkpoints, vision retries with backoff), redetect cleans orphaned
crop files, and `DELETE /api/collections/{id}` exists.

Phase 1 was completed the same day: the UI is a Vite + React 19 + TypeScript
SPA under `frontend/` served by FastAPI from `frontend/dist`; `visualizer.py`
and the costing dashboard are deleted; all model output renders through React
(the old XSS is gone). The full review workflow was browser-verified against
a real HEIC page with the YOLO detector.

Phase 2 (Tier 1 identification) is implemented: `stamp-observation-v2` adds
identity candidates (stored as `catalog_candidates` with source
`ai_vision_prior`, never with a claimed catalog_id) and a prior value bucket
(`likely_common`/`possibly_interesting`/`investigate`) that drives valuation
buckets; near-duplicate crops (dHash + color guard in `similarity.py`) share
one vision call. The first real OpenAI calibration ran 2026-08-06 (46 stamps,
$0.07, identifications judged good by the user; all 46 bucketed
`likely_common`).

Phase 3 (Tier 2 market evidence) was implemented 2026-08-07: source adapter
interface in `sources.py` (Wikidata live with country-level fallback; eBay
Browse built and tested but inactive until the user's eBay developer keys
arrive — configured via Settings/.env, never committed), Tier 2 orchestration
in `market_evidence.py` (enriches the latest completed run, appends one
updated valuation per crop, range only from >= 2 realized-sale prices with
identity confidence >= 0.5, explicit "No value range:" reasons otherwise),
evidence endpoints, and UI (drawer Gather evidence button, Market value
section, Overview batch button, Settings eBay fields). See
`docs/rebuild-plan-v2.md` Phase 3 notes for pending acceptance items. Next:
Phase 4 (shortlist + recapture loop) once flagged stamps exist and evidence
quality is judged.

Workflow refinements (2026-08-08, from user feedback): Overview has a
scope-selectable "Run evaluation" panel (not-analyzed / flagged / failed /
all — crop id sets computed client-side over the existing selected-crop
path), the top-bar run pill expands into a detailed progress popover
(analyzed/pending counts, current stamp, elapsed, estimated cost), and runs
can be stopped gracefully (`POST /api/evaluation-jobs/{id}/cancel` → run
marked `interrupted`, per-crop work preserved, resumable). The user
re-curated the calibration pages: 99 crops, 0 pending review, all 99
`likely_common` after a full run (user-confirmed as correct).

## User Intent

The user has many stamp album page photos: the confirmed full universe is
241 page images (~685 MB, mostly HEIC — earlier estimates said ~80). Each
page contains multiple stamps, so expect roughly 8,000 crops collection-wide. The desired tool should let the
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
- durable SQLite evaluation records for runs, observations, candidates, source
  evidence, valuations, and embedding metadata
- HEIC-aware image normalization in `backend/src/philalens/imaging.py`
- optional YOLO stamp segmentation plus OpenCV fallback in
  `backend/src/philalens/segmentation.py`
- a crop-readiness evaluation skeleton in `backend/src/philalens/evaluation.py`
- a strict `stamp-observation-v1` schema and parser in
  `backend/src/philalens/observation_schema.py`
- an optional OpenAI vision adapter in `backend/src/philalens/vision.py`,
  disabled unless `PHILALENS_VISION_PROVIDER=openai` is configured
- OpenAI evaluation cost tracking in `backend/src/philalens/costing.py`
- local visible-observation value triage in `backend/src/philalens/triage.py`
- Tier 2 evidence source adapters (Wikidata live, eBay Browse key-gated) in
  `backend/src/philalens/sources.py`
- Tier 2 market-evidence orchestration in
  `backend/src/philalens/market_evidence.py`
- CSV/JSON export shaping in `backend/src/philalens/exports.py`
- a local browser visualizer in `backend/src/philalens/visualizer.py`
- a downloader for the optional Apache-2.0 detector model in
  `scripts/download_stamp_detector.py`
- API endpoints in `backend/src/philalens/api.py` for collection upload,
  collection review, media serving, crop correction, crop-readiness evaluation,
  evaluation cost estimates, evaluation-run reads, settings cost dashboard, and
  exports
- product, architecture, data, and roadmap docs under `docs/`
- a consolidated final-tool northstar and staged evaluation specification in
  `docs/project-northstar.md`
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
- multi-select stamp rows, delete selected crops, and evaluate only selected
  stamps
- select visible review crops and mark them ready in a batch
- scan stamp-list badges labeled by topic: `Crop:` for crop status and `Eval:`
  for value triage
- edit OpenAI provider, model, image-detail, and API key from a local settings
  dialog that writes `.env`
- show live evaluation progress with a progress bar and the current stamp crop
  image being analyzed
- show rough pre-run API cost estimates and post-run recorded API cost when
  token usage is returned by the provider
- view a settings cost dashboard summarizing recorded evaluation API usage and
  cost calculations
- persist and read evaluation runs, stamp observations, catalog candidates,
  source evidence, stamp valuations, and embedding metadata
- create a first crop-readiness evaluation run from the browser `Evaluate`
  action, recording placeholder observations and conservative buckets such as
  `needs_better_image` and `not_enough_evidence`
- validate AI vision observations against `stamp-observation-v1`,
  including strict fields, bounded confidence, allowed cancellation/centering
  values, and default front-photo unobservable factors
- optionally call OpenAI vision during evaluation and store validated
  observation records for crops that do not still need crop review
- store OpenAI token usage and local USD cost calculations on observation/run
  metadata when provider responses include usage
- assign first-pass triage buckets such as `likely_common`,
  `possibly_interesting`, `needs_expert_check`, and `needs_source_matching`
  without price estimates
- include latest evaluation-run fields in collection JSON/CSV exports when
  records exist
- export collection data as CSV and JSON

The following are not implemented yet:

- OCR
- catalog/reference matching beyond AI priors and keyword-matched Wikidata
  reference items
- realized-sale (sold price) evidence sources — the `realized_sale` tier
  exists but no adapter produces it, so value ranges stay withheld in
  practice until one does
- eBay Browse activation (adapter built; waiting on the user's App ID/Cert
  ID from eBay developer application review)
- reviewed valuation workflow
- recapture kit / shortlist loop (Phase 4)

The desired evaluation direction is specified in `docs/project-northstar.md`.
Evaluation should be modeled as a durable run over curated crops, producing
observations, ranked candidates, source evidence, valuation buckets,
recommended next actions, and conservative collection summaries.

The detailed build sequence for future heavy implementation sessions lives in
`docs/final-tool-build-plan.md`. Use it when creating short `/goal` prompts or
splitting the remaining work into checkpoints.

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
- The first durable evaluation foundation exists in SQLite: `evaluation_runs`,
  `stamp_observations`, `catalog_candidates`, `source_evidence`,
  `stamp_valuations`, and `embedding_index`. The browser can create a
  crop-readiness evaluation run, and collection exports surface the latest run
  when records exist.
- The strict `stamp-observation-v1` schema exists and maps validated AI payloads
  into durable observation records. The prompt draft has been updated to match
  this schema.
- The optional OpenAI vision adapter exists and is opt-in via
  `PHILALENS_VISION_PROVIDER=openai`; default local operation makes no external
  model calls.
- Local visible-observation triage exists. It is useful for attention
  prioritization but is not catalog-backed valuation.
- The visualizer supports selected-crop batch deletion, selected-crop
  evaluation runs, selected-crop ready marking, visibly labeled crop/evaluation
  badges in the stamp list, live evaluation progress, rough API cost estimates,
  post-run API cost display, and local OpenAI settings/cost dashboard editing.
- The second Reddit tool link supplied by the user was blocked by Reddit network
  security and no public source/license was found.
- A source scan found no mature open-source end-to-end stamp album valuation
  system. Useful pieces include the Apache-2.0 `code2k13/philately-tool` for
  YOLO cropping plus CLIP-style local vector search, structured visual catalogue
  patterns from `adrianspeyer/Canadian-Stamp-Identifier`, image-similarity
  prototypes that require user-provided datasets, and collection-management
  ideas from My Stamps and OpenNumismat.
- A deeper source investigation found no clean open worldwide stamp catalog API
  with authoritative catalog IDs, images, variants, and values. The source layer
  should therefore be layered: Wikidata/Commons first, Smithsonian Open Access
  second, Europeana third, WNS/WADP only if usable access is confirmed, and
  eBay Browse only later as weak active-listing evidence. Continue avoiding
  unlicensed scraping of Colnect, StampWorld, StampData, Freestampcatalogue, or
  commercial catalog data.

## Open Product Questions

- Which specific public references have terms suitable for automated access?
- What exact CSV/spreadsheet shape should the first user-imported source
  adapter require?
- What minimum image quality warnings should block or defer AI analysis?
- What concrete thresholds should drive identity, condition, market, valuation,
  and expert-review confidence?
- Which embedding backend should be used first: sqlite-vec, raw NumPy vectors in
  SQLite, or another optional local vector store?

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
- Evaluation northstar: use durable evaluation runs over curated crops, preserve
  evidence and uncertainty, start with user-imported/permitted sources, use
  visual similarity as a supporting signal, assign value buckets and next
  actions, and avoid presenting formal appraisals.
- Development calibration policy: do not use the full 80-page collection as a
  development experiment. Use 2-4 representative pages until source-backed
  insights are trustworthy, then run the full collection.
- Source matching policy: the user does not currently have a catalog CSV, so
  first candidate matching should use open/permitted APIs rather than assuming
  user-supplied source data.

## Next Likely Work

1. Use `docs/project-northstar.md` as the northstar for future work sessions.
2. Use `docs/final-tool-build-plan.md` as the execution plan for heavy work.
3. Add the source adapter foundation and first Wikidata/Commons adapter slice.
4. Wire candidate retrieval into selected-crop evaluation only.
5. Add local similarity search and duplicate grouping for crops/reference data.
6. Calibrate triage buckets against calibration pages and source-confirmed examples.
7. Harden AI observation prompts and skip/downgrade rules against more real
   crops.
8. Improve segmentation/crop review only when representative calibration pages
   show concrete failures.
9. Improve crop review ergonomics after real drag-handle use.
