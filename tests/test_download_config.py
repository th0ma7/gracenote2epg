"""dlworkers / dlthreshold resolution (auto, overrides, fallbacks)."""

import tempfile
import unittest
from pathlib import Path

from gracenote2epg.config.base import ConfigManager


def _cm(**settings):
    cm = ConfigManager(Path(tempfile.mkdtemp()) / "gracenote2epg.xml")
    cm.settings = settings
    return cm


class DownloadThresholdTests(unittest.TestCase):
    def test_auto_means_no_cutoff_adaptive(self):
        # auto -> None: stay parallel, adaptive concurrency handles 429s.
        self.assertIsNone(_cm(dlthreshold="auto").get_download_threshold())

    def test_default_when_missing_is_auto(self):
        self.assertIsNone(_cm().get_download_threshold())

    def test_positive_integer_overrides(self):
        self.assertEqual(_cm(dlthreshold="250").get_download_threshold(), 250)

    def test_zero_and_garbage_fall_back_to_auto(self):
        self.assertIsNone(_cm(dlthreshold="0").get_download_threshold())
        self.assertIsNone(_cm(dlthreshold="nope").get_download_threshold())


class DownloadWorkersTests(unittest.TestCase):
    def test_auto_and_overrides(self):
        self.assertEqual(_cm(dlworkers="auto").get_download_workers(), 4)
        self.assertEqual(_cm(dlworkers="2").get_download_workers(), 2)
        self.assertEqual(_cm(dlworkers="99").get_download_workers(), 8)  # clamped
        self.assertEqual(_cm(dlworkers="x").get_download_workers(), 4)  # fallback


if __name__ == "__main__":
    unittest.main()
