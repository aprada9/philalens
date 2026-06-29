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
backend/              Python API and analysis pipeline
docs/                 Product, architecture, data, and roadmap notes
data/                 Local sample data, ignored except placeholders
notebooks/            Exploration notebooks, ignored except placeholders
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

