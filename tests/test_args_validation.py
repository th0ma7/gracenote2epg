"""Unit tests for gracenote2epg.args.validator.ArgumentValidator."""

import unittest

from gracenote2epg.args.validator import ArgumentValidator as V


class DaysValidationTests(unittest.TestCase):
    def test_none_is_allowed(self):
        ok, err = V.validate_days(None)
        self.assertTrue(ok)

    def test_in_range(self):
        for d in (1, 7, 14):
            self.assertTrue(V.validate_days(d)[0], d)

    def test_out_of_range(self):
        for d in (0, 15, 99):
            ok, err = V.validate_days(d)
            self.assertFalse(ok, d)
            self.assertIn("1-14", err)


class RefreshValidationTests(unittest.TestCase):
    def test_in_range(self):
        for r in (0, 48, 168):
            self.assertTrue(V.validate_refresh(r)[0], r)

    def test_out_of_range(self):
        for r in (169, 200, -5):
            self.assertFalse(V.validate_refresh(r)[0], r)


class OffsetValidationTests(unittest.TestCase):
    def test_in_range(self):
        self.assertTrue(V.validate_offset(1)[0])
        self.assertTrue(V.validate_offset(14)[0])

    def test_out_of_range(self):
        self.assertFalse(V.validate_offset(0)[0])
        self.assertFalse(V.validate_offset(15)[0])


class LocationCodeValidationTests(unittest.TestCase):
    def test_valid_us_zip(self):
        self.assertTrue(V.validate_location_code("90210")[0])

    def test_valid_ca_postal(self):
        self.assertTrue(V.validate_location_code("J3B1M4")[0])
        self.assertTrue(V.validate_location_code("J3B 1M4")[0])

    def test_invalid(self):
        self.assertFalse(V.validate_location_code("hello")[0])


if __name__ == "__main__":
    unittest.main()
