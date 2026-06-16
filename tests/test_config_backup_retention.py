"""Config backup retention: old timestamped backups are pruned on each new one."""

import tempfile
import unittest
from pathlib import Path

from gracenote2epg.config.migration import ConfigMigrator


class BackupRetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = self.tmp / "gracenote2epg.xml"
        self.cfg.write_text("<settings/>")

    def _make_backups(self, n):
        # Sortable second-resolution timestamps: 20260616_000000 .. _0000NN
        for i in range(n):
            (self.tmp / f"gracenote2epg.xml.backup.20260616_{i:06d}").write_text("x")

    def _backups(self):
        return sorted(self.tmp.glob("gracenote2epg.xml.backup.*"))

    def test_keeps_only_the_most_recent_N(self):
        self._make_backups(25)
        ConfigMigrator()._prune_old_backups(self.cfg)
        kept = self._backups()
        self.assertEqual(len(kept), ConfigMigrator.BACKUP_RETENTION)
        # The newest ones (highest timestamps) are the ones kept.
        self.assertEqual(kept[-1].name, "gracenote2epg.xml.backup.20260616_000024")
        self.assertEqual(kept[0].name, "gracenote2epg.xml.backup.20260616_000015")

    def test_no_prune_when_under_limit(self):
        self._make_backups(3)
        ConfigMigrator()._prune_old_backups(self.cfg)
        self.assertEqual(len(self._backups()), 3)

    def test_create_backup_prunes(self):
        self._make_backups(ConfigMigrator.BACKUP_RETENTION + 5)
        m = ConfigMigrator()
        m.create_backup(self.cfg)  # creates one more, then prunes
        self.assertEqual(len(self._backups()), ConfigMigrator.BACKUP_RETENTION)


if __name__ == "__main__":
    unittest.main()
