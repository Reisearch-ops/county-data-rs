#!/usr/bin/env python3
"""
Florida County Property Appraiser Enricher.

Scrapes dwelling characteristics (beds, baths, sqft, year built)
from county property appraiser websites that the state NAL files
don't include.

Currently supported counties:
- Miami-Dade (Dade) — searchable by folio number

Usage:
    python -m fl.enricher --county Dade --folio 01-4111-015-0630
    python -m fl.enricher --county Dade --csv parcel_list.csv
"""

import argparse
import csv
import logging
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from fl.config import FL_COUNTIES, FL_DOR_BASE, TAX_YEAR
from shared import data_dir, setup_logging

logger = logging.getLogger("county-data.fl.enricher")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
})


# --- Miami-Dade County ---

MIAMIDADE_SEARCH_URL = "https://apps.miamidadepa.gov/PropertySearch/#/"


def enrich_miamidade(folio: str) -> dict | None:
    """
    Scrape Miami-Dade property detail for dwelling characteristics.
    Uses their SPA's underlying API endpoints.
    """
    # Miami-Dade PA has a REST API under the SPA
    api_url = (
        f"https://apps.miamidadepa.gov/PropertySearch/api/"
        f"PropertySearch/GetProperty?folio={folio}"
    )
    try:
        resp = SESSION.get(api_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        return {
            "folio": folio,
            "beds": data.get("bedCount"),
            "baths": data.get("bathCount"),
            "half_baths": data.get("halfBathCount"),
            "living_area_sqft": data.get("livingArea"),
            "lot_size_sqft": data.get("lotSize"),
            "year_built": data.get("yearBuilt"),
            "floors": data.get("floorCount"),
            "living_units": data.get("livingUnits"),
            "owner": data.get("ownerName"),
            "property_address": data.get("propertyAddress"),
            "land_use": data.get("primaryLandUse"),
        }
    except requests.HTTPError as e:
        logger.error(f"Miami-Dade API error for {folio}: {e}")
        return None
    except Exception as e:
        logger.error(f"Miami-Dade parse error for {folio}: {e}")
        return None


# --- Orange County ---

def enrich_orange(parcel_id: str) -> dict | None:
    """
    Scrape Orange County property detail.
    Uses their public parcel detail page.
    """
    url = f"https://www.ocpafl.org/Searches/ParcelSearch?parcelid={parcel_id}"
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Orange County uses element IDs for field extraction
        def _span_text(id_pattern: str) -> str | None:
            elem = soup.find("span", {"id": re.compile(id_pattern)})
            return elem.get_text(strip=True) if elem else None

        return {
            "parcel_id": parcel_id,
            "beds": _span_text(r"Bed"),
            "baths": _span_text(r"Bath"),
            "living_area_sqft": _span_text(r"Living|Heated"),
            "year_built": _span_text(r"Year"),
        }
    except Exception as e:
        logger.error(f"Orange County error for {parcel_id}: {e}")
        return None


# --- Enricher registry ---

ENRICHERS = {
    "Dade": enrich_miamidade,
    "Orange": enrich_orange,
}


def enrich_county(county_name: str, parcel_ids: list[str]) -> list[dict]:
    """Enrich a list of parcel IDs for a given county."""
    if county_name not in ENRICHERS:
        logger.error(
            f"No enricher for {county_name}. "
            f"Available: {list(ENRICHERS.keys())}"
        )
        return []

    enrich_fn = ENRICHERS[county_name]
    results = []

    for pid in parcel_ids:
        logger.info(f"Enriching {county_name}: {pid}")
        data = enrich_fn(pid)
        if data:
            results.append(data)
        else:
            results.append({"parcel_id": pid, "error": "failed"})
        time.sleep(0.5)  # Be gentle

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Enrich parcel data with dwelling characteristics"
    )
    parser.add_argument(
        "--county", required=True, type=str,
        help="County name (e.g., Dade, Orange)"
    )
    parser.add_argument(
        "--folio", type=str, help="Single parcel/folio ID"
    )
    parser.add_argument(
        "--csv", type=str, help="CSV file with parcel IDs (column: parcel_id)"
    )
    args = parser.parse_args()

    setup_logging()

    if args.folio:
        parcel_ids = [args.folio]
    elif args.csv:
        with open(args.csv) as f:
            reader = csv.DictReader(f)
            parcel_ids = [row["parcel_id"] for row in reader]
    else:
        logger.error("Provide --folio or --csv")
        sys.exit(1)

    results = enrich_county(args.county, parcel_ids)

    # Write results
    out_dir = data_dir("fl") / "enriched"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{args.county}_enriched.csv"

    if results:
        fieldnames = results[0].keys()
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        logger.info(f"Wrote {len(results)} records to {out_path}")
    else:
        logger.warning("No results.")


if __name__ == "__main__":
    main()
