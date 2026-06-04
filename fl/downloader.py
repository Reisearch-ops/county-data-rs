#!/usr/bin/env python3
"""
Florida DOR Tax Roll Downloader.

Downloads NAL (Name-Address-Legal), SDF (Sales Data File), and NAP
(Tangible Personal Property) files for all 67 Florida counties from
the Department of Revenue data portal.

Usage:
    python -m fl.downloader              # Download all NAL + SDF
    python -m fl.downloader --type nal   # NAL only
    python -m fl.downloader --type sdf   # SDF only
    python -m fl.downloader --county "Dade"  # Single county
    python -m fl.downloader --extract    # Also extract zips to CSV
"""

import argparse
import logging
import sys
import zipfile
from pathlib import Path
from typing import Optional


import requests
from tqdm import tqdm

from fl.config import FL_COUNTIES, FL_DOR_BASE, DATA_TYPES, TAX_YEAR, DOR_DOWNLOAD_NAME_OVERRIDES
from shared import data_dir, setup_logging, ensure_dir

logger = logging.getLogger("county-data.fl")

# Session with standard browser headers
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
})


def build_url(county_name: str, county_num: int, data_type: str) -> str:
    """Build the download URL for a county's data file."""
    # URL pattern: /NAL/2025F/CountyName%20XX%20Final%20NAL%202025.zip
    folder = DATA_TYPES[data_type]
    dor_county_name = DOR_DOWNLOAD_NAME_OVERRIDES.get(county_name, county_name)
    filename = f"{dor_county_name}%20{county_num}%20Final%20{folder}%20{TAX_YEAR[:4]}.zip"
    return f"{FL_DOR_BASE}/Tax%20Roll%20Data%20Files/{folder}/{TAX_YEAR}/{filename}"


def download_file(url: str, dest: Path, desc: str) -> bool:
    """Download a file with progress bar. Returns True on success."""
    if dest.exists():
        logger.info(f"Already exists: {dest.name}")
        return True

    try:
        resp = SESSION.get(url, stream=True, timeout=60)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=desc,
            bar_format="{l_bar}{bar:30}{r_bar}"
        ) as pbar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                pbar.update(len(chunk))
        return True

    except requests.HTTPError as e:
        logger.error(f"HTTP {e.response.status_code} for {desc}: {url}")
        return False
    except Exception as e:
        logger.error(f"Failed {desc}: {e}")
        return False


def extract_zip(zip_path: Path, extract_dir: Path) -> list[Path]:
    """Extract a zip file. Returns list of extracted file paths."""
    ensure_dir(extract_dir)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    return [extract_dir / name for name in zipfile.ZipFile(zip_path, "r").namelist()]


def download_county(
    county_name: str,
    county_num: int,
    data_types: list[str],
    extract: bool = False,
) -> dict:
    """Download data files for a single county."""
    state_data = data_dir("fl")
    results = {}

    for dtype in data_types:
        url = build_url(county_name, county_num, dtype)
        folder = DATA_TYPES[dtype]
        dest_dir = ensure_dir(state_data / folder.lower())
        zip_path = dest_dir / f"{county_name}_{county_num}_{folder}_{TAX_YEAR}.zip"

        desc = f"{county_name:15s} {folder}"
        success = download_file(url, zip_path, desc)

        if success and extract and zip_path.exists():
            csv_dir = ensure_dir(dest_dir / county_name)
            csv_files = extract_zip(zip_path, csv_dir)
            results[dtype] = {
                "zip": str(zip_path),
                "csvs": [str(f) for f in csv_files],
            }
        elif success:
            results[dtype] = {"zip": str(zip_path)}
        else:
            results[dtype] = {"error": "download failed"}

    return results


def download_all(
    data_types: list[str] = None,
    counties: Optional[list] = None,
    extract: bool = False,
) -> dict:
    """Download data for all specified counties."""
    if data_types is None:
        data_types = ["nal", "sdf"]
    if counties is None:
        counties = FL_COUNTIES

    summary = {"success": 0, "failed": 0, "counties": {}}

    for name, num, _ in counties:
        logger.info(f"--- {name} ({num}) ---")
        result = download_county(name, num, data_types, extract)
        summary["counties"][name] = result

        failed = sum(1 for v in result.values() if "error" in v)
        if failed:
            summary["failed"] += 1
        else:
            summary["success"] += 1

    return summary


def main():
    parser = argparse.ArgumentParser(description="Download FL DOR tax roll data")
    parser.add_argument(
        "--type", choices=["nal", "sdf", "nap", "all"],
        default="all", help="Data type to download (default: all nal+sdf)"
    )
    parser.add_argument(
        "--county", type=str, help="Download a single county by name"
    )
    parser.add_argument(
        "--extract", action="store_true", help="Extract zips to CSV"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print URLs without downloading"
    )
    args = parser.parse_args()

    setup_logging()

    # Determine data types
    types: list[str]
    if args.type == "all":
        types = ["nal", "sdf"]
    else:
        types = [args.type]

    # Determine counties
    if args.county:
        counties = [(c[0], c[1], c[2]) for c in FL_COUNTIES
                     if c[0].lower() == args.county.lower()]
        if not counties:
            logger.error(f"County not found: {args.county}")
            sys.exit(1)
    else:
        counties = FL_COUNTIES

    if args.dry_run:
        for name, num, _ in counties:
            for dtype in types:
                print(build_url(name, num, dtype))
        return

    logger.info(
        f"Downloading {len(types)} data type(s) for {len(counties)} county(s)..."
    )
    summary = download_all(types, counties, extract=args.extract)

    logger.info(
        f"Done. {summary['success']} succeeded, {summary['failed']} failed "
        f"out of {len(counties)} counties."
    )

    if summary["failed"]:
        failed = [k for k, v in summary["counties"].items()
                   if any("error" in r for r in v.values())]
        logger.warning(f"Failed counties: {', '.join(failed)}")


if __name__ == "__main__":
    main()
