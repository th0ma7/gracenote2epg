"""Tests for CacheManager: guide/series/movies layout and legacy migration."""

import json
import tempfile
import unittest
from pathlib import Path

from gracenote2epg.cache import CacheManager


class CacheLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cache_dir = Path(self.tmp) / "cache"

    def test_subdirs_created(self):
        cm = CacheManager(self.cache_dir)
        self.assertTrue(cm.guide_dir.is_dir())
        self.assertTrue(cm.series_dir.is_dir())
        self.assertTrue(cm.movies_dir.is_dir())
        self.assertEqual(cm.guide_dir, self.cache_dir / "guide")
        self.assertEqual(cm.series_dir, self.cache_dir / "series")
        self.assertEqual(cm.movies_dir, self.cache_dir / "movies")

    def test_series_saved_under_series_subdir(self):
        cm = CacheManager(self.cache_dir)
        cm.save_series_details("SH00012345", json.dumps({"ok": 1}).encode("utf-8"))
        self.assertTrue((cm.series_dir / "SH00012345.json").exists())
        self.assertFalse((cm.movies_dir / "SH00012345.json").exists())
        self.assertFalse((self.cache_dir / "SH00012345.json").exists())

    def test_movie_saved_under_movies_subdir(self):
        cm = CacheManager(self.cache_dir)
        cm.save_series_details("MV00067890", json.dumps({"title": "x"}).encode("utf-8"))
        self.assertTrue((cm.movies_dir / "MV00067890.json").exists())
        self.assertFalse((cm.series_dir / "MV00067890.json").exists())

    def test_save_load_roundtrip(self):
        cm = CacheManager(self.cache_dir)
        cm.save_series_details("MV00067890", json.dumps({"title": "x"}).encode("utf-8"))
        self.assertEqual(cm.load_series_details("MV00067890"), {"title": "x"})

    def test_guide_block_saved_under_guide_subdir(self):
        cm = CacheManager(self.cache_dir)
        cm.save_guide_block("2026061412.json.gz", b"\x1f\x8b guide")
        self.assertTrue((cm.guide_dir / "2026061412.json.gz").exists())
        self.assertFalse((self.cache_dir / "2026061412.json.gz").exists())
        self.assertEqual(cm.load_guide_block("2026061412.json.gz"), b"\x1f\x8b guide")

    def test_legacy_flat_layout_is_migrated(self):
        # Simulate an old cache: flat detail files + a guide block at the root.
        self.cache_dir.mkdir(parents=True)
        (self.cache_dir / "SH99999999.json").write_text('{"legacy": true}')
        (self.cache_dir / "MV88888888.json").write_text('{"film": true}')
        (self.cache_dir / "2026061412.json.gz").write_bytes(b"\x1f\x8b guide")

        cm = CacheManager(self.cache_dir)

        # Detail files routed by prefix, guide block moved into guide/.
        self.assertFalse((self.cache_dir / "SH99999999.json").exists())
        self.assertTrue((cm.series_dir / "SH99999999.json").exists())
        self.assertTrue((cm.movies_dir / "MV88888888.json").exists())
        self.assertFalse((self.cache_dir / "2026061412.json.gz").exists())
        self.assertTrue((cm.guide_dir / "2026061412.json.gz").exists())
        # And they are reusable (no re-download needed).
        self.assertEqual(cm.load_series_details("SH99999999"), {"legacy": True})
        self.assertEqual(cm.load_series_details("MV88888888"), {"film": True})

    def test_movies_left_in_series_dir_are_migrated(self):
        # First series/ layout stored movies in series/ too; relocate them.
        series_dir = self.cache_dir / "series"
        series_dir.mkdir(parents=True)
        (series_dir / "MV12121212.json").write_text('{"film": 1}')
        (series_dir / "SH13131313.json").write_text('{"show": 1}')

        cm = CacheManager(self.cache_dir)

        self.assertFalse((cm.series_dir / "MV12121212.json").exists())
        self.assertTrue((cm.movies_dir / "MV12121212.json").exists())
        # Series stay put.
        self.assertTrue((cm.series_dir / "SH13131313.json").exists())


if __name__ == "__main__":
    unittest.main()
