# Philalens

AI-assisted stamp collection analyzer that identifies stamps from album page photos, matches them against catalog data, and estimates potential collection value.

Philalens is designed for collections where each album page photo contains multiple stamps. The goal is to turn a folder of page images into a structured inventory with candidate identifications, evidence, confidence levels, and estimated value ranges.

## MVP Workflow

1. Upload album page photos in batches, including mostly HEIC collections.
2. Store originals locally and create normalized working images.
3. Detect and crop individual stamps from each page.
4. Review detected crops in the local browser visualizer, with uncertain crops flagged for correction.
5. Extract visual signals such as country, text, denomination, color, cancellation marks, perforation hints, and condition.
6. Match each stamp against catalog and market data sources.
7. Estimate a value range with confidence and source evidence.
8. Produce a collection-level summary and CSV/JSON exports.

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

The consolidated final-tool direction lives in `docs/project-northstar.md`.
Use it as the northstar when splitting future work into focused sessions,
especially for evaluation, matching, valuation, review, and reporting.

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
http://127.0.0.1:8000/
```

The OpenAPI docs remain available at:

```text
http://127.0.0.1:8000/docs
```

By default, local runtime data is stored under `data/local/`, including the
SQLite database, original uploads, normalized JPEG page images, and crop images.
The SQLite schema also includes the durable evaluation foundation: versioned
evaluation runs, stamp observations, catalog candidates, source evidence,
valuations, and embedding metadata. The local visualizer can create an
evaluation run that assigns conservative buckets such as `needs_better_image`,
`likely_common`, `possibly_interesting`, or `needs_expert_check` without prices.
AI source matching and real valuation logic are not connected by default. An
optional OpenAI vision adapter can be enabled with
`PHILALENS_VISION_PROVIDER=openai`; it writes validated
`stamp-observation-v1` records for crops that do not need crop review, and the
evaluation run uses those visible observations for first-pass value triage. The
OpenAI path records returned token usage and a local USD cost calculation on the
evaluation run, and the API can provide a rough pre-run cost estimate for the
current collection or selected crops. Catalog matching and price valuation still
remain later phases.

## Optional YOLO Stamp Detector

The baseline app can segment stamps with OpenCV, but the better local path is an
optional YOLO detector adapted from the Apache-2.0
[`code2k13/philately-tool`](https://github.com/code2k13/philately-tool)
approach.

```bash
cd backend
source .venv/bin/activate
pip install -e ".[dev,yolo]"
cd ..
python3 scripts/download_stamp_detector.py
```

With the downloaded model at the default path, `PHILALENS_STAMP_DETECTOR=auto`
uses YOLO for new uploads and falls back to OpenCV when the model or dependency
is unavailable. The default YOLO confidence is intentionally low (`0.1`) for
review coverage; low-confidence detections are flagged for crop review instead
of being silently dropped. Existing pages can be processed again with the
visualizer's `Re-detect page` control.

The local visualizer supports crop review in two modes: no selected stamp shows
a shaded coverage view for spotting stamps outside detected crop boxes, while a
selected stamp opens inspector-based crop resizing with corner drag handles and
numeric fields. It also includes a quick `Review only` filter plus controls to
remove false-positive crop boxes or uploaded pages that should be re-uploaded.
Stamp rows can be multi-selected to remove several crops or evaluate only that
subset. The review filter plus `Select visible` and `Mark ready` controls let
the user accept many `needs_crop_review` crops at once. Each row separates crop
status (`Crop: ready` or `Crop: needs review`) from evaluation triage (`Eval:
likely common`, `Eval: needs expert check`, etc.) so attention-worthy crops are
easier to find. Evaluation runs show a live progress bar with the current stamp
crop image being analyzed plus estimated or recorded API cost when available.
Missed stamps can be added by drawing a manual crop on the full page, and
rotated stamps can be corrected with an inspector drag handle; crop rotation is
saved in local storage and exports. The browser also includes a local settings
dialog for OpenAI provider, model, image-detail, API-key configuration, and a
cost dashboard summarizing recorded evaluation API usage.

## Early Development Priorities

- Improve robust page-to-stamp segmentation.
- Collect allowed catalog and market data sources.
- Show validated AI observations in the review flow.
- Implement candidate matching and confidence scoring.
- Add manual review before treating estimates as useful.
