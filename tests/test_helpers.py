"""Unit tests for the pure helpers in gracenote2epg.utils."""

import re
import unittest
from unittest import mock

from gracenote2epg.utils import TimeUtils, HtmlUtils


class TimezoneOffsetTests(unittest.TestCase):
    """Regression coverage for the signed +-HHMM XMLTV offset (see 2.0.0 fix)."""

    def _offset_for(self, *, timezone, altzone, daylight, isdst):
        """Call get_timezone_offset() with the time module values patched."""
        fake_lt = mock.Mock()
        fake_lt.tm_isdst = isdst
        with mock.patch("gracenote2epg.utils.time") as t:
            t.daylight = daylight
            t.timezone = timezone
            t.altzone = altzone
            t.localtime.return_value = fake_lt
            return TimeUtils.get_timezone_offset()

    def test_utc_is_signed(self):
        # UTC used to emit "0000" with no sign; must now be "+0000".
        self.assertEqual(self._offset_for(timezone=0, altzone=0, daylight=0, isdst=0), "+0000")

    def test_eastern_standard(self):
        # EST = UTC-5, no DST
        self.assertEqual(
            self._offset_for(timezone=18000, altzone=14400, daylight=1, isdst=0),
            "-0500",
        )

    def test_eastern_daylight(self):
        # EDT = UTC-4, DST active
        self.assertEqual(
            self._offset_for(timezone=18000, altzone=14400, daylight=1, isdst=1),
            "-0400",
        )

    def test_newfoundland_half_hour(self):
        # NST = UTC-3:30 (non-zero minutes used to be truncated to -0300)
        self.assertEqual(
            self._offset_for(timezone=12600, altzone=9000, daylight=0, isdst=0),
            "-0330",
        )

    def test_india_positive_half_hour(self):
        # IST = UTC+5:30 (used to render as "0500")
        self.assertEqual(
            self._offset_for(timezone=-19800, altzone=-19800, daylight=0, isdst=0),
            "+0530",
        )

    def test_format_is_always_signed_hhmm(self):
        out = self._offset_for(timezone=0, altzone=0, daylight=0, isdst=0)
        self.assertRegex(out, r"^[+-]\d{4}$")


class GuideBlockFilenameTests(unittest.TestCase):
    def test_format(self):
        name = TimeUtils.guide_block_filename(1_700_000_000)
        self.assertRegex(name, r"^\d{10}\.json\.gz$")

    def test_floors_to_three_hour_block(self):
        # Two timestamps inside the same 3-hour block share one filename;
        # crossing the boundary changes it.
        base = TimeUtils.get_standard_block_time(1_700_000_000)
        ts = base.timestamp()
        same = TimeUtils.guide_block_filename(ts + 3600)  # +1h, same block
        later = TimeUtils.guide_block_filename(ts + 3 * 3600)  # +3h, next block
        self.assertEqual(TimeUtils.guide_block_filename(ts), same)
        self.assertNotEqual(TimeUtils.guide_block_filename(ts), later)


class ConvHtmlTests(unittest.TestCase):
    def test_none_returns_empty(self):
        self.assertEqual(HtmlUtils.conv_html(None), "")

    def test_escapes_xml_metacharacters(self):
        self.assertEqual(
            HtmlUtils.conv_html("<a> & \"b\" 'c'"),
            "&lt;a&gt; &amp; &quot;b&quot; &apos;c&apos;",
        )

    def test_no_double_escaping(self):
        # Pre-escaped entities are unescaped first, then re-escaped once.
        self.assertEqual(HtmlUtils.conv_html("Tom &amp; Jerry"), "Tom &amp; Jerry")


if __name__ == "__main__":
    unittest.main()
