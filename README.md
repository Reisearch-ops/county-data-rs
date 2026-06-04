# County Data Pipeline

Multi-state county property data ingestion from primary government sources.

## States

| State | Status | Parcel Count | Data Sources |
|-------|--------|-------------|--------------|
| **Florida** | Pipeline ready | ~10M | FL DOR bulk NAL/SDF + county PA enrichment |
| Arizona | Legacy | 2M | Maricopa (DynamoDB), Pinal (CSV) |

## Florida Pipeline

### Quick Start

```bash
pip install -r requirements.txt

# Download all 67 counties (NAL + SDF)
python -m fl.downloader

# Download single county
python -m fl.downloader --county Dade --type nal

# Download and extract CSVs
python -m fl.downloader --extract

# Preview URLs without downloading
python -m fl.downloader --dry-run
```

### Enrichment (beds/baths from county sites)

```bash
# Single property
python -m fl.enricher --county Dade --folio 01-4111-015-0630

# Batch from CSV
python -m fl.enricher --county Dade --csv parcels.csv
```

### Data Layers

1. **NAL** (Name-Address-Legal) — Tax roll: owner, address, valuation, year built, living area, lot size, land use, exemptions
2. **SDF** (Sales Data File) — Sales: price, date, OR book/page, qualification codes
3. **GIS** — Parcel polygons (shapefiles, separate download from DOR)
4. **Enrichment** — Dwelling characteristics: beds, baths, half baths, floors (from county PA websites)

### What the state NAL files DON'T include

- Bedroom count
- Bathroom count
- Construction class details
- Garage/pool/feature data

These are available at the **county property appraiser** level and handled by `fl/enricher.py`.

## Directory Structure

```
data/fl/
├── nal/          # Downloaded NAL zips by county
├── sdf/          # Downloaded SDF zips by county
├── enriched/     # Enriched CSV output
└── ...
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COUNTY_DATA_DIR` | `~/county-data` | Root data directory |
