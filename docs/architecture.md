# Architecture

## Pipeline

```text
album photos
  -> page preprocessing
  -> stamp detection and crop extraction
  -> manual crop review and correction
  -> OCR and visual feature extraction
  -> catalog candidate retrieval
  -> market evidence retrieval
  -> confidence scoring
  -> value estimation
  -> manual review and export
```

## Components

### Image Ingestion

Accepts album page photos, preserves the original image, and creates normalized derivatives for analysis.

### Stamp Segmentation

Finds individual stamps on a page and stores bounding boxes, crop paths, and quality metrics. Early versions can use classical image processing; later versions can add object detection models.

The sample album page shows that segmentation must handle regular grid-like
groups, rotated stamps, overlapping stamps, cancellations, dark album stock,
album rings, and partial crops. A manual correction loop is required before
valuation results are trusted.

### Vision Extraction

Extracts observable features from each crop:

- visible text
- country or issuing authority
- denomination and currency
- color palette
- cancellation state
- condition observations
- design description

### Candidate Matching

Searches catalog/reference records using extracted features and visual similarity. Returns ranked candidates with evidence, not a single forced answer.

### Valuation

Combines catalog metadata, condition signals, and market evidence into a range. Every estimate should include confidence and source references.

Valuation should explicitly separate:

- identity confidence
- condition confidence
- market evidence strength
- unobservable risk, such as watermark, paper, gum, hidden faults, or repairs

### Review UI

Lets a human confirm, reject, or edit candidate matches before exporting the inventory.

## Data Model

The first backend schema focuses on evidence capture:

- `StampObservation`: what the system sees in the image
- `CatalogCandidate`: possible catalog/reference match
- `StampAssessment`: combined observation, candidates, and value estimate
- `PageAnalysis`: all stamps detected on a page
- `CollectionSummary`: aggregate counts and value range

Future schema work should add persistent records for page images, crop regions,
source evidence, review state, and recommended next action.
