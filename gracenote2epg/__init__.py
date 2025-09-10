"""
gracenote2epg - North America TV Guide Grabber

A modular Python implementation for downloading TV guide data from
tvlistings.gracenote.com with intelligent caching and TVheadend integration.
"""

__version__ = "1.6.0"
__author__ = "th0ma7"
__license__ = "GPL-3.0"

from .gracenote2epg_args import ArgumentParser
from .gracenote2epg_config import ConfigManager
from .gracenote2epg_lineup import LineupManager
from .gracenote2epg_downloader import OptimizedDownloader
from .gracenote2epg_language import LanguageDetector
from .gracenote2epg_parser import GuideParser
from .gracenote2epg_tvheadend import TvheadendClient
from .gracenote2epg_utils import CacheManager, TimeUtils
from .gracenote2epg_xmltv import XmltvGenerator
from .gracenote2epg_dictionaries import (
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
    "LineupManager",
    "OptimizedDownloader",
    "LanguageDetector",
    "GuideParser",
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
