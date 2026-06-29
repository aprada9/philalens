# Decision Log

Durable project decisions live here. Add new entries when a choice affects
product direction, architecture, data strategy, or agent workflow.

## Template

```text
## YYYY-MM-DD: Decision Title

Status: Proposed | Accepted | Replaced

Context:
Decision:
Rationale:
Consequences:
```

## 2026-06-29: Use Philalens As Repository And Product Name

Status: Accepted

Context: The user wanted a name for a stamp analysis and valuation project.

Decision: Use `philalens` as the GitHub repository name and Philalens as the
product name.

Rationale: The name is short, brandable, and connected to philately and visual
analysis.

Consequences: Documentation and project identity should consistently use
Philalens.

## 2026-06-29: Position Estimates As Research, Not Appraisal

Status: Accepted

Context: Stamp values depend on subtle physical details, condition, and market
evidence. AI analysis from photos can be useful but uncertain.

Decision: Philalens should provide evidence-backed value ranges with confidence,
not formal appraisals.

Rationale: This is more honest, legally safer, and better aligned with the
limitations of image-based identification.

Consequences: UI, API, docs, and exports should avoid definitive appraisal
language unless a qualified expert review workflow is introduced later.

## 2026-06-29: Start With A Python/FastAPI Backend

Status: Accepted

Context: The project needs image ingestion, AI processing, data matching, and
future API/UI integration.

Decision: Start with a Python backend using FastAPI and structured domain models.

Rationale: Python has strong image processing and AI ecosystem support, while
FastAPI provides a simple API surface for future UI work.

Consequences: Backend code currently lives under `backend/`; frontend decisions
remain open.

## 2026-06-29: Make Agent Context A First-Class Artifact

Status: Accepted

Context: The user wants future AI sessions to understand the project without
repeating prior context.

Decision: Add `AGENTS.md`, agent adapter files, durable context docs, and a
context freshness guard.

Rationale: Future agents need a stable bootstrap path and a feedback loop that
keeps project memory synchronized with code changes.

Consequences: Meaningful changes must update context docs. CI should flag
changes that skip context updates.

