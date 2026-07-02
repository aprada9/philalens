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
- durable evaluation-run records, observations, candidates, source evidence,
  valuations, and embedding metadata
- original uploaded album page images
- normalized JPEG page images for browser display and segmentation
- crop images for detected stamps

These local artifacts are ignored by Git. They should not be treated as bundled
catalog or market data and should not be committed without explicit user intent.
Source evidence records preserve metadata about where evidence came from, but
the first automated source adapters are still future work.

AI vision is also opt-in. By default, the local MVP does not send user images to
external model providers. Setting `PHILALENS_VISION_PROVIDER=openai` and
`OPENAI_API_KEY` enables the OpenAI vision adapter, which sends stamp crop
images to the configured model and stores only validated
`stamp-observation-v1` results in the local evaluation tables. The local browser
settings dialog can update these OpenAI settings in `.env`; API reads only
return whether a key is present, not the key value.

OpenAI evaluation cost tracking is local metadata. Pre-run cost estimates are
rough token heuristics based on configured model/detail and the number of crops
that would be sent to the provider. Post-run cost summaries use token usage
returned by OpenAI responses and a local USD-per-million-token pricing table.
These values help the user understand evaluation cost, but provider billing
remains the final source of truth and pricing should be rechecked when model
prices change.

## Candidate Source Types

The current preferred source order is:

1. Wikidata and Wikimedia Commons for open candidate discovery and reusable
   image metadata, with Commons file licenses handled per image.
2. Smithsonian Open Access for CC0 U.S. and notable philatelic metadata/images.
3. Europeana for broader cultural heritage records and images with per-record
   rights handling.
4. WNS/WADP only if usable access is confirmed, mainly for modern official
   issues since 2002.
5. Marketplace APIs only after identity is plausible, and active listings must
   be stored as weak evidence.

Do not assume the user has a catalog CSV. Keep a CSV/import adapter as a useful
fallback and future licensed-data path, but the first source-backed matching
work should use open/permitted APIs.

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

The eBay Browse API should be introduced after candidate matching, not before.
It can help gather weak active-listing evidence for plausible candidates or
outliers, but it should not drive identity or valuation by itself.

## Matching Strategy

1. Extract visible observations from the stamp image.
2. Retrieve candidates using text, denomination, country, date, and design clues.
3. Use visual similarity to re-rank candidates.
4. Apply condition and confidence adjustments.
5. Return a range with evidence rather than a single definitive price.

## Evaluation Source Lessons

A recent source scan did not find a mature open-source end-to-end stamp album
valuation system. Useful pieces exist and should guide Philalens:

- `code2k13/philately-tool` is Apache-2.0 and combines YOLO cropping, local
  crop indexing, CLIP/sentence-transformer embeddings, and SQLite vector search.
- `adrianspeyer/Canadian-Stamp-Identifier` demonstrates a structured visual
  stamp catalogue with proprietary IDs and explicit avoidance of Scott numbers,
  but it is AGPL and Canada-specific, so reuse needs license review.
- smaller image-similarity prototypes reinforce that Philalens should support
  user-provided or permitted reference datasets rather than assume a public
  all-world catalog is freely available.

The durable evaluation source policy and adapter shape are specified in
`docs/project-northstar.md`.

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
