"""
Synology NAS system detector and configuration

Handles Synology-specific detection, DSM version identification,
and TVheadend path configuration.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Optional


class SynologyDetector:
    """Synology NAS detection and configuration"""
    
    system_type = "synology"
    
    def detect(self) -> bool:
        """
        Detect if running on Synology NAS
        
        Returns:
            bool: True if Synology system detected
        """
        # Method 1: Check for Synology-specific config file (most reliable)
        if Path("/etc/synoinfo.conf").exists():
            return True
        
        # Method 2: Check VERSION file for Synology content
        try:
            version_file = Path("/etc/VERSION")
            if version_file.exists():
                with open(version_file, "r") as f:
                    content = f.read().lower()
                    if "synology" in content or (
                        "majorversion=" in content and "buildnumber=" in content
                    ):
                        return True
        except Exception:
            pass
        
        # Method 3: Check for TVheadend Synology packages
        if (
            Path("/var/packages/tvheadend/var").exists()
            or Path("/var/packages/tvheadend/target/var").exists()
        ):
            return True
        
        # Method 4: Platform check (fallback)
        try:
            import platform
            if "synology" in platform.uname().release.lower():
                return True
        except Exception:
            pass
        
        return False
    
    def get_dsm_version(self) -> int:
        """
        Get Synology DSM version number
        
        Returns:
            int: Build number (e.g., 50000 for DSM7+, 30000 for DSM6)
        """
        # Parse /etc/VERSION file for accurate version
        try:
            version_file = Path("/etc/VERSION")
            if version_file.exists():
                with open(version_file, "r") as f:
                    content = f.read()
                
                # Extract major version and build number
                major_match = re.search(r'majorversion="?(\d+)"?', content)
                build_match = re.search(r'buildnumber="?(\d+)"?', content)
                
                if major_match:
                    major_version = int(major_match.group(1))
                    
                    if build_match:
                        # Return actual build number for precise detection
                        return int(build_match.group(1))
                    
                    # Map major version to typical build ranges
                    if major_version >= 7:
                        return 50000  # DSM7+
                    elif major_version >= 6:
                        return 30000  # DSM6
                    else:
                        return 20000  # DSM5 and older
        except Exception as e:
            logging.debug(f"Error reading DSM version: {e}")
        
        # Check directory structure as fallback
        try:
            # DSM7+ uses new path structure
            if (
                Path("/var/packages/tvheadend/var").exists()
                and not Path("/var/packages/tvheadend/target/var").exists()
            ):
                return 50000  # DSM7+
            # DSM6 uses old path structure
            elif Path("/var/packages/tvheadend/target/var").exists():
                return 30000  # DSM6
            # Both exist (transition case)
            elif Path("/var/packages/tvheadend/var").exists():
                return 50000  # Prefer newer structure
        except Exception:
            pass
        
        # Default to DSM7+ if detection fails
        return 50000
    
    def get_base_path(self, home: Path) -> Path:
        """
        Get Synology-specific base path
        
        Args:
            home: User home directory
            
        Returns:
            Path: Base directory for gracenote2epg
        """
        dsm_version = self.get_dsm_version()
        
        # Select path based on DSM version
        if dsm_version < 40000:
            # DSM6 and earlier
            base_dir = Path("/var/packages/tvheadend/target/var/epggrab/gracenote2epg")
        else:
            # DSM7 and later
            base_dir = Path("/var/packages/tvheadend/var/epggrab/gracenote2epg")
        
        logging.debug(f"Synology DSM version: {dsm_version}, selected path: {base_dir}")
        
        # Verify parent directory exists
        if not base_dir.parent.exists():
            logging.warning(f"Expected TVheadend path {base_dir.parent} not found")
            
            # Try to find valid TVheadend path
            for check_path in [
                "/var/packages/tvheadend/var",
                "/var/packages/tvheadend/target/var",
            ]:
                if Path(check_path).exists():
                    logging.warning(f"Using alternative path: {check_path}")
                    base_dir = Path(check_path) / "epggrab" / "gracenote2epg"
                    break
            else:
                # No TVheadend paths found, fallback to home
                logging.warning("No TVheadend paths found, using home directory")
                base_dir = home / "gracenote2epg"
        
        return base_dir
    
    def get_system_info(self) -> Dict:
        """
        Get Synology system information
        
        Returns:
            Dict: System details including DSM version
        """
        info = {
            "type": self.system_type,
            "dsm_version": None,
            "dsm_major": None,
            "tvheadend_path": None,
        }
        
        dsm_version = self.get_dsm_version()
        info["dsm_version"] = dsm_version
        
        # Determine DSM major version
        if dsm_version >= 50000:
            info["dsm_major"] = 7
        elif dsm_version >= 30000:
            info["dsm_major"] = 6
        else:
            info["dsm_major"] = 5
        
        # Find TVheadend path
        for path in [
            "/var/packages/tvheadend/var",
            "/var/packages/tvheadend/target/var",
        ]:
            if Path(path).exists():
                info["tvheadend_path"] = path
                break
        
        return info
