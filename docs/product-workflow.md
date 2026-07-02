# Product Workflow

Philalens should turn album page photos into a reviewed, evidence-backed stamp
inventory. The workflow must make uncertainty explicit because many valuation
drivers are not visible in a single front-side album photo.

## 1. Collection Intake

The user uploads a batch of album page images. The first real target batch is
around 80 mostly HEIC photos. The system stores originals locally and normalizes
browser-friendly JPEG working copies.

For each page, capture:

- original filename
- page order
- image dimensions and format
- quality warnings such as blur, glare, skew, partial page crop, or low light
- detected page bounds

## 2. Page Segmentation

The system detects individual stamps on each page and creates crops.

Each crop should preserve:

- bounding box on the original page
- rotation angle
- crop image path
- segmentation confidence
- overlap/touching warnings
- manual correction status

Manual correction is required for the MVP because album pages can include
overlapping, rotated, partially hidden, or touching stamps.

The current implementation detects likely stamp regions automatically and flags
low-confidence or geometrically suspicious crops with `needs_crop_review`.
When the optional YOLO detector model is installed locally, new uploads use it;
otherwise the app falls back to OpenCV. The YOLO threshold is tuned for higher
review coverage; low-confidence detections are flagged instead of dropped.
Manual correction should focus on flagged crops first, while still making all
crop boxes editable in the selected-stamp inspector with drag handles and
numeric fields. Full-page overlays should remain focused on locating and
selecting stamps. When no stamp is selected, the full-page review mode should
shade areas outside detected crop boxes so missed stamps stand out during
coverage checks. The user must be able to filter to crops pending review and
remove false-positive crop boxes or uploaded pages that need a clean re-upload.
When a stamp is missed, the user can draw a new manual crop on the full-page
view. Rotated stamps can be handled from the selected-stamp inspector through a
drag rotation handle; rotation is persisted with the crop rather than exposed as
a numeric correction field.

## 3. Stamp Observation

Each crop is analyzed for visible facts, not final identity.

Capture:

- visible country or issuing authority
- visible text
- denomination and currency
- design subject
- dominant colors
- cancellation or unused/mint hints
- centering and margin observations
- visible perforation issues
- visible faults such as tears, stains, toning, clipped corners, folds, or heavy
  cancellation
- missing information that cannot be determined from the crop

Observation should run inside a durable evaluation run so results can be
reproduced, reviewed, and superseded by later pipeline versions.

The current app can create a durable crop-readiness evaluation run. With the
default local configuration, this skeleton records placeholder observations and
assigns conservative per-crop buckets such as `needs_better_image` for crops
still needing review or `not_enough_evidence` when no source evidence exists
yet.

The strict `stamp-observation-v1` schema preserves visible facts, uncertainty,
image-quality warnings, and front-photo unobservable factors while rejecting
catalog identity or valuation fields that belong to later stages. An optional
OpenAI vision adapter can now write those observation records during evaluation
for crops that do not still need crop review.

After an observation exists, the current app applies a conservative local triage
pass. It can mark a stamp as `likely_common`, `needs_source_matching`,
`possibly_interesting`, or `needs_expert_check` based on visible clues such as
age hints, special-issue text, overprint/surcharge signals, obvious faults, and
observation confidence. This is not a price estimate; it is a prioritization
step for finding stamps worth deeper source matching.

The browser review workflow supports triage-oriented batch actions. Stamp rows
can be multi-selected, selected crops can be deleted together, and evaluation
can be run only for the selected stamps. Each row shows the latest triage bucket
next to the stamp label so the user can scan for relevant results before deeper
source matching. For crop QA, the user can filter to `needs_crop_review`, select
all visible review crops, and mark them ready in one action when visual
inspection confirms the crops are acceptable. Row badges are labeled by topic:
`Crop:` for crop-review state and `Eval:` for evaluation triage.

Evaluation runs should show progress while they are active. The current browser
starts an evaluation job, polls job status, and displays the current stamp crop
image plus a progress bar so long-running AI vision calls are observable.
Before a run starts, the browser asks the API for a rough OpenAI cost estimate
for the current selection. After a run completes, returned token usage and local
USD cost calculations are kept on the durable evaluation run and summarized in
the Settings cost dashboard.

## 4. Candidate Identification

The system retrieves candidate matches from allowed catalog/reference sources.
It should return ranked candidates, not a single forced answer.

Candidate ranking should combine:

- country/issuer match
- denomination and text match
- design and color similarity
- approximate issue period
- catalog metadata
- visual similarity
- contradiction checks

## 5. Valuation

Valuation should produce a range with evidence and confidence.

Inputs:

- candidate identity confidence
- catalog/reference price data when available and licensed
- market evidence from active listings, realized sale data, or user-imported
  price history
- observable condition adjustments
- warnings for unobservable high-impact factors

Outputs:

- low estimate
- high estimate
- currency
- confidence
- evidence list
- assumptions
- recommended next action

Valuation should also assign a value bucket such as `likely_common`,
`identified_low_value`, `needs_better_image`, `possible_mid_value`,
`possible_high_value`, `expert_review_recommended`, or `not_enough_evidence`.
These buckets should drive collection-level triage and batch review.

## 6. Review And Export

The user reviews page crops and candidate matches before treating estimates as
useful.

Useful exports:

- CSV inventory
- JSON project data
- spreadsheet with one row per stamp
- collection summary report

The full evaluation workflow, source strategy, conceptual data model, and
implementation sequence are tracked in `docs/project-northstar.md`.

## Review States

Use explicit review states:

- `unreviewed`
- `needs_crop_review`
- `needs_better_image`
- `candidate_confirmed`
- `candidate_rejected`
- `expert_review_recommended`
- `valuation_ready`

## High-Value Escalation

When a stamp might be valuable, Philalens should recommend more evidence rather
than pretend certainty:

- front and back scan
- higher-resolution crop
- watermark/perforation check
- expert certificate search
- professional expertization
