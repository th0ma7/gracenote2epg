#!/usr/bin/env python3
"""
gracenote2epg - North America TV Guide Grabber

A modular implementation:
- downloader/: HTTP operations and caching
- parser/: Pure data parsing logic
- main.py: Application orchestration and flow
"""

import logging
import sys
import time
from pathlib import Path

# Specific imports
from .args import ArgumentParser
from .config import ConfigManager
from .parser import DataParser
from .tvheadend import TvheadendClient
from .utils import CacheManager
from .xmltv import XmltvGenerator
from .logrotate import LogRotationManager

# Package version
from . import __version__


def check_rotation_status(log_file: Path, retention_config: dict):
    """Check and report any rotation that occurred during startup"""
    if not retention_config.get("enabled", False):
        return

    try:
        log_dir = log_file.parent
        log_basename = log_file.name

        # Find backup files created recently (last 10 minutes)
        recent_cutoff = time.time() - 600  # 10 minutes ago
        recent_backups = []

        for backup_file in log_dir.glob(f"{log_basename}.*"):
            if str(backup_file) != str(log_file):
                try:
                    if backup_file.stat().st_mtime > recent_cutoff:
                        recent_backups.append(backup_file)
                except Exception:
                    continue

        if recent_backups:
            logging.info("Log Rotation Report:")
            logging.info(
                "  Recent rotation detected - %d backup files created:", len(recent_backups)
            )

            for backup in sorted(recent_backups):
                try:
                    size_mb = backup.stat().st_size / (1024 * 1024)
                    logging.info(
                        "    Created backup: %s (%.1f MB) - %s rotation",
                        backup.name,
                        size_mb,
                        retention_config.get("interval", "unknown"),
                    )
                except Exception:
                    logging.info("    Created backup: %s", backup.name)

            current_size_mb = log_file.stat().st_size / (1024 * 1024) if log_file.exists() else 0
            logging.info(
                "    Current log: %s (%.1f MB) - contains current %s only",
                log_basename,
                current_size_mb,
                retention_config.get("interval", "period"),
            )
            logging.info("  Log rotation completed successfully")
        else:
            logging.debug("No recent log rotation detected")

    except Exception as e:
        logging.debug("Error checking rotation status: %s", str(e))


def setup_logging(logging_config: dict, log_file: Path, retention_config: dict):
    """Setup logging configuration with unified retention policy"""
    # Create log directory
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Determine file logging level based on mode
    if logging_config["level"] == "warning":
        file_level = logging.WARNING
    elif logging_config["level"] == "debug":
        file_level = logging.DEBUG
    else:  # default
        file_level = logging.INFO

    # Create rotating file handler using unified retention config
    file_handler = LogRotationManager.create_rotating_handler(log_file, retention_config)
    file_handler.setLevel(file_level)

    # Set file formatter
    file_formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y/%m/%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(file_level)

    # Clear any existing handlers and add file handler
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)

    # Console logging only if --console is specified (and not --quiet)
    # IMPORTANT: Use stderr to avoid polluting XML output on stdout
    if logging_config["console"] and not logging_config["quiet"]:
        console_handler = logging.StreamHandler(sys.stderr)  # Force stderr for console output

        # Set console level to match file level
        console_handler.setLevel(file_level)

        formatter = logging.Formatter("%(levelname)s: %(message)s")
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Log unified retention status for transparency
    if retention_config.get("enabled", False):
        rotation_status = LogRotationManager.get_rotation_status(log_file, retention_config)

        log_retention = retention_config.get("log_retention_days", 30)
        xmltv_retention = retention_config.get("xmltv_retention_days", 7)

        # Log details about unified retention policy
        logging.debug("Unified retention policy:")
        logging.debug(
            "  Log rotation: %s (%s interval, %d days retention)",
            "enabled" if retention_config.get("enabled") else "disabled",
            retention_config.get("interval", "daily"),
            log_retention,
        )
        logging.debug("  XMLTV backups: %d days retention", xmltv_retention)
        logging.debug(
            "  Current log size: %d bytes, backup files: %d",
            rotation_status.get("current_log_size", 0),
            rotation_status.get("backup_files_count", 0),
        )

    # Return the file handler so it can be used for manual rotation triggering
    return file_handler


def log_command_line_processing(args):
    """Log command line argument processing for better debugging"""
    logging.info("Command line arguments processed:")

    # Log zipcode processing - only if passed explicitly as argument
    zipcode_from_extraction = False
    if hasattr(args, "location_code") and args.location_code:
        source = getattr(args, "location_source", "unknown")
        if source == "explicit":
            # Only log if passed explicitly by user
            logging.info("  zipcode: %s (explicit)", args.location_code)
        elif source == "extracted":
            # Track extraction but don't log - it's not a command line argument
            zipcode_from_extraction = True
        # Don't log if source is unknown

    # Log lineupid processing
    if hasattr(args, "original_lineupid") and args.original_lineupid:
        if zipcode_from_extraction:
            # Don't repeat the extraction info since it's already mentioned in zipcode
            logging.info("  lineupid: %s", args.original_lineupid)
        else:
            extracted = getattr(args, "extracted_location", None)
            if extracted:
                # Normalize postal code display (remove spaces)
                normalized_extracted = extracted.replace(" ", "")
                logging.info(
                    "  lineupid: %s (contains zipcode %s)",
                    args.original_lineupid,
                    normalized_extracted,
                )
            else:
                logging.info("  lineupid: %s", args.original_lineupid)

    # Log other parameters
    if args.days:
        logging.info("  days: %d", args.days)
    if hasattr(args, "refresh_hours") and args.refresh_hours is not None:
        if args.refresh_hours == 0:
            logging.info("  refresh: disabled (--norefresh)")
        else:
            logging.info("  refresh: %d hours", args.refresh_hours)
    if args.langdetect is not None:
        logging.info("  langdetect: %s", args.langdetect)


def main():
    """Main application entry point"""
    python_start_time = time.time()

    try:
        # Parse command line arguments
        arg_parser = ArgumentParser()
        args = arg_parser.parse_args()

        # Get system defaults
        defaults = arg_parser.get_system_defaults()

        # Override defaults with command line arguments
        config_file = args.config_file or defaults["config_file"]
        xmltv_file = args.output or defaults["xmltv_file"]
        log_file = defaults["log_file"]

        # Ensure directories exist
        arg_parser.create_directories_with_proper_permissions()

        # Load and validate configuration
        config_manager = ConfigManager(config_file)
        config = config_manager.load_config(
            location_code=getattr(args, "location_code", None),
            location_source=getattr(args, "location_source", "explicit"),
            location_extracted_from=getattr(args, "original_lineupid", None),
            days=args.days,
            langdetect=args.langdetect,
            refresh_hours=getattr(args, "refresh_hours", None),
            lineupid=getattr(args, "original_lineupid", None),
        )

        # Get unified retention configuration
        retention_config = config_manager.get_retention_config()

        # Setup logging with unified retention policy
        logging_config = arg_parser.get_logging_config(args)
        file_handler = setup_logging(logging_config, log_file, retention_config)

        # FIRST: Check for log rotation (this may truncate/rebuild the log file)
        if retention_config.get("enabled", False) and hasattr(
            file_handler, "_check_startup_rotation"
        ):
            try:
                logging.info("Checking for startup log rotation...")
                file_handler._check_startup_rotation()
                logging.info("Startup rotation check completed")
            except Exception as e:
                logging.warning("Error during startup rotation check: %s", str(e))

        # Report any rotation that occurred (includes its own separator if needed)
        check_rotation_status(log_file, retention_config)

        # NOW start the normal session logging with consistent separator
        logging.info("=" * 60)
        logging.info("gracenote2epg session started - Version %s", __version__)

        if logging_config["level"] == "debug":
            logging.info("Debug logging enabled - all debug information will be logged")
        if logging_config["console"]:
            logging.info("Console logging enabled - logs also displayed on stderr")

        # Log command line processing BEFORE config summary
        log_command_line_processing(args)

        # Log configuration summary
        logging.info("Configuration loaded from: %s", config_file)
        config_manager.log_config_summary()

        # Initialize components with new architecture
        cache_manager = CacheManager(defaults["cache_dir"])

        # Setup TVheadend client if enabled
        tvh_client = None
        if config.get("tvhoff", False):
            tvh_client = TvheadendClient(
                url=config.get("tvhurl", "127.0.0.1"),
                port=config.get("tvhport", "9981"),
                username=config.get("usern") or None,
                password=config.get("passw") or None,
            )

            # Fetch channels if TVheadend matching is enabled
            if config.get("tvhmatch", False):
                tvh_client.fetch_channels()
                tvh_client.log_filtering_summary(
                    explicit_station_list=config_manager.get_station_list(),
                    use_tvh_matching=config.get("tvhmatch", False),
                )

        # Calculate guide parameters
        days = int(config.get("days", 1))
        offset = float(getattr(args, "offset", 0) or 0)
        day_hours = days * 8  # 8 three-hour blocks per day

        # Get refresh hours from configuration/command line
        refresh_hours = config_manager.get_refresh_hours()

        # Calculate start time
        from datetime import datetime

        now = datetime.now().replace(microsecond=0, second=0, minute=0)
        grid_time_start = int(time.mktime(now.timetuple())) + int(offset * 86400)

        # Log guide parameters
        logging.info("TV Guide duration: %s days", days)

        if offset > 1:
            logging.info("TV Guide Start: %i [offset: %i days]", grid_time_start, int(offset))
        elif offset == 1:
            logging.info("TV Guide Start: %i [offset: %i day]", grid_time_start, int(offset))
        else:
            logging.info("TV Guide Start: %i", grid_time_start)

        logging.info("Caching directory: %s", defaults["cache_dir"])

        # Log cache refresh configuration
        if refresh_hours == 0:
            logging.info("Cache refresh: disabled (--norefresh or refresh=0)")
        else:
            logging.info(
                "Cache refresh: %d hours (first %d hours will be re-downloaded)",
                refresh_hours,
                refresh_hours,
            )

        # Perform initial cache cleanup with unified retention policy
        xmltv_retention_days = retention_config.get("xmltv_retention_days", 7)
        cache_manager.perform_initial_cleanup(
            grid_time_start, days, xmltv_file, xmltv_retention_days
        )

        # Download and parse guide data
        with DataParser(cache_manager, tvh_client) as data_parser:
            # Download and parse guide blocks
            guide_success = data_parser.download_and_parse_guide(
                grid_time_start=grid_time_start,
                day_hours=day_hours,
                config_manager=config_manager,
                refresh_hours=refresh_hours,
            )

            if not guide_success:
                logging.warning("Guide download had issues, but continuing with available data")

            # Clean show cache now that we have parsed episodes
            active_series = data_parser.get_active_series_list()
            cache_manager.perform_show_cleanup(active_series)

            # Download extended details if needed
            if config_manager.needs_extended_download():
                extended_success = data_parser.download_and_parse_series_details()
                if not extended_success:
                    logging.warning(
                        "Extended details download had issues, using basic descriptions"
                    )

            # Generate XMLTV
            xmltv_generator = XmltvGenerator(cache_manager)
            xmltv_success = xmltv_generator.generate_xmltv(
                schedule=data_parser.get_schedule(), config=config, xmltv_file=xmltv_file
            )

            if not xmltv_success:
                logging.error("XMLTV generation failed")
                return 1

            # Final cleanup
            final_active_series = data_parser.get_active_series_list()
            if final_active_series:
                cache_manager.clean_show_cache(final_active_series)
                logging.info(
                    "Final show cache verification: keeping %d active series",
                    len(final_active_series),
                )

            # Final statistics
            time_run = round(time.time() - python_start_time, 2)
            logging.info("gracenote2epg completed in %s seconds", time_run)
            logging.info(
                "%d Stations and %d Episodes written to xmltv.xml file",
                xmltv_generator.station_count,
                xmltv_generator.episode_count,
            )

            # Comprehensive download statistics
            dl_stats = data_parser.get_downloader_statistics()
            logging.info("Final download statistics:")
            logging.info("  Guide blocks: %d downloaded, %d cached, %d failed", 
                        dl_stats["guide"]["downloaded"],
                        dl_stats["guide"]["cached"], 
                        dl_stats["guide"]["failed"])
            logging.info("  Series details: %d downloaded, %d cached, %d failed",
                        dl_stats["series"]["downloaded"],
                        dl_stats["series"]["cached"],
                        dl_stats["series"]["failed"])
            logging.info("  HTTP requests: %d total, %d WAF blocks, %.2fs final delay",
                        dl_stats["http_engine"]["total_requests"],
                        dl_stats["http_engine"]["waf_blocks"],
                        dl_stats["http_engine"]["current_delay"])

            # Log final cache and retention policy status for transparency
            if retention_config.get("enabled", False):
                log_retention = retention_config.get("log_retention_days", 30)
                xmltv_retention = retention_config.get("xmltv_retention_days", 7)

                log_desc = "unlimited" if log_retention == 0 else f"{log_retention} days"
                xmltv_desc = "unlimited" if xmltv_retention == 0 else f"{xmltv_retention} days"

                logging.info("Unified cache and retention policy applied:")
                logging.info(
                    "  logrotate: %s (%s retention)",
                    retention_config.get("interval", "daily"),
                    log_desc,
                )
                logging.info("  rexmltv: %s retention", xmltv_desc)

            # Output XMLTV to stdout ONLY if not redirected to file
            # XMLTV standard: XML goes to stdout, logs go to stderr or file
            if args.output is None:
                # No --output specified, display XML on stdout
                try:
                    with open(xmltv_file, "r", encoding="utf-8") as f:
                        print(f.read(), end="")  # end='' to avoid extra blank line
                except Exception as e:
                    logging.error("Could not output XMLTV to stdout: %s", str(e))
                    return 1
            else:
                # --output specified, XML is in the file
                logging.info("XMLTV output written to: %s", args.output)

        logging.info("Script completed successfully")
        logging.info("gracenote2epg session ended successfully")
        logging.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        return 1
    except Exception as e:
        logging.exception("Critical error: %s", str(e))
        logging.info("gracenote2epg session ended with error")
        logging.info("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
