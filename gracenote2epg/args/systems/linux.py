"""
Generic Linux system detector and configuration

Handles standard Linux distributions and Docker containers.
Acts as catch-all detector when no specific system is identified.
"""

import logging
import os
from pathlib import Path
from typing import Dict


class LinuxDetector:
    """Generic Linux detection and configuration"""
    
    system_type = "linux"
    
    def detect(self) -> bool:
        """
        Detect generic Linux system (catch-all)
        
        Returns:
            bool: Always True as this is the fallback
        """
        # This is the catch-all detector, always returns True
        # More specific detectors should be checked first
        return True
    
    def get_base_path(self, home: Path) -> Path:
        """
        Get Linux-specific base path
        
        Args:
            home: User home directory
            
        Returns:
            Path: Base directory for gracenote2epg
        """
        # Check if running in Docker
        if self._is_docker():
            # Docker containers might have specific mount points
            docker_paths = [
                Path("/config/gracenote2epg"),
                Path("/data/gracenote2epg"),
                Path("/app/gracenote2epg"),
            ]
            
            for docker_path in docker_paths:
                try:
                    if docker_path.parent.exists():
                        logging.debug(f"Docker detected, using: {docker_path}")
                        return docker_path
                except (PermissionError, OSError):
                    continue
                except Exception:
                    continue
        
        # Check for TVheadend installation
        tvheadend_paths = [
            Path("/usr/share/tvheadend/data/epggrab/gracenote2epg"),
            Path("/var/lib/tvheadend/epggrab/gracenote2epg"),
            Path("/etc/tvheadend/epggrab/gracenote2epg"),
            home / ".hts" / "tvheadend" / "epggrab" / "gracenote2epg",
        ]
        
        for tvh_path in tvheadend_paths:
            try:
                if tvh_path.parent.exists():
                    logging.debug(f"TVheadend installation detected, using: {tvh_path}")
                    return tvh_path
            except (PermissionError, OSError) as e:
                # Skip paths we don't have permission to check
                logging.debug(f"Cannot check {tvh_path.parent}: {type(e).__name__}")
                continue
            except Exception as e:
                # Skip any other errors
                logging.debug(f"Error checking path {tvh_path.parent}: {e}")
                continue
        
        # Default Linux path in home directory
        default_path = home / "gracenote2epg"
        logging.debug(f"Using default Linux path: {default_path}")
        return default_path
    
    def _is_docker(self) -> bool:
        """
        Check if running inside a Docker container
        
        Returns:
            bool: True if Docker environment detected
        """
        # Method 1: Check for .dockerenv file
        if Path("/.dockerenv").exists():
            return True
        
        # Method 2: Check cgroup for docker
        try:
            with open("/proc/1/cgroup", "r") as f:
                if "docker" in f.read().lower():
                    return True
        except Exception:
            pass
        
        # Method 3: Check environment variables
        if os.environ.get("DOCKER_CONTAINER"):
            return True
        
        return False
    
    def _get_distribution_info(self) -> Dict:
        """
        Get Linux distribution information
        
        Returns:
            Dict: Distribution details
        """
        dist_info = {
            "distribution": "unknown",
            "version": None,
        }
        
        # Try to read from os-release (most modern distributions)
        os_release = Path("/etc/os-release")
        if os_release.exists():
            try:
                with open(os_release, "r") as f:
                    for line in f:
                        if line.startswith("ID="):
                            dist_info["distribution"] = line.split("=")[1].strip().strip('"')
                        elif line.startswith("VERSION_ID="):
                            dist_info["version"] = line.split("=")[1].strip().strip('"')
            except Exception:
                pass
        
        # Fallback to older methods
        elif Path("/etc/debian_version").exists():
            dist_info["distribution"] = "debian"
            try:
                with open("/etc/debian_version", "r") as f:
                    dist_info["version"] = f.read().strip()
            except Exception:
                pass
        
        elif Path("/etc/redhat-release").exists():
            dist_info["distribution"] = "redhat"
            try:
                with open("/etc/redhat-release", "r") as f:
                    content = f.read().strip()
                    # Extract version from string like "CentOS Linux release 7.9.2009"
                    import re
                    version_match = re.search(r'release\s+([\d.]+)', content)
                    if version_match:
                        dist_info["version"] = version_match.group(1)
            except Exception:
                pass
        
        return dist_info
    
    def get_system_info(self) -> Dict:
        """
        Get Linux system information
        
        Returns:
            Dict: System details including distribution
        """
        info = {
            "type": self.system_type,
            "is_docker": self._is_docker(),
            "kernel_version": None,
        }
        
        # Get distribution information
        dist_info = self._get_distribution_info()
        info.update(dist_info)
        
        # Get kernel version
        try:
            import platform
            info["kernel_version"] = platform.release()
        except Exception:
            pass
        
        # Check for TVheadend
        tvheadend_markers = [
            Path("/usr/bin/tvheadend"),
            Path("/usr/share/tvheadend"),
            Path("/var/lib/tvheadend"),
            Path.home() / ".hts" / "tvheadend",
        ]
        
        tvheadend_detected = False
        for path in tvheadend_markers:
            try:
                if path.exists():
                    tvheadend_detected = True
                    break
            except (PermissionError, OSError):
                # Skip paths we don't have permission to check
                continue
            except Exception:
                continue
        
        info["tvheadend_detected"] = tvheadend_detected
        
        return info
