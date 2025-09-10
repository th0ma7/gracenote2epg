"""
Raspberry Pi system detector and configuration

Handles Raspberry Pi detection and Kodi integration paths.
"""

import logging
from pathlib import Path
from typing import Dict


class RaspberryDetector:
    """Raspberry Pi detection and configuration"""
    
    system_type = "raspberry"
    
    def detect(self) -> bool:
        """
        Detect if running on Raspberry Pi
        
        Returns:
            bool: True if Raspberry Pi detected
        """
        # Method 1: Check device tree model (most reliable for RPi)
        device_tree_model = Path("/proc/device-tree/model")
        if device_tree_model.exists():
            try:
                with open(device_tree_model, "r") as f:
                    model = f.read().lower()
                    if "raspberry" in model:
                        logging.debug(f"Raspberry Pi detected via device-tree: {model[:50]}")
                        return True
            except Exception as e:
                logging.debug(f"Error reading device-tree model: {e}")
        
        # Method 2: Check CPU info
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.exists():
            try:
                with open(cpuinfo, "r") as f:
                    content = f.read().lower()
                    # Check for Raspberry Pi specific markers
                    if any(marker in content for marker in ["raspberry", "bcm27", "bcm28"]):
                        logging.debug("Raspberry Pi detected via cpuinfo")
                        return True
            except Exception as e:
                logging.debug(f"Error reading cpuinfo: {e}")
        
        # Method 3: Check for Raspberry Pi specific files
        rpi_markers = [
            "/opt/vc/bin/vcgencmd",  # VideoCore tools
            "/boot/config.txt",      # RPi boot config
            "/sys/firmware/devicetree/base/model",  # Alternative model location
        ]
        
        for marker in rpi_markers:
            if Path(marker).exists():
                logging.debug(f"Raspberry Pi detected via marker: {marker}")
                return True
        
        return False
    
    def get_base_path(self, home: Path) -> Path:
        """
        Get Raspberry Pi specific base path
        
        Args:
            home: User home directory
            
        Returns:
            Path: Base directory for gracenote2epg
        """
        # Check for Kodi/XBMC integration first
        kodi_paths = [
            home / "script.module.zap2epg" / "epggrab",
            home / ".kodi" / "addons" / "script.module.gracenote2epg",
            home / ".xbmc" / "addons" / "script.module.gracenote2epg",
        ]
        
        for kodi_path in kodi_paths:
            if kodi_path.exists():
                logging.debug(f"Using Kodi integration path: {kodi_path}")
                return kodi_path
        
        # Check for OSMC (Raspberry Pi media center)
        if Path("/home/osmc").exists() and home == Path("/home/osmc"):
            osmc_path = home / "gracenote2epg"
            logging.debug(f"OSMC detected, using: {osmc_path}")
            return osmc_path
        
        # Default Raspberry Pi path
        default_path = home / "gracenote2epg"
        logging.debug(f"Using default Raspberry Pi path: {default_path}")
        return default_path
    
    def get_system_info(self) -> Dict:
        """
        Get Raspberry Pi system information
        
        Returns:
            Dict: System details including model
        """
        info = {
            "type": self.system_type,
            "model": None,
            "revision": None,
            "kodi_detected": False,
            "osmc_detected": False,
        }
        
        # Try to get model information
        try:
            device_tree_model = Path("/proc/device-tree/model")
            if device_tree_model.exists():
                with open(device_tree_model, "r") as f:
                    model = f.read().strip().replace('\x00', '')
                    info["model"] = model
        except Exception:
            pass
        
        # Try to get revision from cpuinfo
        try:
            cpuinfo = Path("/proc/cpuinfo")
            if cpuinfo.exists():
                with open(cpuinfo, "r") as f:
                    for line in f:
                        if "revision" in line.lower():
                            revision = line.split(":")[-1].strip()
                            info["revision"] = revision
                            break
        except Exception:
            pass
        
        # Check for Kodi
        kodi_markers = [
            Path.home() / ".kodi",
            Path.home() / ".xbmc",
            Path.home() / "script.module.zap2epg",
        ]
        info["kodi_detected"] = any(path.exists() for path in kodi_markers)
        
        # Check for OSMC
        info["osmc_detected"] = Path("/home/osmc").exists()
        
        return info
