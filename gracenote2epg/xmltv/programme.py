"""
gracenote2epg.xmltv.programme - Per-programme <programme> elements (DTD element order).
"""

import logging
import re
from typing import Dict, Any
from ..utils import TimeUtils, HtmlUtils


class ProgrammeMixin:
    """Per-programme <programme> elements (DTD element order)."""

    def _print_episodes(self, fh, schedule: Dict, config: Dict[str, Any]):
        """Print episode/program information - DTD compliant with enhanced metadata"""
        self.episode_count = 0
        enhanced_desc_count = 0
        missing_desc_count = 0

        # Configuration values
        use_extended_desc = config.get(
            "xdesc", False
        )  # Use extended series description AND add enhanced info
        use_extended_details = config.get("xdetails", False)  # Download extended details from API
        safe_titles = config.get("stitle", False)
        ep_genre = config.get("epgenre", "3")
        ep_icon = config.get("epicon", "1")

        try:
            logging.info("Writing Episodes to xmltv.xml file...")
            logging.info(
                "Configuration: xdesc=%s (controls description selection and enhanced info), xdetails=%s (controls API download)",
                use_extended_desc,
                use_extended_details,
            )

            # Count total episodes for progress tracking
            total_episodes = sum(
                1
                for station_id, station_data in schedule.items()
                for episode_key, episode_data in station_data.items()
                if not episode_key.startswith("ch") and episode_data.get("epstart")
            )

            logging.info("Total episodes to process: %d", total_episodes)

            # Progress tracking variables
            processed_episodes = 0
            last_progress_log = 0
            progress_interval = max(1, total_episodes // 20)  # Log every 5% (20 intervals)

            for station_id, station_data in schedule.items():
                for episode_key, episode_data in station_data.items():
                    if episode_key.startswith("ch"):  # Skip channel metadata
                        continue

                    try:
                        if not episode_data.get("epstart"):
                            continue

                        processed_episodes += 1

                        # Log progress
                        if (
                            processed_episodes - last_progress_log >= min(progress_interval, 1000)
                            or processed_episodes == total_episodes
                        ):
                            progress_percent = (
                                round((processed_episodes / total_episodes * 100))
                                if total_episodes > 0
                                else 0
                            )
                            logging.info(
                                "XMLTV generation progress: %d/%d episodes (%d%%)",
                                processed_episodes,
                                total_episodes,
                                progress_percent,
                            )
                            last_progress_log = processed_episodes

                        # === PREPARATION PHASE ===
                        start_time = TimeUtils.conv_time(float(episode_data["epstart"]))
                        stop_time = (
                            TimeUtils.conv_time(float(episode_data["epend"]))
                            if episode_data.get("epend")
                            else start_time
                        )
                        tz_offset = TimeUtils.get_timezone_offset()

                        # Detect language
                        program_id = episode_data.get("epid", "")
                        detected_language = "en"

                        if self.language_detector:
                            # Priority 1: Try to detect from extended description if available
                            if use_extended_desc and use_extended_details:
                                extended_desc = episode_data.get("epseriesdesc")
                                if extended_desc and str(extended_desc).strip():
                                    detected_language = self.language_detector.detect_language(
                                        str(extended_desc), program_id
                                    )

                            # Priority 2: Detect from basic description
                            if detected_language == "en":
                                basic_desc = episode_data.get("epdesc")
                                if basic_desc and str(basic_desc).strip():
                                    detected_language = self.language_detector.detect_language(
                                        str(basic_desc), program_id
                                    )

                        # Prepare description
                        final_description = self._prepare_description(
                            episode_data, detected_language, use_extended_desc, use_extended_details
                        )

                        if final_description:
                            enhanced_desc_count += 1
                        else:
                            missing_desc_count += 1

                        # === START XMLTV PROGRAMME ===
                        fh.write(
                            f'\t<programme start="{start_time} {tz_offset}" stop="{stop_time} {tz_offset}" channel="{station_id}.gracenote2epg">\n'
                        )

                        # 1. TITLE+
                        if episode_data.get("epshow"):
                            show_title = HtmlUtils.conv_html(episode_data["epshow"])
                            fh.write(
                                f'\t\t<title lang="{detected_language}">{show_title}</title>\n'
                            )

                        # 2. SUB-TITLE*
                        if episode_data.get("eptitle"):
                            episode_title = HtmlUtils.conv_html(episode_data["eptitle"])
                            if safe_titles:
                                episode_title = re.sub(r"[\\/*?:|]", "_", episode_title)
                            fh.write(
                                f'\t\t<sub-title lang="{detected_language}">{episode_title}</sub-title>\n'
                            )

                        # 3. DESC*
                        if final_description:
                            fh.write(
                                f'\t\t<desc lang="{detected_language}">{HtmlUtils.conv_html(final_description)}</desc>\n'
                            )

                        # 4. CREDITS?
                        self._write_credits_dtd_compliant(fh, episode_data, use_extended_details)

                        # 5. DATE?
                        if episode_data.get("epyear"):
                            fh.write(f'\t\t<date>{episode_data["epyear"]}</date>\n')

                        # 6. CATEGORY*
                        self._write_categories(
                            fh, episode_data, ep_genre, detected_language, use_extended_details
                        )

                        # 7. KEYWORD* (not used)

                        # 8. LANGUAGE? (only if xdetails=true)
                        if use_extended_details:
                            lang_names = {"fr": "Français", "en": "English", "es": "Español"}
                            lang_name = lang_names.get(detected_language, "English")
                            fh.write(f"\t\t<language>{lang_name}</language>\n")

                        # 9. ORIG-LANGUAGE? (not used)

                        # 10. LENGTH?
                        if episode_data.get("eplength"):
                            fh.write(
                                f'\t\t<length units="minutes">{episode_data["eplength"]}</length>\n'
                            )

                        # 11. ICON*
                        self._write_program_icons(
                            fh, episode_data, ep_icon, episode_key, use_extended_details
                        )

                        # 12. URL* (not used)

                        # 13. COUNTRY* (only if xdetails=true)
                        if use_extended_details:
                            country_code = "US"
                            zipcode = config.get("zipcode", "")
                            if zipcode:
                                if re.match(r"^[A-Z][0-9][A-Z]", zipcode.replace(" ", "")):
                                    country_code = "CA"
                                elif zipcode.isdigit() and len(zipcode) == 5:
                                    country_code = "US"
                            fh.write(f"\t\t<country>{country_code}</country>\n")

                        # 14. EPISODE-NUM* (Proper xmltv_ns format with spaces)
                        dd_progid = episode_data.get("epid", "")
                        if dd_progid and len(dd_progid) >= 4:
                            fh.write(
                                f'\t\t<episode-num system="dd_progid">{dd_progid[:-4]}.{dd_progid[-4:]}</episode-num>\n'
                            )

                        if episode_data.get("epsn") and episode_data.get("epen"):
                            season = str(episode_data["epsn"]).zfill(2)
                            episode_num = str(episode_data["epen"]).zfill(2)
                            fh.write(
                                f'\t\t<episode-num system="onscreen">S{season}E{episode_num}</episode-num>\n'
                            )

                            # XMLTV numbering with spaces and proper format (zero-based)
                            season_xmltv = int(episode_data["epsn"]) - 1
                            episode_xmltv = int(episode_data["epen"]) - 1
                            # Format: "season . episode . part/total" with spaces
                            fh.write(
                                f'\t\t<episode-num system="xmltv_ns">{season_xmltv} . {episode_xmltv} . </episode-num>\n'
                            )

                        # 15-16. VIDEO/AUDIO BLOCK (only if xdetails=true)
                        if use_extended_details:
                            # Get release year once for both video and audio
                            release_year = episode_data.get("epyear")

                            # 15. VIDEO?
                            fh.write("\t\t<video>\n")
                            fh.write("\t\t\t<present>yes</present>\n")
                            fh.write("\t\t\t<colour>yes</colour>\n")

                            # Aspect ratio based on age
                            if (
                                release_year
                                and str(release_year).isdigit()
                                and int(release_year) < 1960
                            ):
                                fh.write("\t\t\t<aspect>4:3</aspect>\n")
                            else:
                                fh.write("\t\t\t<aspect>16:9</aspect>\n")
                            fh.write("\t\t</video>\n")

                            # 16. AUDIO?
                            fh.write("\t\t<audio>\n")
                            fh.write("\t\t\t<present>yes</present>\n")

                            # Proper stereo detection from tags
                            tags = episode_data.get("eptags", [])
                            has_stereo = False

                            if isinstance(tags, list):
                                has_stereo = (
                                    "STEREO" in tags
                                    or "Stereo" in tags
                                    or "DD 5.1" in tags
                                    or "DD" in tags
                                )
                            elif isinstance(tags, str):
                                has_stereo = "STEREO" in tags.upper()

                            # Modern content defaults to stereo
                            if not has_stereo and release_year:
                                if str(release_year).isdigit() and int(release_year) >= 1990:
                                    has_stereo = True  # Assume stereo for modern content

                            stereo_value = "stereo" if has_stereo else "mono"
                            fh.write(f"\t\t\t<stereo>{stereo_value}</stereo>\n")
                            fh.write("\t\t</audio>\n")

                        # 17. PREVIOUSLY-SHOWN?
                        if not self._is_new_or_live(episode_data):
                            fh.write("\t\t<previously-shown")
                            if episode_data.get("epoad") and int(episode_data["epoad"]) > 0:
                                orig_time = TimeUtils.conv_time(float(episode_data["epoad"]))
                                fh.write(f' start="{orig_time} {tz_offset}"')
                            fh.write(" />\n")

                        # 18. PREMIERE?
                        flags = episode_data.get("epflag", [])
                        if isinstance(flags, (list, tuple)) and "Premiere" in flags:
                            fh.write("\t\t<premiere />\n")

                        # 19. LAST-CHANCE?
                        if isinstance(flags, (list, tuple)) and "Finale" in flags:
                            fh.write("\t\t<last-chance />\n")

                        # 20. NEW?
                        if isinstance(flags, (list, tuple)) and "New" in flags:
                            fh.write("\t\t<new />\n")

                        # 21. SUBTITLES*
                        if episode_data.get("eptags") and "CC" in episode_data["eptags"]:
                            fh.write('\t\t<subtitles type="teletext" />\n')

                        # 22. RATING* (ENHANCED: Support for MPAA system)
                        self._write_enhanced_ratings(fh, episode_data)

                        # 23. STAR-RATING*
                        if episode_data.get("epstar"):
                            fh.write(
                                f'\t\t<star-rating>\n\t\t\t<value>{episode_data["epstar"]}/4</value>\n\t\t</star-rating>\n'
                            )

                        # 24. IMAGE* (typed poster/backdrop/still - must be last)
                        self._write_program_images(fh, episode_data, use_extended_details)

                        fh.write("\t</programme>\n")
                        self.episode_count += 1

                    except Exception as e:
                        logging.exception("Error processing episode %s: %s", episode_key, str(e))

            # Log statistics
            logging.info(
                "Description statistics: Episodes=%d, Enhanced_desc=%d, Missing_desc=%d",
                self.episode_count,
                enhanced_desc_count,
                missing_desc_count,
            )

        except Exception as e:
            logging.exception("Exception in _print_episodes: %s", str(e))

