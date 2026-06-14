"""
gracenote2epg.xmltv.media - <rating>, program <icon> and new/live detection.
"""

from typing import Dict


class MediaMixin:
    """<rating>, program <icon> and new/live detection."""

    def _write_enhanced_ratings(self, fh, episode_data: Dict):
        """Write enhanced rating information with MPAA system support"""
        rating = episode_data.get("eprating")
        if rating:
            # Map common ratings to MPAA system
            mpaa_ratings = {
                "G": "G",
                "PG": "PG",
                "PG-13": "PG-13",
                "R": "R",
                "NC-17": "NC-17",
                "TV-Y": "TV-Y",
                "TV-Y7": "TV-Y7",
                "TV-G": "TV-G",
                "TV-PG": "TV-PG",
                "TV-14": "TV-14",
                "TV-MA": "TV-MA",
            }

            # Check if it's an MPAA rating
            if rating in mpaa_ratings:
                fh.write(f'\t\t<rating system="MPAA">\n')
                fh.write(f"\t\t\t<value>{rating}</value>\n")
                fh.write(f"\t\t</rating>\n")
            else:
                # Generic rating
                fh.write(f"\t\t<rating>\n")
                fh.write(f"\t\t\t<value>{rating}</value>\n")
                fh.write(f"\t\t</rating>\n")


    def _write_program_icons(
        self,
        fh,
        episode_data: Dict,
        ep_icon: str,
        episode_key: str,
        use_extended_details: bool = True,
    ):
        """Write program icon information"""
        if episode_key.startswith("MV"):  # Movie
            if episode_data.get("epthumb"):
                fh.write(
                    f'\t\t<icon src="{self.ASSETS_BASE_URL}/g/{episode_data["epthumb"]}.jpg" />\n'
                )
        else:  # TV Show
            if ep_icon == "1":  # Series + episode icons
                # Only use epimage (from extended details) if xdetails=true
                if use_extended_details and episode_data.get("epimage"):
                    fh.write(
                        f'\t\t<icon src="{self.ASSETS_BASE_URL}/g/{episode_data["epimage"]}.jpg" />\n'
                    )
                elif episode_data.get("epthumb"):
                    fh.write(
                        f'\t\t<icon src="{self.ASSETS_BASE_URL}/g/{episode_data["epthumb"]}.jpg" />\n'
                    )
            elif ep_icon == "2":  # Episode icons only
                if episode_data.get("epthumb"):
                    fh.write(
                        f'\t\t<icon src="{self.ASSETS_BASE_URL}/g/{episode_data["epthumb"]}.jpg" />\n'
                    )


    def _is_new_or_live(self, episode_data: Dict) -> bool:
        """Check if episode is new or live"""
        flags = episode_data.get("epflag", [])
        if isinstance(flags, (list, tuple)):
            return any(flag in ["New", "Live"] for flag in flags)
        return False

