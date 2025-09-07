"""
gracenote2epg.config.retention - Retention policy management

Handles unified cache and retention policy configuration for logs and XMLTV backups,
including validation and conversion between different retention formats.
"""

import logging
from typing import Dict, Any


class RetentionManager:
    """Handles retention policy configuration and validation"""

    def get_retention_config(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Get unified cache and retention configuration"""
        # Parse logrotate setting
        logrotate = settings.get("logrotate", "true").lower()

        # Convert to rotation configuration
        if logrotate == "false":
            rotation_enabled = False
            rotation_interval = "daily"  # Default when disabled
        elif logrotate == "true":
            rotation_enabled = True
            rotation_interval = "daily"  # Default when true
        elif logrotate in ["daily", "weekly", "monthly"]:
            rotation_enabled = True
            rotation_interval = logrotate
        else:
            rotation_enabled = True
            rotation_interval = "daily"  # Fallback

        # Parse retention values and convert to days
        log_retention_days = self._parse_retention_to_days(
            settings.get("relogs", "30"), rotation_interval
        )

        xmltv_retention_days = self._parse_retention_to_days(
            settings.get("rexmltv", "7"), "daily"  # XMLTV backups are always daily
        )

        return {
            # Log rotation configuration
            "enabled": rotation_enabled,
            "interval": rotation_interval,
            "keep_files": self._days_to_keep_files(log_retention_days, rotation_interval),
            # Extended retention information
            "log_retention_days": log_retention_days,
            "xmltv_retention_days": xmltv_retention_days,
            # Original settings for logging
            "logrotate_setting": settings.get("logrotate", "true"),
            "relogs_setting": settings.get("relogs", "30"),
            "rexmltv_setting": settings.get("rexmltv", "7"),
        }

    def _parse_retention_to_days(self, retention_value: str, interval: str) -> int:
        """Convert retention setting to number of days"""
        retention_value = retention_value.strip().lower()

        # Handle numeric values (days)
        try:
            return int(retention_value)
        except ValueError:
            pass

        # Handle period-based retention
        if retention_value == "weekly":
            return 7
        elif retention_value == "monthly":
            return 30
        elif retention_value == "quarterly":
            return 90
        elif retention_value == "unlimited":
            return 0  # 0 means unlimited
        else:
            # Default based on interval
            if interval == "daily":
                return 30
            elif interval == "weekly":
                return 90  # ~3 months
            elif interval == "monthly":
                return 365  # 1 year
            else:
                return 30

    def _days_to_keep_files(self, retention_days: int, interval: str) -> int:
        """Convert retention days to number of backup files to keep"""
        if retention_days == 0:
            return 0  # Unlimited

        if interval == "daily":
            return retention_days
        elif interval == "weekly":
            return max(1, retention_days // 7)
        elif interval == "monthly":
            return max(1, retention_days // 30)
        else:
            return retention_days

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

    def log_retention_summary(self, retention_config: Dict[str, Any]):
        """Log retention policy summary for transparency"""
        log_retention = retention_config.get("log_retention_days", 30)
        xmltv_retention = retention_config.get("xmltv_retention_days", 7)

        logging.info("Cache and retention policies:")
        
        if retention_config.get("enabled", False):
            logging.info(
                "  logrotate: enabled (%s, %d days retention)",
                retention_config.get("interval", "daily"),
                log_retention,
            )
        else:
            logging.info("  logrotate: disabled")

        logging.info(
            "  rexmltv: %d days (XMLTV backup retention)", 
            xmltv_retention
        )

        # Log final cache and retention policy status for transparency
        if retention_config.get("enabled", False):
            log_desc = "unlimited" if log_retention == 0 else f"{log_retention} days"
            xmltv_desc = "unlimited" if xmltv_retention == 0 else f"{xmltv_retention} days"

            logging.debug("Unified cache and retention policy details:")
            logging.debug(
                "  logrotate: %s (%s retention)",
                retention_config.get("interval", "daily"),
                log_desc,
            )
            logging.debug("  rexmltv: %s retention", xmltv_desc)

    def get_cache_retention_days(self, settings: Dict[str, Any]) -> int:
        """Get cache retention period in days"""
        try:
            return int(settings.get("redays", "1"))
        except (ValueError, TypeError):
            logging.warning("Invalid redays setting, using default 1")
            return 1

    def should_refresh_cache(self, settings: Dict[str, Any]) -> bool:
        """Determine if cache refresh is enabled"""
        refresh_hours = self._get_refresh_hours(settings)
        return refresh_hours > 0

    def _get_refresh_hours(self, settings: Dict[str, Any]) -> int:
        """Get cache refresh hours from configuration"""
        try:
            return int(settings.get("refresh", "48"))
        except (ValueError, TypeError):
            logging.warning("Invalid refresh setting, using default 48 hours")
            return 48

    def get_refresh_hours(self, settings: Dict[str, Any]) -> int:
        """Public method to get refresh hours"""
        return self._get_refresh_hours(settings)

    def optimize_retention_settings(self, settings: Dict[str, Any]) -> Dict[str, str]:
        """
        Analyze retention settings and provide optimization recommendations
        
        Returns:
            Dict with optimization recommendations
        """
        recommendations = {}
        
        days = int(settings.get("days", "1"))
        redays = int(settings.get("redays", str(days)))
        refresh_hours = self._get_refresh_hours(settings)
        
        # Cache optimization
        if redays > days * 7:  # Much higher than needed
            recommendations["redays"] = (
                f"Consider reducing redays from {redays} to {days * 2} "
                f"for better disk usage (current setting keeps {redays - days} extra days)"
            )
            
        if refresh_hours > 72:  # Very high refresh
            recommendations["refresh"] = (
                f"Consider reducing refresh from {refresh_hours}h to 48h "
                f"for more current data (current setting may use stale data)"
            )
            
        # Retention optimization
        retention_config = self.get_retention_config(settings)
        log_retention = retention_config.get("log_retention_days", 30)
        
        if log_retention > 90:  # Very long log retention
            recommendations["relogs"] = (
                f"Consider reducing log retention from {log_retention} to 30 days "
                f"for better disk usage"
            )
            
        return recommendations
