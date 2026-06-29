# Philalens

AI-assisted stamp collection analyzer that identifies stamps from album page photos, matches them against catalog data, and estimates potential collection value.

Philalens is designed for collections where each album page photo contains multiple stamps. The goal is to turn a folder of page images into a structured inventory with candidate identifications, evidence, confidence levels, and estimated value ranges.

## MVP Workflow

1. Upload album page photos.
2. Detect and crop individual stamps from each page.
3. Extract visual signals such as country, text, denomination, color, cancellation marks, perforation hints, and condition.
4. Match each stamp against catalog and market data sources.
5. Estimate a value range with confidence and source evidence.
6. Produce a collection-level summary and exportable inventory.

## Valuation Note

Stamp values depend heavily on condition, rarity, watermark, perforation, cancellation, gum, printing variant, and current market demand. Philalens should provide research-backed estimates and confidence levels, not formal appraisals.

## Repository Structure

```text
AGENTS.md             Canonical operating guide for AI agents
backend/              Python API and analysis pipeline
docs/                 Product, architecture, data, and roadmap notes
docs/ai/              Durable context for future AI coding sessions
data/                 Local sample data, ignored except placeholders
notebooks/            Exploration notebooks, ignored except placeholders
scripts/              Developer and context-maintenance utilities
```

## Agentic Development

Philalens is set up to be easy for future AI agents to continue. New sessions
should start with `AGENTS.md`, then read `docs/ai/context.md` and
`docs/ai/session-handoff.md`.

When meaningful code, product, architecture, data, or workflow changes are made,
the durable context docs should be updated in the same change. The repository
includes a context guard:

```bash
python3 scripts/check_agent_context.py --base HEAD~1 --head HEAD
```

Or use:

```bash
make context-check
make smoke
```

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn philalens.api:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

## Early Development Priorities

- Build robust page-to-stamp segmentation.
- Define a normalized stamp inventory schema.
- Collect allowed catalog and market data sources.
- Add AI vision extraction with evidence capture.
- Implement candidate matching and confidence scoring.
- Add manual review before treating estimates as useful.
