"""
gracenote2epg.logrotate.manager - log rotation configuration/setup

Thin facade that builds the rotating handler from the unified retention
configuration and exposes startup-rotation / status helpers.
"""

import logging
from pathlib import Path

from .handler import CopyTruncateTimedRotatingFileHandler

class LogRotationManager:
    """Manages log rotation configuration and setup with unified retention policies."""

    @staticmethod
    def create_rotating_handler(log_file: Path, retention_config: dict) -> logging.Handler:
        """
        Create appropriate log handler based on unified retention configuration.

        Args:
            log_file: Path to log file
            retention_config: Unified retention configuration from config manager

        Returns:
            Configured logging handler
        """
        if not retention_config.get("enabled", False):
            # Standard file handler without rotation
            handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            logging.debug("Log rotation disabled - using standard FileHandler")
            return handler

        # Extract rotation parameters from unified config
        when = retention_config.get("interval", "daily").lower()
        backup_count = retention_config.get("keep_files", 7)

        # Map configuration values to handler parameters
        when_mapping = {"daily": "midnight", "weekly": "weekly", "monthly": "monthly"}

        handler_when = when_mapping.get(when, "midnight")

        # Create rotating handler
        handler = CopyTruncateTimedRotatingFileHandler(
            filename=str(log_file),
            when=handler_when,
            interval=1,
            backup_count=backup_count,
            encoding="utf-8",
        )

        # Log details about the unified cache and retention policy
        log_retention_days = retention_config.get("log_retention_days", 30)
        if log_retention_days == 0:
            retention_desc = "unlimited"
        else:
            retention_desc = f"{log_retention_days} days"

        logging.info(
            "Log rotation enabled: %s rotation, %s retention (%d backup files)",
            when,
            retention_desc,
            backup_count,
        )

        # Log settings used for transparency
        logging.debug("Cache and retention policy settings:")
        logging.debug("  logrotate: %s", retention_config.get("logrotate_setting", "true"))
        logging.debug("  relogs: %s", retention_config.get("relogs_setting", "30"))

        return handler

    @staticmethod
    def trigger_startup_rotation(handler) -> bool:
        """
        Manually trigger startup rotation check after logging is configured

        Args:
            handler: The log handler (should be CopyTruncateTimedRotatingFileHandler)

        Returns:
            bool: True if rotation was performed
        """
        if hasattr(handler, "_check_startup_rotation"):
            try:
                # Call the rotation check method directly
                handler._check_startup_rotation()
                return True
            except Exception as e:
                logging.warning("Error during manual startup rotation trigger: %s", str(e))
                return False
        return False

    @staticmethod
    def get_rotation_status(log_file: Path, retention_config: dict) -> dict:
        """
        Get current rotation status information with unified cache and retention details.

        Args:
            log_file: Path to log file
            retention_config: Unified cache and retention configuration

        Returns:
            Dictionary with rotation status information
        """
        if not retention_config.get("enabled", False):
            return {"enabled": False}

        status = {
            "enabled": True,
            "interval": retention_config.get("interval", "daily"),
            "keep_files": retention_config.get("keep_files", 7),
            "log_retention_days": retention_config.get("log_retention_days", 30),
            "xmltv_retention_days": retention_config.get("xmltv_retention_days", 7),
            "current_log_size": 0,
            "backup_files_count": 0,
            "week_start_day": "Sunday",  # Document that we use Sunday as week start
            # Include original settings for reference
            "logrotate_setting": retention_config.get("logrotate_setting", "true"),
            "relogs_setting": retention_config.get("relogs_setting", "30"),
            "rexmltv_setting": retention_config.get("rexmltv_setting", "7"),
        }

        # Get current log file size
        if log_file.exists():
            status["current_log_size"] = log_file.stat().st_size

        # Count backup files
        try:
            log_dir = log_file.parent
            log_basename = log_file.name
            backup_count = 0

            for file_path in log_dir.glob(f"{log_basename}.*"):
                if str(file_path) != str(log_file):
                    backup_count += 1

            status["backup_files_count"] = backup_count

        except Exception:
            status["backup_files_count"] = 0

        return status
