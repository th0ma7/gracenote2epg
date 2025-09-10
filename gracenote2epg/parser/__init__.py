"""
gracenote2epg.parser - Data parsing module

Handles parsing of TV guide data with separated download/parse concerns.
Pure parsing logic without HTTP or caching responsibilities.
"""

from .base import DataParser
from .guide import GuideParser
from .series import SeriesParser

__all__ = [
    "DataParser",      # Main orchestrator
    "GuideParser",     # Pure guide parsing
    "SeriesParser",    # Pure series parsing
]
