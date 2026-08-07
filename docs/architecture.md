# Architecture

## Pipeline

```text
album photos
  -> page preprocessing
  -> stamp detection and crop extraction
  -> manual crop review and correction
  -> evaluation run creation
  -> OCR/AI vision and visual feature extraction
  -> duplicate and page-context grouping
  -> catalog candidate retrieval
  -> visual similarity reranking
  -> market evidence retrieval
  -> confidence scoring
  -> value estimation
  -> manual review and export
```

## Components

### Local Storage

The current local MVP uses SQLite plus filesystem storage under `data/local/` by
default. The database tracks collections, pages, detected crops, and durable
evaluation records for runs, observations, candidates, source evidence,
valuations, and embedding metadata. The filesystem stores original uploads,
normalized JPEG page derivatives, and crop images.

Relevant modules:

- `backend/src/philalens/storage.py`
- `backend/src/philalens/imaging.py`

### Image Ingestion

Accepts batch album page photos, preserves the original image, and creates
normalized JPEG derivatives for browser display and segmentation. HEIC/HEIF
support is provided through `pillow-heif`.

### Stamp Segmentation

Finds individual stamps on a page and stores bounding boxes, crop paths, and quality metrics. Early versions can use classical image processing; later versions can add object detection models.

The sample album page shows that segmentation must handle regular grid-like
groups, rotated stamps, overlapping stamps, cancellations, dark album stock,
album rings, and partial crops. A manual correction loop is required before
valuation results are trusted.

The current segmentation implementation supports two local detector paths:

- optional YOLO detector using a local `model.pt` file, configured by
  `PHILALENS_STAMP_DETECTOR`, `PHILALENS_STAMP_YOLO_MODEL_PATH`,
  `PHILALENS_STAMP_YOLO_CONFIDENCE`, and
  `PHILALENS_STAMP_CROP_MARGIN_PERCENT`
- OpenCV fallback that thresholds likely foreground regions and filters
  stamp-like boxes

When available, the YOLO path follows the useful pattern from the Apache-2.0
`code2k13/philately-tool`: run a trained detector, expand boxes by a small
margin, write crops, and keep uncertain results reviewable. Philalens defaults
to a lower confidence threshold of `0.1` because the sample HEIC page recovered
68 candidate crops instead of 41 at the original stricter threshold. Low
confidence detections are marked `low_detector_confidence` and require crop
review rather than being trusted silently. The local model can be downloaded with
`scripts/download_stamp_detector.py`; it is stored under `data/local/models/`
and not committed to Git.

Both detector paths write crop images and mark suspicious boxes as
`needs_crop_review`. The detector is still expected to produce false positives,
missed stamps, and merged crops on difficult pages until iterated against real
album batches.

Relevant module:

- `backend/src/philalens/segmentation.py`

### Vision Extraction

Extracts observable features from each crop:

- visible text
- country or issuing authority
- denomination and currency
- color palette
- cancellation state
- condition observations
- design description

Vision extraction must distinguish visible facts from unobservable factors. A
front-side album photo usually cannot prove watermark, paper, gum, hidden thins,
repairs, regumming, or expertized authenticity. These unknowns should be stored
as uncertainty, not silently ignored.

The strict `stamp-observation-v1` schema now lives in
`backend/src/philalens/observation_schema.py`. It rejects unexpected fields,
normalizes visible text/list fields, enforces allowed cancellation and centering
values, bounds confidence to 0.0-1.0, defaults front-photo unobservable factors,
and converts validated payloads into durable `StampObservationRecord` rows. The
prompt draft in `backend/src/philalens/prompts/stamp_analysis.md` mirrors the
same JSON shape. `backend/src/philalens/vision.py` provides an optional OpenAI
Responses API adapter, disabled by default, that sends eligible crop images only
when `PHILALENS_VISION_PROVIDER=openai` and `OPENAI_API_KEY` are configured. The
adapter attaches returned token usage and local cost calculations to observation
metadata when the provider response includes usage.

### Evaluation Runs

Durable evaluation-run storage now exists. A run records the pipeline version,
model/source settings, status, warnings, errors, and the observation, candidate,
source evidence, valuation, and embedding metadata records produced for a
collection. Runs make the process reproducible enough that improved pipelines
can be re-run without overwriting older evidence.

The current implementation provides the schema, storage methods, read endpoints,
CSV/JSON export fields, and a first `Evaluate` action in the local visualizer.
That action creates a completed crop-readiness run. By default it records
placeholder observations and assigns conservative per-crop value buckets such as
`needs_better_image` for crops still needing review or `not_enough_evidence`
when no source evidence exists yet. When the optional OpenAI vision adapter is
configured, the same run writes validated AI-visible observations for crops that
do not need crop review, then applies local visible-observation triage rules in
`backend/src/philalens/triage.py`. Those rules can mark crops as
`likely_common`, `possibly_interesting`, `needs_expert_check`, or
`needs_source_matching` without assigning prices. Source adapters, candidate
retrieval, and real valuation logic remain future phases.

Evaluation run settings also carry cost metadata. `backend/src/philalens/costing.py`
creates rough pre-run OpenAI estimates from the configured model/detail and the
number of billable crops, then summarizes actual token usage and calculated USD
cost after the run. This avoids a schema migration while preserving cost data in
the durable run export. The cost calculation is informational and should be
checked against provider billing for final charges.

### Candidate Matching

Searches catalog/reference records using extracted features and visual similarity. Returns ranked candidates with evidence, not a single forced answer.

Candidate retrieval should start with user-imported or otherwise permitted
source adapters. Visual similarity should be a supporting signal, likely through
a local embedding index over crop and reference images, not the only source of
identity.

### Market Evidence Sources (Tier 2)

`backend/src/philalens/sources.py` defines the source adapter interface:
`EvidenceQuery` (built from a crop's top AI identity candidate),
`EvidenceItem`, and a `SourceAdapter` protocol. Two adapters exist:

- `WikidataStampAdapter` (live, no key): keyword search against the Wikidata
  API with a required contact-URL user agent. Wikidata search ANDs all terms,
  so when the full issue query matches nothing it falls back to country-level
  "postage stamps of {issuer}" reference items at lower confidence. Reference
  metadata only, never prices.
- `EbayBrowseAdapter` (inactive until `PHILALENS_EBAY_APP_ID` and
  `PHILALENS_EBAY_CERT_ID` are set via settings/.env): OAuth
  client-credentials token flow plus Browse keyword search over the Stamps
  category. Active listings are stored as `active_listing_weak` evidence with
  asking prices; keys are never committed.

`backend/src/philalens/market_evidence.py` orchestrates the Tier 2 pass. It
attaches to the latest completed evaluation run, targets crops whose latest
valuation bucket is `possibly_interesting`, `investigate`, or
`needs_expert_check` (or an explicit crop selection), stores evidence records,
and appends an updated valuation per crop in the same run (the newest
valuation per crop wins in exports and summaries). Value ranges are computed
only from `realized_sale` evidence (at least two price points and identity
confidence at or above 0.5); asking prices never set a range and appear only
as labeled context. Every other outcome writes an explicit
"No value range: ..." reason into the valuation assumptions. Endpoints:
`POST /api/crops/{crop_id}/evidence` (single crop, synchronous) and
`POST /api/collections/{collection_id}/evidence/start` (background job over
flagged crops, polled via `/api/evaluation-jobs/{job_id}`).

### Valuation

Combines catalog metadata, condition signals, and market evidence into a range. Every estimate should include confidence and source references.

Valuation should explicitly separate:

- identity confidence
- condition confidence
- market evidence strength
- unobservable risk, such as watermark, paper, gum, hidden faults, or repairs

### Review UI

Lets a human confirm, reject, or edit candidate matches before exporting the inventory.

The current local browser visualizer lets the user upload batches, inspect page
images with crop overlays, move stamp-by-stamp through detected crops, re-detect
the current page, create full-collection or selected-stamp evaluation runs,
multi-select stamp rows for batch crop deletion or batch crop-ready acceptance,
remove uploaded pages for fresh re-upload, manually draw crop boxes for missed
stamps, and export CSV/JSON. Stamp rows show separate `Crop:` and `Eval:` badges
so crop review status and value triage are visually distinct. Full-page overlays
are for location and selection only; the selected
stamp is highlighted strongly in the full page, and crop-box resizing happens in
the selected-stamp inspector with corner drag handles or numeric fields. The
inspector also has a drag rotation handle for rotated stamps; rotation is stored
as `rotation_degrees` and used when writing the crop image. When no stamp is
selected, the full-page view shades areas outside detected crop boxes so missed
stamps are easier to spot. The stamp list can be filtered to `needs_crop_review`
crops, and the page/stamp lists scroll independently of the main page image.
Evaluation can also run as an in-memory job exposed through
`/api/collections/{collection_id}/evaluate/start` and
`/api/evaluation-jobs/{job_id}`, letting the browser show a progress bar and
current crop image during AI vision calls. The API also exposes
`/api/collections/{collection_id}/evaluation-cost-estimate` for rough pre-run
cost checks. A local settings dialog reads and writes OpenAI vision settings to
`.env` without exposing the saved key in API responses and includes a cost
dashboard built from durable evaluation runs. Candidate matching and price
valuation are placeholders until later pipeline stages are connected.

Relevant modules:

- `backend/src/philalens/api.py`
- `backend/src/philalens/costing.py`
- `backend/src/philalens/visualizer.py`
- `backend/src/philalens/exports.py`

## Data Model

The initial in-memory backend schema focuses on evidence capture:

- `StampObservation`: what the system sees in the image
- `CatalogCandidate`: possible catalog/reference match
- `StampAssessment`: combined observation, candidates, and value estimate
- `PageAnalysis`: all stamps detected on a page
- `CollectionSummary`: aggregate counts and value range

Persistent records now exist for page images, crop regions, crop rotation, crop
review state, evaluation runs, stamp observations, catalog candidates, source
evidence, stamp valuations, and embedding metadata. A strict AI observation
schema also exists. Future schema work should focus on source-import records,
review decisions, collection-level rollups, and richer reporting.

The intended evaluation schema and staged implementation plan are specified in
`docs/project-northstar.md`.
