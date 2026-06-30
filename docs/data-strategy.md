# Data Strategy

## Principles

- Prefer data sources with clear usage rights.
- Store source attribution with every match and valuation.
- Separate catalog identity from market price evidence.
- Keep confidence explicit when the source data is weak.
- Keep user-uploaded image artifacts separate from catalog or market datasets.

## Local Project Data

The local MVP stores runtime project data under `data/local/` by default. This
includes:

- `philalens.sqlite` for collection, page, and crop metadata
- original uploaded album page images
- normalized JPEG page images for browser display and segmentation
- crop images for detected stamps

These local artifacts are ignored by Git. They should not be treated as catalog
or market data and should not be committed without explicit user intent.

## Candidate Source Types

### User-provided Data

CSV, spreadsheet, or local catalog exports supplied by the user. This is the safest first source because permissions are controlled by the user.

### Public Reference Data

Open or permissively licensed references can help identify countries, issuers, themes, and historical context. Public references may not be detailed enough for exact catalog numbers.

Potential references include Colnect, StampWorld, StampData, Freestampcatalogue,
Stamps of the World Wiki, Wikidata, and Wikipedia. API availability and terms
must be verified before automation; no source should be scraped without clear
permission.

### Licensed Catalog Data

Specialized philatelic catalogs are often copyrighted or licensed. Philalens should support importing licensed data but avoid bundling restricted datasets.

### Market Evidence

Useful valuation evidence includes realized sale prices, auction results, and recent marketplace transactions. Asking prices should be treated as weak evidence unless no better data exists.

eBay's Browse API can provide keyword and image-based search over listings, but
active listings are not the same as realized prices. Treat active marketplace
listings as weaker evidence than completed sales or auction realizations.

## Matching Strategy

1. Extract visible observations from the stamp image.
2. Retrieve candidates using text, denomination, country, date, and design clues.
3. Use visual similarity to re-rank candidates.
4. Apply condition and confidence adjustments.
5. Return a range with evidence rather than a single definitive price.

## Current Research Notes

More detailed notes are tracked in:

- `docs/research/data-sources.md`
- `docs/research/philatelic-valuation.md`
- `docs/research/sample-page-observations.md`

## Audit Trail

Each estimate should preserve:

- source name
- source URL or local reference id
- retrieved date
- matched fields
- confidence score
- explanation of the estimate
