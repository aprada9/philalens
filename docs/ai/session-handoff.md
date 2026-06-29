# Session Handoff

Last updated: 2026-06-29

## Current State

Philalens is an empty-new project that now has a committed foundation:

- Python/FastAPI backend skeleton.
- Initial domain models and placeholder pipeline.
- Product, architecture, data strategy, and roadmap docs.
- Agent operating guide and context infrastructure.
- Context guard script and GitHub Actions workflow.

## What The User Has Explained

The user owns many stamp album photos. Each page contains multiple stamps. The
target product should upload those photos, identify and analyze individual
stamps, cross-check against available sources, estimate individual stamp values,
and summarize full collection value.

The user specifically wants the repo to be easy for AI agents to develop,
maintain, and improve. New sessions should learn context from repo files rather
than requiring repeated chat history.

## What Is Not Built Yet

- Persistent storage.
- Real file upload handling.
- Stamp detection.
- OCR or AI vision extraction.
- Catalog matching.
- Market evidence retrieval.
- Value estimation.
- UI or review workflow.

## Recommended Next Session Start

1. Read `AGENTS.md`.
2. Read `docs/ai/context.md`.
3. Read `docs/product-brief.md`, `docs/architecture.md`, and
   `docs/data-strategy.md`.
4. Check `git status --short --branch`.
5. Ask or define the detailed MVP workflow before building more product code.

## Next Good Tasks

- Define the full product workflow with user decisions.
- Choose initial UI/deployment shape.
- Design persistent data models and storage.
- Implement upload persistence for album page photos.
- Prototype stamp segmentation on sample page images.

