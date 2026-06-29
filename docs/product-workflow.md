# Product Workflow

Philalens should turn album page photos into a reviewed, evidence-backed stamp
inventory. The workflow must make uncertainty explicit because many valuation
drivers are not visible in a single front-side album photo.

## 1. Collection Intake

The user uploads a batch of album page images. The system stores originals and
normalizes working copies.

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

## 6. Review And Export

The user reviews page crops and candidate matches before treating estimates as
useful.

Useful exports:

- CSV inventory
- JSON project data
- spreadsheet with one row per stamp
- collection summary report

## Review States

Use explicit review states:

- `unreviewed`
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

