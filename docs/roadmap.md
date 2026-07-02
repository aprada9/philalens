# Roadmap

## Milestone 1: Repository Foundation

- Define product scope and architecture.
- Create backend project skeleton.
- Add initial API contract.
- Add inventory and valuation data models.
- Add agent operating docs and context update guardrails.
- Document sample page observations, valuation method, and source strategy.

Status: complete.

## Milestone 1.5: Product Definition

- Define detailed MVP workflow and review states.
- Decide first UI and deployment shape.
- Decide initial data-source policy.
- Design persistent records for pages, crops, observations, candidates, evidence,
  valuations, and review state.
- Define confidence scoring and escalation rules.

Status: mostly complete for direction. The local-first app shape, batch HEIC
input assumption, CSV/JSON exports, automatic-first crop review policy, and
full evaluation northstar are accepted. Detailed thresholds, source-specific
terms, and concrete scoring formulas still need implementation-time tuning.

## Milestone 2: Image Intake

- Upload multiple album page photos.
- Store originals and normalized derivatives.
- Return basic page analysis records.

Status: initial implementation exists for local batch upload, HEIC-aware
normalization, SQLite metadata, filesystem artifacts, and collection summaries.

## Milestone 3: Stamp Detection

- Detect likely stamp regions on a page.
- Extract crops and bounding boxes.
- Add manual correction hooks for missed or incorrect crops.
- Handle rotated, overlapping, partial, and tightly spaced stamps.

Status: prototype implementation exists. It can use an optional Ultralytics YOLO
detector with a locally downloaded Apache-2.0 model and falls back to classical
OpenCV segmentation when YOLO is unavailable. It extracts crops, stores bounding
boxes, and flags uncertain crops for manual review. The YOLO threshold has been
lowered to prioritize recall on the sample HEIC page, increasing detections from
41 to 68 candidates while flagging low-confidence crops. It still needs
iteration against more real HEIC album batches, better rotation/overlap
handling, and detector tuning.

## Milestone 4: Vision Extraction

- Extract visible text and visual observations.
- Store evidence and uncertainty.
- Add prompt and schema tests for repeatability.

Status: partially implemented. Durable evaluation-run and stamp observation
storage exists, and `stamp-observation-v1` defines a strict AI-visible
observation contract with parser tests and an updated prompt draft. An optional
OpenAI vision adapter now writes validated observations into evaluation runs
when explicitly enabled, records returned token usage/cost metadata, and local
triage rules classify observed stamps into attention buckets without prices. The
next implementation step is a permitted catalog/source adapter for candidate
matching.

## Milestone 5: Catalog Matching

- Import a user-provided reference catalog.
- Rank candidate matches by observations and visual similarity.
- Expose alternative matches for review.

Status: specified, not implemented. Start with user-imported source adapters and
local text/visual retrieval. Avoid bundling restricted catalog data. Current
triage buckets are not catalog matches.

## Milestone 6: Valuation

- Attach market evidence to candidate matches.
- Produce low/high value estimates.
- Add collection-level summaries and export.
- Separate catalog/reference value, active asking price evidence, realized sale
  evidence, and condition uncertainty.

Status: specified, not implemented. Valuation should use value buckets,
confidence bands, evidence tiers, and recommended next actions before presenting
collection-level ranges.

## Milestone 6.5: Collection Evaluation Run

- Add durable evaluation run records.
- Process curated crops through observation extraction, candidate retrieval,
  evidence gathering, valuation bucketing, and conservative collection rollup.
- Preserve old runs when the pipeline is re-run.
- Show run progress, warnings, errors, and source coverage.

Status: skeleton started. SQLite tables, dataclass records, storage methods,
read API endpoints, and CSV/JSON export fields now exist for evaluation runs,
observations, candidates, source evidence, valuations, and embedding metadata.
The local visualizer has an `Evaluate` action that creates a completed
crop-readiness run, records placeholder observations, and assigns conservative
per-crop buckets such as `needs_better_image` or `not_enough_evidence`. It does
not yet process crops through AI observation extraction, source matching,
evidence gathering, real valuation logic, or collection rollup.

## Milestone 7: Review Experience

- Build a review UI for confirming or editing matches.
- Export CSV and JSON inventories.
- Track reviewed versus unreviewed estimates.

Status: partly started. A local visualizer can upload batches, inspect pages and
crops, re-detect the current page, highlight the selected stamp on the full
page, edit crop boxes in the selected-stamp inspector with drag handles or
numeric fields, shade non-cropped areas during no-selection coverage review,
filter the stamp list to crops pending review, remove false-positive crops,
remove uploaded pages for clean re-upload, manually draw crops for missed
stamps, rotate crops with an inspector drag handle, run full-collection or
selected-stamp evaluation, multi-select stamps for batch crop deletion, show
topic-labeled crop/evaluation badges in the stamp list, batch-mark selected
review crops as ready, show live evaluation progress with the current crop
thumbnail and API cost information when available, edit local OpenAI settings,
show a settings cost dashboard, keep side lists scrolling independently, and
export CSV/JSON. Candidate matching and valuation review are still placeholders.
