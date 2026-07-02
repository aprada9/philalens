# Product Brief

## Problem

Large stamp collections are hard to inventory manually. Album page photos often contain many stamps, and each stamp may require identification across country, year, denomination, print variant, condition, and market context.

## Goal

Philalens helps convert album photos into a searchable, reviewable stamp inventory with candidate identifications and value estimates.

The full product northstar and staged implementation specification are tracked
in `docs/project-northstar.md`. That document should guide future sessions when
splitting the final tool into buildable steps.

## Primary User

A collector or inheritor of a stamp collection who wants an initial understanding of what the collection contains and which stamps may deserve expert review.

## Inputs

- Batch album page photos, mostly HEIC for the first user collection.
- Optional manual notes.
- Optional catalog exports or user-provided reference data.

## Outputs

- Page-level detected stamps.
- Stamp-level candidate matches.
- Confidence scores and evidence.
- Estimated value range per stamp.
- Collection-level summary.
- Exportable CSV and JSON inventory.
- Local visualizer for page-by-page and stamp-by-stamp review.

## Core Product Position

Philalens should optimize for triage and evidence. The first valuable product is
not an exact appraisal engine; it is a workflow that separates common low-value
material from possible outliers, explains the evidence, and tells the user when
better images or expert review are needed.

The first implementation is local-first: it stores uploaded page images,
normalized derivatives, crop images, SQLite project state, and durable
evaluation-result records on the user's machine. The browser UI should support
batch review and correction before later AI description, matching, and valuation
stages are trusted.

After crop curation, the next major product phase is an explicit collection
evaluation run. The storage and read/export foundation for evaluation runs now
exists, and the browser can create a first crop-readiness run that records
placeholder observations and conservative per-crop buckets without prices. The
strict `stamp-observation-v1` schema now defines the AI-visible observation
contract, and an optional OpenAI adapter can write validated observations when
explicitly enabled. The run now performs first-pass visible-observation triage
to surface `possibly_interesting` or `needs_expert_check` crops without prices.
When OpenAI vision is used, Philalens records returned token usage and local USD
cost calculations on the run, exposes a rough pre-run estimate for selected or
full-collection evaluations, and shows a cost dashboard in Settings. The next
product work is to retrieve ranked candidates from allowed sources, gather
source and market evidence where configured, assign evidence-backed value
buckets, and produce value ranges with recommended next actions.

## Non-goals

- Replacing a professional philatelic appraisal.
- Guaranteeing exact catalog numbers without human review.
- Scraping or redistributing restricted catalog data without permission.

## Key Risks

- Similar stamp designs can differ by subtle perforation, watermark, paper, or overprint details.
- Cancellations and poor photo quality can hide critical features.
- Catalog and market data may be licensed, incomplete, or region-specific.
- Asking price is not the same as realized sale price.
- A front-side album photo cannot reliably assess gum, watermark, hidden thins,
  regumming, or many repairs.
