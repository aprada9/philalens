# Agent Context Index

This index tells future agents where to find durable project memory.

## Required First Reads

- `AGENTS.md`: canonical agent operating guide.
- `docs/ai/context.md`: current project memory and known constraints.
- `docs/ai/session-handoff.md`: latest working state and next actions.
- `docs/ai/update-protocol.md`: how to keep context synchronized.

## Product Context

- `README.md`: high-level project summary and setup.
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
- `backend/src/philalens/pipeline.py`: current analysis pipeline placeholder.
- `backend/src/philalens/api.py`: FastAPI entrypoint.

## Decision Memory

- `docs/ai/decisions.md`: durable decisions and rationale.

## Context Guard

- `scripts/check_agent_context.py`: local/CI check that asks for context updates
  when important files change.
- `.github/workflows/context-guard.yml`: GitHub Actions workflow for the guard.
