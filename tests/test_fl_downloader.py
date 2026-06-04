import unittest

from fl.downloader import build_url


class FloridaDownloaderTests(unittest.TestCase):
    def test_build_url_uses_dor_county_name_overrides(self):
        self.assertIn("Indin River%2041%20Final%20NAL%202025.zip", build_url("Indian River", 41, "nal"))
        self.assertIn("Saint Johns%2065%20Final%20NAL%202025.zip", build_url("St. Johns", 65, "nal"))
        self.assertIn("Saint Lucie%2066%20Final%20SDF%202025.zip", build_url("St. Lucie", 66, "sdf"))


if __name__ == "__main__":
    unittest.main()
