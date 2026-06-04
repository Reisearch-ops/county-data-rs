#!/usr/bin/env python3
"""One-command Florida statewide property pipeline.

Runs the full base layer workflow:
1. Download FL DOR NAL/SDF zips.
2. Extract raw CSVs.
3. Normalize each county into the standard parcel schema with address hashes.

County PA bed/bath enrichers are intentionally separate. They enrich nullable
fields after statewide base coverage exists.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from fl.config import FL_COUNTIES
from fl.downloader import download_county
from fl.normalizer import default_county_input, normalize_county
from shared import data_dir, ensure_dir, setup_logging

logger = logging.getLogger("county-data.fl.pipeline")

COUNTY_BY_NAME = {name.lower(): (name, num, website) for name, num, website in FL_COUNTIES}


def output_name(county_name: str) -> str:
    """Return normalized output filename stem for a county."""
    return county_name.lower().replace(" ", "_").replace(".", "")


def first_csv_from_download_result(result: dict, dtype: str) -> Optional[Path]:
    """Extract first CSV path from downloader result for dtype if present."""
    item = result.get(dtype) or {}
    csvs = item.get("csvs") or []
    return Path(csvs[0]) if csvs else None


def resolve_county_csvs(county_name: str, download_result: Optional[dict] = None) -> tuple[Optional[Path], Optional[Path]]:
    """Resolve NAL/SDF CSVs from fresh download result or existing extracted data."""
    nal_csv = first_csv_from_download_result(download_result, "nal") if download_result else None
    sdf_csv = first_csv_from_download_result(download_result, "sdf") if download_result else None

    if not nal_csv:
        nal_csv = default_county_input(county_name, "nal")
    if not sdf_csv:
        sdf_csv = default_county_input(county_name, "sdf")

    return nal_csv, sdf_csv


def run_pipeline(
    counties: Iterable[tuple[str, int, str]],
    *,
    do_download: bool = True,
    do_normalize: bool = True,
    output_dir: Optional[Path] = None,
) -> dict:
    """Run download/extract/normalize for the selected counties.

    Returns a JSON-serializable summary suitable for manifests and monitoring.
    """
    normalized_dir = ensure_dir(output_dir or data_dir("fl") / "normalized")
    summary = {
        "downloaded_counties": 0,
        "download_failed_counties": 0,
        "normalized_counties": 0,
        "normalized_parcels": 0,
        "skipped_counties": 0,
        "counties": {},
    }

    for county_name, county_num, _ in counties:
        logger.info("--- %s (%s) ---", county_name, county_num)
        county_summary: dict[str, object] = {
            "county_number": county_num,
            "download": "skipped",
            "normalize": "skipped",
            "parcels": 0,
        }
        download_result = None

        if do_download:
            download_result = download_county(county_name, county_num, ["nal", "sdf"], extract=True)
            county_summary["download_result"] = download_result
            failed = any("error" in details for details in download_result.values())
            if failed:
                county_summary["download"] = "failed"
                summary["download_failed_counties"] += 1
            else:
                county_summary["download"] = "ok"
                summary["downloaded_counties"] += 1

        if do_normalize:
            nal_csv, sdf_csv = resolve_county_csvs(county_name, download_result)
            if not nal_csv:
                county_summary["normalize"] = "missing_nal"
                summary["skipped_counties"] += 1
                summary["counties"][county_name] = county_summary
                logger.warning("Skipping normalization for %s: no NAL CSV found", county_name)
                continue

            output_csv = normalized_dir / f"{output_name(county_name)}.parcels.csv"
            parcel_count = normalize_county(nal_csv, output_csv, county_name, sdf_csv)
            county_summary["normalize"] = "ok"
            county_summary["parcels"] = parcel_count
            county_summary["output_csv"] = str(output_csv)
            summary["normalized_counties"] += 1
            summary["normalized_parcels"] += parcel_count

        summary["counties"][county_name] = county_summary

    return summary


def select_counties(county_name: Optional[str]) -> list[tuple[str, int, str]]:
    if not county_name:
        return list(FL_COUNTIES)
    county = COUNTY_BY_NAME.get(county_name.lower())
    if not county:
        raise SystemExit(f"County not found: {county_name}")
    return [county]


def write_manifest(summary: dict, manifest_path: Path) -> None:
    ensure_dir(manifest_path.parent)
    manifest_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    logger.info("Wrote manifest -> %s", manifest_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FL statewide download/extract/normalize pipeline")
    parser.add_argument("--county", help="Single county to process; omit for all 67 counties")
    parser.add_argument("--skip-download", action="store_true", help="Use already extracted CSVs; do not download")
    parser.add_argument("--skip-normalize", action="store_true", help="Download/extract only; do not normalize")
    parser.add_argument("--output-dir", type=Path, help="Directory for normalized parcel CSVs")
    parser.add_argument("--manifest", type=Path, help="Path for JSON run manifest")
    parser.add_argument("--dry-run", action="store_true", help="Print selected counties and exit")
    args = parser.parse_args()

    setup_logging()
    counties = select_counties(args.county)

    if args.dry_run:
        for county_name, county_num, _ in counties:
            print(f"{county_name},{county_num}")
        return

    summary = run_pipeline(
        counties,
        do_download=not args.skip_download,
        do_normalize=not args.skip_normalize,
        output_dir=args.output_dir,
    )

    manifest_path = args.manifest or data_dir("fl") / "manifests" / "latest_pipeline_run.json"
    write_manifest(summary, manifest_path)

    logger.info(
        "Done. Downloaded: %s ok / %s failed. Normalized: %s counties, %s parcels.",
        summary["downloaded_counties"],
        summary["download_failed_counties"],
        summary["normalized_counties"],
        summary["normalized_parcels"],
    )


if __name__ == "__main__":
    main()
