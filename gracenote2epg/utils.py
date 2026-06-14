"""
gracenote2epg.utils - Time and HTML utilities

Provides time/date helpers (TimeUtils) and HTML/XML escaping (HtmlUtils)
for the gracenote2epg system. Cache management lives in gracenote2epg.cache.
"""

import calendar
import html
import time
from datetime import datetime, timedelta
from typing import Optional


class TimeUtils:
    """Time and date utilities"""

    @staticmethod
    def get_standard_block_time(timestamp: float) -> datetime:
        """Convert timestamp to standardized 3-hour block time (0,3,6,9,12,15,18,21)"""
        dt = datetime.fromtimestamp(timestamp)
        # Calculate standardized 3-hour block (0,3,6,9,12,15,18,21)
        standard_hour = (dt.hour // 3) * 3
        standard_dt = dt.replace(hour=standard_hour, minute=0, second=0, microsecond=0)
        return standard_dt

    @staticmethod
    def guide_block_filename(grid_time: float) -> str:
        """Cache filename for the 3-hour guide block covering ``grid_time``.

        Single source of truth for the YYYYMMDDHH.json.gz convention shared by
        the downloader (writes blocks) and the parser (reads them).
        """
        return TimeUtils.get_standard_block_time(grid_time).strftime("%Y%m%d%H") + ".json.gz"

    @staticmethod
    def conv_time(timestamp: float) -> str:
        """Convert timestamp to XMLTV time format (local time like zap2epg)"""
        return time.strftime("%Y%m%d%H%M%S", time.localtime(int(timestamp)))

    @staticmethod
    def get_timezone_offset() -> str:
        """Get local timezone offset as a signed XMLTV ``±HHMM`` string.

        Conforms to the XMLTV date format regardless of the host timezone:
        always emits a sign and handles offsets with non-zero minutes
        (e.g. Newfoundland -0330, India +0530). UTC yields ``+0000``.
        """
        is_dst = time.daylight and time.localtime().tm_isdst > 0
        offset_seconds = -(time.altzone if is_dst else time.timezone)
        sign = "+" if offset_seconds >= 0 else "-"
        offset_seconds = abs(offset_seconds)
        return "%s%02d%02d" % (sign, offset_seconds // 3600, (offset_seconds % 3600) // 60)

    @staticmethod
    def calculate_guide_time_range(grid_time_start: float, guide_days: int) -> tuple:
        """Calculate time range covered by the guide"""
        guide_start = grid_time_start
        guide_end = grid_time_start + (guide_days * 24 * 3600)

        # Round to standard 3h blocks (0,3,6,9,12,15,18,21)
        start_dt = TimeUtils.get_standard_block_time(guide_start)
        end_dt = TimeUtils.get_standard_block_time(guide_end)

        # Ensure we cover the complete range
        if end_dt.timestamp() <= guide_end:
            end_dt = end_dt + timedelta(hours=3)

        return start_dt, end_dt

    @staticmethod
    def parse_gracenote_time(value: Optional[str], fix_missing_seconds: bool = False) -> Optional[int]:
        """Convert a Gracenote ISO-8601 UTC timestamp (YYYY-MM-DDTHH:MM:SSZ) to
        epoch seconds, or None if it is empty/unparseable.

        Set fix_missing_seconds=True for originalAirDate values that omit the
        seconds field (inserts ':00' before the trailing Z).
        """
        if not value:
            return None
        if fix_missing_seconds:
            value = value.replace("Z", ":00Z")
        try:
            return calendar.timegm(time.strptime(value, "%Y-%m-%dT%H:%M:%SZ"))
        except (ValueError, TypeError):
            return None


class HtmlUtils:
    """HTML/XML utilities"""

    @staticmethod
    def conv_html(data) -> str:
        """Convert data to HTML-safe format for XMLTV with proper entity normalization"""
        if data is None:
            return ""

        data = str(data)

        try:
            data = html.unescape(data)
        except Exception:
            pass

        data = data.replace("&", "&amp;")  # & -> &amp;
        data = data.replace('"', "&quot;")  # " -> &quot;
        data = data.replace("'", "&apos;")  # ' -> &apos;
        data = data.replace("<", "&lt;")  # < -> &lt;
        data = data.replace(">", "&gt;")  # > -> &gt;

        return data
