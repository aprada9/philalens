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

### Local Storage

The current local MVP uses SQLite plus filesystem storage under `data/local/` by
default. The database tracks collections, pages, and detected crops. The
filesystem stores original uploads, normalized JPEG page derivatives, and crop
images.

Relevant modules:

- `backend/src/philalens/storage.py`
- `backend/src/philalens/imaging.py`

### Image Ingestion

Accepts batch album page photos, preserves the original image, and creates
normalized JPEG derivatives for browser display and segmentation. HEIC/HEIF
support is provided through `pillow-heif`.

### Stamp Segmentation

Finds individual stamps on a page and stores bounding boxes, crop paths, and quality metrics. Early versions can use classical image processing; later versions can add object detection models.

The sample album page shows that segmentation must handle regular grid-like
groups, rotated stamps, overlapping stamps, cancellations, dark album stock,
album rings, and partial crops. A manual correction loop is required before
valuation results are trusted.

The current segmentation implementation supports two local detector paths:

- optional YOLO detector using a local `model.pt` file, configured by
  `PHILALENS_STAMP_DETECTOR`, `PHILALENS_STAMP_YOLO_MODEL_PATH`,
  `PHILALENS_STAMP_YOLO_CONFIDENCE`, and
  `PHILALENS_STAMP_CROP_MARGIN_PERCENT`
- OpenCV fallback that thresholds likely foreground regions and filters
  stamp-like boxes

When available, the YOLO path follows the useful pattern from the Apache-2.0
`code2k13/philately-tool`: run a trained detector, expand boxes by a small
margin, write crops, and keep uncertain results reviewable. Philalens defaults
to a lower confidence threshold of `0.1` because the sample HEIC page recovered
68 candidate crops instead of 41 at the original stricter threshold. Low
confidence detections are marked `low_detector_confidence` and require crop
review rather than being trusted silently. The local model can be downloaded with
`scripts/download_stamp_detector.py`; it is stored under `data/local/models/`
and not committed to Git.

Both detector paths write crop images and mark suspicious boxes as
`needs_crop_review`. The detector is still expected to produce false positives,
missed stamps, and merged crops on difficult pages until iterated against real
album batches.

Relevant module:

- `backend/src/philalens/segmentation.py`

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

The current local browser visualizer lets the user upload batches, inspect page
images with crop overlays, move stamp-by-stamp through detected crops, re-detect
the current page, remove false-positive crop boxes, remove uploaded pages for
fresh re-upload, manually draw crop boxes for missed stamps, and export
CSV/JSON. Full-page overlays are for location and selection only; the selected
stamp is highlighted strongly in the full page, and crop-box resizing happens in
the selected-stamp inspector with corner drag handles or numeric fields. The
inspector also has a drag rotation handle for rotated stamps; rotation is stored
as `rotation_degrees` and used when writing the crop image. When no stamp is
selected, the full-page view shades areas outside detected crop boxes so missed
stamps are easier to spot. The stamp list can be filtered to `needs_crop_review`
crops, and the page/stamp lists scroll independently of the main page image.
Candidate descriptions, matching, and valuation are placeholders until later
pipeline stages are connected.

Relevant modules:

- `backend/src/philalens/api.py`
- `backend/src/philalens/visualizer.py`
- `backend/src/philalens/exports.py`

## Data Model

The first backend schema focuses on evidence capture:

- `StampObservation`: what the system sees in the image
- `CatalogCandidate`: possible catalog/reference match
- `StampAssessment`: combined observation, candidates, and value estimate
- `PageAnalysis`: all stamps detected on a page
- `CollectionSummary`: aggregate counts and value range

Future schema work should add persistent records for page images, crop regions,
source evidence, review state, and recommended next action.

Persistent records for page images, crop regions, crop rotation, and crop review
state now exist. Future schema work should add durable observation records,
source evidence records, candidate records, valuation records, and recommended
next action fields.
