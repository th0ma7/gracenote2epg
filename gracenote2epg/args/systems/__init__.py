"""
System detection module for gracenote2epg

Provides system type detection and configuration for different platforms
including Synology NAS, Raspberry Pi, and generic Linux systems.
"""

from .base import SystemDetector
from .synology import SynologyDetector
from .raspberry import RaspberryDetector
from .linux import LinuxDetector

__all__ = [
    "SystemDetector",     # Main orchestrator
    "SynologyDetector",   # Synology NAS specific
    "RaspberryDetector",  # Raspberry Pi specific
    "LinuxDetector",      # Generic Linux fallback
]
