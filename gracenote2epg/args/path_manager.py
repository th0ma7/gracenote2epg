"""
Path management module for gracenote2epg

Handles system-specific default directories, path creation with proper
permissions, and directory structure management.
"""

import logging
from pathlib import Path
from typing import Dict

from .systems import SystemDetector


class PathManager:
    """Manages system-specific paths and directory creation"""
    
    @staticmethod
    def get_system_defaults() -> Dict[str, Path]:
        """
        Get system-specific default directories
        
        Returns:
            Dict containing base_dir, cache_dir, conf_dir, log_dir, and file paths
        """
        home = Path.home()
        
        # Use new SystemDetector orchestrator
        detector = SystemDetector()
        detector.detect_system()  # Run detection
        base_dir = detector.get_base_path(home)
        
        return {
            "base_dir": base_dir,
            "cache_dir": base_dir / "cache",
            "conf_dir": base_dir / "conf",
            "log_dir": base_dir / "log",
            "config_file": base_dir / "conf" / "gracenote2epg.xml",
            "xmltv_file": base_dir / "cache" / "xmltv.xml",
            "log_file": base_dir / "log" / "gracenote2epg.log",
        }
    
    @staticmethod
    def create_directories(defaults: Dict[str, Path]):
        """
        Create required directories with proper 755 permissions
        
        Args:
            defaults: Dictionary containing directory paths
        """
        # Create directories with 755 permissions (rwxr-xr-x)
        for key in ["cache_dir", "conf_dir", "log_dir"]:
            if key in defaults:
                directory = defaults[key]
                try:
                    directory.mkdir(parents=True, exist_ok=True, mode=0o755)
                except Exception:
                    # Fallback: create without mode specification (depends on umask)
                    directory.mkdir(parents=True, exist_ok=True)
