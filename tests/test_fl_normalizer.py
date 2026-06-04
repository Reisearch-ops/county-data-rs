import csv
import tempfile
from pathlib import Path
import unittest

from fl.normalizer import normalize_county, normalize_nal_row
from shared.address import hash_address_parts


class FloridaNormalizerTests(unittest.TestCase):
    def test_normalize_nal_row_adds_address_hash_and_core_fields(self):
        row = {
            "CO_NO": "12",
            "PARCEL_ID": "0001",
            "STATE_PAR_ID": "C12-0001",
            "OWN_NAME": "Jane Owner",
            "PHY_ADDR1": "123 Main Street",
            "PHY_ADDR2": "Apt 2",
            "PHY_CITY": "Macclenny",
            "PHY_ZIPCD": "32063-1234",
            "OWN_ADDR1": "PO Box 1",
            "OWN_CITY": "Macclenny",
            "OWN_STATE": "FL",
            "OWN_ZIPCD": "32063",
            "DOR_UC": "001",
            "PA_UC": "00",
            "ACT_YR_BLT": "1999",
            "EFF_YR_BLT": "2001",
            "TOT_LVG_AREA": "1500",
            "LND_SQFOOT": "7500",
            "NO_RES_UNTS": "1",
            "NO_BULDNG": "1",
            "LND_VAL": "50000",
            "NCONST_VAL": "120000",
            "AV_SD": "100000",
            "AV_NSD": "90000",
            "JV": "170000",
            "TV_SD": "80000",
            "TV_NSD": "70000",
            "SALE_YR1": "2024",
            "SALE_MO1": "7",
            "SALE_PRC1": "250000",
            "QUAL_CD1": "01",
            "VI_CD1": "I",
        }

        normalized = normalize_nal_row(row, "Baker")

        self.assertEqual(normalized["county"], "Baker")
        self.assertEqual(normalized["situs_address_normalized"], "123 Main ST APT 2, Macclenny, FL 32063")
        self.assertEqual(
            normalized["property_address_hash"],
            hash_address_parts("123 Main Street Apt 2", "Macclenny", "FL", "32063"),
        )
        self.assertEqual(normalized["last_sale_date"], "2024-07")
        self.assertEqual(normalized["bedrooms"], "")
        self.assertEqual(normalized["base_source"], "FL_DOR_NAL")

    def test_normalize_county_writes_csv_and_prefers_latest_sdf_sale(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            nal = tmp_path / "nal.csv"
            sdf = tmp_path / "sdf.csv"
            out = tmp_path / "normalized.csv"

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

            count = normalize_county(nal, out, "Baker", sdf)

            self.assertEqual(count, 1)
            with out.open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["last_sale_date"], "2024-02")
            self.assertEqual(rows[0]["last_sale_price"], "200000")
            self.assertEqual(rows[0]["base_source"], "FL_DOR_NAL_SDF")


if __name__ == "__main__":
    unittest.main()
