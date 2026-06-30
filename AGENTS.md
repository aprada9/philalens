# Agent Operating Guide

This is the canonical operating guide for AI agents working on Philalens. Claude,
Gemini, GPT-based agents, Codex, and future agents should treat this file as the
starting point for every session.

## Start Every Session Here

1. Read this file completely.
2. Read `docs/ai/context.md` for the current project memory.
3. Read `docs/ai/context-index.md` to understand where durable context lives.
4. Read the relevant product and technical docs before changing behavior:
   - `README.md`
   - `docs/product-brief.md`
   - `docs/architecture.md`
   - `docs/data-strategy.md`
   - `docs/roadmap.md`
5. Check repository state with `git status --short --branch`.
6. Before finishing, follow `docs/ai/update-protocol.md`.

## Project Mission

Philalens helps analyze stamp collections from album page photos. A user should
be able to upload many page images, detect individual stamps, identify likely
catalog matches, collect evidence, estimate value ranges, and review/export a
collection inventory.

Philalens is a research and organization assistant, not a formal appraisal
replacement. Estimates must carry evidence and confidence.

## Current Phase

The project is in local MVP foundation mode. The codebase contains a Python /
FastAPI backend with local SQLite/filesystem persistence, HEIC-aware batch image
intake, normalized page derivatives, automatic stamp segmentation with optional
YOLO and OpenCV fallback paths, CSV/JSON exports, and a browser visualizer for
page-by-page and stamp-by-stamp review. Do not assume AI vision extraction,
catalog matching, market retrieval, or valuation are implemented yet.

## Engineering Principles

- Prefer small, reviewable changes over broad rewrites.
- Keep product decisions explicit in docs, not only in chat.
- Preserve evidence and uncertainty in data models and UI language.
- Do not bundle restricted catalog data unless licensing is clear.
- Treat asking prices as weaker valuation evidence than realized sales.
- Prefer structured schemas and tests for AI outputs.
- Add manual review paths for any AI-generated identification or estimate.

## Agent Context Rule

Any change that affects product behavior, architecture, data flow, dependencies,
developer workflow, roadmap, or agent workflow must update the relevant durable
context before the work is considered done.

At minimum, check whether these files need updates:

- `docs/ai/context.md`
- `docs/ai/session-handoff.md`
- `docs/ai/decisions.md`
- `docs/architecture.md`
- `docs/product-brief.md`
- `docs/data-strategy.md`
- `docs/roadmap.md`

The repository includes `scripts/check_agent_context.py` and a GitHub Actions
workflow to catch code/product changes that do not update context.

## Definition Of Done

A change is done when:

- Code or docs are implemented in the smallest coherent scope.
- Tests or smoke checks relevant to the change pass.
- Durable context is updated when the change alters project understanding.
- `docs/ai/session-handoff.md` reflects the current state and next likely steps.
- `scripts/check_agent_context.py` passes for the change set.
- The repository is left in a clean, understandable state.

## Useful Commands

```bash
git status --short --branch
python3 scripts/check_agent_context.py --base HEAD~1 --head HEAD
```

Backend setup:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn philalens.api:app --reload
```

The local visualizer is served at `http://127.0.0.1:8000/`. Runtime collection
data is stored under `data/local/` by default and is intentionally ignored by
Git.

The better cropper is optional because it uses Ultralytics/PyTorch. To enable it,
install `pip install -e ".[dev,yolo]"` from `backend/`, then run
`python3 scripts/download_stamp_detector.py` from the repository root.

## When Unsure

If requirements are unclear, capture the uncertainty in `docs/ai/context.md` or
`docs/ai/session-handoff.md`, then make the smallest reversible implementation
that improves the project.
