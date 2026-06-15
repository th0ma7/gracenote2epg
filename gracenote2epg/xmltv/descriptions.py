"""
gracenote2epg.xmltv.descriptions - Description selection and enhanced-info enrichment.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Optional


class DescriptionsMixin:
    """Description selection and enhanced-info enrichment."""

    def _prepare_description(
        self,
        episode_data: Dict,
        detected_language: str,
        use_extended_desc: bool,
        use_extended_details: bool,
    ) -> Optional[str]:
        """
        Prepare final description based on xdesc setting

        Behavior:
        - xdesc=false: Use basic guide description WITHOUT any enhanced info
        - xdesc=true: Use extended series description (if available) WITH enhanced info

        Args:
            episode_data: Episode data dictionary
            detected_language: Detected language for translations
            use_extended_desc: Whether to use extended descriptions and add enhanced info (xdesc setting)
            use_extended_details: Whether extended details were downloaded (xdetails setting)
        """
        try:
            base_description = None

            # Select which description to use
            if use_extended_desc and use_extended_details:
                # xdesc=true AND xdetails=true: Try to use extended series description
                extended_desc = episode_data.get("epseriesdesc")
                if extended_desc and str(extended_desc).strip():
                    base_description = str(extended_desc).strip()
                    logging.debug(
                        "Using extended series description for %s",
                        episode_data.get("epshow", "Unknown"),
                    )
                else:
                    # Fall back to basic if extended not available
                    basic_desc = episode_data.get("epdesc")
                    base_description = str(basic_desc).strip() if basic_desc else ""
                    logging.debug(
                        "Extended description not available, using basic for %s",
                        episode_data.get("epshow", "Unknown"),
                    )
            else:
                # xdesc=false OR xdetails=false: Use basic description from guide
                basic_desc = episode_data.get("epdesc")
                base_description = str(basic_desc).strip() if basic_desc else ""
                logging.debug(
                    "Using basic guide description for %s (xdesc=%s, xdetails=%s)",
                    episode_data.get("epshow", "Unknown"),
                    use_extended_desc,
                    use_extended_details,
                )

            # Only add enhanced info if xdesc=true
            if base_description:
                if use_extended_desc:
                    # xdesc=true: Add enhanced info (year, rating, flags, etc.)
                    # but WITHOUT S##E## as Kodi already displays it
                    return self._add_enhanced_info_to_basic_desc(
                        base_description,
                        episode_data,
                        detected_language,
                        include_season_episode=False,
                    )
                else:
                    # xdesc=false: Return description as-is, no enhancements
                    return base_description

            return None

        except Exception as e:
            logging.warning(
                "Error preparing description for episode %s: %s",
                episode_data.get("epid", "unknown"),
                str(e),
            )
            return None

    def _add_enhanced_info_to_basic_desc(
        self,
        base_desc: str,
        episode_data: Dict,
        language: str,
        include_season_episode: bool = False,
    ) -> str:
        """
        Add enhanced info (with translations) to basic description

        Added parameter to control whether to include S##E## info
        (default False as Kodi already displays this)
        """
        try:
            # Build additional info with translations
            additional_info = []

            # Add year for movies/shows
            if episode_data.get("epyear") and str(episode_data["epyear"]) != "0":
                additional_info.append(str(episode_data["epyear"]))

            # Add season/episode info ONLY if requested (by default NO as Kodi shows it)
            if include_season_episode and episode_data.get("epsn") and episode_data.get("epen"):
                try:
                    season_ep = f"S{int(episode_data['epsn']):02d}E{int(episode_data['epen']):02d}"
                    additional_info.append(season_ep)
                except (ValueError, TypeError):
                    pass

            # Add premiere date if available
            if (
                episode_data.get("epoad")
                and str(episode_data["epoad"]).isdigit()
                and int(episode_data["epoad"]) > 0
            ):
                try:
                    is_dst = time.daylight and time.localtime().tm_isdst > 0
                    tz_offset_seconds = time.altzone if is_dst else time.timezone
                    orig_date = int(episode_data["epoad"]) + tz_offset_seconds
                    premiere_date = datetime.fromtimestamp(orig_date).strftime("%Y-%m-%d")
                    # Use language detector for translation
                    premiered_text = (
                        self.language_detector.get_translated_term("premiered", language)
                        if self.language_detector
                        else "Premiered"
                    )
                    additional_info.append(f"{premiered_text}: {premiere_date}")
                except (ValueError, TypeError, OSError):
                    pass

            # Add rating if available
            if episode_data.get("eprating") and str(episode_data["eprating"]).strip():
                # Use language detector for translation
                rated_text = (
                    self.language_detector.get_translated_term("rated", language)
                    if self.language_detector
                    else "Rated"
                )
                additional_info.append(f"{rated_text}: {episode_data['eprating']}")

            # Add flags with translations
            flags = []
            if episode_data.get("epflag") and isinstance(episode_data["epflag"], (list, tuple)):
                if "New" in episode_data["epflag"]:
                    new_text = (
                        self.language_detector.get_translated_term("new", language)
                        if self.language_detector
                        else "NEW"
                    )
                    flags.append(new_text)
                if "Live" in episode_data["epflag"]:
                    live_text = (
                        self.language_detector.get_translated_term("live", language)
                        if self.language_detector
                        else "LIVE"
                    )
                    flags.append(live_text)
                if "Premiere" in episode_data["epflag"]:
                    premiere_text = (
                        self.language_detector.get_translated_term("premiere", language)
                        if self.language_detector
                        else "PREMIERE"
                    )
                    flags.append(premiere_text)
                if "Finale" in episode_data["epflag"]:
                    finale_text = (
                        self.language_detector.get_translated_term("finale", language)
                        if self.language_detector
                        else "FINALE"
                    )
                    flags.append(finale_text)

            if episode_data.get("eptags") and isinstance(episode_data["eptags"], (list, tuple)):
                if "CC" in episode_data["eptags"]:
                    flags.append("CC")
                if "HD" in episode_data["eptags"]:
                    flags.append("HD")

            if flags:
                additional_info.append(" | ".join(flags))

            if additional_info:
                info_str = " | ".join(additional_info)
                enhanced_description = f"{base_desc} • {info_str}"
                logging.debug(
                    "Enhanced description created for %s: added %d info items in %s (S##E## excluded)",
                    episode_data.get("epshow", "Unknown"),
                    len(additional_info),
                    language,
                )
                return enhanced_description

            return base_desc

        except Exception as e:
            logging.warning(
                "Error enhancing basic description for episode %s: %s",
                episode_data.get("epid", "unknown"),
                str(e),
            )
            return base_desc
