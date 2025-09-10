"""
gracenote2epg.config.validation - Configuration validation

Handles postal code validation, format checking, and configuration
consistency validation for gracenote2epg configurations.
"""

import logging
import re
from typing import Dict, Any, Tuple, Optional


class ConfigValidator:
    """Handles configuration validation and consistency checks"""

    def __init__(self):
        # Valid settings and their types
        self.VALID_SETTINGS = {
            # Required settings
            "zipcode": str,
            # Single lineup setting
            "lineupid": str,
            # Basic settings
            "days": str,
            # Station filtering
            "slist": str,
            "stitle": bool,
            # Extended details
            "xdetails": bool,
            "xdesc": bool,
            "langdetect": bool,
            # Display options
            "epgenre": str,
            "epicon": str,
            # TVheadend integration
            "tvhoff": bool,
            "usern": str,
            "passw": str,
            "tvhurl": str,
            "tvhport": str,
            "tvhmatch": bool,
            "chmatch": bool,
            # Cache and retention policies
            "redays": str,
            "refresh": str,
            "logrotate": str,
            "relogs": str,
            "rexmltv": str,
        }

    def validate_postal_code_format(self, postal_code: str) -> Tuple[bool, str, str]:
        """
        Validate postal code format and return country info

        Args:
            postal_code: Raw postal code input

        Returns:
            tuple: (is_valid, country_code, clean_postal)
        """
        clean_postal = postal_code.replace(" ", "").upper()

        if clean_postal.isdigit() and len(clean_postal) == 5:
            return True, "USA", clean_postal
        elif re.match(r"^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$", clean_postal):
            return True, "CAN", clean_postal
        else:
            return False, "", clean_postal

    def extract_location_from_lineupid(self, lineupid: str) -> Optional[str]:
        """Extract postal/ZIP code from lineup ID if it's in OTA format"""
        # Pattern for OTA lineups: COUNTRY-OTA<LOCATION>[-DEFAULT]
        ota_pattern = re.compile(r"^(CAN|USA)-OTA([A-Z0-9]+)(?:-DEFAULT)?$", re.IGNORECASE)

        match = ota_pattern.match(lineupid.strip())
        if match:
            country = match.group(1).upper()
            location = match.group(2).upper()

            # Validate extracted location format
            if country == "CAN":
                # Canadian postal: should be A1A1A1 format
                if re.match(r"^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$", location):
                    # Format as A1A 1A1 (with space)
                    return f"{location[:3]} {location[3:]}"
            elif country == "USA":
                # US ZIP: should be 5 digits
                if re.match(r"^[0-9]{5}$", location):
                    return location

        return None

    def validate_config_consistency(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate configuration consistency between zipcode and lineupid
        
        Args:
            settings: Configuration settings dictionary
            
        Returns:
            Dict with any changes made for consistency
        """
        zipcode = settings.get("zipcode", "").strip()
        lineupid = settings.get("lineupid", "auto").strip()
        changes = {}

        # If lineupid is not 'auto', check for consistency with zipcode
        if lineupid.lower() != "auto":
            extracted_location = self.extract_location_from_lineupid(lineupid)

            if extracted_location and zipcode:
                # Both zipcode in config and extractable location from lineupid
                clean_extracted = extracted_location.replace(" ", "").upper()
                clean_zipcode = zipcode.replace(" ", "").upper()

                if clean_extracted != clean_zipcode:
                    logging.error("Configuration mismatch detected:")
                    logging.error("  Configured zipcode: %s", zipcode)
                    # Normalize display (remove spaces)
                    normalized_extracted = extracted_location.replace(" ", "")
                    logging.error(
                        "  LineupID contains: %s (extracted from %s)",
                        normalized_extracted,
                        lineupid,
                    )
                    logging.error("  These must match for consistent operation")
                    raise ValueError(
                        f'Configuration mismatch: zipcode "{zipcode}" conflicts with '
                        f'lineupid "{lineupid}" (contains {normalized_extracted}). '
                        "Either use auto-detection with zipcode or ensure consistency."
                    )
                else:
                    logging.debug(
                        'Configuration consistency verified: zipcode "%s" matches lineupid "%s"',
                        zipcode,
                        lineupid,
                    )

            elif extracted_location and not zipcode:
                # Lineupid contains location but no zipcode configured - auto-extract
                normalized_extracted = extracted_location.replace(" ", "")
                settings["zipcode"] = normalized_extracted
                changes["zipcode"] = (
                    f"(empty) → {normalized_extracted} (extracted from {lineupid})"
                )
                logging.info(
                    "Auto-extracted zipcode from lineupid: %s → %s", lineupid, normalized_extracted
                )

        return changes

    def validate_required_settings(self, settings: Dict[str, Any]):
        """Validate required configuration settings with enhanced error messages"""
        # Check required zipcode
        zipcode = settings.get("zipcode", "").strip()
        if not zipcode:
            logging.error("Zipcode is required but not found in configuration")
            logging.error("Available settings: %s", list(settings.keys()))
            raise ValueError("Missing required zipcode in configuration")

        # Enhanced validation for auto-detection lineup
        lineupid = settings.get("lineupid", "auto").strip().lower()
        if lineupid == "auto":
            # Validate zipcode format for auto-detection
            is_valid, _, _ = self.validate_postal_code_format(zipcode)

            if not is_valid:
                logging.error("Auto-detection (lineupid=auto) requires a valid ZIP/postal code")
                logging.error('Current zipcode: "%s"', zipcode)
                logging.error("Expected formats:")
                logging.error("  - US ZIP code: 90210")
                logging.error("  - Canadian postal: J3B1M4 or J3B 1M4")
                raise ValueError(
                    f'Invalid zipcode "{zipcode}" for auto-detection. '
                    "Auto-detection requires valid US ZIP (12345) or Canadian postal (A1A1A1)"
                )

            logging.debug('Zipcode "%s" validated for auto-detection', zipcode)

    def validate_refresh_hours(self, settings: Dict[str, Any]):
        """Validate refresh hours configuration"""
        refresh_setting = settings.get("refresh", "48")
        try:
            refresh_hours = int(refresh_setting)
            if refresh_hours < 0 or refresh_hours > 168:
                logging.warning("Invalid refresh hours %d, using default 48", refresh_hours)
                settings["refresh"] = "48"
        except (ValueError, TypeError):
            logging.warning('Invalid refresh setting "%s", using default 48', refresh_setting)
            settings["refresh"] = "48"

    def validate_retention_value(self, value: str) -> bool:
        """Validate retention value: must be number (days) or weekly/monthly/quarterly/unlimited"""
        if not value:
            return False

        # Check if it's a number (days)
        try:
            days = int(value)
            return 0 <= days <= 3650  # 0 to 10 years seems reasonable
        except ValueError:
            pass

        # Check if it's a valid period
        valid_periods = ["weekly", "monthly", "quarterly", "unlimited"]
        return value.lower() in valid_periods

    def validate_cache_and_retention_policies(self, settings: Dict[str, Any]):
        """Validate unified cache and retention policy configuration settings"""
        # Validate logrotate
        logrotate = settings.get("logrotate", "true").lower().strip()
        valid_rotations = ["true", "false", "daily", "weekly", "monthly"]

        if logrotate not in valid_rotations:
            logging.warning('Invalid logrotate value "%s", using default "true"', logrotate)
            settings["logrotate"] = "true"
        else:
            settings["logrotate"] = logrotate

        # Validate relogs (log retention)
        relogs = settings.get("relogs", "30").strip()
        if not self.validate_retention_value(relogs):
            logging.warning('Invalid relogs value "%s", using default "30"', relogs)
            settings["relogs"] = "30"

        # Validate rexmltv (XMLTV backup retention)
        rexmltv = settings.get("rexmltv", "7").strip()
        if not self.validate_retention_value(rexmltv):
            logging.warning('Invalid rexmltv value "%s", using default "7"', rexmltv)
            settings["rexmltv"] = "7"

        # Validate redays >= days
        try:
            days = int(settings.get("days", "1"))
            redays = int(settings.get("redays", str(days)))

            if redays < days:
                logging.warning(
                    "redays (%d) must be >= days (%d), adjusting redays to %d", redays, days, days
                )
                settings["redays"] = str(days)
            # Remove the excessive warning - just log at debug level
            elif redays > days * 3:  # Reasonable upper limit
                logging.debug(
                    "redays (%d) is much higher than days (%d) - see documentation for optimization tips",
                    redays,
                    days,
                )

        except (ValueError, TypeError):
            # Set redays to match days if invalid
            days = int(settings.get("days", "1"))
            settings["redays"] = str(days)
            logging.warning("Invalid redays value, setting to match days (%d)", days)

    def parse_boolean(self, value: Any) -> bool:
        """Parse boolean values from configuration"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def validate_setting_type(self, setting_id: str, setting_value: Any) -> Any:
        """Validate and convert setting to expected type"""
        if setting_id not in self.VALID_SETTINGS:
            return setting_value

        expected_type = self.VALID_SETTINGS[setting_id]

        if expected_type == bool:
            return self.parse_boolean(setting_value)
        elif expected_type == str:
            return setting_value if setting_value is not None else ""
        else:
            return setting_value

    def get_country_from_zipcode(self, zipcode: str) -> str:
        """Determine country from zipcode format"""
        clean_zipcode = zipcode.replace(" ", "")
        if clean_zipcode.isdigit():
            return "USA"
        else:
            return "CAN"
