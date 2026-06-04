# Florida Statewide Property Data Plan

## Goal

Build a complete Florida property dataset first, then enrich and productize it.

The base requirement is **every Florida property across all 67 counties**. Bedroom/bathroom coverage is valuable, but it must not block statewide parcel coverage.

Implementation status:

- Full statewide pipeline runner: `fl/pipeline.py`
- Raw downloader: `fl/downloader.py`
- Normalized parcel writer: `fl/normalizer.py`
- Address normalization/hash: `shared/address.py`

## Phase 1 — Statewide base ingest

Source: Florida Department of Revenue bulk tax roll files.

- Download NAL for all 67 counties.
- Download SDF for all 67 counties.
- Extract raw CSVs into reproducible raw storage.
- Normalize records into one Florida parcel schema.
- Generate a deterministic `property_address_hash` from normalized situs address fields.

Base fields:

- `state`
- `county`
- `parcel_id`
- `owner_name`
- `situs_street`
- `situs_city`
- `situs_state`
- `situs_zip`
- `situs_address_normalized`
- `property_address_hash`
- `mailing_address`
- `land_use`
- `year_built`
- `living_area_sqft`
- `land_value`
- `building_value`
- `assessed_value`
- `market_value`
- `last_sale_date`
- `last_sale_price`
- `base_source`

## Phase 2 — County PA enrichment

Source: county Property Appraiser sites.

Add enrichers county-by-county for fields missing from DOR files:

- `bedrooms`
- `bathrooms`
- `half_bathrooms`
- `stories`
- `pool`
- `garage`
- other dwelling characteristics where public and reliable

Important rule: if enrichment is unavailable for a county/property, the parcel remains in the dataset with nullable enrichment fields.

## Phase 3 — Search/index layer

Once normalized statewide data exists, build a query layer for the frontend.

Recommended first storage/index shape:

- Postgres for canonical property records.
- PostGIS later if we add parcel polygons/GIS search.
- OpenSearch/Meilisearch only if Postgres full-text/trigram search is not enough.

Initial search requirements:

- Search by address.
- Search by owner.
- Search by parcel ID.
- Filter by county, city, ZIP, price/value range, year built, living area, bedrooms, bathrooms.
- Sort by assessed value, sale price/date, living area, year built.

## Phase 4 — Frontend visualization

Frontend should expose:

- Property search page.
- Property detail page.
- County/city/ZIP KPI dashboards.
- Map view once GIS parcel geometry is ingested.

Useful KPIs:

- Total property count.
- Median assessed value.
- Median sale price.
- Median living area.
- Properties by land use.
- Sales volume by month/year.
- Residential count with/without bed/bath enrichment.
- County enrichment coverage percentage.

## Address hashing

Python implementation lives in `shared/address.py`.

Algorithm:

1. Normalize address into canonical USPS-style format:
   - street suffixes: `Street` → `ST`, `Road` → `RD`, etc.
   - directionals: `North West` → `NW`
   - state names: `Florida` → `FL`
   - ZIP+4 collapsed to 5-digit ZIP
   - unit tokens normalized to `APT <unit>`
2. Hash canonical string with SHA-256.

Example:

```python
from shared.address import normalize_address_string, hash_address

normalized = normalize_address_string("123 Main Street, Miami, Florida 33101-1234")
# "123 Main ST, Miami, FL 33101"

property_hash = hash_address("123 Main Street, Miami, Florida 33101-1234")
```

The hash is for deduplication and stable joining. It should not replace parcel ID; Florida parcel IDs remain the authoritative county-specific property identifiers.
