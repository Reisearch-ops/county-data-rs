import tempfile
from pathlib import Path
import unittest

from fl.load_db import (
    BIGINT_COLUMNS,
    INTEGER_COLUMNS,
    NUMERIC_COLUMNS,
    normalized_csv_paths,
    select_expression,
    staging_table_sql,
    upsert_sql,
)
from fl.normalizer import NORMALIZED_FIELDS


class DatabaseLoaderTests(unittest.TestCase):
    def test_staging_table_has_all_normalized_fields_as_text(self):
        sql = staging_table_sql()
        for field in NORMALIZED_FIELDS:
            self.assertIn(f"{field} text", sql)

    def test_select_expression_casts_numeric_columns(self):
        for field in INTEGER_COLUMNS:
            self.assertEqual(select_expression(field), f"NULLIF({field}, '')::integer AS {field}")
        for field in BIGINT_COLUMNS:
            self.assertEqual(select_expression(field), f"NULLIF({field}, '')::bigint AS {field}")
        for field in NUMERIC_COLUMNS:
            self.assertEqual(select_expression(field), f"NULLIF({field}, '')::numeric AS {field}")
        self.assertEqual(select_expression("owner_name"), "NULLIF(owner_name, '') AS owner_name")

    def test_upsert_sql_targets_property_primary_key(self):
        sql = upsert_sql()
        self.assertIn("INSERT INTO fl.properties", sql)
        self.assertIn("ON CONFLICT (state, county, parcel_id) DO UPDATE", sql)
        self.assertIn("property_address_hash = EXCLUDED.property_address_hash", sql)
        self.assertIn("updated_at = now()", sql)

    def test_normalized_csv_paths_expands_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wanted = root / "baker.parcels.csv"
            ignored = root / "notes.csv"
            wanted.write_text("state,county,parcel_id\n", encoding="utf-8")
            ignored.write_text("x\n", encoding="utf-8")
            self.assertEqual(normalized_csv_paths([root]), [wanted])


if __name__ == "__main__":
    unittest.main()
