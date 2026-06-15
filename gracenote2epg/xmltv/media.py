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
                fh.write('\t\t<rating system="MPAA">\n')
                fh.write(f"\t\t\t<value>{rating}</value>\n")
                fh.write("\t\t</rating>\n")
            else:
                # Generic rating
                fh.write("\t\t<rating>\n")
                fh.write(f"\t\t\t<value>{rating}</value>\n")
                fh.write("\t\t</rating>\n")

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
                    f'\t\t<icon src="{self.ASSETS_BASE_URL}/{episode_data["epthumb"]}.jpg" />\n'
                )
        else:  # TV Show
            if ep_icon == "1":  # Series + episode icons
                # Only use epimage (from extended details) if xdetails=true
                if use_extended_details and episode_data.get("epimage"):
                    fh.write(
                        f'\t\t<icon src="{self.ASSETS_BASE_URL}/{episode_data["epimage"]}.jpg" />\n'
                    )
                elif episode_data.get("epthumb"):
                    fh.write(
                        f'\t\t<icon src="{self.ASSETS_BASE_URL}/{episode_data["epthumb"]}.jpg" />\n'
                    )
            elif ep_icon == "2":  # Episode icons only
                if episode_data.get("epthumb"):
                    fh.write(
                        f'\t\t<icon src="{self.ASSETS_BASE_URL}/{episode_data["epthumb"]}.jpg" />\n'
                    )

    def _write_program_images(self, fh, episode_data: Dict, use_extended_details: bool = True):
        """Write typed <image> elements (poster/backdrop/still).

        Uses the DTD's dedicated <image> element (with a real type attribute),
        unlike <icon> which cannot be typed. Must be emitted last in
        <programme> per the DTD content model. The legacy <icon> is kept for
        consumers that only read it. poster/backdrop come from the extended
        series details; the episode still comes from the guide thumbnail.
        """

        def image(img_type, orient, code):
            fh.write(
                f'\t\t<image type="{img_type}" orient="{orient}">'
                f"{self.ASSETS_BASE_URL}/{code}.jpg</image>\n"
            )

        if use_extended_details:
            if episode_data.get("epimage"):
                image("poster", "P", episode_data["epimage"])
            if episode_data.get("epfan"):
                image("backdrop", "L", episode_data["epfan"])

        if episode_data.get("epthumb"):
            image("still", "L", episode_data["epthumb"])

    def _is_new_or_live(self, episode_data: Dict) -> bool:
        """Check if episode is new or live"""
        flags = episode_data.get("epflag", [])
        if isinstance(flags, (list, tuple)):
            return any(flag in ["New", "Live"] for flag in flags)
        return False
