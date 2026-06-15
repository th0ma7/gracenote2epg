"""
gracenote2epg.xmltv.stations - Channel/station <channel> elements.
"""

import logging
from collections import OrderedDict
from typing import Dict
from ..utils import HtmlUtils


class StationsMixin:
    """Channel/station <channel> elements."""

    def _print_stations(self, fh, schedule: Dict):
        """Print station/channel information"""
        self.station_count = 0

        try:
            logging.info("Writing Stations to xmltv.xml file...")

            # Sort stations by channel number, fallback to call sign
            try:
                schedule_sort = OrderedDict(
                    sorted(
                        schedule.items(),
                        key=lambda x: (
                            int(x[1]["chnum"].split(".")[0])
                            if x[1].get("chnum", "").replace(".", "").isdigit()
                            else float("inf")
                        ),
                    )
                )
            except (ValueError, TypeError):
                schedule_sort = OrderedDict(
                    sorted(schedule.items(), key=lambda x: x[1].get("chfcc", ""))
                )

            for station_id, station_data in schedule_sort.items():
                fh.write(f'\t<channel id="{station_id}.gracenote2epg">\n')

                # TVheadend channel name (if available)
                if station_data.get("chtvh"):
                    tvh_name = HtmlUtils.conv_html(station_data["chtvh"])
                    fh.write(f"\t\t<display-name>{tvh_name}</display-name>\n")

                # Channel number and call sign
                if station_data.get("chnum") and station_data.get("chfcc"):
                    ch_num = station_data["chnum"]
                    ch_fcc = station_data["chfcc"]
                    ch_name = station_data.get("chnam", "")

                    fh.write(
                        f"\t\t<display-name>{ch_num} {HtmlUtils.conv_html(ch_fcc)}</display-name>\n"
                    )

                    if ch_name and ch_name != "INDEPENDENT":
                        fh.write(
                            f"\t\t<display-name>{HtmlUtils.conv_html(ch_name)}</display-name>\n"
                        )

                    fh.write(f"\t\t<display-name>{HtmlUtils.conv_html(ch_fcc)}</display-name>\n")
                    fh.write(f"\t\t<display-name>{ch_num}</display-name>\n")

                elif station_data.get("chfcc"):
                    ch_fcc = station_data["chfcc"]
                    fh.write(f"\t\t<display-name>{HtmlUtils.conv_html(ch_fcc)}</display-name>\n")

                elif station_data.get("chnum"):
                    ch_num = station_data["chnum"]
                    fh.write(f"\t\t<display-name>{ch_num}</display-name>\n")

                # Channel icon
                if station_data.get("chicon"):
                    icon_url = station_data["chicon"]
                    if not icon_url.startswith("http"):
                        icon_url = f"http:{icon_url}"
                    fh.write(f'\t\t<icon src="{icon_url}" />\n')

                fh.write("\t</channel>\n")
                self.station_count += 1

        except Exception as e:
            logging.exception("Exception in _print_stations: %s", str(e))
