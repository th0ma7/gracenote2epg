"""
Series details parser for gracenote2epg

Handles parsing of extended series details from gracenote.com API responses,
applying enhanced metadata to episode data. Contains only parsing logic.
"""

import calendar
import logging
import re
import time
from typing import Dict, Optional


class SeriesParser:
    """Parses extended series details"""
    
    def parse_series_details(self, episode_data: Dict, series_details: Dict, 
                            series_id: str) -> bool:
        """
        Parse and apply series details to episode data
        
        Args:
            episode_data: Episode data dictionary to enhance
            series_details: Series details JSON from API
            series_id: Series ID for logging
            
        Returns:
            bool: True if successful
        """
        try:
            # Extract and apply extended series description
            self._apply_series_description(episode_data, series_details, series_id)
            
            # Process images
            self._apply_series_images(episode_data, series_details)
            
            # Handle genres with movie detection
            self._apply_series_genres(episode_data, series_details, series_id)
            
            # Process credits for movies
            if series_id.startswith("MV"):
                self._apply_movie_credits(episode_data, series_details)
            
            # Process original air date from upcoming episodes
            self._apply_original_air_date(episode_data, series_details, series_id)
            
            return True
            
        except Exception as e:
            logging.warning(
                "Error processing series details for %s: %s",
                series_id,
                str(e),
            )
            return False
    
    def _apply_series_description(self, episode_data: Dict, series_details: Dict,
                                 series_id: str):
        """Extract and apply extended series description"""
        series_desc = series_details.get("seriesDescription")
        if series_desc and str(series_desc).strip():
            episode_data["epseriesdesc"] = str(series_desc).strip()
            logging.debug(
                "Applied extended series description for %s: %s",
                series_id,
                series_desc[:50] + "..." if len(series_desc) > 50 else series_desc,
            )

    def _apply_series_images(self, episode_data: Dict, series_details: Dict):
        """Apply series and background images"""
        episode_data["epimage"] = series_details.get("seriesImage")
        episode_data["epfan"] = series_details.get("backgroundImage")

    def _apply_series_genres(self, episode_data: Dict, series_details: Dict,
                            series_id: str):
        """Parse and apply genres with movie detection"""
        ep_genres = series_details.get("seriesGenres")
        
        # Special handling for movies
        if series_id.startswith("MV"): 
            ep_genres = "Movie|" + ep_genres if ep_genres else "Movie"
            
        if ep_genres:
            episode_data["epgenres"] = ep_genres.split("|")
            logging.debug("Applied genres for %s: %s", series_id, ep_genres)
    
    def _apply_movie_credits(self, episode_data: Dict, series_details: Dict):
        """Parse and apply credits for movies"""
        overview_tab = series_details.get("overviewTab", {})
        if isinstance(overview_tab, dict):
            cast_info = overview_tab.get("cast")
            if cast_info:
                episode_data["epcredits"] = cast_info
                logging.debug("Applied movie credits: %d cast members",
                             len(cast_info) if isinstance(cast_info, list) else 1)
    
    def _apply_original_air_date(self, episode_data: Dict, series_details: Dict,
                                series_id: str):
        """Parse original air date from upcoming episodes data"""
        ep_list = series_details.get("upcomingEpisodeTab", [])
        if not isinstance(ep_list, list):
            return

        ep_id = episode_data.get("epid", "")
        if not ep_id:
            return

        for airing in ep_list:
            if not isinstance(airing, dict):
                continue
                
            if ep_id.lower() == airing.get("tmsID", "").lower():
                # Process original air date for TV shows (not movies)
                if not series_id.startswith("MV"):
                    self._extract_original_air_date(episode_data, airing, series_id)
                    
                # Check for TBA listings
                self._check_tba_in_airing(airing, series_id)
                break

    def _extract_original_air_date(self, episode_data: Dict, airing: Dict, series_id: str):
        """Extract and format original air date"""
        try:
            orig_date = airing.get("originalAirDate")
            if orig_date and orig_date != "":
                # Handle date format - fix Z suffix if needed
                ep_oad = re.sub("Z", ":00Z", orig_date)
                timestamp = calendar.timegm(
                    time.strptime(ep_oad, "%Y-%m-%dT%H:%M:%SZ")
                )
                episode_data["epoad"] = str(timestamp)
                logging.debug("Applied original air date for %s: %s", series_id, orig_date)
        except Exception as e:
            logging.debug("Could not parse original air date for %s: %s", series_id, str(e))
    
    def _check_tba_in_airing(self, airing: Dict, series_id: str):
        """Check for TBA (To Be Announced) content in airing data"""
        try:
            episode_title = airing.get("episodeTitle", "")
            if episode_title and "TBA" in episode_title:
                logging.info("Found TBA listing in series %s: %s", series_id, episode_title)
        except Exception:
            pass

    def get_parsing_statistics(self) -> Dict:
        """Get parsing statistics (placeholder for future implementation)"""
        return {
            "series_processed": 0,  # Could be tracked if needed
            "descriptions_added": 0,  # Could be tracked if needed
            "genres_added": 0,  # Could be tracked if needed
            "air_dates_added": 0,  # Could be tracked if needed
        }
