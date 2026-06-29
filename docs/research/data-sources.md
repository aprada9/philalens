# Data Source Research Notes

Philalens needs separate source layers for identity, catalog metadata, market
evidence, and expertization. Do not treat one source as sufficient for valuation.

## Source Categories

### Licensed Or Commercial Catalogs

Major worldwide catalogs include Scott, Michel, Stanley Gibbons, and Yvert et
Tellier. National catalogs such as Edifil can matter for Spain and former
Spanish colonies.

Use:

- authoritative identity and catalog numbering
- reference prices
- issue metadata
- variants, perforations, watermarks, and specialized notes

Constraints:

- data may be copyrighted or licensed
- numbering systems may have usage restrictions
- values are reference values, not guaranteed sale prices

Recommended approach:

- support user-provided licensed exports or manual imports
- avoid bundling restricted catalog datasets
- keep a source adapter boundary so licensed providers can be added later

### Online Reference Catalogs

Useful discovery/reference targets include:

- Colnect
- StampWorld
- StampData
- Freestampcatalogue
- Stamps of the World Wiki
- Wikidata/Wikipedia for broad context

Current research did not verify an official, reliable public API for the major
stamp-specific online catalogs. Treat them as candidate references whose terms
and access methods must be checked before automation.

Recommended approach:

- start with user-imported CSV/spreadsheet reference data
- add manual source links for evidence
- only build automated connectors for sources with clear API/terms permission

### Marketplace And Market Evidence

Market data should be separated into asking price versus realized sale evidence.

Potential sources:

- eBay Browse API keyword search
- eBay Browse API image search
- auction house result archives
- dealer inventories
- user-imported sale data

eBay's Browse API supports keyword search and image-based item search. This can
help collect active listing evidence, but active listings are not equivalent to
realized sale prices.

Recommended approach:

- use active listing data as weak-to-medium evidence
- prefer realized sales when available
- store retrieved date, URL, price, currency, condition, and matching rationale
- do not scrape sources unless terms allow it

### Expertization And Certificate Data

For possible high-value candidates, expertization may matter more than automated
visual scoring.

Potential uses:

- check whether a candidate catalog number is often forged or altered
- search certificate databases when available
- recommend professional expertization for high-value uncertain material

## Normalized Source Adapter Shape

Each source adapter should return:

- source name
- source type
- source URL or local reference id
- retrieved date
- candidate catalog id
- title or issue description
- issuer/country
- year or date range
- denomination
- condition assumptions
- value or price fields
- currency
- confidence or match score
- licensing/usage notes

## Source Links

- Stamp catalog overview and major catalogs:
  https://en.wikipedia.org/wiki/Stamp_catalog
- Scott catalogue:
  https://en.wikipedia.org/wiki/Scott_catalogue
- Stanley Gibbons catalogue:
  https://en.wikipedia.org/wiki/Stanley_Gibbons_catalogue
- Michel catalog:
  https://en.wikipedia.org/wiki/Michel_catalog
- Yvert et Tellier:
  https://en.wikipedia.org/wiki/Yvert_et_Tellier
- Colnect overview:
  https://en.wikipedia.org/wiki/Colnect
- eBay Browse API keyword search:
  https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
- eBay Browse API image search:
  https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/searchByImage

