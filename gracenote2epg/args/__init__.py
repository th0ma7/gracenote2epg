"""
gracenote2epg.args - Command line argument parsing module

Provides argument parsing, validation, and system detection functionality
for the gracenote2epg grabber with baseline XMLTV capabilities.
"""

from .base import ArgumentParser
from .validator import ArgumentValidator
from .location import LocationProcessor
from .path_manager import PathManager
from .systems import SystemDetector

# Primary export
__all__ = [
    "ArgumentParser",      # Main public interface
    "ArgumentValidator",   # For testing/validation
    "LocationProcessor",   # For location handling
    "PathManager",         # For path management
    "SystemDetector",      # For system detection
]
