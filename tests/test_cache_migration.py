"""Tests for CacheManager: series/ subdirectory layout and legacy migration."""

import json
import tempfile
import unittest
from pathlib import Path

from gracenote2epg.cache import CacheManager


class CacheLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cache_dir = Path(self.tmp) / "cache"

    def test_series_dir_created(self):
        cm = CacheManager(self.cache_dir)
        self.assertTrue(cm.series_dir.is_dir())
        self.assertEqual(cm.series_dir, self.cache_dir / "series")

    def test_series_saved_under_subdir(self):
        cm = CacheManager(self.cache_dir)
        cm.save_series_details("SH00012345", json.dumps({"ok": 1}).encode("utf-8"))
        self.assertTrue((cm.series_dir / "SH00012345.json").exists())
        self.assertFalse((self.cache_dir / "SH00012345.json").exists())

    def test_save_load_roundtrip(self):
        cm = CacheManager(self.cache_dir)
        cm.save_series_details("MV00067890", json.dumps({"title": "x"}).encode("utf-8"))
        self.assertEqual(cm.load_series_details("MV00067890"), {"title": "x"})

    def test_legacy_flat_series_are_migrated(self):
        # Simulate an old cache: flat series files + a guide block at the root.
        self.cache_dir.mkdir(parents=True)
        (self.cache_dir / "SH99999999.json").write_text('{"legacy": true}')
        (self.cache_dir / "2026061412.json.gz").write_bytes(b"\x1f\x8b guide")

        cm = CacheManager(self.cache_dir)

        # Series file moved into series/, guide block left at the root.
        self.assertFalse((self.cache_dir / "SH99999999.json").exists())
        self.assertTrue((cm.series_dir / "SH99999999.json").exists())
        self.assertTrue((self.cache_dir / "2026061412.json.gz").exists())
        # And it is reusable (no re-download needed).
        self.assertEqual(cm.load_series_details("SH99999999"), {"legacy": True})


if __name__ == "__main__":
    unittest.main()
