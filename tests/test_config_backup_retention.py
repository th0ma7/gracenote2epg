"""Config backup retention: keep only the most recent *distinct* backups."""

import tempfile
import unittest
from pathlib import Path

from gracenote2epg.config.migration import ConfigMigrator


class BackupRetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = self.tmp / "gracenote2epg.xml"
        self.cfg.write_text("<settings/>")

    def _backup(self, stamp, content):
        (self.tmp / f"gracenote2epg.xml.backup.{stamp}").write_text(content)

    def _names(self):
        return sorted(p.name for p in self.tmp.glob("gracenote2epg.xml.backup.*"))

    def test_keeps_only_the_most_recent_N_distinct(self):
        for i in range(25):  # all distinct contents
            self._backup(f"20260616_{i:06d}", f"version {i}")
        ConfigMigrator()._prune_old_backups(self.cfg)
        kept = self._names()
        self.assertEqual(len(kept), ConfigMigrator.BACKUP_RETENTION)
        # The 10 newest (highest timestamps) survive.
        self.assertEqual(kept[-1], "gracenote2epg.xml.backup.20260616_000024")
        self.assertEqual(kept[0], "gracenote2epg.xml.backup.20260616_000015")

    def test_identical_backups_are_deduped(self):
        # 20 identical + 1 distinct newest -> only 2 distinct versions kept.
        for i in range(20):
            self._backup(f"20260616_{i:06d}", "same content")
        self._backup("20260616_000099", "a different version")
        ConfigMigrator()._prune_old_backups(self.cfg)
        kept = self._names()
        self.assertEqual(len(kept), 2)
        self.assertIn("gracenote2epg.xml.backup.20260616_000099", kept)
        # The kept copy of the identical version is the newest occurrence.
        self.assertIn("gracenote2epg.xml.backup.20260616_000019", kept)

    def test_no_prune_when_under_limit(self):
        for i in range(3):
            self._backup(f"20260616_{i:06d}", f"v{i}")
        ConfigMigrator()._prune_old_backups(self.cfg)
        self.assertEqual(len(self._names()), 3)

    def test_create_backup_skips_when_identical_to_latest(self):
        # Latest backup already holds the exact current config -> no new file.
        self._backup("20260616_000000", "<settings/>")
        m = ConfigMigrator()
        m.create_backup(self.cfg)
        self.assertEqual(self._names(), ["gracenote2epg.xml.backup.20260616_000000"])

    def test_create_backup_writes_when_changed(self):
        self._backup("20260616_000000", "<old/>")
        m = ConfigMigrator()
        m.create_backup(self.cfg)  # current config is "<settings/>", differs
        self.assertEqual(len(self._names()), 2)


if __name__ == "__main__":
    unittest.main()
