"""Tests for the configurable <imagesources> image host block."""

import tempfile
import unittest
from pathlib import Path

from gracenote2epg.config.settings import SettingsManager
from gracenote2epg.cache import CacheManager
from gracenote2epg.xmltv import XmltvGenerator

FANCYBITS = "https://tmsimg.fancybits.co/assets"
TVTV = "https://www.tvtv.ca/gn/pi/assets"


def _write(xml):
    p = Path(tempfile.mkdtemp()) / "config.xml"
    p.write_text('<?xml version="1.0"?>\n' + xml)
    return p


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.sm = SettingsManager()

    def test_parses_sources_with_status(self):
        p = _write(
            "<settings><imagesources>"
            f'<source status="disabled">{TVTV}</source>'
            f'<source status="enabled">{FANCYBITS}</source>'
            "</imagesources></settings>"
        )
        self.assertEqual(self.sm.parse_image_sources(p), [(TVTV, False), (FANCYBITS, True)])

    def test_no_block_returns_empty(self):
        p = _write('<settings><setting id="days">7</setting></settings>')
        self.assertEqual(self.sm.parse_image_sources(p), [])

    def test_missing_status_defaults_enabled(self):
        p = _write(
            f"<settings><imagesources><source>{FANCYBITS}</source></imagesources></settings>"
        )
        self.assertEqual(self.sm.parse_image_sources(p), [(FANCYBITS, True)])


class ActiveSourceTests(unittest.TestCase):
    def test_first_enabled_wins(self):
        self.assertEqual(
            SettingsManager.active_image_source([(TVTV, False), (FANCYBITS, True)]), FANCYBITS
        )

    def test_empty_falls_back_to_default(self):
        self.assertEqual(SettingsManager.active_image_source([]), FANCYBITS)

    def test_none_enabled_falls_back_to_default(self):
        self.assertEqual(SettingsManager.active_image_source([(TVTV, False)]), FANCYBITS)


class RoundTripTests(unittest.TestCase):
    def setUp(self):
        self.sm = SettingsManager()

    def test_block_preserved_on_rewrite(self):
        p = _write(
            '<settings version="5">'
            f'<imagesources><source status="enabled">{TVTV}</source></imagesources>'
            "</settings>"
        )
        before = self.sm.parse_image_sources(p)
        self.sm.write_clean_config(p, {"days": "7"})
        self.assertEqual(self.sm.parse_image_sources(p), before)

    def test_default_block_injected_when_absent(self):
        p = _write('<settings version="5"><setting id="days">7</setting></settings>')
        self.sm.write_clean_config(p, {"days": "7"})
        self.assertEqual(self.sm.active_image_source(self.sm.parse_image_sources(p)), FANCYBITS)


class GeneratorTests(unittest.TestCase):
    def _gen(self, url=None):
        cm = CacheManager(Path(tempfile.mkdtemp()) / "cache")
        return XmltvGenerator(cm, image_base_url=url)

    def test_default_host_is_a_mirror_not_tvtv(self):
        self.assertEqual(self._gen().ASSETS_BASE_URL, FANCYBITS)

    def test_configured_url_overrides_default(self):
        self.assertEqual(self._gen(TVTV + "/").ASSETS_BASE_URL, TVTV)  # trailing slash stripped


if __name__ == "__main__":
    unittest.main()
