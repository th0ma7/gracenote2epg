"""Config schema migration: a version-5 file upgrades to 6 + gets the block."""

import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from gracenote2epg.config.base import ConfigManager
from gracenote2epg.config.settings import SettingsManager

FIXTURE_V5 = Path(__file__).parent / "fixtures" / "config_v5.xml"


class MigrationV5toV6Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = self.tmp / "gracenote2epg.xml"
        shutil.copy(FIXTURE_V5, self.cfg)

    def _root(self):
        return ET.parse(self.cfg).getroot()

    def test_fixture_starts_at_v5_without_block(self):
        root = self._root()
        self.assertEqual(root.attrib.get("version"), "5")
        self.assertIsNone(root.find("imagesources"))

    def test_load_upgrades_to_v6_and_injects_block(self):
        ConfigManager(self.cfg).load_config()
        root = self._root()
        self.assertEqual(root.attrib.get("version"), SettingsManager.CONFIG_VERSION)  # "6"
        block = root.find("imagesources")
        self.assertIsNotNone(block, "migration should inject the <imagesources> block")
        self.assertGreaterEqual(len(block.findall("source")), 1)

    def test_upgraded_config_resolves_default_image_source(self):
        cm = ConfigManager(self.cfg)
        cm.load_config()
        self.assertEqual(cm.get_image_source(), "https://tmsimg.fancybits.co/assets")

    def test_version_upgrade_creates_a_backup(self):
        ConfigManager(self.cfg).load_config()
        backups = list(self.tmp.glob("gracenote2epg.xml.backup.*"))
        self.assertTrue(backups, "a one-time schema upgrade should back up the old config")


if __name__ == "__main__":
    unittest.main()
