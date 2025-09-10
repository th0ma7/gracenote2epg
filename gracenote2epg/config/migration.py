"""
gracenote2epg.config.migration - Configuration migration and cleanup

Handles migration from older configuration versions, deprecated settings removal,
backup creation, and configuration file cleanup operations.
"""

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


class ConfigMigrator:
    """Handles configuration migration and cleanup operations"""

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

    def analyze_migration_needs(self, 
                               all_settings: Dict[str, Any], 
                               valid_settings: Dict[str, Any],
                               original_order: List[str]) -> Tuple[bool, List[str], List[str], bool]:
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
        """Create backup of configuration file before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{config_file}.backup.{timestamp}"
        
        try:
            shutil.copy2(config_file, backup_file)
            logging.info("Created configuration backup: %s", backup_file)
            self._backup_file_created = backup_file
            return backup_file
        except Exception as e:
            logging.error("Failed to create backup: %s", str(e))
            raise

    def perform_migration(self, 
                         config_file: Path,
                         valid_settings: Dict[str, Any],
                         removed_settings: List[str],
                         ordering_needed: bool = False) -> bool:
        """
        Perform configuration migration with backup
        
        Returns:
            bool: True if migration was successful
        """
        try:
            # Create backup only if we're making changes
            backup_file = None
            if removed_settings or ordering_needed:
                backup_file = self.create_backup(config_file)

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

            logging.info("  Updated to version 5 with unified retention policies")

            # User notification about cleanup/migration - simplified
            if removed_settings:
                self._notify_config_cleanup(removed_settings)

            return True

        except Exception as e:
            logging.error("Error updating configuration file: %s", str(e))
            logging.error("Continuing with existing configuration...")
            return False

    def update_config_with_defaults(self, 
                                   config_file: Path, 
                                   new_settings: Dict[str, Any],
                                   version: str) -> bool:
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

            # Get existing settings to preserve their ORIGINAL values
            existing_settings = {}
            for setting in root.findall("setting"):
                setting_id = setting.get("id")

                # Get value based on version (same logic as in SettingsManager)
                if version == "2":
                    setting_value = setting.text
                else:
                    setting_value = setting.get("value")
                    if setting_value is None:
                        setting_value = setting.text
                    if setting_value == "":
                        setting_value = None

                # Only include valid settings that we want to preserve
                from .validation import ConfigValidator
                validator = ConfigValidator()
                if setting_id in validator.VALID_SETTINGS:
                    existing_settings[setting_id] = setting_value

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

    def notify_config_upgrade(self, added_defaults: List[str]):
        """Notify user about configuration upgrade with visible warning"""
        backup_file = self._backup_file_created

        logging.warning("=" * 60)
        logging.warning("CONFIGURATION UPGRADED TO VERSION 5")
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

    def get_backup_file_path(self) -> str:
        """Get the path of the backup file created during migration"""
        return self._backup_file_created

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
                
            if root.attrib.get("version") != "5":
                logging.warning("Migration validation: version is not '5'")
                
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
