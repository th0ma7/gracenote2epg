"""
gracenote2epg.xmltv.generator - XMLTV generation (DTD compliant)

Orchestrates XMLTV file generation. The per-element writers are organised
into focused mixins (stations, programme, descriptions, credits, categories,
media) that this class composes.
"""

import codecs
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..cache import CacheManager
from ..language import LanguageDetector
from .stations import StationsMixin
from .programme import ProgrammeMixin
from .descriptions import DescriptionsMixin
from .credits import CreditsMixin
from .categories import CategoriesMixin
from .media import MediaMixin


class XmltvGenerator(
    StationsMixin,
    ProgrammeMixin,
    DescriptionsMixin,
    CreditsMixin,
    CategoriesMixin,
    MediaMixin,
):
    """Generates XMLTV files from parsed guide data - DTD Compliant"""

    ASSETS_BASE_URL = "https://www.tvtv.ca/gn/pi/assets"

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.station_count = 0
        self.episode_count = 0

        # Language detection is handled by LanguageDetector module
        self.language_detector: Optional[LanguageDetector] = None

    def generate_xmltv(self, schedule: Dict, config: Dict[str, Any], xmltv_file: Path) -> bool:
        """Generate XMLTV file with automatic backup and optimized language detection"""
        try:
            logging.info("=== XMLTV Generation (DTD Compliant) ===")

            # Initialize language detector with configuration
            langdetect_enabled = config.get("langdetect", True)
            self.language_detector = LanguageDetector(enabled=langdetect_enabled)

            # Load cache from previous XMLTV if language detection is enabled
            if langdetect_enabled:
                self.language_detector.load_cache_from_xmltv(xmltv_file)

            # Always backup existing XMLTV
            self.cache_manager.backup_xmltv(xmltv_file)

            # Generate new XMLTV
            encoding = "utf-8"

            with codecs.open(xmltv_file, "w+b", encoding=encoding) as f:
                self._print_header(f, encoding)
                self._print_stations(f, schedule)
                self._print_episodes(f, schedule, config)
                self._print_footer(f)

            # Log language statistics via detector
            if self.language_detector:
                self.language_detector.log_final_statistics()

            # Verify and log result
            if xmltv_file.exists():
                file_size = xmltv_file.stat().st_size
                logging.info("XMLTV file created: %s (%d bytes)", xmltv_file.name, file_size)
                return True
            else:
                logging.error("XMLTV file was not created: %s", xmltv_file)
                return False

        except Exception as e:
            logging.exception("Exception in XMLTV generation: %s", str(e))
            return False


    def _print_header(self, fh, encoding: str):
        """Print XMLTV header"""
        logging.info("Creating xmltv.xml file...")
        fh.write(f'<?xml version="1.0" encoding="{encoding}"?>\n')
        fh.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        fh.write(
            '<tv source-info-url="http://tvschedule.gracenote.com/" source-info-name="gracenote.com">\n'
        )


    def _print_footer(self, fh):
        """Print XMLTV footer"""
        fh.write("</tv>\n")

