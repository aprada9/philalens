# Roadmap

## Milestone 1: Repository Foundation

- Define product scope and architecture.
- Create backend project skeleton.
- Add initial API contract.
- Add inventory and valuation data models.
- Add agent operating docs and context update guardrails.
- Document sample page observations, valuation method, and source strategy.

## Milestone 1.5: Product Definition

- Define detailed MVP workflow and review states.
- Decide first UI and deployment shape.
- Decide initial data-source policy.
- Design persistent records for pages, crops, observations, candidates, evidence,
  valuations, and review state.
- Define confidence scoring and escalation rules.

## Milestone 2: Image Intake

- Upload multiple album page photos.
- Store originals and normalized derivatives.
- Return basic page analysis records.

## Milestone 3: Stamp Detection

- Detect likely stamp regions on a page.
- Extract crops and bounding boxes.
- Add manual correction hooks for missed or incorrect crops.
- Handle rotated, overlapping, partial, and tightly spaced stamps.

## Milestone 4: Vision Extraction

- Extract visible text and visual observations.
- Store evidence and uncertainty.
- Add prompt and schema tests for repeatability.

## Milestone 5: Catalog Matching

- Import a user-provided reference catalog.
- Rank candidate matches by observations and visual similarity.
- Expose alternative matches for review.

## Milestone 6: Valuation

- Attach market evidence to candidate matches.
- Produce low/high value estimates.
- Add collection-level summaries and export.
- Separate catalog/reference value, active asking price evidence, realized sale
  evidence, and condition uncertainty.

## Milestone 7: Review Experience

- Build a review UI for confirming or editing matches.
- Export CSV and JSON inventories.
- Track reviewed versus unreviewed estimates.
