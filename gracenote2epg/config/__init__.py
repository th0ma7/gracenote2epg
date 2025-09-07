"""
gracenote2epg.config - Configuration management module

Provides unified configuration management for gracenote2epg including
XML parsing, validation, migration, lineup management, and retention policies.

Main interface:
    ConfigManager: Primary configuration manager that orchestrates all operations

The module is organized into specialized components:
    - validation: Configuration validation and consistency checks
    - settings: XML settings parsing and management  
    - migration: Configuration migration and cleanup
    - lineup: Lineup ID management and auto-detection
    - retention: Cache and retention policy management
    - display: Display utilities and testing functions
    - base: Main ConfigManager orchestration

Usage:
    from gracenote2epg.config import ConfigManager
    
    config_manager = ConfigManager("/path/to/config.xml")
    config = config_manager.load_config()
"""

# Main public interface - maintain backward compatibility
from .base import ConfigManager

# Export only the main interface to maintain clean API
__all__ = ["ConfigManager"]

# Internal components are not exported to keep the public API clean
# They can still be imported explicitly if needed for testing:
# from gracenote2epg.config.validation import ConfigValidator
# from gracenote2epg.config.lineup import LineupManager
# etc.
