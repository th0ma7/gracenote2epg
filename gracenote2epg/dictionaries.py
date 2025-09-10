"""
gracenote2epg.gracenote2epg_dictionaries - i18n Translation system using .po files

Handles internationalization using standard .po (Portable Object) files for
categories, terms, and other translatable content. Supports English, French,
and Spanish translations with fallback mechanisms.
"""

import html
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Try to import polib for .po file support
try:
    import polib

    POLIB_AVAILABLE = True
except ImportError:
    POLIB_AVAILABLE = False
    logging.warning("polib not available - install with: pip install polib")


class TranslationManager:
    """Manages translations using .po files with caching and fallback"""

    def __init__(self, locales_dir: Optional[Path] = None):
        """
        Initialize translation manager

        Args:
            locales_dir: Directory containing locale subdirectories with .po files
                        If None, uses package default locales directory
        """
        self.locales_dir = locales_dir or self._get_default_locales_dir()
        self.translations: Dict[str, Dict[str, str]] = {}
        self.available_languages = ["en", "fr", "es"]
        self.fallback_language = "en"

        # Load all available translations
        self._load_translations()

    def _get_default_locales_dir(self) -> Path:
        """Get default locales directory relative to this module"""
        # Locales directory in the same package
        package_dir = Path(__file__).parent
        return package_dir / "locales"

    def _load_translations(self):
        """Load all .po files from locales directory"""
        if not POLIB_AVAILABLE:
            logging.warning("polib not available - translations disabled")
            return

        if not self.locales_dir.exists():
            logging.warning("Locales directory not found: %s", self.locales_dir)
            return

        for lang_code in self.available_languages:
            if lang_code == self.fallback_language:
                continue  # Skip English as it's the source language

            po_file = self.locales_dir / lang_code / "LC_MESSAGES" / "gracenote2epg.po"

            if po_file.exists():
                try:
                    po = polib.pofile(str(po_file))

                    # Build translation dictionary
                    lang_translations = {}
                    for entry in po:
                        if entry.msgstr and not entry.obsolete:
                            # Normalize msgid for case-insensitive lookup
                            normalized_key = entry.msgid.lower().strip()
                            lang_translations[normalized_key] = entry.msgstr

                    self.translations[lang_code] = lang_translations
                    logging.debug(
                        "Loaded %d translations for %s", len(lang_translations), lang_code
                    )

                except Exception as e:
                    logging.warning("Error loading %s translations: %s", lang_code, e)
            else:
                logging.debug("Translation file not found: %s", po_file)

        # Log summary
        total_loaded = sum(len(trans) for trans in self.translations.values())
        logging.info(
            "Translation system initialized: %d languages, %d total translations",
            len(self.translations),
            total_loaded,
        )

    def translate(self, text: str, target_language: str, context: str = "general") -> str:
        """
        Translate text to target language with proper case handling

        Args:
            text: Text to translate
            target_language: Target language code (fr, en, es)
            context: Translation context for disambiguation (category, term, etc.)

        Returns:
            Translated text or original if translation not found
        """
        # Fallback to English if target language not supported
        if target_language not in self.available_languages:
            target_language = self.fallback_language

        # Return original if English or no translations available
        if target_language == self.fallback_language or not self.translations.get(target_language):
            # Apply English title case for categories
            if context == "category" and target_language == "en":
                return text.title()
            return text

        # Normalize for lookup: decode HTML entities first, then lowercase
        # Ceci gère les cas comme "Books &amp; Literature" -> "books & literature"
        normalized_text = html.unescape(text).lower().strip()

        # Remove common prefixes
        if normalized_text.startswith("filter-"):
            normalized_text = normalized_text[7:]

        # Look up translation
        lang_translations = self.translations[target_language]
        translated = lang_translations.get(normalized_text)

        if translated:
            # Apply case transformation based on context and target language
            if context == "category":
                if target_language in ["fr", "es"]:
                    # French/Spanish: sentence case (première lettre majuscule seulement)
                    return translated.capitalize()
                elif target_language == "en":
                    # English: title case
                    return translated.title()

            elif context == "term":
                # Status terms: keep uppercase
                return translated.upper()

            elif context == "language":
                # Language names: title case
                return translated.title()

            return translated
        else:
            logging.debug('No translation found for "%s" in %s', text, target_language)
            # Apply proper case even for untranslated text
            if context == "category":
                if target_language in ["fr", "es"]:
                    return text.capitalize()
                elif target_language == "en":
                    return text.title()
            return text

    def get_available_languages(self) -> List[str]:
        """Get list of supported language codes"""
        return self.available_languages.copy()

    def get_language_display_name(self, language_code: str, display_language: str = "en") -> str:
        """
        Get language display name in target language with proper case handling

        Args:
            language_code: Language code to display (fr, en, es)
            display_language: Language to display name in (fr, en, es)

        Returns:
            Language display name
        """
        # Language names as translatable strings
        language_names = {"en": "English", "fr": "French", "es": "Spanish"}

        base_name = language_names.get(language_code, language_code.upper())
        return self.translate(base_name, display_language, "language")

    def get_statistics(self) -> Dict[str, int]:
        """Get translation statistics"""
        stats = {}
        for lang, translations in self.translations.items():
            stats[lang] = len(translations)
        return stats


# Global translation manager instance
_translation_manager: Optional[TranslationManager] = None


def get_translation_manager() -> TranslationManager:
    """Get or create global translation manager instance"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


def get_category_translation(category: str, target_language: str) -> str:
    """
    Get translated category name using .po files with proper case handling

    Args:
        category: Original category name (case-insensitive)
        target_language: Target language code (fr, en, es)

    Returns:
        Translated category name or original if translation not found
    """
    manager = get_translation_manager()
    return manager.translate(category, target_language, "category")


def get_term_translation(term: str, target_language: str) -> str:
    """
    Get translated term (rated, new, premiere, etc.) using .po files with proper case handling

    Args:
        term: Term to translate
        target_language: Target language code (fr, en, es)

    Returns:
        Translated term or original if translation not found
    """
    manager = get_translation_manager()
    return manager.translate(term, target_language, "term")


def get_language_display_name(language_code: str, display_language: str = "en") -> str:
    """
    Get language display name in target language using .po files with proper case handling

    Args:
        language_code: Language code to display (fr, en, es)
        display_language: Language to display name in (fr, en, es)

    Returns:
        Language display name
    """
    manager = get_translation_manager()
    return manager.get_language_display_name(language_code, display_language)


def get_available_languages() -> List[str]:
    """Get list of supported language codes"""
    manager = get_translation_manager()
    return manager.get_available_languages()


def reload_translations(locales_dir: Optional[Path] = None):
    """
    Reload translations from .po files

    Args:
        locales_dir: Optional custom locales directory
    """
    global _translation_manager
    _translation_manager = TranslationManager(locales_dir)


def get_translation_statistics() -> Dict[str, int]:
    """Get translation statistics for all loaded languages"""
    manager = get_translation_manager()
    return manager.get_statistics()
