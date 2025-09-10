"""
gracenote2epg - North America TV Guide Grabber

A modular Python implementation for downloading TV guide data from
tvlistings.gracenote.com with intelligent caching and TVheadend integration.
"""

__version__ = "2.0.0-dev"
__author__ = "th0ma7"
__license__ = "GPL-3.0"

from .args import ArgumentParser
from .config import ConfigManager
from .downloader import OptimizedDownloader
from .language import LanguageDetector
from .parser import DataParser
from .tvheadend import TvheadendClient
from .utils import CacheManager, TimeUtils
from .xmltv import XmltvGenerator
from .dictionaries import (
    get_category_translation,
    get_term_translation,
    get_language_display_name,
    get_available_languages,
    get_translation_statistics,
    reload_translations,
)

__all__ = [
    "ArgumentParser",
    "ConfigManager",
    "OptimizedDownloader",
    "LanguageDetector",
    "DataParser",
    "TvheadendClient",
    "CacheManager",
    "TimeUtils",
    "XmltvGenerator",
    "get_category_translation",
    "get_term_translation",
    "get_language_display_name",
    "get_available_languages",
    "get_translation_statistics",
    "reload_translations",
]
