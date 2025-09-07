"""
gracenote2epg.config.base - Main configuration manager

Orchestrates all configuration operations including parsing, validation,
migration, lineup management, and display functionality.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .validation import ConfigValidator
from .settings import SettingsManager
from .migration import ConfigMigrator
from .lineup import LineupManager
from .retention import RetentionManager
from .display import ConfigDisplayer


class ConfigManager:
    """Main configuration manager that orchestrates all config operations"""

    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.settings: Dict[str, Any] = {}
        self.version: str = "5"
        self.zipcode_extracted_from_lineupid: bool = False
        self.config_changes: Dict[str, str] = {}
        self._original_file_settings: Dict[str, Any] = {}

        # Initialize component managers
        self.validator = ConfigValidator()
        self.settings_manager = SettingsManager()
        self.migrator = ConfigMigrator()
        self.lineup_manager = LineupManager()
        self.retention_manager = RetentionManager()
        self.displayer = ConfigDisplayer(self.validator, self.lineup_manager)

    def load_config(
        self,
        location_code: Optional[str] = None,
        location_source: str = "explicit",
        location_extracted_from: Optional[str] = None,
        days: Optional[int] = None,
        langdetect: Optional[bool] = None,
        refresh_hours: Optional[int] = None,
        lineupid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Load and validate configuration file"""

        # Create default config if doesn't exist
        if not self.config_file.exists():
            self.settings_manager.create_default_config(self.config_file)

        # Parse configuration
        self._parse_and_migrate_config()

        # Store original values from config file before any command line modifications
        self._original_file_settings = self.settings.copy()

        # Track original values for clearer logging
        original_zipcode = self.settings.get("zipcode", "").strip()
        original_lineupid = self.settings.get("lineupid", "auto").strip()

        # Track changes for logging
        self.config_changes = {}
        self.zipcode_extracted_from_lineupid = False

        # Override with command line arguments (TEMPORARY for this execution only)
        self._process_command_line_overrides(
            location_code, location_source, location_extracted_from,
            days, langdetect, refresh_hours, lineupid,
            original_zipcode, original_lineupid
        )

        # Validate configuration consistency before processing
        consistency_changes = self.validator.validate_config_consistency(self.settings)
        self.config_changes.update(consistency_changes)

        # Validate required settings
        self._validate_all_settings()

        # Set defaults for missing settings
        self._set_defaults_and_update_file()

        return self.settings

    def _parse_and_migrate_config(self):
        """Parse configuration file and handle migration if needed"""
        # Parse configuration file
        all_settings, original_order, version = self.settings_manager.parse_config_file(self.config_file)
        self.version = version

        # Categorize settings and check migration needs
        valid_settings = {
            k: v for k, v in all_settings.items() 
            if k in self.validator.VALID_SETTINGS
        }

        migration_needed, deprecated_settings, unknown_settings, ordering_needed = \
            self.migrator.analyze_migration_needs(all_settings, valid_settings, original_order)

        # Process valid settings
        self._process_valid_settings(valid_settings)

        # Perform migration if needed
        if migration_needed or ordering_needed:
            removed_settings = deprecated_settings + unknown_settings
            self._perform_migration(valid_settings, removed_settings, ordering_needed)

    def _process_valid_settings(self, valid_settings: Dict[str, Any]):
        """Process and type-convert valid settings"""
        for setting_id, setting_value in valid_settings.items():
            processed_value = self.validator.validate_setting_type(setting_id, setting_value)
            self.settings[setting_id] = processed_value
            logging.debug(
                "Processed setting: %s = %s (%s)",
                setting_id,
                processed_value,
                type(processed_value).__name__,
            )

    def _perform_migration(self, valid_settings: Dict[str, Any], removed_settings: List[str], ordering_needed: bool):
        """Perform configuration migration"""
        reason = []
        if removed_settings:
            reason.append(f"removed {len(removed_settings)} deprecated/unknown settings")
        if ordering_needed:
            reason.append("reordered settings for consistency")

        logging.info("Configuration update needed: %s", ", ".join(reason))
        
        success = self.migrator.perform_migration(
            self.config_file, valid_settings, removed_settings, ordering_needed
        )
        
        if success:
            # Validate migration result
            if not self.migrator.validate_migration_result(self.config_file):
                logging.warning("Migration validation failed, attempting rollback")
                self.migrator.rollback_migration(self.config_file)

    def _process_command_line_overrides(self, location_code, location_source, location_extracted_from,
                                       days, langdetect, refresh_hours, lineupid,
                                       original_zipcode, original_lineupid):
        """Process command line argument overrides"""
        # Override zipcode
        if location_code:
            self._process_zipcode_override(
                location_code, location_source, location_extracted_from, original_zipcode
            )

        # Override other settings
        if days:
            self._process_setting_override("days", str(days), self.settings.get("days", "1"))

        if langdetect is not None:
            self._process_setting_override("langdetect", langdetect, self.settings.get("langdetect", True))

        if refresh_hours is not None:
            self._process_setting_override("refresh", str(refresh_hours), self.settings.get("refresh", "48"))

        if lineupid is not None:
            self._process_setting_override("lineupid", lineupid, original_lineupid)

    def _process_zipcode_override(self, location_code, location_source, location_extracted_from, original_zipcode):
        """Process zipcode override from command line"""
        if not original_zipcode:  # Empty in config
            if location_source == "extracted" and location_extracted_from:
                self.config_changes["zipcode"] = (
                    f"(empty) → {location_code} (extracted from {location_extracted_from})"
                )
            else:
                self.config_changes["zipcode"] = (
                    f"(empty) → {location_code} (from command line)"
                )
        elif original_zipcode != location_code:
            if location_source == "extracted" and location_extracted_from:
                self.config_changes["zipcode"] = (
                    f"{original_zipcode} → {location_code} (extracted from {location_extracted_from})"
                )
                self._handle_zipcode_mismatch(original_zipcode, location_code, location_extracted_from)
            else:
                self.config_changes["zipcode"] = (
                    f"{original_zipcode} → {location_code} (overridden)"
                )
        
        self.settings["zipcode"] = location_code

    def _handle_zipcode_mismatch(self, original_zipcode, location_code, location_extracted_from):
        """Handle zipcode mismatch detection and resolution"""
        normalized_location = location_code.replace(" ", "")
        logging.warning("Configuration mismatch detected and resolved:")
        logging.warning("  Configured zipcode: %s", original_zipcode)
        logging.warning("  LineupID contains: %s (from %s)", normalized_location, location_extracted_from)
        logging.warning("  Resolution: Using zipcode from lineupid (%s takes precedence)", location_extracted_from)

    def _process_setting_override(self, setting_name, new_value, original_value):
        """Process generic setting override"""
        if str(original_value) != str(new_value):
            self.config_changes[setting_name] = f"{original_value} → {new_value}"
        self.settings[setting_name] = new_value

    def _validate_all_settings(self):
        """Validate all configuration settings"""
        self.validator.validate_required_settings(self.settings)
        self.validator.validate_refresh_hours(self.settings)
        self.retention_manager.validate_cache_and_retention_policies(self.settings)

    def _set_defaults_and_update_file(self):
        """Set default values for missing settings and update config file if needed"""
        # Set defaults using original file values
        added_defaults = self.settings_manager.set_missing_defaults(self.settings)

        # Update config file if we added defaults
        if added_defaults:
            added_list = [f"{k}={v}" for k, v in added_defaults.items()]
            logging.info("Added missing settings with defaults: %s", ", ".join(added_list))

            # Update file with new defaults
            success = self.migrator.update_config_with_defaults(
                self.config_file, added_defaults, self.version
            )
            
            if success:
                # Notify user about upgrade
                self.migrator.notify_config_upgrade(added_list)

    # Public interface methods that maintain compatibility

    def get_lineup_config(self) -> Dict[str, str]:
        """Get lineup configuration with automatic normalization and detection"""
        country = self.get_country()
        return self.lineup_manager.get_lineup_config(self.settings, country)

    def get_retention_config(self) -> Dict[str, Any]:
        """Get unified cache and retention configuration"""
        return self.retention_manager.get_retention_config(self.settings)

    def get_country(self) -> str:
        """Determine country from zipcode format"""
        return self.validator.get_country_from_zipcode(self.settings.get("zipcode", ""))

    def needs_extended_download(self) -> bool:
        """Determine if extended details download is needed"""
        return self.settings_manager.needs_extended_download(self.settings)

    def get_station_list(self) -> Optional[List[str]]:
        """Get explicit station list if configured"""
        return self.settings_manager.get_station_list(self.settings)

    def get_refresh_hours(self) -> int:
        """Get cache refresh hours from configuration"""
        return self.retention_manager.get_refresh_hours(self.settings)

    def validate_postal_code_format(self, postal_code: str):
        """Validate postal code format"""
        return self.validator.validate_postal_code_format(postal_code)

    def display_lineup_detection_test(self, postal_code: str, debug_mode: bool = False) -> bool:
        """Display lineup detection test results"""
        return self.displayer.display_lineup_detection_test(postal_code, debug_mode)

    def log_config_summary(self):
        """Log configuration summary with improved clarity"""
        logging.info("Configuration values processed:")

        # Get configurations for summary
        lineup_config = self.get_lineup_config()
        retention_config = self.get_retention_config()

        # Enhanced zipcode logging
        zipcode = self.settings.get("zipcode")
        if "zipcode" in self.config_changes:
            change_info = self.config_changes["zipcode"]
            logging.info("  zipcode: %s", change_info)
        else:
            logging.info("  zipcode: %s", zipcode)

        # Enhanced lineup configuration logging
        original_lineupid = lineup_config["original_config"]
        final_lineup_id = lineup_config["lineup_id"]

        if "lineupid" in self.config_changes:
            change_info = self.config_changes["lineupid"]
            logging.info("  lineupid: %s", change_info)
        elif lineup_config["auto_detected"]:
            logging.info("  lineupid: %s → %s (auto-detection)", original_lineupid, final_lineup_id)
        else:
            logging.info("  lineupid: %s → %s", original_lineupid, final_lineup_id)

        # Country information
        country = self.get_country()
        country_name = "Canada" if country == "CAN" else "United States of America"
        logging.info("  country: %s [%s] (auto-detected from zipcode)", country_name, country)

        logging.debug(
            "  device: %s (auto-detected for optional &device= URL parameter)",
            lineup_config["device_type"],
        )

        logging.info("  description: %s", lineup_config["description"])
        logging.info("  xdetails (download extended data): %s", self.settings.get("xdetails"))
        logging.info("  xdesc (use extended descriptions): %s", self.settings.get("xdesc"))
        logging.info("  langdetect (automatic language detection): %s", self.settings.get("langdetect"))

        # Log cache and retention using retention manager
        self.retention_manager.log_retention_summary(retention_config)

        # Log configuration logic
        self._log_feature_logic()

    def _log_feature_logic(self):
        """Log configuration logic explanation"""
        xdetails = self.settings.get("xdetails", False)
        xdesc = self.settings.get("xdesc", False)
        langdetect = self.settings.get("langdetect", False)

        if xdesc and not xdetails:
            logging.info("xdesc=true detected - automatically enabling extended details download")
        elif xdetails and not xdesc:
            logging.info("xdetails=true - downloading extended data but using basic descriptions")
        elif xdetails and xdesc:
            logging.info("Both xdetails and xdesc enabled - full extended functionality")
        else:
            logging.info("Extended features disabled - using basic guide data only")

        if langdetect:
            logging.info("Language detection enabled - will auto-detect French/English/Spanish")
        else:
            logging.info("Language detection disabled - all content will be marked as English")
