"""
gracenote2epg.xmltv.categories - <category> genres with translation and EIT mapping.
"""

from typing import Dict, List
from ..utils import HtmlUtils


class CategoriesMixin:
    """<category> genres with translation and EIT mapping."""

    def _write_categories(
        self,
        fh,
        episode_data: Dict,
        ep_genre: str,
        detected_language: str = "en",
        use_extended_details: bool = True,
    ):
        """Write program categories/genres with translation support and proper capitalization"""
        if ep_genre == "0":  # No genres
            return

        # Pass use_extended_details parameter
        genres = self._get_genre_list(episode_data, ep_genre, use_extended_details)
        if genres:
            for genre in genres:
                # Clean before translating (no HTML encoding yet)
                clean_genre = genre.replace("filter-", "")

                # Translate before HTML encoding
                if self.language_detector:
                    translated_genre = self.language_detector.translate_category(
                        clean_genre, detected_language
                    )
                else:
                    # Fallback to English with proper capitalization
                    if detected_language == "en":
                        translated_genre = clean_genre.title()
                    else:
                        translated_genre = clean_genre.capitalize()

                # HTML encoding on translated text
                html_safe_genre = HtmlUtils.conv_html(translated_genre)

                fh.write(f'\t\t<category lang="{detected_language}">{html_safe_genre}</category>\n')

    def _get_genre_list(
        self, episode_data: Dict, ep_genre: str, use_extended_details: bool = True
    ) -> List[str]:
        """Get processed genre list based on configuration"""
        ep_filter = episode_data.get("epfilter", [])

        # Only use epgenres (from extended details) if xdetails=true
        if use_extended_details:
            ep_genres = episode_data.get("epgenres", [])
        else:
            ep_genres = []  # Don't use extended genres if xdetails=false

        if not isinstance(ep_filter, list):
            ep_filter = []
        if not isinstance(ep_genres, list):
            ep_genres = []

        if ep_genre == "1":  # Primary genre only
            return self._get_primary_genre(ep_filter, ep_genres)
        elif ep_genre == "2":  # EIT categories
            return self._get_eit_genres(ep_filter, ep_genres)
        elif ep_genre == "3":  # All genres
            return ep_genres if ep_genres else ep_filter

        return []

    def _get_primary_genre(self, ep_filter: List, ep_genres: List) -> List[str]:
        """Get primary genre mapping"""
        genres = ep_genres if ep_genres else ep_filter

        for genre in genres:
            if "Movie" in genre or "movie" in genre:
                return ["Movie / Drama"]
            elif "News" in genre:
                return ["News / Current affairs"]
            elif "Sports" in genre:
                return ["Sports"]
            elif "Talk" in genre:
                return ["Talk show"]
            elif "Game show" in genre:
                return ["Game show / Quiz / Contest"]
            elif "Children" in genre:
                return ["Children's / Youth programs"]
            elif "Sitcom" in genre:
                return ["Variety show"]

        return ["Variety show"]  # Default

    def _get_eit_genres(self, ep_filter: List, ep_genres: List) -> List[str]:
        """Get EIT-style genre mapping"""
        genre_list = []
        all_genres = ep_genres if ep_genres else ep_filter

        for genre in all_genres:
            if genre != "Comedy":
                genre_list.append(genre)

        # Apply EIT transformations
        if any("Movie" in g for g in genre_list):
            genre_list.insert(0, "Movie / Drama")
        if any("News" in g for g in genre_list):
            genre_list.insert(0, "News / Current affairs")

        return genre_list
