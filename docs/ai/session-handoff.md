# Session Handoff

Last updated: 2026-06-29

## Current State

Philalens is an empty-new project that now has a committed foundation:

- Python/FastAPI backend skeleton.
- Initial domain models and placeholder pipeline.
- Product, architecture, data strategy, and roadmap docs.
- Agent operating guide and context infrastructure.
- Context guard script and GitHub Actions workflow.
- Product workflow and research notes for segmentation, valuation, and data
  sources.

## What The User Has Explained

The user owns many stamp album photos. Each page contains multiple stamps. The
target product should upload those photos, identify and analyze individual
stamps, cross-check against available sources, estimate individual stamp values,
and summarize full collection value.

The user specifically wants the repo to be easy for AI agents to develop,
maintain, and improve. New sessions should learn context from repo files rather
than requiring repeated chat history.

The user uploaded `ALBUM2_0659.HEIC` as the first real example. It is a
4032 x 3024 HEIC photo of a black album page with many mostly French used
stamps. The image confirms the workflow must isolate each stamp on a page before
analysis and must handle rotated, overlapping, partial, and tightly spaced
stamps.

## What Is Not Built Yet

- Persistent storage.
- Real file upload handling.
- Stamp detection.
- OCR or AI vision extraction.
- Catalog matching.
- Market evidence retrieval.
- Value estimation.
- UI or review workflow.

## Research Conclusions

- Valuation must be evidence-weighted and expressed as ranges.
- A front album photo is useful for issuer, denomination, design, cancellation,
  centering, visible faults, and rough condition.
- A front album photo usually cannot determine gum, watermark, paper, hidden
  thins, regumming, repairs, or expertized authenticity.
- Start with user-imported/source-adapter data; avoid unlicensed catalog bundling.
- eBay Browse API may help with active listing evidence, including image search,
  but active asking prices are weaker than realized sales.

## Recommended Next Session Start

1. Read `AGENTS.md`.
2. Read `docs/ai/context.md`.
3. Read `docs/product-brief.md`, `docs/product-workflow.md`,
   `docs/architecture.md`, `docs/data-strategy.md`, and `docs/research/`.
4. Check `git status --short --branch`.
5. Ask or define the detailed MVP workflow before building more product code.

## Next Good Tasks

- Define the full product workflow with user decisions.
- Choose initial UI/deployment shape.
- Design persistent data models and storage.
- Implement upload persistence for album page photos.
- Prototype stamp segmentation on sample page images.
- Define the source adapter schema and first CSV import path.
