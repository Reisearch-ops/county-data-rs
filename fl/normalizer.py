#!/usr/bin/env python3
"""Normalize Florida DOR NAL/SDF files into a statewide parcel schema.

The downloader keeps official raw files intact. This normalizer creates a clean,
frontend/search-friendly parcel CSV and computes `property_address_hash` from the
situs address using `shared.address`.
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import Iterable, Optional

from fl.config import FL_COUNTIES
from shared import data_dir, ensure_dir, setup_logging
from shared.address import AddressNormalizationError, new_address_from_parts

logger = logging.getLogger("county-data.fl.normalizer")

NORMALIZED_FIELDS = [
    "state",
    "county",
    "county_number",
    "parcel_id",
    "state_parcel_id",
    "owner_name",
    "situs_street",
    "situs_city",
    "situs_state",
    "situs_zip",
    "situs_address_normalized",
    "property_address_hash",
    "mailing_street_1",
    "mailing_street_2",
    "mailing_city",
    "mailing_state",
    "mailing_zip",
    "dor_land_use_code",
    "pa_land_use_code",
    "neighborhood_code",
    "market_area",
    "year_built_actual",
    "year_built_effective",
    "living_area_sqft",
    "land_sqft",
    "residential_units",
    "building_count",
    "land_value",
    "building_value",
    "assessed_value_sd",
    "assessed_value_nsd",
    "just_value",
    "taxable_value_sd",
    "taxable_value_nsd",
    "last_sale_date",
    "last_sale_price",
    "last_sale_qualified_code",
    "last_sale_vacant_improved_code",
    "bedrooms",
    "bathrooms",
    "half_bathrooms",
    "base_source",
    "enrichment_source",
]

COUNTY_BY_NUMBER = {str(num): name for name, num, _ in FL_COUNTIES}
COUNTY_BY_NAME = {name.lower(): (name, num) for name, num, _ in FL_COUNTIES}


def clean(value: object) -> str:
    """Return a stripped string without CSV padding/noise."""
    if value is None:
        return ""
    return str(value).strip().strip('"')


def int_string(value: object) -> str:
    """Normalize integer-like CSV values while preserving blanks."""
    text = clean(value)
    if text == "":
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def sale_date(year: object, month: object) -> str:
    year_text = int_string(year)
    month_text = int_string(month)
    if not year_text:
        return ""
    if not month_text:
        return year_text
    return f"{year_text}-{month_text.zfill(2)}"


def normalize_zip(value: object) -> str:
    text = int_string(value)
    if not text:
        return ""
    return text.zfill(5)[:5]


def build_situs_address(row: dict[str, str]) -> tuple[str, str]:
    """Return normalized situs address and hash, or blank values if incomplete."""
    street_parts = [clean(row.get("PHY_ADDR1")), clean(row.get("PHY_ADDR2"))]
    street = " ".join(part for part in street_parts if part)
    city = clean(row.get("PHY_CITY"))
    zip_code = normalize_zip(row.get("PHY_ZIPCD"))

    if not (street and city and zip_code):
        return "", ""

    try:
        addr = new_address_from_parts(street, city, "FL", zip_code)
        return addr.normalized, addr.address_hash
    except AddressNormalizationError as exc:
        logger.debug("Could not normalize situs address for parcel %s: %s", row.get("PARCEL_ID"), exc)
        return "", ""


def latest_sdf_sales(sdf_csv: Optional[Path]) -> dict[str, dict[str, str]]:
    """Load latest sale by parcel from SDF, keyed by PARCEL_ID.

    SDF can contain multiple sale rows per parcel. We keep the latest by year,
    month, then sale price as a stable tie-breaker.
    """
    if not sdf_csv or not sdf_csv.exists():
        return {}

    latest: dict[str, dict[str, str]] = {}
    with sdf_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parcel_id = clean(row.get("PARCEL_ID"))
            if not parcel_id:
                continue
            candidate_key = (
                int(int_string(row.get("SALE_YR")) or 0),
                int(int_string(row.get("SALE_MO")) or 0),
                int(int_string(row.get("SALE_PRC")) or 0),
            )
            existing = latest.get(parcel_id)
            if existing is None:
                latest[parcel_id] = row
                continue
            existing_key = (
                int(int_string(existing.get("SALE_YR")) or 0),
                int(int_string(existing.get("SALE_MO")) or 0),
                int(int_string(existing.get("SALE_PRC")) or 0),
            )
            if candidate_key > existing_key:
                latest[parcel_id] = row
    return latest


def normalize_nal_row(row: dict[str, str], county_name: Optional[str], sdf_sale: Optional[dict[str, str]] = None) -> dict[str, str]:
    county_number = int_string(row.get("CO_NO"))
    resolved_county = county_name or COUNTY_BY_NUMBER.get(county_number, "")
    situs_normalized, address_hash = build_situs_address(row)

    sale_source = sdf_sale or row
    if sdf_sale:
        last_sale_date = sale_date(sale_source.get("SALE_YR"), sale_source.get("SALE_MO"))
        last_sale_price = int_string(sale_source.get("SALE_PRC"))
        last_sale_qualified_code = clean(sale_source.get("QUAL_CD"))
        last_sale_vi_code = clean(sale_source.get("VI_CD"))
    else:
        last_sale_date = sale_date(row.get("SALE_YR1"), row.get("SALE_MO1"))
        last_sale_price = int_string(row.get("SALE_PRC1"))
        last_sale_qualified_code = clean(row.get("QUAL_CD1"))
        last_sale_vi_code = clean(row.get("VI_CD1"))

    return {
        "state": "FL",
        "county": resolved_county,
        "county_number": county_number,
        "parcel_id": clean(row.get("PARCEL_ID")),
        "state_parcel_id": clean(row.get("STATE_PAR_ID")) or clean(row.get("STATE_PARCEL_ID")),
        "owner_name": clean(row.get("OWN_NAME")),
        "situs_street": " ".join(part for part in [clean(row.get("PHY_ADDR1")), clean(row.get("PHY_ADDR2"))] if part),
        "situs_city": clean(row.get("PHY_CITY")),
        "situs_state": "FL" if clean(row.get("PHY_CITY")) or clean(row.get("PHY_ZIPCD")) else "",
        "situs_zip": normalize_zip(row.get("PHY_ZIPCD")),
        "situs_address_normalized": situs_normalized,
        "property_address_hash": address_hash,
        "mailing_street_1": clean(row.get("OWN_ADDR1")),
        "mailing_street_2": clean(row.get("OWN_ADDR2")),
        "mailing_city": clean(row.get("OWN_CITY")),
        "mailing_state": clean(row.get("OWN_STATE")),
        "mailing_zip": normalize_zip(row.get("OWN_ZIPCD")),
        "dor_land_use_code": clean(row.get("DOR_UC")),
        "pa_land_use_code": clean(row.get("PA_UC")),
        "neighborhood_code": clean(row.get("NBRHD_CD")),
        "market_area": clean(row.get("MKT_AR")),
        "year_built_actual": int_string(row.get("ACT_YR_BLT")),
        "year_built_effective": int_string(row.get("EFF_YR_BLT")),
        "living_area_sqft": int_string(row.get("TOT_LVG_AREA")),
        "land_sqft": int_string(row.get("LND_SQFOOT")),
        "residential_units": int_string(row.get("NO_RES_UNTS")),
        "building_count": int_string(row.get("NO_BULDNG")),
        "land_value": int_string(row.get("LND_VAL")),
        "building_value": int_string(row.get("NCONST_VAL")),
        "assessed_value_sd": int_string(row.get("AV_SD")),
        "assessed_value_nsd": int_string(row.get("AV_NSD")),
        "just_value": int_string(row.get("JV")),
        "taxable_value_sd": int_string(row.get("TV_SD")),
        "taxable_value_nsd": int_string(row.get("TV_NSD")),
        "last_sale_date": last_sale_date,
        "last_sale_price": last_sale_price,
        "last_sale_qualified_code": last_sale_qualified_code,
        "last_sale_vacant_improved_code": last_sale_vi_code,
        "bedrooms": "",
        "bathrooms": "",
        "half_bathrooms": "",
        "base_source": "FL_DOR_NAL_SDF" if sdf_sale else "FL_DOR_NAL",
        "enrichment_source": "",
    }


def normalize_county(nal_csv: Path, output_csv: Path, county_name: Optional[str] = None, sdf_csv: Optional[Path] = None) -> int:
    """Normalize one county NAL CSV into the standard parcel schema."""
    ensure_dir(output_csv.parent)
    sales = latest_sdf_sales(sdf_csv)
    count = 0

    with nal_csv.open("r", encoding="utf-8-sig", newline="") as src, output_csv.open("w", encoding="utf-8", newline="") as dest:
        reader = csv.DictReader(src)
        writer = csv.DictWriter(dest, fieldnames=NORMALIZED_FIELDS)
        writer.writeheader()
        for row in reader:
            parcel_id = clean(row.get("PARCEL_ID"))
            writer.writerow(normalize_nal_row(row, county_name, sales.get(parcel_id)))
            count += 1

    logger.info("Normalized %s parcels -> %s", count, output_csv)
    return count


def find_first_csv(path: Path) -> Optional[Path]:
    if path.is_file() and path.suffix.lower() == ".csv":
        return path
    if not path.exists():
        return None
    csvs = sorted(path.glob("*.csv"))
    return csvs[0] if csvs else None


def default_county_input(county_name: str, dtype: str) -> Optional[Path]:
    state_data = data_dir("fl")
    folder = dtype.lower()
    candidates = [
        state_data / folder / county_name,
        state_data / folder / county_name.replace(" ", "_"),
    ]
    for candidate in candidates:
        found = find_first_csv(candidate)
        if found:
            return found
    return None


def normalize_counties(counties: Iterable[tuple[str, int, str]], output_dir: Path) -> dict[str, int]:
    summary: dict[str, int] = {}
    for county_name, _, _ in counties:
        nal_csv = default_county_input(county_name, "nal")
        if not nal_csv:
            logger.warning("Skipping %s: no extracted NAL CSV found", county_name)
            continue
        sdf_csv = default_county_input(county_name, "sdf")
        output_csv = output_dir / f"{county_name.lower().replace(' ', '_').replace('.', '')}.parcels.csv"
        summary[county_name] = normalize_county(nal_csv, output_csv, county_name, sdf_csv)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize FL DOR NAL/SDF CSV files")
    parser.add_argument("--county", help="County name to normalize; omit for all counties with extracted files")
    parser.add_argument("--nal", type=Path, help="Path to extracted NAL CSV")
    parser.add_argument("--sdf", type=Path, help="Optional path to extracted SDF CSV")
    parser.add_argument("--output", type=Path, help="Output CSV path for --nal mode, or output directory for county/all mode")
    args = parser.parse_args()

    setup_logging()

    if args.nal:
        county_name = args.county
        if not county_name:
            logger.warning("--county not provided; county will be inferred from CO_NO where possible")
        output = args.output or data_dir("fl") / "normalized" / "parcels.csv"
        normalize_county(args.nal, output, county_name, args.sdf)
        return

    output_dir = args.output or data_dir("fl") / "normalized"
    if args.county:
        match = COUNTY_BY_NAME.get(args.county.lower())
        if not match:
            raise SystemExit(f"County not found: {args.county}")
        county = next(c for c in FL_COUNTIES if c[0].lower() == args.county.lower())
        summary = normalize_counties([county], output_dir)
    else:
        summary = normalize_counties(FL_COUNTIES, output_dir)

    logger.info("Done. Normalized %s county file(s), %s parcel(s).", len(summary), sum(summary.values()))


if __name__ == "__main__":
    main()
