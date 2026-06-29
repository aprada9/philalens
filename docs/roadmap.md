# Roadmap

## Milestone 1: Repository Foundation

- Define product scope and architecture.
- Create backend project skeleton.
- Add initial API contract.
- Add inventory and valuation data models.
- Add agent operating docs and context update guardrails.

## Milestone 2: Image Intake

- Upload multiple album page photos.
- Store originals and normalized derivatives.
- Return basic page analysis records.

## Milestone 3: Stamp Detection

- Detect likely stamp regions on a page.
- Extract crops and bounding boxes.
- Add manual correction hooks for missed or incorrect crops.

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

## Milestone 7: Review Experience

- Build a review UI for confirming or editing matches.
- Export CSV and JSON inventories.
- Track reviewed versus unreviewed estimates.
