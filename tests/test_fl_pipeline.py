import csv
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from fl.pipeline import resolve_county_csvs, run_pipeline, select_counties


class FloridaPipelineTests(unittest.TestCase):
    def test_select_counties_returns_single_county(self):
        counties = select_counties("Baker")
        self.assertEqual(len(counties), 1)
        self.assertEqual(counties[0][0], "Baker")
        self.assertEqual(counties[0][1], 12)

    def test_resolve_county_csvs_prefers_download_result(self):
        result = {
            "nal": {"csvs": ["/tmp/nal.csv"]},
            "sdf": {"csvs": ["/tmp/sdf.csv"]},
        }
        nal, sdf = resolve_county_csvs("Baker", result)
        self.assertEqual(nal, Path("/tmp/nal.csv"))
        self.assertEqual(sdf, Path("/tmp/sdf.csv"))

    def test_run_pipeline_downloads_and_normalizes_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nal = tmp_path / "nal.csv"
            sdf = tmp_path / "sdf.csv"
            out_dir = tmp_path / "normalized"

            with nal.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "CO_NO", "PARCEL_ID", "STATE_PAR_ID", "OWN_NAME", "PHY_ADDR1", "PHY_ADDR2",
                    "PHY_CITY", "PHY_ZIPCD", "SALE_YR1", "SALE_MO1", "SALE_PRC1", "QUAL_CD1", "VI_CD1",
                ])
                writer.writeheader()
                writer.writerow({
                    "CO_NO": "12",
                    "PARCEL_ID": "0001",
                    "STATE_PAR_ID": "C12-0001",
                    "OWN_NAME": "Jane Owner",
                    "PHY_ADDR1": "123 Main Street",
                    "PHY_ADDR2": "",
                    "PHY_CITY": "Macclenny",
                    "PHY_ZIPCD": "32063",
                    "SALE_YR1": "2023",
                    "SALE_MO1": "1",
                    "SALE_PRC1": "100000",
                    "QUAL_CD1": "01",
                    "VI_CD1": "I",
                })

            with sdf.open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["PARCEL_ID", "SALE_YR", "SALE_MO", "SALE_PRC", "QUAL_CD", "VI_CD"])
                writer.writeheader()
                writer.writerow({"PARCEL_ID": "0001", "SALE_YR": "2024", "SALE_MO": "2", "SALE_PRC": "200000", "QUAL_CD": "02", "VI_CD": "V"})

            fake_download = {
                "nal": {"zip": str(tmp_path / "nal.zip"), "csvs": [str(nal)]},
                "sdf": {"zip": str(tmp_path / "sdf.zip"), "csvs": [str(sdf)]},
            }

            with patch("fl.pipeline.download_county", return_value=fake_download):
                summary = run_pipeline([("Baker", 12, "https://www.bakerpa.com")], output_dir=out_dir)

            self.assertEqual(summary["downloaded_counties"], 1)
            self.assertEqual(summary["normalized_counties"], 1)
            self.assertEqual(summary["normalized_parcels"], 1)
            self.assertTrue((out_dir / "baker.parcels.csv").exists())

    def test_run_pipeline_skip_download_skips_missing_nal(self):
        with tempfile.TemporaryDirectory() as tmp, patch("fl.pipeline.default_county_input", return_value=None):
            summary = run_pipeline(
                [("Baker", 12, "https://www.bakerpa.com")],
                do_download=False,
                output_dir=Path(tmp),
            )
        self.assertEqual(summary["skipped_counties"], 1)
        self.assertEqual(summary["counties"]["Baker"]["normalize"], "missing_nal")


if __name__ == "__main__":
    unittest.main()
