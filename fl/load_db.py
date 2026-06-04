#!/usr/bin/env python3
"""Load normalized Florida parcel CSVs into Postgres.

Expected input is one or more CSV files produced by `fl.normalizer` or
`fl.pipeline`, e.g. `data/fl/data/normalized/baker.parcels.csv`.
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
from pathlib import Path
from typing import Iterable, Sequence

from fl.normalizer import NORMALIZED_FIELDS
from shared import data_dir, setup_logging

logger = logging.getLogger("county-data.fl.load_db")

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
TABLE_NAME = "fl.properties"
STAGING_TABLE = "fl_properties_stage"

INTEGER_COLUMNS = {
    "county_number",
    "year_built_actual",
    "year_built_effective",
    "living_area_sqft",
    "land_sqft",
    "residential_units",
    "building_count",
}

BIGINT_COLUMNS = {
    "land_value",
    "building_value",
    "assessed_value_sd",
    "assessed_value_nsd",
    "just_value",
    "taxable_value_sd",
    "taxable_value_nsd",
    "last_sale_price",
}

NUMERIC_COLUMNS = {"bedrooms", "bathrooms", "half_bathrooms"}
TEXT_COLUMNS = [
    field for field in NORMALIZED_FIELDS
    if field not in INTEGER_COLUMNS | BIGINT_COLUMNS | NUMERIC_COLUMNS
]


def database_url_from_env(explicit_url: str | None = None) -> str:
    """Resolve database URL from CLI argument or DATABASE_URL env var."""
    url = explicit_url or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit(
            "DATABASE_URL is required. Example: "
            "export DATABASE_URL='postgresql://user:password@localhost:5432/county_data'"
        )
    return url


def normalized_csv_paths(paths: Sequence[Path] | None = None) -> list[Path]:
    """Return normalized CSV paths from explicit paths or default data dir."""
    if paths:
        results: list[Path] = []
        for path in paths:
            if path.is_dir():
                results.extend(sorted(path.glob("*.parcels.csv")))
            else:
                results.append(path)
        return results

    default_dir = data_dir("fl") / "normalized"
    return sorted(default_dir.glob("*.parcels.csv"))


def create_schema(conn) -> None:
    """Apply the database schema idempotently."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()


def staging_table_sql() -> str:
    cols = ",\n    ".join(f"{col} text" for col in NORMALIZED_FIELDS)
    return f"CREATE TEMP TABLE {STAGING_TABLE} (\n    {cols}\n) ON COMMIT DROP"


def select_expression(column: str) -> str:
    """Return SQL expression to cast staging text into target column type."""
    if column in INTEGER_COLUMNS:
        return f"NULLIF({column}, '')::integer AS {column}"
    if column in BIGINT_COLUMNS:
        return f"NULLIF({column}, '')::bigint AS {column}"
    if column in NUMERIC_COLUMNS:
        return f"NULLIF({column}, '')::numeric AS {column}"
    return f"NULLIF({column}, '') AS {column}"


def upsert_sql() -> str:
    insert_cols = ", ".join(NORMALIZED_FIELDS)
    select_cols = ",\n        ".join(select_expression(col) for col in NORMALIZED_FIELDS)
    update_cols = [col for col in NORMALIZED_FIELDS if col not in {"state", "county", "parcel_id"}]
    update_assignments = ",\n        ".join(f"{col} = EXCLUDED.{col}" for col in update_cols)
    return f"""
INSERT INTO {TABLE_NAME} ({insert_cols})
SELECT
        {select_cols}
FROM {STAGING_TABLE}
ON CONFLICT (state, county, parcel_id) DO UPDATE SET
        {update_assignments},
        updated_at = now()
"""


def copy_csv_to_staging(conn, csv_path: Path) -> int:
    """Copy one normalized CSV into a temp staging table and upsert it."""
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = [field for field in NORMALIZED_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{csv_path} is missing required fields: {', '.join(missing)}")

        with conn.cursor() as cur:
            cur.execute(staging_table_sql())
            copy_sql = f"COPY {STAGING_TABLE} ({', '.join(NORMALIZED_FIELDS)}) FROM STDIN"
            row_count = 0
            with cur.copy(copy_sql) as copy:
                for row in reader:
                    copy.write_row([row.get(field, "") or "" for field in NORMALIZED_FIELDS])
                    row_count += 1
            cur.execute(upsert_sql())
        conn.commit()
        return row_count


def load_csvs(database_url: str, csv_paths: Iterable[Path], create: bool = True) -> dict[str, int]:
    """Load normalized parcel CSVs into Postgres and return row counts by file."""
    import psycopg

    paths = list(csv_paths)
    if not paths:
        raise SystemExit("No normalized CSV files found to load")

    summary: dict[str, int] = {}
    with psycopg.connect(database_url) as conn:
        if create:
            create_schema(conn)
        for csv_path in paths:
            logger.info("Loading %s", csv_path)
            summary[str(csv_path)] = copy_csv_to_staging(conn, csv_path)
            logger.info("Loaded %s row(s) from %s", summary[str(csv_path)], csv_path)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Load normalized FL parcel CSVs into Postgres")
    parser.add_argument("paths", nargs="*", type=Path, help="CSV files or directories; default: COUNTY_DATA_DIR/fl/data/normalized")
    parser.add_argument("--database-url", help="Postgres URL; default: DATABASE_URL env var")
    parser.add_argument("--no-create", action="store_true", help="Do not apply db/schema.sql before loading")
    args = parser.parse_args()

    setup_logging()
    database_url = database_url_from_env(args.database_url)
    paths = normalized_csv_paths(args.paths)
    summary = load_csvs(database_url, paths, create=not args.no_create)
    logger.info("Done. Loaded %s file(s), %s row(s).", len(summary), sum(summary.values()))


if __name__ == "__main__":
    main()
