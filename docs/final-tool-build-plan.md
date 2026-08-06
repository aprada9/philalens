# Philalens Final Tool Build Plan

Last updated: 2026-07-02

> **SUPERSEDED (2026-08-06):** this plan is replaced by
> `docs/rebuild-plan-v2.md` after a full code audit and user decisions
> (OpenAI provider, personal-collection scope, React SPA rewrite, recapture
> loop). Kept for history; do not use as the execution plan.

This file is the execution plan for turning the current local crop/review MVP
into the final useful Philalens tool: an evidence-backed stamp identification
and value-triage assistant for a large album-photo collection.

Use this file as the detailed plan behind short `/goal` prompts. It is more
operational than `docs/project-northstar.md`: the northstar defines the final
product shape; this file defines the build sequence and guardrails for heavy
implementation sessions.

## Objective

Build Philalens so that, for each reviewed stamp crop, it can produce:

- visible observations with confidence and image-quality warnings
- ranked candidate identities from permitted/open sources
- source evidence records with attribution and usage notes
- conservative value/outlier buckets
- recommended next actions
- exportable review state and evidence

The tool should help the user find possibly valuable stamps with high practical
accuracy while avoiding false certainty. It should surface promising outliers,
common material, unresolved source gaps, and stamps that require better images
or expert checks.

## Hard Guardrails

- Do not run the full 80-page collection as a development experiment.
- Use a small calibration set of 2-4 representative pages until the insight
  pipeline is trustworthy.
- Treat cropping as mostly good. Improve segmentation or crop review only when
  direct evidence from the calibration set shows a problem.
- Do not send crops to paid/external AI providers unless the user intentionally
  starts selected-crop evaluation and cost/usage is visible.
- Do not scrape restricted catalogs or sites unless terms explicitly allow it.
- Do not bundle copyrighted catalog data without explicit permission.
- Do not present active asking prices as realized market value.
- Do not force a single identity when source evidence is ambiguous.
- Do not show confident value estimates without source-backed identity and
  market/reference evidence.
- Preserve uncertainty for watermark, paper, gum, perforation gauge, hidden
  faults, repairs, regumming, authenticity, and expertization when they cannot
  be determined from a front album photo.
- Store results in durable evaluation runs so improved pipelines can be re-run
  without destroying old evidence.

## Current Starting Point

The current app already has:

- local FastAPI backend
- SQLite/filesystem persistence
- HEIC-aware batch intake
- normalized page derivatives
- optional YOLO crop detection plus OpenCV fallback
- browser crop review and manual correction
- crop rotation and manual crop creation
- durable evaluation-run tables for observations, candidates, evidence,
  valuations, and embedding metadata
- strict `stamp-observation-v1` schema
- optional OpenAI vision adapter
- local visible-observation triage buckets
- evaluation cost estimates and recorded usage summaries
- CSV/JSON exports with latest evaluation fields

The missing final-tool layers are:

- source-record storage/import
- open-source/reference adapters
- candidate retrieval and ranking
- local similarity search and duplicate grouping
- source-backed value/outlier dashboard
- market evidence adapters
- conservative valuation ranges
- candidate and valuation review workflow
- final collection-level summary and report

## Source Reality

There does not appear to be a clean, open, worldwide stamp catalog API that
provides authoritative catalog IDs, images, variants, and values for all stamps.
The source strategy must therefore be layered:

1. Open knowledge/reference sources for candidate discovery.
2. Museum/archive sources for high-quality images and metadata.
3. Local similarity search over permitted reference images.
4. Marketplace evidence only after candidate identity is plausible.
5. User-imported or licensed catalog data as an optional future upgrade.

Primary source candidates:

- Wikidata: CC0 metadata, SPARQL/API/dumps, useful for entities, dates,
  countries, topics, and links.
- Wikimedia Commons: reusable images, but each file license and attribution
  requirement must be checked.
- Smithsonian Open Access: CC0 assets and API/GitHub metadata, especially useful
  for U.S. and notable philatelic material.
- Europeana: broad cultural heritage Search/Record/IIIF APIs with per-record
  rights metadata.
- WNS/WADP: official modern issue records since 2002 from participating postal
  administrations, likely weak for old album pages and no confirmed clean public
  API yet.
- eBay Browse API/searchByImage: useful later as weak active-listing evidence,
  not as appraisal evidence.

Avoid by default:

- scraping Colnect, StampWorld, StampData, Freestampcatalogue, or similar
  catalogs without clear terms/API/export permission
- using Scott, Michel, Yvert, Stanley Gibbons, Edifil, or other catalog numbers
  or price tables unless licensed or supplied by the user

## Phase 1: Make Current Observations Useful

Goal: ensure selected-crop evaluation produces reviewable observations, not just
opaque triage labels.

Tasks:

- Verify selected-crop OpenAI vision evaluation works only when explicitly
  configured.
- Keep full-collection evaluation disabled by habit during development; use
  selected crops from the calibration pages.
- Show observations clearly in stamp detail:
  - visible text
  - issuer/country hints
  - denomination and currency hints
  - date hints
  - design subject
  - dominant colors
  - cancellation state
  - condition notes
  - image-quality warnings
  - unobservable factors
  - confidence and model metadata
- Add or improve filters for:
  - `needs_source_matching`
  - `possibly_interesting`
  - `needs_expert_check`
  - `needs_better_image`
  - `not_enough_evidence`
- Harden prompt/skip rules against the calibration set.

Acceptance:

- On 10-20 selected crops, the user can see exactly what the model observed,
  what is uncertain, and why the crop needs source matching or expert review.
- No source-backed identity or value is implied at this phase.

## Phase 2: Source Adapter Foundation

Goal: create the local data layer that all source adapters and candidate
matching will use.

Tasks:

- Add durable source-record storage, either as a new `source_records` table or
  equivalent normalized records.
- Define a source record shape with:
  - source record id
  - source name
  - source type
  - license/usage notes
  - source URL or local path
  - retrieved/imported timestamp
  - issuer/country
  - issue year/date range
  - title/design description
  - denomination/currency
  - colors
  - topics/subjects
  - variant notes
  - image URL/path and image rights metadata
  - catalog/reference ids where legally supplied
  - value fields where legally supplied
  - raw payload JSON
- Add a source adapter interface separated from candidate ranking.
- Add a generic CSV/import adapter as a fallback path, even though the user does
  not currently have a CSV.
- Add tests for source-record parsing, storage, idempotent import, and export
  shape.

Acceptance:

- At least one source adapter can store normalized source records.
- Records can be queried locally and cited as source evidence.
- Source metadata and usage notes survive export.

## Phase 3: Open Source Adapters

Goal: obtain candidate identity evidence without relying on user-provided CSVs
or restricted catalog scraping.

Recommended order:

1. Wikidata/Commons adapter.
2. Smithsonian Open Access adapter.
3. Europeana adapter.
4. WNS/WADP research or limited adapter only if usable access is confirmed.

Wikidata/Commons tasks:

- Build query/search by issuer/country, visible text, denomination, design
  subject, topic, and date hints.
- Retrieve entity labels, descriptions, aliases, country/issuer, dates, topics,
  linked pages, and Commons images where available.
- Preserve Wikidata item IDs and source URLs.
- Preserve Commons file license, author, attribution, and image URL metadata.
- Respect Wikidata/Commons access etiquette.

Smithsonian tasks:

- Add API/GitHub metadata search for stamp/postal records.
- Keep CC0/open-access status explicit.
- Store Smithsonian object IDs, URLs, titles, places, dates, subjects, and image
  URLs where available.

Europeana tasks:

- Add Search API queries for stamp/postal terms and observations.
- Retrieve full records through Record API when a search result looks relevant.
- Preserve rights fields and provider attribution.
- Use images only when rights metadata permits.

Acceptance:

- Given observations such as "France", "25c", "Semeuse", "Liberty", or a
  visible name/topic, the system retrieves plausible source records with
  attribution.
- Source adapters can fail gracefully and mark source coverage gaps.

## Phase 4: Candidate Matching

Goal: turn observations plus source records into ranked candidate identities.

Tasks:

- Implement a candidate retrieval service that searches source records from
  enabled adapters.
- Rank candidates using:
  - issuer/country compatibility
  - denomination compatibility
  - visible text overlap
  - date/year compatibility
  - design/topic similarity
  - color compatibility
  - source reliability
  - contradiction warnings
- Store multiple `catalog_candidates` per crop and run.
- Link each candidate to supporting `source_evidence`.
- Keep no-match and ambiguous-match states explicit.
- Add ranking tests with synthetic records and real-like observation examples.

Acceptance:

- Each selected evaluated crop gets 0-N ranked candidates.
- Strong candidates explain matched fields.
- Weak candidates include contradiction warnings.
- No-match cases become `needs_source_matching` or `not_enough_evidence`, not
  fake identifications.

## Phase 5: Local Similarity And Duplicate Grouping

Goal: reduce expensive analysis and improve candidate ranking by grouping
similar stamps.

Tasks:

- Add local embeddings for crop images.
- Add embeddings for permitted reference images from source records.
- Cache embeddings in the existing embedding metadata/index structure.
- Start with a simple local vector approach before adding a heavier dependency.
- Add duplicate/near-duplicate grouping for collection crops.
- Use representative crops for deeper evaluation where duplicates are strong.
- Add UI filters or group display for duplicate groups.

Acceptance:

- Visually similar crops are grouped.
- Candidate ranking can use visual similarity as a supporting signal.
- Evaluation can avoid repeated expensive calls for obvious duplicate groups.

## Phase 6: First Real Evaluation Dashboard

Goal: make the app produce useful "what matters" insight before exact valuation.

Tasks:

- Add collection dashboard summaries:
  - evaluated stamps
  - unevaluated stamps
  - crop review remaining
  - source matched
  - no source match
  - likely common
  - possible outliers
  - needs better image
  - expert review recommended
  - source coverage
  - API cost summary
- Add stamp detail sections:
  - crop and page location
  - observations
  - candidate list
  - source evidence
  - uncertainty warnings
  - recommended next action
- Add filters by value/attention bucket, confidence, source missing, expert
  review, and duplicate group.

Acceptance:

- After running a calibration set, the user can quickly identify crops worth
  attention and crops that likely do not matter.
- The dashboard distinguishes AI observations from source-backed candidates.

## Phase 7: Market Evidence

Goal: attach market evidence only after candidate identity is plausible.

Tasks:

- Add a marketplace adapter interface.
- Implement eBay Browse keyword search and image search only when configured.
- Store evidence with:
  - listing title
  - URL
  - price and currency
  - listing format
  - active/sold status if known
  - condition text
  - query used
  - retrieved timestamp
  - confidence
  - evidence tier
  - raw payload
- Mark active eBay listings as weak evidence by default.
- Keep realized sale or auction-result adapters separate and stronger if a
  permitted source is later found.

Acceptance:

- Marketplace evidence is visible as weak/medium/strong evidence.
- Active asking prices never become standalone value estimates.
- Market searches are selective, ideally for plausible outliers or confirmed
  candidate groups.

## Phase 8: Conservative Valuation

Goal: produce value ranges and next actions only when evidence supports them.

Tasks:

- Implement valuation buckets before exact prices:
  - `likely_common`
  - `identified_low_value`
  - `possible_mid_value`
  - `possible_high_value`
  - `expert_review_recommended`
  - `needs_better_image`
  - `not_enough_evidence`
- Add low/high ranges only when identity confidence and evidence support them.
- Track separate confidence values:
  - identity confidence
  - condition confidence
  - market evidence confidence
  - overall valuation confidence
- Add explicit assumptions and uncertainty warnings.
- Recommend actions such as:
  - review crop
  - capture better front image
  - capture back image
  - measure perforation
  - check watermark
  - inspect gum/hinge state
  - compare with licensed catalog
  - search realized sales
  - seek expert review

Acceptance:

- Possible high-value stamps are surfaced without pretending certainty.
- Common/low-value stamps are separated from outliers.
- Every value range has evidence IDs, assumptions, and confidence fields.

## Phase 9: Final Collection Run

Goal: run the complete collection only after calibration pages prove the insight
pipeline is useful.

Full-run flow:

1. Upload all pages.
2. Review crops and mark obvious crop issues.
3. Group duplicates and near-duplicates.
4. Run cheap source matching broadly.
5. Run expensive AI vision/market calls selectively.
6. Review outliers, no-match cases, and expert-review recommendations.
7. Export inventory and collection summary.

Acceptance:

- The full run produces a conservative inventory.
- Possible outliers are clearly listed.
- Common material is grouped efficiently.
- Exports preserve observations, candidates, source evidence, valuation buckets,
  confidence, uncertainty, and review state.

## First Heavy-Work Session Checklist

The next heavy-work session should:

1. Read `AGENTS.md`.
2. Read `docs/ai/context.md`.
3. Read `docs/ai/context-index.md`.
4. Read `docs/project-northstar.md`.
5. Read this file.
6. Read `docs/data-strategy.md`, `docs/architecture.md`, and
   `docs/product-workflow.md`.
7. Check `git status --short --branch`.
8. Run backend tests if dependencies are installed.
9. Implement Phase 2 source adapter foundation.
10. Implement the first Wikidata/Commons source adapter slice.
11. Wire candidate retrieval into selected-crop evaluation only.
12. Add tests and update durable docs.

## Stop Conditions For Heavy Sessions

Do not stop after a half-wired source experiment. A checkpoint is complete when:

- relevant tests pass or skipped tests are explained
- source records are durable
- evidence attribution is preserved
- selected-crop evaluation can use the new layer without requiring a full run
- exports remain coherent
- `docs/ai/session-handoff.md` is accurate
- context updates are made for any product, architecture, data, prompt, or
  workflow change
