# Data Strategy

## Principles

- Prefer data sources with clear usage rights.
- Store source attribution with every match and valuation.
- Separate catalog identity from market price evidence.
- Keep confidence explicit when the source data is weak.

## Candidate Source Types

### User-provided Data

CSV, spreadsheet, or local catalog exports supplied by the user. This is the safest first source because permissions are controlled by the user.

### Public Reference Data

Open or permissively licensed references can help identify countries, issuers, themes, and historical context. Public references may not be detailed enough for exact catalog numbers.

### Licensed Catalog Data

Specialized philatelic catalogs are often copyrighted or licensed. Philalens should support importing licensed data but avoid bundling restricted datasets.

### Market Evidence

Useful valuation evidence includes realized sale prices, auction results, and recent marketplace transactions. Asking prices should be treated as weak evidence unless no better data exists.

## Matching Strategy

1. Extract visible observations from the stamp image.
2. Retrieve candidates using text, denomination, country, date, and design clues.
3. Use visual similarity to re-rank candidates.
4. Apply condition and confidence adjustments.
5. Return a range with evidence rather than a single definitive price.

## Audit Trail

Each estimate should preserve:

- source name
- source URL or local reference id
- retrieved date
- matched fields
- confidence score
- explanation of the estimate

