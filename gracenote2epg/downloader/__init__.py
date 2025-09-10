"""
gracenote2epg.downloader - Download management module

Handles all HTTP download operations for gracenote2epg with WAF protection,
intelligent caching, and specialized downloaders for guide and series data.
"""

from .base import OptimizedDownloader
from .guide import GuideDownloader  
from .series import SeriesDownloader

__all__ = [
    "OptimizedDownloader",
    "GuideDownloader", 
    "SeriesDownloader",
]
