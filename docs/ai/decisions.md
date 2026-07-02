# Decision Log

Durable project decisions live here. Add new entries when a choice affects
product direction, architecture, data strategy, or agent workflow.

## Template

```text
## YYYY-MM-DD: Decision Title

Status: Proposed | Accepted | Replaced

Context:
Decision:
Rationale:
Consequences:
```

## 2026-06-29: Use Philalens As Repository And Product Name

Status: Accepted

Context: The user wanted a name for a stamp analysis and valuation project.

Decision: Use `philalens` as the GitHub repository name and Philalens as the
product name.

Rationale: The name is short, brandable, and connected to philately and visual
analysis.

Consequences: Documentation and project identity should consistently use
Philalens.

## 2026-06-29: Position Estimates As Research, Not Appraisal

Status: Accepted

Context: Stamp values depend on subtle physical details, condition, and market
evidence. AI analysis from photos can be useful but uncertain.

Decision: Philalens should provide evidence-backed value ranges with confidence,
not formal appraisals.

Rationale: This is more honest, legally safer, and better aligned with the
limitations of image-based identification.

Consequences: UI, API, docs, and exports should avoid definitive appraisal
language unless a qualified expert review workflow is introduced later.

## 2026-06-29: Start With A Python/FastAPI Backend

Status: Accepted

Context: The project needs image ingestion, AI processing, data matching, and
future API/UI integration.

Decision: Start with a Python backend using FastAPI and structured domain models.

Rationale: Python has strong image processing and AI ecosystem support, while
FastAPI provides a simple API surface for future UI work.

Consequences: Backend code currently lives under `backend/`; frontend decisions
remain open.

## 2026-06-29: Make Agent Context A First-Class Artifact

Status: Accepted

Context: The user wants future AI sessions to understand the project without
repeating prior context.

Decision: Add `AGENTS.md`, agent adapter files, durable context docs, and a
context freshness guard.

Rationale: Future agents need a stable bootstrap path and a feedback loop that
keeps project memory synchronized with code changes.

Consequences: Meaningful changes must update context docs. CI should flag
changes that skip context updates.

## 2026-06-29: Use A Segmentation-First Product Workflow

Status: Accepted

Context: The first real sample page contains many stamps on one album page,
including regular rows, rotated stamps, overlapping stamps, cancellations, album
rings, and partial crops.

Decision: Philalens should first solve page-to-stamp segmentation with manual
crop review before trying to value stamps.

Rationale: Identification and valuation are only useful if the system isolates
the correct stamp and records crop confidence.

Consequences: The MVP needs page records, crop records, segmentation confidence,
and manual correction states.

## 2026-06-29: Estimate Value As Evidence-Weighted Ranges

Status: Accepted

Context: Many valuation factors are not visible from one front-side album photo,
including watermark, paper, gum, hidden thins, regumming, and repairs.

Decision: Philalens should output value ranges with identity confidence,
condition confidence, evidence links, assumptions, and next-action guidance.

Rationale: This gives useful collection triage without pretending to be a formal
appraisal.

Consequences: The data model and UI should represent evidence, uncertainty, and
review status as first-class fields.

## 2026-06-29: Use Source Adapters And Avoid Unlicensed Catalog Bundling

Status: Accepted

Context: Stamp catalogs and price data may be copyrighted or licensed. Current
research did not verify a reliable official public API for stamp-specific online
catalogs such as Colnect or StampWorld.

Decision: Start with source adapters and user-imported reference data. Add
automated connectors only for sources with clear API and terms permission.

Rationale: This keeps the project useful while reducing legal and maintenance
risk.

Consequences: Data-source code should preserve source attribution, retrieved
date, licensing notes, and confidence.

## 2026-06-29: Build A Local-First MVP

Status: Accepted

Context: The user clarified that Philalens should be local for now and should
handle batches of around 80 mostly HEIC album page photos.

Decision: Build the first MVP as a local FastAPI web app with browser UI,
SQLite metadata storage, and filesystem storage for original uploads,
normalized page derivatives, and stamp crops.

Rationale: A local app is faster to iterate, avoids early hosting/privacy
complexity, and fits the user's private album-photo workflow.

Consequences: Runtime data lives under `data/local/` by default and is ignored
by Git. Future hosted or multi-user deployment would need an explicit storage,
auth, and privacy design.

## 2026-06-29: Support Batch HEIC Intake In The MVP

Status: Accepted

Context: The user's real collection photos are mostly HEIC files and are likely
uploaded in batches of around 80 page images.

Decision: Add HEIC/HEIF support through `pillow-heif`, preserve original
uploads, and create normalized JPEG working copies for browser display and
segmentation.

Rationale: HEIC support is required for the actual source material, while JPEG
derivatives simplify downstream browser display and OpenCV processing.

Consequences: Backend setup must install `pillow-heif`. Image-processing code
should treat normalized-image coordinates as the first crop-review coordinate
system.

## 2026-06-29: Automatic Segmentation With Review Flags

Status: Accepted

Context: The user asked whether crop correction can be automatic, with manual
correction only where the system thinks a crop may be inaccurate.

Decision: Run automatic stamp-region detection first and mark uncertain,
edge-touching, unusually shaped, too-small, or potentially merged regions as
`needs_crop_review`.

Rationale: Reviewing every crop manually would be slow for 80-page batches, but
valuation should not proceed blindly from questionable segmentation.

Consequences: The visualizer should prioritize flagged crops while keeping all
crop boxes editable. Future segmentation improvements should reduce false
review prompts without hiding uncertainty.

## 2026-06-29: Add Optional YOLO Stamp Detector

Status: Accepted

Context: The first OpenCV cropper produced poor results on early manual review.
The user supplied a Reddit link to an open-source autocropping tool. Review
found the linked `code2k13/philately-tool` GitHub repository is Apache-2.0 and
ships a trained `model.pt` detector.

Decision: Add an optional Ultralytics YOLO detector path and a downloader script
for the Apache-2.0 model, while keeping OpenCV as the default fallback when the
model or optional dependency is unavailable.

Rationale: A trained detector is more appropriate than generic thresholding for
mixed album pages, but PyTorch/Ultralytics is too heavy to make mandatory for
the base backend.

Consequences: Install `pip install -e ".[dev,yolo]"` and run
`python3 scripts/download_stamp_detector.py` to enable the better detector
locally. The downloaded model and source metadata live under `data/local/models/`
and remain ignored by Git.

## 2026-06-30: Prioritize Segmentation Recall During Review

Status: Accepted

Context: User testing showed that the YOLO detector produced generally good
crops but missed full rows on the sample HEIC page, detecting 41 stamps out of
about 68.

Decision: Lower the default YOLO confidence threshold to `0.1`, keep
low-confidence detections visible, and mark them with `low_detector_confidence`
and `needs_crop_review` instead of dropping them.

Rationale: For a review-first inventory tool, a questionable crop is better than
a silently missing stamp. Manual review can reject weak detections, but it
cannot review stamps that never appear.

Consequences: New uploads and page re-detection should recover more candidates
but will flag more crops for review. Detector thresholds and crop margins should
be tuned against more real HEIC pages before valuation depends on segmentation.

## 2026-06-30: Split Coverage Review From Crop Editing

Status: Accepted

Context: User testing showed that crop outlines alone made it hard to tell
whether stamps in the middle of a page had been missed, and crop editing should
stay in the per-stamp view rather than cluttering the full page.

Decision: Treat no selected stamp as a coverage-review mode that shades areas
outside detected crop boxes. Keep full-page overlays for selection/location and
selected-stamp highlighting. Keep crop resizing in the inspector, and add review
filtering plus delete controls for false-positive crops and uploaded pages.

Rationale: Batch review needs two different jobs: finding missed detections on
the whole page and correcting one detected crop precisely. Combining both jobs
on the full image makes review harder.

Consequences: The visualizer now starts page review without an auto-selected
stamp, exposes a quick `Review only` filter, and persists crop/page removal via
API endpoints so exports match the reviewed state.

## 2026-06-30: Persist Manual Crops And Crop Rotation

Status: Accepted

Context: The user needs to add stamps missed by automatic detection and handle
stamps placed at arbitrary angles on album pages.

Decision: Add manual crop creation from the full-page view by dragging a new
crop rectangle. Add `rotation_degrees` to crop records and exports. Keep
rotation as an interactive inspector drag handle, not a numeric input field.

Rationale: Missed stamps are found while reviewing the full page, but precise
geometry correction belongs in the per-stamp inspector. Rotation must persist so
reloaded projects and CSV/JSON exports reflect reviewed crop geometry.

Consequences: The local SQLite schema now migrates crops with a
`rotation_degrees` column. Crop image generation samples a rotated rectangle
when rotation is nonzero. Future crop-review improvements should account for
rotated crop geometry in overlays, coverage masks, and downstream vision.

## 2026-06-30: Use A Northstar Spec For Evaluation Work

Status: Accepted

Context: After stamp detection and crop curation reached a usable local MVP, the
user wanted a full project description and specification that can guide future
sessions toward automatic collection evaluation.

Decision: Add `docs/project-northstar.md` as the consolidated final-tool
northstar. It defines the end-state workflow, evidence-backed evaluation method,
source strategy, conceptual persistent data model, confidence/review policy, UI
requirements, implementation phases, and acceptance criteria.

Rationale: The next work spans AI observation, source adapters, visual
similarity, evidence storage, valuation, review, and reporting. A single
northstar reduces drift and lets future sessions implement one bounded step at a
time.

Consequences: Future changes to evaluation, matching, source strategy,
valuation, or review UX should stay consistent with `docs/project-northstar.md`
or explicitly update it.

## 2026-06-30: Start Evaluation With Crop-Readiness Skeleton

Status: Accepted

Context: Durable evaluation tables existed, but the browser still had no
testable evaluation workflow before AI vision, source adapters, and valuation
logic were connected.

Decision: Add an `Evaluate` action that creates a completed crop-readiness run,
stores placeholder observations, and assigns conservative per-crop buckets such
as `needs_better_image` or `not_enough_evidence`.

Rationale: This makes the evaluation lifecycle testable end to end without
pretending that identification, catalog matching, market evidence, or valuation
has happened.

Consequences: Future AI observation and source-adapter work should replace or
extend the skeleton records inside the same durable run model rather than
creating a separate workflow.

## 2026-06-30: Use Strict Observation Schema Before Vision Adapter

Status: Accepted

Context: The next pipeline stage needs AI-visible stamp observations, but model
output must remain reviewable, bounded, and separate from catalog identity or
valuation claims.

Decision: Define `stamp-observation-v1` as a strict JSON contract before adding
an AI vision adapter. The schema rejects extra fields, bounds confidence,
constrains cancellation and centering values, defaults important front-photo
unobservable factors, and maps validated payloads into durable observation
records.

Rationale: A strict contract makes prompt, parser, storage, and tests align
before network/model behavior is introduced.

Consequences: Future vision adapters should emit this schema and treat catalog
candidate IDs, market evidence, and value ranges as later pipeline stages.

## 2026-06-30: Keep AI Vision Opt-In

Status: Accepted

Context: The local MVP stores user album photos on disk and should remain
usable without sending private images to a model provider. At the same time,
the next evaluation phase needs a practical way to populate structured
observations from stamp crop images.

Decision: Add an OpenAI Responses API vision adapter behind explicit local
configuration: `PHILALENS_VISION_PROVIDER=openai` plus `OPENAI_API_KEY`. The
default provider remains `none`, so local evaluation creates placeholder
observations and no external calls. When enabled, only crops that do not need
crop review are submitted, and responses must validate against
`stamp-observation-v1` before they are stored.

Rationale: This makes the vision stage testable and useful while preserving the
local-first privacy posture by default.

Consequences: Future adapters should follow the same opt-in pattern and record
provider/model settings on each evaluation run. Source matching and valuation
must remain separate stages; vision observations cannot claim catalog identity
or price.

## 2026-06-30: Use Non-Price Triage Before Catalog Valuation

Status: Accepted

Context: The user wants to know whether a collection contains anything worth
attention before full catalog matching and market retrieval exist. OpenAI vision
can provide visible observations, but stamp prices often depend on catalog
variant, watermark, perforation, paper, shade, condition, and market evidence.

Decision: Add a local visible-observation triage pass that assigns conservative
non-price buckets: `likely_common`, `needs_source_matching`,
`possibly_interesting`, and `needs_expert_check`. Estimated value fields remain
empty until source-backed candidate matching and market evidence are connected.

Rationale: This gives immediate collection triage without presenting model-only
guesses as appraisals.

Consequences: Triage buckets should be treated as prioritization signals, not
prices. Future candidate matching and valuation may supersede these buckets
with source-backed value ranges and stronger confidence.

## 2026-06-30: Track OpenAI Evaluation Cost On Runs

Status: Accepted

Context: OpenAI vision evaluation can generate real API spend, and the user
wants to understand both expected and post-run cost before deeper valuation
features are connected.

Decision: Add a local costing module that gives rough pre-run estimates for the
configured OpenAI model/detail and stores post-run token usage/cost summaries in
evaluation-run `settings_json`. The settings dialog shows a cost dashboard built
from durable runs.

Rationale: Evaluation runs already preserve provider/model settings and are the
right audit boundary for reproducible analysis. Keeping cost data in run
settings avoids a schema migration while still making the data exportable and
visible in the UI.

Consequences: Cost values are informational and should be checked against
provider billing for final charges. Future non-OpenAI providers or richer
billing views can add structured tables if run-settings metadata becomes too
limited.
