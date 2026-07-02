# Agent Context Index

This index tells future agents where to find durable project memory.

## Required First Reads

- `AGENTS.md`: canonical agent operating guide.
- `docs/ai/context.md`: current project memory and known constraints.
- `docs/ai/session-handoff.md`: latest working state and next actions.
- `docs/ai/update-protocol.md`: how to keep context synchronized.

## Product Context

- `README.md`: high-level project summary and setup.
- `docs/project-northstar.md`: consolidated final-tool northstar and staged
  product/technical specification.
- `docs/final-tool-build-plan.md`: execution plan for heavy implementation
  sessions, including calibration-set guardrails, source adapter order,
  candidate matching, similarity search, dashboard, market evidence, and
  valuation.
- `docs/product-brief.md`: product problem, user, inputs, outputs, and non-goals.
- `docs/product-workflow.md`: proposed end-to-end product workflow and review states.
- `docs/roadmap.md`: staged plan.

## Technical Context

- `docs/architecture.md`: pipeline and component boundaries.
- `docs/data-strategy.md`: catalog, market data, licensing, and evidence strategy.
- `docs/research/philatelic-valuation.md`: valuation factors and confidence method.
- `docs/research/data-sources.md`: catalog, marketplace, and API source notes.
- `docs/research/sample-page-observations.md`: observations from the first album page example.
- `backend/pyproject.toml`: backend dependencies and tooling.
- `backend/src/philalens/models.py`: current data contracts.
- `backend/src/philalens/storage.py`: local SQLite persistence for collections,
  pages, crops, evaluation runs, observations, candidates, evidence,
  valuations, and embedding metadata.
- `backend/src/philalens/imaging.py`: image format support and normalization,
  including HEIC/HEIF registration.
- `backend/src/philalens/segmentation.py`: current OpenCV crop detection
  prototype plus optional YOLO detector path.
- `backend/src/philalens/evaluation.py`: current crop-readiness evaluation
  skeleton that creates durable runs and conservative placeholder buckets.
- `backend/src/philalens/observation_schema.py`: strict
  `stamp-observation-v1` schema, parser, JSON schema helper, and conversion to
  durable observation records.
- `backend/src/philalens/vision.py`: optional AI vision adapters, currently an
  opt-in OpenAI Responses API adapter for `stamp-observation-v1` records.
- `backend/src/philalens/costing.py`: OpenAI evaluation cost estimates,
  returned-token usage parsing, per-run cost summaries, and settings dashboard
  rollups.
- `backend/src/philalens/triage.py`: local visible-observation value-triage
  rules for attention buckets before catalog matching or pricing.
- `backend/src/philalens/exports.py`: CSV/JSON export shaping, including
  latest evaluation-run fields when records exist.
- `backend/src/philalens/prompts/stamp_analysis.md`: prompt draft aligned to
  `stamp-observation-v1`.
- `backend/src/philalens/visualizer.py`: local browser UI.
- `backend/src/philalens/pipeline.py`: compatibility pipeline placeholder.
- `backend/src/philalens/api.py`: FastAPI entrypoint.
  Includes settings read/write endpoints, selected-crop evaluation, and
  selected-crop deletion. Evaluation jobs expose pollable progress and cost
  metadata for the browser progress bar.
- `scripts/download_stamp_detector.py`: downloads the optional Apache-2.0 YOLO
  model into ignored local storage.

## Decision Memory

- `docs/ai/decisions.md`: durable decisions and rationale.

## Context Guard

- `scripts/check_agent_context.py`: local/CI check that asks for context updates
  when important files change.
- `.github/workflows/context-guard.yml`: GitHub Actions workflow for the guard.
