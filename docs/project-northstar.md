# Philalens Northstar And Product Specification

Last updated: 2026-06-30

This document is the durable northstar for Philalens. Future sessions should use
it to split work into small implementation steps while preserving the final
product direction.

## Northstar

Philalens turns a batch of stamp album page photos into a reviewed,
evidence-backed collection inventory.

The final tool should let a user:

1. Upload all album pages in a collection.
2. Detect every individual stamp on every page.
3. Correct missed, merged, false-positive, or rotated crops.
4. Run automatic evaluation once crop curation is good enough.
5. Extract visible observations from each stamp crop.
6. Retrieve ranked candidate identities from allowed reference sources.
7. Gather catalog and market evidence where permitted.
8. Produce stamp-level value ranges, confidence, and next actions.
9. Produce collection-level triage, summary value ranges, and exports.
10. Review, override, and export results without losing evidence.

Philalens is a research and triage assistant, not a formal appraisal system.
Every identity and value estimate must remain explainable, source-backed, and
reviewable.

## Product Position

The product should be useful before it is perfect. The most valuable early
outcome is not exact catalog-number certainty for every stamp. It is a workflow
that quickly separates likely common material from stamps that deserve more
evidence, better images, or expert review.

Philalens should explicitly communicate:

- what is visible in the image
- what is inferred
- what source evidence supports the inference
- what important facts are unknown
- what confidence level applies
- what action the user should take next

## Primary User

The first user is a collector or inheritor with many album page photos, around
80 or more HEIC images for the initial collection. The user wants to understand
what is in the collection, identify possible outliers, estimate broad value
ranges, and export a usable inventory.

The user should not need to be a philatelic expert to benefit from the tool, but
the tool should respect expert workflows and uncertainty.

## Non-Goals

- Replacing a professional philatelic appraisal.
- Guaranteeing exact catalog numbers from front-side album photos.
- Bundling restricted catalog data without explicit permission.
- Treating active asking prices as realized market value.
- Hiding low-confidence or AI-generated assumptions.
- Spending expensive analysis effort equally on every common low-value stamp.

## End-State Workflow

### 1. Collection Setup

The user creates or opens a local collection and uploads all page photos.

The system stores:

- original files
- normalized page images
- page dimensions and format
- quality warnings
- page order
- collection metadata

### 2. Page-To-Stamp Segmentation

The system detects likely stamp regions and writes one crop per candidate
stamp.

Each crop stores:

- crop id
- page id
- page coordinate box
- rotation angle
- crop image path
- detector used
- segmentation confidence
- segmentation warnings
- review state

Manual correction remains mandatory before evaluation is trusted. Automatic
detection should favor recall during review because a weak crop can be rejected,
but a missing stamp cannot be evaluated.

### 3. Crop Curation

The user reviews coverage page by page.

The UI must support:

- coverage mode for spotting missed stamps
- selected-stamp location highlighting
- crop resizing
- crop rotation
- manual crop creation
- false-positive crop deletion
- page deletion and re-upload
- pending crop-review filter

Evaluation should be allowed only when the user chooses it, and the tool should
warn if unresolved crop-review items remain.

### 4. Evaluation Run

The user clicks an "Evaluate collection" action. The system creates an
evaluation run, then processes all eligible crops.

An evaluation run should be durable and versioned:

- run id
- collection id
- started/finished timestamps
- pipeline version
- model names and settings
- source adapters enabled
- status
- warnings and errors

Runs should be reproducible enough that later improvements can create a new run
without destroying old evidence.

### 5. Stamp Observation

For each crop, the system records visible observations, not final identity.

Observation fields should include:

- visible text
- country or issuing authority hints
- denomination and currency hints
- likely date or date range
- design subject
- dominant colors
- cancellation state
- approximate centering and margins
- visible perforation issues
- visible faults
- image quality warnings
- missing or unobservable details
- observation confidence
- model/source metadata

The observation step should explicitly say when watermark, paper, gum, reverse
condition, hidden thins, repairs, regumming, perforation gauge, or authenticity
cannot be determined from the image.

### 6. Candidate Retrieval

The system retrieves ranked candidate identities from source adapters.

Candidate ranking should combine:

- observation text match
- country/issuer match
- denomination match
- date/year compatibility
- design/topic similarity
- color compatibility
- visual embedding similarity
- contradiction checks
- source reliability

The system must return multiple candidates when uncertainty is meaningful. It
should not force one identity when evidence is weak.

### 7. Evidence Gathering

Each candidate can have supporting or contradicting evidence.

Evidence records should include:

- source name
- source type
- source URL or local reference id
- retrieved date
- matched fields
- price or catalog value fields, when present
- currency
- condition assumptions
- evidence tier
- confidence score
- licensing or usage notes

Evidence types:

- user-imported catalog/reference data
- public reference data
- licensed catalog data supplied by the user
- active marketplace listings
- realized sale or auction result data
- expertization/certificate references
- AI or embedding similarity evidence

### 8. Valuation

Valuation should produce ranges and next actions, not single definitive prices.

Each stamp valuation should store:

- low estimate
- high estimate
- currency
- identity confidence
- condition confidence
- market evidence confidence
- overall valuation confidence
- value bucket
- assumptions
- uncertainty warnings
- recommended next action
- evidence ids used

Value buckets:

- `likely_common`
- `identified_low_value`
- `needs_better_image`
- `possible_mid_value`
- `possible_high_value`
- `expert_review_recommended`
- `not_enough_evidence`

Recommended next actions:

- no further review needed
- review crop
- capture better front image
- capture back image
- measure perforation
- check watermark
- inspect gum or hinge state
- compare with licensed catalog
- search realized sales
- seek expert review

### 9. Collection Summary

The collection-level result should summarize value and risk without simply
summing optimistic high estimates.

Collection summary should include:

- total pages
- total crops
- evaluated stamps
- unevaluated stamps
- crop-review remaining
- candidate-confirmed count
- value bucket counts
- low/high collection range
- high-risk/high-uncertainty count
- possible outlier list
- recommended next batch actions

Collection totals should be conservative when many individual stamps have weak
identity or market confidence.

### 10. Review And Export

The user must be able to review each stage:

- crop review
- observation review
- candidate confirmation or rejection
- valuation readiness
- expert-review recommendation

Exports should include:

- CSV inventory
- JSON project export
- spreadsheet-ready rows
- collection summary
- evidence and source attribution
- review states
- confidence and uncertainty fields

## Evaluation Method

### Core Rule

Philalens should evaluate from evidence, not from unsupported model certainty.

The pipeline should follow this order:

1. Validate crop readiness.
2. Extract visible observations.
3. Group duplicates and near-duplicates.
4. Retrieve candidates from allowed sources.
5. Re-rank candidates with visual similarity and contradictions.
6. Gather catalog/reference evidence.
7. Gather market evidence where configured and permitted.
8. Estimate value range with uncertainty adjustments.
9. Assign value bucket and next action.
10. Store all intermediate evidence.

### Duplicate Clustering

Large album collections often contain duplicates or visually similar stamps.
Philalens should group likely duplicates before expensive valuation.

Duplicate grouping can be used to:

- evaluate one representative deeply
- apply lighter evaluation to group members
- detect condition differences between duplicates
- summarize bulk common material
- reduce marketplace/API calls

### Page And Series Context

Nearby stamps often share country, period, series, album organization, or theme.
Philalens should eventually use page-level context to improve ranking, while
still storing stamp-level evidence separately.

Examples:

- A page with mostly France stamps should raise France candidates.
- A row of same-series definitives should help ambiguous denominations.
- Multiple similar stamps may imply a series or issue period.

### Outlier Detection

The product should surface possible outliers even when confidence is not high.

Outlier signals:

- candidate set includes known high-value variants
- rare overprint or error possibility
- early issue date
- unusually high catalog/reference value
- scarce cancellation or cover-related context
- strong visual match to a higher-value candidate but missing variant evidence

Outlier output should say what proof is missing.

## Source Strategy

### First Source Priority

Start with user-imported sources and open/permissive source adapters.

This avoids relying on scraping and avoids bundling restricted catalogs. The
first source adapter should support a CSV or spreadsheet import with explicit
source metadata.

### Source Adapter Shape

Each adapter should return normalized source records with:

- source name
- source type
- license/usage notes
- source record id
- source URL or local path
- issuer/country
- issue year or date range
- title or design description
- denomination
- color
- catalog id, if legally supplied by the user/source
- variant notes
- condition/value fields, if supplied
- image path or URL, if permitted

### Public References

Public references can help with broad identification and context, but may not
be sufficient for exact catalog numbers or pricing.

Candidate public references:

- WADP Numbering System/WNS for official modern stamp issue records
- Wikidata/Wikipedia for broad structured facts and context
- public-domain or permissively licensed catalog/reference exports
- community datasets with clear licenses

### Marketplace Sources

Marketplace evidence must be separated by strength.

Evidence strength:

- strongest: realized auction/sale prices for same catalog identity and
  comparable condition
- medium: dealer prices or active listings with strong visual/source match
- weak: active asking prices, vague keyword matches, or AI-only similarity

eBay Browse API is useful for active listing keyword and image search, but
active listings are not realized sale prices. They should help identify market
interest and possible comparables, not determine final value alone.

### Open-Source Project Lessons

The current landscape does not show a mature open-source end-to-end stamp
valuation system. Useful pieces are:

- `code2k13/philately-tool`: Apache-2.0 YOLO cropper plus CLIP/sentence
  transformer embeddings and SQLite vector search. This is useful for image and
  text similarity over local stamps.
- `adrianspeyer/Canadian-Stamp-Identifier`: structured visual catalogue,
  proprietary IDs, strong browser performance, and explicit avoidance of Scott
  numbers. The project is AGPL and Canada-specific, so borrow concepts rather
  than copy data or code without license review.
- `stellasia/stamp-identifier`: small Weaviate-based image similarity
  prototype. It reinforces the idea that users need to bring or build a
  reference dataset.
- `php-coder/mystamps`: collection statistics, auction-sharing, and inventory
  UX ideas.
- `OpenNumismat/open-numismat`: adjacent collectibles inventory with import,
  export, reports, and image search concepts.

## Proposed Persistent Data Model

These are conceptual tables or records. Names can change during implementation,
but the information should remain represented.

### `evaluation_runs`

- `run_id`
- `collection_id`
- `status`
- `started_at`
- `finished_at`
- `pipeline_version`
- `vision_model`
- `embedding_model`
- `enabled_sources_json`
- `settings_json`
- `warnings_json`
- `errors_json`

### `stamp_observations`

- `observation_id`
- `run_id`
- `crop_id`
- `visible_text_json`
- `issuer_hint`
- `denomination_hint`
- `date_hint`
- `design_subject`
- `color_hints_json`
- `cancellation_state`
- `condition_notes_json`
- `image_quality_warnings_json`
- `unobservable_factors_json`
- `confidence`
- `model_metadata_json`
- `created_at`

### `catalog_candidates`

- `candidate_id`
- `run_id`
- `crop_id`
- `source_name`
- `source_record_id`
- `catalog_id`
- `issuer`
- `title`
- `year`
- `denomination`
- `variant_notes_json`
- `match_score`
- `rank`
- `supporting_evidence_ids_json`
- `contradiction_warnings_json`

### `source_evidence`

- `evidence_id`
- `run_id`
- `crop_id`
- `candidate_id`
- `source_name`
- `source_type`
- `source_url`
- `local_reference_id`
- `retrieved_at`
- `matched_fields_json`
- `price_low`
- `price_high`
- `price`
- `currency`
- `condition_assumptions`
- `evidence_tier`
- `confidence`
- `license_notes`
- `raw_payload_json`

### `stamp_valuations`

- `valuation_id`
- `run_id`
- `crop_id`
- `candidate_id`
- `estimated_value_low`
- `estimated_value_high`
- `currency`
- `identity_confidence`
- `condition_confidence`
- `market_evidence_confidence`
- `valuation_confidence`
- `value_bucket`
- `assumptions_json`
- `uncertainty_warnings_json`
- `recommended_next_action`
- `evidence_ids_json`
- `created_at`

### `embedding_index`

Embeddings may live in SQLite, sqlite-vec, a local vector database, or another
backend. They should be treated as a derived index over durable records.

Possible records:

- `embedding_id`
- `owner_type`
- `owner_id`
- `model_name`
- `embedding_dimension`
- `embedding_vector`
- `created_at`

## Confidence And Review Policy

### Identity Confidence

Identity confidence should reflect:

- crop quality
- observation confidence
- source agreement
- exact field matches
- visual similarity
- contradiction count
- unresolved variant risk

### Condition Confidence

Condition confidence should reflect:

- visible image quality
- cancellation and visible faults
- centering/margins
- whether front and back are available
- whether gum, watermark, paper, repairs, or hidden faults remain unknown

### Market Confidence

Market confidence should reflect:

- realized sale evidence vs active listing evidence
- number of comparable records
- recency
- source reliability
- condition comparability
- identity certainty
- price spread

### Review Gates

Suggested gates:

- If crop state is `needs_crop_review`, block or downgrade evaluation.
- If observation confidence is low, mark `needs_better_image`.
- If candidate match is ambiguous, keep multiple candidates.
- If candidate could be high value but variant evidence is missing, mark
  `expert_review_recommended`.
- If only active listings exist, keep market confidence low.
- If no trustworthy source exists, output `not_enough_evidence`.

## User Interface Requirements

### Evaluation Control

Add an explicit "Evaluate collection" action after crop curation. The user
should see:

- crops pending review
- sources enabled
- expected limitations
- run status and progress
- warnings for unavailable API keys or source data

### Evaluation Dashboard

The dashboard should show:

- collection value range
- value bucket counts
- possible outliers
- stamps needing better images
- stamps needing crop review
- expert-review recommendations
- source coverage

### Stamp Detail Review

Each stamp should show:

- crop image and page location
- observations
- candidate list with evidence
- valuation range and confidence
- uncertainty warnings
- recommended next action
- review controls

### Batch Review

Batch review should support:

- filter by value bucket
- filter by review state
- filter by low confidence
- filter by possible outlier
- filter by source missing
- group duplicates

## Implementation Sequence

Each step should be small enough for a focused development session.

### Phase A: Durable Evaluation Foundation

1. Add persistent tables for evaluation runs, observations, candidates,
   evidence, valuations, and embeddings or embedding metadata.
2. Add export fields for evaluation outputs.
3. Add API read endpoints for evaluation state.
4. Add tests for schema migration and export shape.

### Phase B: Observation Extraction

1. Define a strict stamp observation schema.
2. Add prompt and parser tests.
3. Add an optional AI vision adapter.
4. Store observations per crop and run.
5. Show observations in the visualizer.

### Phase C: User-Imported Source Adapter

1. Define normalized source record schema.
2. Add CSV/spreadsheet import.
3. Store source records with license/source metadata.
4. Add candidate retrieval over text fields.
5. Add candidate ranking tests.

### Phase D: Local Similarity Search

1. Add image/text embeddings for crops.
2. Add embeddings for allowed reference images.
3. Add duplicate clustering.
4. Add similar-stamp candidate retrieval.
5. Add search/debug UI for similarity matches.

### Phase E: First Evaluation Run

1. Add "Evaluate collection" endpoint.
2. Process eligible crops through observation and candidate retrieval.
3. Produce placeholder valuation buckets without marketplace calls.
4. Store run status and errors.
5. Add evaluation dashboard summary.

### Phase F: Market Evidence

1. Add marketplace source adapter interface.
2. Add eBay Browse API keyword search when configured.
3. Add eBay image search when configured and permitted.
4. Store active listing evidence as weak/medium evidence.
5. Keep realized-sales support as a separate stronger adapter when available.

### Phase G: Valuation And Review

1. Implement valuation range logic.
2. Add confidence scoring and escalation rules.
3. Add candidate confirmation/rejection workflow.
4. Add valuation review workflow.
5. Add collection-level conservative rollup.

### Phase H: Reporting

1. Add spreadsheet-style export.
2. Add collection summary report.
3. Add evidence appendix.
4. Add possible-outlier report.

## Acceptance Criteria For Final Tool

The final tool is useful when:

- the user can upload a full collection batch
- every visible stamp can be represented as an editable crop
- crop curation state is preserved
- evaluation can be run and re-run
- observations are stored with uncertainty
- candidates are ranked with source evidence
- values are ranges with confidence and assumptions
- possible valuable outliers are surfaced
- common low-value material is grouped efficiently
- exports preserve sources, confidence, review state, and next actions
- no restricted catalog data is bundled without permission

## Open Questions

- What first source format should be required for user-imported catalog data?
- Which public references have terms suitable for automated access?
- Should the first embedding backend be sqlite-vec, raw NumPy in SQLite, or a
  separate optional vector store?
- Which OpenAI vision model and schema should be used for observation
  extraction?
- Should marketplace search run automatically for all stamps or only possible
  outliers?
- What threshold should require expert review before showing high value ranges?
- Should front/back image capture be added before or after first valuation?

