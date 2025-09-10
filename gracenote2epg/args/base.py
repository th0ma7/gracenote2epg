"""
Main argument parser module for gracenote2epg

Orchestrates argument parsing, validation, and special actions handling.
Provides baseline XMLTV grabber capabilities and lineup testing functionality.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .validator import ArgumentValidator
from .location import LocationProcessor
from .path_manager import PathManager
from .systems import SystemDetector


class ArgumentParser:
    """Command line argument parser for gracenote2epg"""
    
    def __init__(self):
        self.parser = self._create_parser()
        self.validator = ArgumentValidator()
        self.location_processor = LocationProcessor()
        self.path_manager = PathManager()
    
    def _create_parser(self):
        """Create the argument parser with all options"""
        parser = argparse.ArgumentParser(
            prog="gracenote2epg",
            description="North America TV guide grabber (gracenote.com)",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_epilog_text()
        )
        
        # XMLTV baseline capabilities
        parser.add_argument(
            "--description", "-d", action="store_true", 
            help="Show grabber description and exit"
        )
        
        parser.add_argument(
            "--version", "-v", action="store_true", 
            help="Show version and exit"
        )
        
        parser.add_argument(
            "--capabilities", "-c", action="store_true", 
            help="Show capabilities and exit"
        )
        
        # LineupID detection and testing
        parser.add_argument(
            "--show-lineup",
            action="store_true",
            help="Show auto-detected lineupID for configured postal/ZIP code and exit (testing mode)",
        )
        
        # Log level selection
        level_group = parser.add_mutually_exclusive_group()
        level_group.add_argument(
            "--warning", "-w", action="store_true", 
            help="Only warnings and errors to file"
        )
        
        level_group.add_argument(
            "--debug", action="store_true", 
            help="All debug information to file (very verbose)"
        )
        
        # Console output control
        console_group = parser.add_mutually_exclusive_group()
        console_group.add_argument(
            "--console",
            action="store_true",
            help="Display active log level to console (can combine with --warning/--debug)",
        )
        
        console_group.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="No console output except XML, logs to file only",
        )
        
        # Output control
        parser.add_argument(
            "--output", "-o", type=Path, 
            help="Redirect XMLTV output to specified file"
        )
        
        # Guide parameters
        parser.add_argument(
            "--days", type=int, 
            help="Number of days to download (1-14)"
        )
        
        parser.add_argument(
            "--offset", type=int, 
            help="Start with data for day today plus X days"
        )
        
        # Cache refresh control
        refresh_group = parser.add_mutually_exclusive_group()
        refresh_group.add_argument(
            "--norefresh",
            action="store_true",
            help="Don't refresh cached blocks (use all cached data, fastest)",
        )
        
        refresh_group.add_argument(
            "--refresh",
            type=int,
            metavar="HOURS",
            help="Refresh blocks from the first HOURS hours (default: 48, range: 0-168)",
        )
        
        # Language detection
        parser.add_argument(
            "--langdetect",
            type=str,
            choices=["true", "false"],
            help="Enable/disable automatic language detection (requires langdetect library)",
        )
        
        # Lineup configuration
        parser.add_argument(
            "--lineupid",
            type=str,
            help="Override lineup configuration (auto, CAN-OTAJ3B1M4, CAN-0005993-X, etc.)",
        )
        
        # Location codes
        location_group = parser.add_mutually_exclusive_group()
        location_group.add_argument(
            "--zip", type=str, 
            help="US ZIP code (5 digits)"
        )
        
        location_group.add_argument(
            "--postal", type=str, 
            help="Canadian postal code (A1A 1A1)"
        )
        
        location_group.add_argument(
            "--code", type=str, 
            help="US ZIP or Canadian postal code"
        )
        
        # Configuration
        parser.add_argument(
            "--config-file", type=Path, 
            help="Configuration file path"
        )
        
        parser.add_argument(
            "--basedir", type=Path, 
            help="Base directory for config, cache, and logs"
        )
        
        return parser
    
    def _get_epilog_text(self):
        """Get the epilog help text"""
        return """
Examples:
  gracenote2epg --capabilities
  gracenote2epg --days 7 --zip 92101
  gracenote2epg --days 3 --postal J3B1M4 --warning --console --output guide.xml
  gracenote2epg --show-lineup --postal J3B1M4                  # Test lineup detection
  gracenote2epg --show-lineup --zip 90210                      # Test US ZIP code
  gracenote2epg --show-lineup --code "J3B 1M4"                 # Test with space
  gracenote2epg --show-lineup --zip 90210 --debug              # Detailed debug output
  gracenote2epg --days 7 --zip 92101 --langdetect false
  gracenote2epg --days 7 --zip 92101 --lineupid auto           # Auto-detection with required ZIP
  gracenote2epg --days 7 --lineupid CAN-OTAJ3B1M4              # Deduces postal J3B1M4
  gracenote2epg --days 7 --lineupid USA-OTA90210               # Deduces ZIP 90210
  gracenote2epg --days 7 --zip 92101 --lineupid CAN-OTAJ3B1M4  # Error: inconsistent
  gracenote2epg --days 7 --zip 92101 --norefresh
  gracenote2epg --days 7 --zip 92101 --refresh 24

Testing and Validation:
  --show-lineup           Show auto-detected lineup parameters and validation URL
                          Must be combined with --zip, --postal, or --code
                          Useful for testing different postal/ZIP codes before configuration
                          Exits immediately after showing results (no download)
                          Use --debug for detailed technical information

Configuration:
  Default config: ~/gracenote2epg/conf/gracenote2epg.xml
  Default cache:  ~/gracenote2epg/cache/
  Default logs:   ~/gracenote2epg/log/

Logging Levels:
  (default)       Info, warnings and errors to file only, XML to console
  --warning       Only warnings and errors to file, XML to console
  --debug         All debug information to file only, XML to console
  --console       Display active log level to console (can combine with --warning/--debug)
  --quiet         No console output except XML, logs to file only

Cache Refresh Options:
  --norefresh     Don't refresh cached blocks (use all cached data)
  --refresh XX    Refresh blocks from the first XX hours (default: 48)

Language Detection:
  --langdetect    Enable/disable automatic language detection (requires langdetect library)
                  Default: auto-enabled if langdetect is installed, disabled otherwise

LineupID Configuration:
  --lineupid      Override lineup configuration from command line
                  Examples: auto, CAN-OTAJ3B1M4, CAN-0005993-X
                  Supports all formats: auto-detection, tvtv.com format, complete provider format
                  Location extraction: OTA lineups automatically provide postal/ZIP codes
                  (e.g., CAN-OTAJ3B1M4 provides postal code J3B1M4)

Location Intelligence:
  When using OTA lineups, postal/ZIP codes are automatically extracted:
  - CAN-OTAJ3B1M4 → postal code J3B1M4 (Canada)
  - USA-OTA90210 → ZIP code 90210 (United States)
  If both --lineupid and --zip/--postal are provided, they must be consistent

LineupID Auto-Detection:
  When enabled (auto_lineup=true), gracenote2epg automatically generates
  lineupID parameters compatible with zap2xml format:
  - Canada: CAN-OTAJ3B1M4-DEFAULT (from postal code J3B1M4)
  - USA:    USA-OTA90210-DEFAULT   (from ZIP code 90210)
        """
    
    def parse_args(self, args=None):
        """Parse command line arguments with validation"""
        args = self.parser.parse_args(args)
        
        # Handle special actions that exit immediately
        if self._handle_special_actions(args):
            sys.exit(0)
        
        # Handle --show-lineup
        if self._handle_show_lineup(args):
            sys.exit(0)
        
        # Validate arguments
        self._validate_args(args)
        
        # Process lineup and location
        self._process_lineup_and_location(args)
        
        # Normalize options
        self._normalize_options(args)
        
        return args
    
    def _handle_special_actions(self, args) -> bool:
        """Handle special actions that exit immediately"""
        if args.description:
            print("North America (tvlistings.gracenote.com using gracenote2epg)")
            return True
            
        if args.version:
            from .. import __version__
            print(__version__)
            return True
            
        if args.capabilities:
            print("baseline")
            return True
            
        return False
    
    def _handle_show_lineup(self, args) -> bool:
        """Handle --show-lineup option"""
        if not args.show_lineup:
            return False
            
        location_code = args.zip or args.postal or args.code
        if not location_code:
            self.parser.error("--show-lineup requires one of: --zip, --postal, or --code")
        
        # Delegated to ConfigManager for the lineup logic
        from ..config import ConfigManager
        temp_config = ConfigManager(Path("temp"))
        debug_mode = args.debug if hasattr(args, "debug") else False
        
        if not temp_config.display_lineup_detection_test(location_code, debug_mode):
            sys.exit(1)
            
        return True
    
    def _validate_args(self, args):
        """Validate argument values"""
        errors = []
        
        # Validate days
        valid, error = self.validator.validate_days(args.days)
        if not valid:
            errors.append(error)
        
        # Validate offset
        valid, error = self.validator.validate_offset(args.offset)
        if not valid:
            errors.append(error)
        
        # Validate refresh
        valid, error = self.validator.validate_refresh(args.refresh)
        if not valid:
            errors.append(error)
        
        # Validate lineupid
        valid, error = self.validator.validate_lineupid(args.lineupid)
        if not valid:
            errors.append(error)
        
        # If any errors, report them
        if errors:
            for error in errors:
                self.parser.error(error)
    
    def _process_lineup_and_location(self, args):
        """Process lineup and location arguments"""
        try:
            location_code, metadata = self.location_processor.process_lineup_and_location(args)
            
            # Store results in args
            args.location_code = location_code
            args.location_source = metadata['location_source']
            args.original_lineupid = metadata['original_lineupid']
            args.extracted_location = metadata['extracted_location']
            
            # Clean up individual fields
            del args.zip, args.postal, args.code
            
        except ValueError as e:
            self.parser.error(str(e))
    
    def _normalize_options(self, args):
        """Normalize various options"""
        # Normalize langdetect
        args.langdetect = self.location_processor.normalize_langdetect(args.langdetect)
        
        # Normalize refresh
        args.refresh_hours = self.location_processor.normalize_refresh(args)
        
        # Clean up individual refresh fields
        del args.norefresh
        if hasattr(args, 'refresh'):
            del args.refresh
    
    def get_logging_config(self, args):
        """Determine logging configuration from arguments"""
        config = {
            "level": "default",
            "console": False,
            "quiet": False,
        }
        
        if args.debug:
            config["level"] = "debug"
        elif args.warning:
            config["level"] = "warning"
        
        if args.console:
            config["console"] = True
        elif args.quiet:
            config["quiet"] = True
            
        return config
    
    def get_system_defaults(self):
        """Get system-specific default directories"""
        return self.path_manager.get_system_defaults()
    
    def create_directories_with_proper_permissions(self):
        """Create required directories with proper permissions"""
        defaults = self.get_system_defaults()
        self.path_manager.create_directories(defaults)
