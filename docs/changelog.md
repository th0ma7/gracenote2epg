# Changelog

All notable changes to gracenote2epg are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2025-09-09

### Added
- **Geographic Resolution**: Intelligent lineup URL generation with automatic location resolution
  - New `gracenote2epg_lineup.py` module with `LineupManager` and `Geocoder` classes
  - Optional `pgeocode` integration for automatic city/province resolution from postal codes
  - Dynamic tvtv.com URL generation based on actual geographic locations
  - Smart fallback to manual lookup instructions when automatic resolution fails
- **Enhanced --show-lineup Output**: Improved lineup testing with geographic status indicators
  - ✅ Status indicator when location is automatically resolved
  - ⚠️ Warning when manual lookup is required

### Fixed
- **--show-lineup URLs**: Fixed non-functional validation URLs caused by hardcoded city names

### Technical Details
- **Optional Dependency**: `pgeocode>=0.4.0` for enhanced geographic resolution
  - Graceful degradation when pgeocode is not installed
  - Manual lookup instructions always provided as fallback
  - No breaking changes for existing installations
- **Debug Output**: Enhanced debugging support for `--show-lineup --debug`
  - Geographic resolution status and details
  - City/province normalization process
  - Clear indication of automatic vs manual resolution paths

### Installation
```bash
# Install with geographic resolution support (recommended)
pip install gracenote2epg[full]

# Or install geographic resolution only
pip install gracenote2epg[geocoding]

# Existing installations continue to work without pgeocode
pip install gracenote2epg  # Basic functionality maintained
```

## [1.5.5] - 2025-09-06

### Fixed
- **Show Lineup**:
   - Fix `--show-lineup` where timestamp was fixed leading to non-functional URL.
   - Refactor display functions to eliminate code duplication.
- **No Refresh**: Fix `--norefresh` where `'refresh_hours == 0'` was not handled leading to first 3h guide block being downloaded instead of using the cache as expected.

## [1.5.4] - 2025-08-27

### Fixed
- **Extended Details**: Fixed issue where `xdetails=true` with `xdesc=false` incorrectly omitted credits, extended categories, and series images.

## [1.5.3] - 2025-08-25

### Fixed
- **Extended Description**: Fixed DTD conformance:
  Before (non-compliant) :
  ```xml
  <credits>
      <actor>John Doe</actor>
      <presenter>Host Name</presenter>  <!-- ❌ Wrong order -->
      <actor>Jane Smith</actor>         <!-- ❌ Actors mixed -->
  </credits>
  ```
  After (DTD compliant) :
  ```xml
  <credits>
      <actor>John Doe</actor>           <!-- ✅ Grouped actors -->
      <actor>Jane Smith</actor>
      <presenter>Host Name</presenter>  <!-- ✅ Presenter after -->
  </credits>
  ```

### Changed
- **Documentation**: Removal of unecessary details related to xmltv validation.

## [1.5.2] - 2025-08-23

### Fixed
- **Extended Description**: Fixed to achieve expected behavior 
  - `xdesc=false`: Use basic guide description WITHOUT any enhanced info
  - `xdesc=true`: Use extended series description (if available) WITH enhanced info (e.g. `• 2023 | Rated: TV-14 | NEW | CC`)

### Changed
- **Documentation**: Many additions and fixes to configuration.md, development.md, installation.md and tvheadend.md

## [1.5.1] - 2025-08-21

### Fixed
- **Documentation Links**: Fixed broken documentation links in README.md when viewed on PyPI
  - Changed all relative links to absolute GitHub URLs (e.g., `docs/installation.md` → `https://github.com/th0ma7/gracenote2epg/blob/main/docs/installation.md`)

### Changed
- **README.md**: Improved structure and removed redundant installation sections for cleaner PyPI display

**Note**: This is a documentation-only release. No functional changes to gracenote2epg itself.

## [1.5] - 2025-08-21

### Added
- **Development Scripts**: Comprehensive development workflow automation
  - New `scripts/dev-helper.bash` - Development workflow assistant with autofix, format, lint commands
  - New `scripts/test-distribution.bash` - Automated distribution testing and validation
  - Complete `scripts/README.md` documentation with usage examples and troubleshooting
- **Makefile Integration**: Root-level Makefile for convenient development task automation
  - `make all` - Complete development workflow (clean, autofix, format, lint, test)
  - `make autofix` - Auto-fix imports and common code issues with autoflake
  - `make format` - Code formatting with black (100-character line length)
  - `make lint` - Code linting with flake8 (permissive configuration)
  - `make test-basic` / `make test-full` - Distribution testing shortcuts
  - `make check-deps` - Development dependency validation
- **Code Quality Tools**: Automated code formatting and linting pipeline
  - **autoflake** integration for automatic import cleanup and unused variable removal
  - **black** formatting with 100-character line length for better readability
  - **flake8** linting with project-specific configuration (`.flake8`)
  - Smart dependency detection (handles Ubuntu apt packages vs pip packages)
- **Enhanced Development Documentation**: Complete development workflow documentation
  - Updated `docs/development.md` with Ubuntu/Debian-specific installation instructions
  - Development tools troubleshooting (flake8-black conflicts, mixed installations)
  - Clear separation between Makefile (primary interface) and scripts (advanced usage)
  - Progressive disclosure: simple commands first, detailed options in scripts documentation

### Changed
- **Version Management**: Centralized version system with single source of truth
  - Version now managed exclusively in `gracenote2epg/__init__.py`
  - `setup.py` automatically reads version from `__init__.py` (eliminates version drift)
  - Simplified release process requires updating only one file
- **Code Standards**: Project-wide code quality improvements
  - All Python code now black-formatted with 100-character line length
  - flake8-compliant with permissive configuration for development workflow
  - Automated removal of unused imports and variables across codebase
  - Consistent code style throughout the project
- **Documentation Structure**: Improved documentation hierarchy and organization
  - `docs/development.md` focuses on concepts, workflow, and Makefile usage
  - `scripts/README.md` contains detailed technical documentation for direct script usage
  - Clear guidance on when to use Makefile vs direct script invocation
  - Project structure documentation now includes Makefile
- **Development Workflow**: Streamlined development process
  - `make all` provides complete validation pipeline for commits
  - Safe auto-fixing that preserves valid f-strings and important code patterns
  - Integration between system packages (Ubuntu apt) and pip packages
  - Better error messages and conflict detection for development tools

### Fixed
- **Distribution Packaging**: Resolved locale files missing from distributions (carried over from v1.4.x issues)
  - Translation `.po` files now correctly included in both wheel and source distributions
  - `MANIFEST.in` properly configured to include `locales/` directory
  - Distribution testing scripts validate locale file inclusion automatically
  - Fixes translation system functionality in installed packages
- **Development Environment Issues**: Comprehensive development setup improvements
  - Automatic detection and warning for problematic packages (e.g., `flake8-black`)
  - Clear installation instructions for Ubuntu/Debian vs pip-only environments
  - Resolved BLK100 errors caused by flake8-black plugin conflicts
  - Better handling of mixed system/pip package installations

### Developer Experience
- **Simplified Onboarding**: New developers can start with `make all`
- **Automated Quality**: Code quality checks happen automatically before commits
- **Clear Documentation**: Progressive disclosure from simple commands to advanced options
- **Platform Support**: Tested on Ubuntu 22.04/24.04 with both apt and pip packages
- **CI/CD Ready**: Scripts designed for integration with GitHub Actions and other CI systems

## [1.4.1] - 2025-08-20

### Added
- Complete documentation refactoring with new structure under `docs/`
- New comprehensive TVheadend integration guide (`docs/tvheadend.md`)
- Installation guide with platform-specific instructions
- Development guide with technical validation procedures

### Changed
- Renamed repository from `tv_grab_gracenote2epg` to `gracenote2epg`
- Restructured documentation: moved files to `docs/` directory
- Renamed documentation files for clarity:
  - `LINEUPID.md` → `docs/lineup-configuration.md`
  - `PACKAGING.md` → `docs/development.md`
  - `CACHE_RETENTION_POLICIES.md` → `docs/cache-retention.md`
  - `LOG_ROTATION.md` → `docs/log-rotation.md`
- Separated TVheadend-specific guidance from general troubleshooting
- Updated installation instructions for GitHub-based installation (PyPI pending)

### Fixed
- Updated all documentation links to reflect new structure
- Corrected platform-specific installation commands
- Updated Synology installation instructions to focus on TVheadend environment
- Updated MANIFEST.in and setup.py for new documentation structure

## [1.4] - Previous Release
### Added
- **Simplified Lineup Configuration**: Single `lineupid` setting replaces complex multi-parameter setup
  - Auto-detection with `lineupid=auto` for Over-the-Air (OTA) channels
  - Direct copy from tvtv.com URLs (auto-normalized to API format)
  - Complete provider format support for Cable/Satellite (e.g., `CAN-0005993-X`)
  - Automatic device type detection (`-` for OTA, `X` for Cable/Satellite)
  - Backward compatibility with legacy configuration (automatic migration)
- **Lineup Testing Tool**: New `--show-lineup` command-line option for configuration validation
  - Test postal/ZIP codes before configuration: `--show-lineup --zip 92101`
  - Simplified output mode for quick verification
  - Debug mode with detailed technical information: `--show-lineup --zip 92101 --debug`
  - Manual validation URLs and step-by-step instructions
  - Complete API URL generation for manual testing
- **Enhanced Command-Line Interface**: New `--lineupid` option for direct lineup specification
  - Override configuration lineup from command line: `--lineupid CAN-OTAJ3B1M4`
  - Consistent with other command-line options (`--zip`, `--postal`, `--langdetect`)
  - Supports all lineup formats (auto, tvtv.com format, complete provider format)
  - **Smart Location Intelligence**: Automatic postal/ZIP extraction from OTA lineups
    - `--lineupid CAN-OTAJ3B1M4` automatically provides postal code `J3B1M4`
    - `--lineupid USA-OTA90210` automatically provides ZIP code `90210`
    - Consistency validation when both lineup and location are explicitly provided
    - Eliminates need to specify both parameters for OTA configurations
- **Unified Cache & Retention Policies**: Streamlined configuration for all temporary data management
  - Single configuration section for cache, logs, and XMLTV backup retention
  - Consistent behavior patterns across all retention policies
  - Flexible retention values: days (numbers), periods (weekly/monthly/quarterly), or unlimited
  - Smart defaults based on system usage patterns
  - Unified validation and error handling for all retention settings
- **Intelligent Log Rotation**: Multi-period rotation with content analysis for daily/weekly/monthly modes
  - Analyzes actual log content instead of file timestamps for accurate rotation decisions
  - Separates complete periods into individual backup files (e.g., W31, W32, W33)
  - Visible rotation messages in logs with clear reporting
  - Compatible with `tail -f` and log monitoring tools using copytruncate strategy
  - Integrated with unified retention policy system
- **Enhanced XMLTV Backup Management**: Intelligent backup retention with unified configuration
  - Configurable retention periods using same syntax as log retention
  - Automatic cleanup of old XMLTV backups based on retention policy
  - Support for days, periods, or unlimited retention
  - Clear reporting of backup creation and cleanup activities
- **Python wheel compatible**: Now allows generating a python wheel redistributable package
- **Comprehensive packaging**: Both wheel (.whl) and source (.tar.gz) distributions
- **Multiple command interfaces**: gracenote2epg, tv_grab_gracenote2epg, and module execution

### Changed
- **Configuration Format**: Updated to version 5 with simplified lineup settings and unified retention policies
  - Single `lineupid` parameter replaces `auto_lineup`, `lineupcode`, `lineup`, and `device`
  - Unified cache and retention section replaces scattered retention settings
  - Automatic migration from legacy configuration formats with backup creation
  - Cleaner configuration file structure with better organization and grouped sections
- **Logging Optimization**: Reduced duplication in lineup configuration logging
  - Single detailed report in configuration summary instead of multiple repetitive messages
  - Debug-level logging for internal lineup operations to reduce log noise
  - Simplified final summary with essential information only
  - Enhanced reporting of unified cache and retention policy status
- **Enhanced documentation**: Separated user and developer documentation with comprehensive guides
  - New LINEUPID.md for detailed lineup configuration instructions
  - New CACHE_RETENTION_POLICIES.md for unified cache and retention system documentation
  - Updated README.md with lineup testing examples and validation procedures
  - Updated LOG_ROTATION.md with unified system integration details
  - Improved troubleshooting section with specific lineup-related solutions

### Fixed
- **Configuration Migration**: Robust handling of legacy configuration formats
  - Automatic detection and migration of deprecated settings
  - Preserves user customizations while updating to new format
  - Clear migration logging with backup file creation
- **Lineup Detection**: Improved reliability of automatic lineup detection
  - Better error handling for invalid postal/ZIP codes
  - Enhanced validation of lineup formats from tvtv.com
  - Fallback mechanisms for edge cases and malformed inputs
- **Cache Management**: Enhanced cache validation and retention handling
  - Proper validation of `redays >= days` relationship
  - Improved error handling for invalid retention values
  - Better cleanup logic for cache, logs, and XMLTV backups

## [1.3] - Previous Release
### Added
- **Categories Translation**: Automatic English/French/Spanish category translation using .po files
  - Proper capitalization rules per language (Title Case for English, Sentence case for French/Spanish)
  - Smart fallback when translation files unavailable
  - Requires `polib` for full functionality (`pip install polib`)
- **Rating system**: Enhanced with MPAA system support

### Changed
- **Credits**: Use proper `<image>` sub-element instead of src attribute - now strict XMLTV DTD compliant
- **`episode-num xmltv_ns`**: Use spaces around dots per DTD standard

### Fixed
- **Stereo detection**: Fixed to properly detect STEREO tag
- **Language Cache**: Allow handling of malformed XML when scrubbing previous xmltv

## [1.2] - Older Release
### Added
- **Language Cache**: 95-100% cache efficiency with automatic reuse of previous language detections
- **Enhanced XMLTV Metadata**: New DTD-compliant fields (language, country, video, audio) controlled by xdetails configuration
- **Modular Language Detection**: New gracenote2epg_language module with LanguageDetector class for better architecture
- **Smart Metadata Logic**: Country detection from zipcode format, stereo audio from tags, aspect ratio from content age

### Changed
- **Performance Optimization**: Eliminates redundant `langdetect` calls, reducing XMLTV generation time from ~15 minutes to ~2-3 minutes

## [1.1] - Older Release
### Added
- **Progress Tracking**: Real-time progress indicators for long operations
- **Migration Documentation**: Complete migration guide from other EPG grabbers
- **Extended Details Improvements**: Better handling and corrections for xdetails and xdesc configuration
- **Strict XMLTV DTD Compliance**: Full DTD compliance except for actor photo `src=` attribute extension
- **XMLTV Generation Progress**: Percentage progress indicators during XML generation (especially useful for langdetect operations)
- **Download Progress Counters**: Added "x/y" counters for extended details downloads to show remaining downloads
- **Cache Refresh Options**: New `--refresh X` and `--norefresh` command-line options for flexible cache management
- **Configuration Version 4**: Updated configuration schema to support new refresh options

### Fixed
- **Directory Permissions Fix**: Create directories with proper 755 permissions instead of 777
- **Enhanced Synology Detection**: Improved system detection for DSM6/DSM7 path selection

## [1.0] - Initial Release
### Added
- **Python Modularization**: Based on edit4ever's script.module.zap2epg with tv_grab_zap2epg improvements and Python modular architecture
- **Multi-Language Support**: Automatic French/English/Spanish detection with localized translations
- **Reliable Language Detection**: langdetect library integration with configurable enable/disable options
- **Enhanced XMLTV Generation**: Line breaks for better Kodi display, proper language attributes
- **Intelligent Cache Management**: Smart caching with 95%+ efficiency  
- **Flexible Logging System**: File-based logging with optional console output and language statistics
- **Improved Error Handling**: Robust downloading and parsing with WAF protection
- **Better Debugging**: Detailed statistics including language distribution and configurable verbosity
- **Platform Auto-detection**: Smart directory configuration for Raspberry Pi, Synology, etc.
- **Full Backward Compatibility**: Works with existing zap2epg configurations and cache
- **Kodi/TVheadend Integration**: Maintains original design goals for media center use with enhanced formatting
