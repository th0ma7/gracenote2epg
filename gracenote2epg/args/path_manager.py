"""
Path management module for gracenote2epg

Handles system-specific default directories, path creation with proper
permissions, and directory structure management.
"""

from pathlib import Path
from typing import Dict, Optional

from .systems import SystemDetector


class PathManager:
    """Manages system-specific paths and directory creation"""

    @staticmethod
    def get_system_defaults(base_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Get default directories, rooted at base_dir when given (--basedir),
        otherwise at the system-specific location.

        Returns:
            Dict containing base_dir, cache_dir, conf_dir, log_dir, and file paths
        """
        if base_dir is None:
            home = Path.home()
            # Use new SystemDetector orchestrator
            detector = SystemDetector()
            detector.detect_system()  # Run detection
            base_dir = detector.get_base_path(home)
        else:
            base_dir = Path(base_dir)

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
