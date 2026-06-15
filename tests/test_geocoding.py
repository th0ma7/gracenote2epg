"""Tests for the bundled (stdlib, no pgeocode) postal-code geocoder."""

import unittest
from pathlib import Path

from gracenote2epg.geocoding import Geocoder, _DATA_FILE


class GeocoderTests(unittest.TestCase):
    def setUp(self):
        self.g = Geocoder()

    def test_bundled_dataset_present(self):
        self.assertTrue(
            Path(_DATA_FILE).exists(),
            "bundled geopostal.csv.gz missing; run: make geodata",
        )

    def test_canadian_full_code(self):
        self.assertEqual(
            self.g.resolve_location("J3B1M4", "CAN"), ("Saint-Jean-sur-Richelieu", "QC")
        )

    def test_canadian_code_with_space(self):
        self.assertEqual(
            self.g.resolve_location("J3B 1M4", "CAN"), ("Saint-Jean-sur-Richelieu", "QC")
        )

    def test_canadian_fsa_fallback(self):
        # Full code absent from FSA-level data -> falls back to the 3-char FSA.
        city, prov = self.g.resolve_location("M5V2T6", "CAN")
        self.assertEqual(prov, "ON")
        self.assertTrue(city)

    def test_us_zip(self):
        self.assertEqual(self.g.resolve_location("90210", "USA"), ("Beverly Hills", "CA"))
        self.assertEqual(self.g.resolve_location("10001", "USA"), ("New York", "NY"))

    def test_unknown_code_returns_none(self):
        self.assertEqual(self.g.resolve_location("00000", "USA"), (None, None))

    def test_result_is_cached(self):
        first = self.g.resolve_location("92101", "USA")
        self.assertIn("92101_USA", self.g._location_cache)
        self.assertEqual(first, self.g.resolve_location("92101", "USA"))


if __name__ == "__main__":
    unittest.main()
