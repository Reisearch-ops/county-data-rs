import unittest

from shared.address import (
    hash_address,
    hash_address_parts,
    new_address,
    normalize_address_string,
)


class AddressNormalizationTests(unittest.TestCase):
    def test_normalizes_street_type_state_and_zip(self):
        normalized = normalize_address_string("123 Main Street, Miami, Florida 33101-1234")
        self.assertEqual(normalized, "123 Main ST, Miami, FL 33101")

    def test_equivalent_addresses_hash_the_same(self):
        a = hash_address("123 Main Street, Miami, Florida 33101-1234")
        b = hash_address("123 main st, miami, FL 33101")
        self.assertEqual(a, b)

    def test_unit_tokens_are_normalized(self):
        normalized = normalize_address_string("500 north west 7th avenue apt 3b, Ft Lauderdale, FL 33311")
        self.assertEqual(normalized, "500 NW 7th AVE APT 3B, Fort Lauderdale, FL 33311")

    def test_hash_from_parts_matches_hash_from_raw_address(self):
        raw_hash = hash_address("one ocean drive, Miami Beach, FL 33139")
        parts_hash = hash_address_parts("1 Ocean Dr", "Miami Beach", "Florida", "33139")
        self.assertEqual(raw_hash, parts_hash)

    def test_new_address_exposes_hash(self):
        addr = new_address("10 second road #5, Orlando, FL 32801")
        self.assertEqual(addr.normalized, "10 2nd RD APT 5, Orlando, FL 32801")
        self.assertEqual(addr.address_hash, hash_address(addr.normalized))

    def test_address_validity_string_and_equality(self):
        addr = new_address("123 Main Street, Miami, Florida 33101-1234")
        same = new_address("123 main st, miami, FL 33101")
        different = new_address("124 Main Street, Miami, FL 33101")

        self.assertTrue(addr.is_valid())
        self.assertEqual(str(addr), "123 Main ST, Miami, FL 33101")
        self.assertTrue(addr.equals(same))
        self.assertEqual(addr, same)
        self.assertFalse(addr.equals(different))
        self.assertFalse(addr.equals(None))


if __name__ == "__main__":
    unittest.main()
