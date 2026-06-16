"""
gracenote2epg.config.migration - Configuration migration and cleanup

Handles migration from older configuration versions, deprecated settings removal,
backup creation, and configuration file cleanup operations.
"""

import hashlib
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


class ConfigMigrator:
    """Handles configuration migration and cleanup operations"""

    # How many timestamped config backups to keep (older ones are pruned on each
    # new backup, so they don't accumulate indefinitely).
    BACKUP_RETENTION = 10

    # DEPRECATED settings for simplified removal (no migration)
    DEPRECATED_SETTINGS = {
        "auto_lineup": "lineupid",
        "lineupcode": "lineupid",
        "lineup": "lineupid",
        "device": "lineupid",  # Auto-detected now
        # Old log rotation settings
        "logrotate_enabled": "logrotate",
        "logrotate_interval": "logrotate",
        "logrotate_keep": "relogs",
        # Intermediate version settings
        "log_rotation": "logrotate",
        "log_retention": "relogs",
        "xmltv_backup_retention": "rexmltv",
    }

    def __init__(self):
        self._backup_file_created: str = None

    def analyze_migration_needs(
        self,
        all_settings: Dict[str, Any],
        valid_settings: Dict[str, Any],
        original_order: List[str],
    ) -> Tuple[bool, List[str], List[str], bool]:
        """
        Analyze what migration operations are needed

        Returns:
            tuple: (migration_needed, deprecated_settings, unknown_settings, ordering_needed)
        """
        deprecated_settings = []
        unknown_settings = []
        migration_needed = False

        # Check for deprecated and unknown settings
        for setting_id in all_settings:
            if setting_id in valid_settings:
                continue  # Valid setting, keep it
            elif setting_id in self.DEPRECATED_SETTINGS:
                deprecated_settings.append(setting_id)
                migration_needed = True
                logging.debug("Deprecated setting found: %s (will be removed)", setting_id)
            elif setting_id.startswith("desc") and re.match(r"desc[0-9]{2}", setting_id):
                # Old description formatting - mark for removal
                deprecated_settings.append(setting_id)
                migration_needed = True
            elif setting_id == "useragent":
                # Old useragent setting - mark for removal
                deprecated_settings.append(setting_id)
                migration_needed = True
            else:
                # Unknown setting - mark for removal
                unknown_settings.append(setting_id)
                migration_needed = True
                logging.warning(
                    "Unknown configuration setting: %s = %s (will be removed)",
                    setting_id,
                    all_settings[setting_id],
                )

        # Check if ordering needs to be corrected (this would be done by SettingsManager)
        from .settings import SettingsManager

        settings_manager = SettingsManager()
        ordering_needed = settings_manager.check_ordering_needed(original_order, valid_settings)

        return migration_needed, deprecated_settings, unknown_settings, ordering_needed

    def create_backup(self, config_file: Path) -> str:
        """Create backup of configuration file before migration.

        Skips writing a new backup when the current config is byte-for-byte
        identical to the most recent one (no point duplicating it), then prunes
        to the most recent distinct versions.
        """
        config_file = Path(config_file)
        existing = sorted(config_file.parent.glob(f"{config_file.name}.backup.*"))

        try:
            current = config_file.read_bytes()
            if existing and existing[-1].read_bytes() == current:
                logging.debug("Config unchanged since last backup; not duplicating it")
                self._backup_file_created = str(existing[-1])
                self._prune_old_backups(config_file)
                return str(existing[-1])
        except OSError:
            pass  # fall through and back up normally

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{config_file}.backup.{timestamp}"
        try:
            shutil.copy2(config_file, backup_file)
            logging.info("Created configuration backup: %s", backup_file)
            self._backup_file_created = backup_file
            self._prune_old_backups(config_file)
            return backup_file
        except Exception as e:
            logging.error("Failed to create backup: %s", str(e))
            raise

    def _prune_old_backups(self, config_file: Path) -> None:
        """Keep only the most recent ``BACKUP_RETENTION`` *distinct* backups.

        Walks the backups newest-first (the ``YYYYMMDD_HHMMSS`` timestamp sorts
        lexicographically) and keeps the newest occurrence of each distinct
        content, up to the retention limit. Older duplicates and anything beyond
        the limit are deleted — so we never keep 10 identical files.
        """
        try:
            retention = self.BACKUP_RETENTION
            if retention <= 0:
                return  # 0/negative = unlimited (no cleanup)
            backups = sorted(config_file.parent.glob(f"{config_file.name}.backup.*"), reverse=True)
            seen_hashes = set()
            removed = 0
            for backup in backups:  # newest first
                try:
                    digest = hashlib.md5(backup.read_bytes()).hexdigest()
                except OSError:
                    continue
                if digest not in seen_hashes and len(seen_hashes) < retention:
                    seen_hashes.add(digest)  # keep newest copy of this version
                else:
                    try:
                        backup.unlink()  # older duplicate, or beyond retention
                        removed += 1
                    except OSError as e:
                        logging.debug("Could not remove old config backup %s: %s", backup.name, e)
            if removed:
                logging.info(
                    "Config backup cleanup: removed %d old/duplicate backup(s), kept %d distinct",
                    removed,
                    len(seen_hashes),
                )
        except Exception as e:
            logging.debug("Config backup cleanup skipped: %s", e)

    def perform_migration(
        self,
        config_file: Path,
        valid_settings: Dict[str, Any],
        removed_settings: List[str],
        ordering_needed: bool = False,
        version_upgrade: bool = False,
    ) -> bool:
        """
        Perform configuration migration with backup

        Returns:
            bool: True if migration was successful
        """
        try:
            # Create backup only if we're making changes
            if removed_settings or ordering_needed or version_upgrade:
                self.create_backup(config_file)

            # Write cleaned and ordered configuration
            from .settings import SettingsManager

            settings_manager = SettingsManager()
            settings_manager.write_clean_config(config_file, valid_settings)

            # Log what was done at INFO level (not WARNING)
            changes = []
            if removed_settings:
                changes.append(f"removed {len(removed_settings)} deprecated/unknown settings")
            if ordering_needed:
                changes.append("reordered settings for consistency")

            logging.info("Configuration updated successfully: %s", ", ".join(changes))

            if removed_settings:
                logging.info("  Removed settings: %s", ", ".join(removed_settings))

            from .settings import SettingsManager

            logging.info("  Updated to configuration version %s", SettingsManager.CONFIG_VERSION)

            # User notification about cleanup/migration - simplified
            if removed_settings:
                self._notify_config_cleanup(removed_settings)

            return True

        except Exception as e:
            logging.error("Error updating configuration file: %s", str(e))
            logging.error("Continuing with existing configuration...")
            return False

    def update_config_with_defaults(
        self, config_file: Path, new_settings: Dict[str, Any], version: str
    ) -> bool:
        """
        Update configuration file to include newly added default settings

        Returns:
            bool: True if update was successful
        """
        try:
            # Re-read the original config file to get the unmodified values
            import xml.etree.ElementTree as ET

            tree = ET.parse(config_file)
            root = tree.getroot()

            # Preserve existing valid settings with their ORIGINAL values
            existing_settings = self._read_existing_valid_settings(root, version)

            # Add only the truly new settings (those not in original file)
            for key, value in new_settings.items():
                if key not in existing_settings:
                    existing_settings[key] = (
                        str(value)
                        if not isinstance(value, bool)
                        else ("true" if value else "false")
                    )
                    logging.debug(
                        "Adding new setting to config file: %s = %s", key, existing_settings[key]
                    )

            # Write the complete configuration with preserved original values
            from .settings import SettingsManager

            settings_manager = SettingsManager()
            settings_manager.write_clean_config(config_file, existing_settings)

            logging.info(
                "Configuration file updated: preserved %d existing settings, added %d new settings",
                len(existing_settings) - len(new_settings),
                len(new_settings),
            )

            return True

        except Exception as e:
            logging.error("Error updating configuration file with defaults: %s", str(e))
            return False

    @staticmethod
    def _setting_value(setting, version: str):
        """Extract a <setting>'s value honouring the config schema version."""
        if version == "2":
            return setting.text
        value = setting.get("value")
        if value is None:
            value = setting.text
        if value == "":
            value = None
        return value

    def _read_existing_valid_settings(self, root, version: str) -> Dict[str, Any]:
        """Read valid settings (with their original values) from a parsed config."""
        from .validation import ConfigValidator

        valid = ConfigValidator().VALID_SETTINGS
        existing = {}
        for setting in root.findall("setting"):
            setting_id = setting.get("id")
            if setting_id in valid:
                existing[setting_id] = self._setting_value(setting, version)
        return existing

    def notify_config_upgrade(self, added_defaults: List[str]):
        """Notify user about configuration upgrade with visible warning"""
        backup_file = self._backup_file_created

        from .settings import SettingsManager

        logging.warning("=" * 60)
        logging.warning("CONFIGURATION UPGRADED TO VERSION %s", SettingsManager.CONFIG_VERSION)
        if backup_file:
            logging.warning("Backup created: %s", backup_file)
        logging.warning("Updated settings: (configuration file)")
        logging.warning("Documentation: https://github.com/th0ma7/gracenote2epg")
        logging.warning("=" * 60)

    def _notify_config_cleanup(self, removed_settings: List[str]):
        """Notify user about configuration cleanup"""
        # Log at INFO level instead of WARNING - this is normal operation
        logging.info(
            "Configuration cleanup: removed %d deprecated settings: %s",
            len(removed_settings),
            ", ".join(removed_settings),
        )

    def validate_migration_result(self, config_file: Path) -> bool:
        """Validate that migration was successful by attempting to parse the result"""
        try:
            import xml.etree.ElementTree as ET

            tree = ET.parse(config_file)
            root = tree.getroot()

            # Basic validation
            if root.tag != "settings":
                logging.error("Migration validation failed: root element is not 'settings'")
                return False

            from .settings import SettingsManager

            if root.attrib.get("version") != SettingsManager.CONFIG_VERSION:
                logging.warning(
                    "Migration validation: version is not '%s'", SettingsManager.CONFIG_VERSION
                )

            # Count settings
            settings_count = len(root.findall("setting"))
            if settings_count == 0:
                logging.error("Migration validation failed: no settings found")
                return False

            logging.debug("Migration validation passed: %d settings found", settings_count)
            return True

        except Exception as e:
            logging.error("Migration validation failed: %s", str(e))
            return False

    def rollback_migration(self, config_file: Path) -> bool:
        """Rollback migration by restoring from backup"""
        if not self._backup_file_created:
            logging.error("Cannot rollback: no backup file available")
            return False

        try:
            backup_path = Path(self._backup_file_created)
            if not backup_path.exists():
                logging.error("Cannot rollback: backup file not found: %s", backup_path)
                return False

            shutil.copy2(backup_path, config_file)
            logging.info("Configuration rolled back from backup: %s", backup_path)
            return True

        except Exception as e:
            logging.error("Failed to rollback configuration: %s", str(e))
            return False
