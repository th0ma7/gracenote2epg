"""
System detection orchestrator for gracenote2epg

Coordinates system-specific detectors and provides unified interface
for system type detection and configuration.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

# Import system-specific detectors
from .synology import SynologyDetector
from .raspberry import RaspberryDetector
from .linux import LinuxDetector


class SystemDetector:
    """Main system detection orchestrator"""
    
    # Registry of system detectors in priority order
    DETECTORS = [
        SynologyDetector,    # Check Synology first (most specific)
        RaspberryDetector,   # Then Raspberry Pi
        LinuxDetector,       # Fallback to generic Linux
        # Future: WindowsDetector, MacOSDetector, DockerDetector
    ]
    
    def __init__(self):
        self._detected_system = None
        self._detector_instance = None
    
    def detect_system(self) -> str:
        """
        Detect system type using registered detectors
        
        Returns:
            str: System type identifier ('synology', 'raspberry', 'linux', etc.)
        """
        if self._detected_system is not None:
            return self._detected_system
        
        for detector_class in self.DETECTORS:
            detector = detector_class()
            if detector.detect():
                self._detected_system = detector.system_type
                self._detector_instance = detector
                logging.debug(f"System detected: {self._detected_system}")
                return self._detected_system
        
        # Should never happen as LinuxDetector is catch-all
        self._detected_system = 'unknown'
        return self._detected_system
    
    def get_base_path(self, home: Path = None) -> Path:
        """
        Get system-specific base path for gracenote2epg
        
        Args:
            home: Home directory (defaults to Path.home())
            
        Returns:
            Path: Base directory for the detected system
        """
        if home is None:
            home = Path.home()
        
        # Ensure detection has run
        if self._detector_instance is None:
            self.detect_system()
        
        if self._detector_instance:
            return self._detector_instance.get_base_path(home)
        
        # Fallback
        return home / "gracenote2epg"
    
    def get_system_info(self) -> Dict:
        """
        Get detailed system information
        
        Returns:
            Dict: System-specific information
        """
        # Ensure detection has run
        if self._detector_instance is None:
            self.detect_system()
        
        if self._detector_instance:
            return self._detector_instance.get_system_info()
        
        return {"type": "unknown", "version": None}
    
    @classmethod
    def register_detector(cls, detector_class, priority: Optional[int] = None):
        """
        Register a new system detector
        
        Args:
            detector_class: Detector class to register
            priority: Position in detector list (None = append to end)
        """
        if priority is not None:
            cls.DETECTORS.insert(priority, detector_class)
        else:
            cls.DETECTORS.append(detector_class)
    
    # Compatibility methods for backward compatibility with old API
    @classmethod
    def detect_system_type(cls) -> str:
        """
        Static method for backward compatibility
        
        Returns:
            str: System type identifier
        """
        detector = cls()
        return detector.detect_system()
    
    @classmethod 
    def get_dsm_version(cls) -> int:
        """
        Static method for getting DSM version (Synology specific)
        
        Returns:
            int: DSM version or 0 if not Synology
        """
        detector = cls()
        if detector.detect_system() == 'synology':
            if detector._detector_instance:
                return detector._detector_instance.get_dsm_version()
        return 0
