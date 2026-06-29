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

## 2026-06-29: Use A Segmentation-First Product Workflow

Status: Accepted

Context: The first real sample page contains many stamps on one album page,
including regular rows, rotated stamps, overlapping stamps, cancellations, album
rings, and partial crops.

Decision: Philalens should first solve page-to-stamp segmentation with manual
crop review before trying to value stamps.

Rationale: Identification and valuation are only useful if the system isolates
the correct stamp and records crop confidence.

Consequences: The MVP needs page records, crop records, segmentation confidence,
and manual correction states.

## 2026-06-29: Estimate Value As Evidence-Weighted Ranges

Status: Accepted

Context: Many valuation factors are not visible from one front-side album photo,
including watermark, paper, gum, hidden thins, regumming, and repairs.

Decision: Philalens should output value ranges with identity confidence,
condition confidence, evidence links, assumptions, and next-action guidance.

Rationale: This gives useful collection triage without pretending to be a formal
appraisal.

Consequences: The data model and UI should represent evidence, uncertainty, and
review status as first-class fields.

## 2026-06-29: Use Source Adapters And Avoid Unlicensed Catalog Bundling

Status: Accepted

Context: Stamp catalogs and price data may be copyrighted or licensed. Current
research did not verify a reliable official public API for stamp-specific online
catalogs such as Colnect or StampWorld.

Decision: Start with source adapters and user-imported reference data. Add
automated connectors only for sources with clear API and terms permission.

Rationale: This keeps the project useful while reducing legal and maintenance
risk.

Consequences: Data-source code should preserve source attribution, retrieved
date, licensing notes, and confidence.
