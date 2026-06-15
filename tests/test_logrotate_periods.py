"""Unit tests for the pure period math extracted into logrotate.periods."""

import unittest
from datetime import datetime

from gracenote2epg.logrotate import periods


class WeekStartTests(unittest.TestCase):
    def test_week_start_is_preceding_sunday_midnight(self):
        # 2026-06-10 is a Wednesday -> week starts Sunday 2026-06-07 00:00.
        ws = periods.get_week_start(datetime(2026, 6, 10, 15, 30, 45))
        self.assertEqual(ws, datetime(2026, 6, 7, 0, 0, 0))

    def test_sunday_maps_to_itself(self):
        ws = periods.get_week_start(datetime(2026, 6, 7, 23, 59))
        self.assertEqual(ws, datetime(2026, 6, 7, 0, 0, 0))


class PeriodInfoTests(unittest.TestCase):
    def test_daily_bounds_and_suffix(self):
        start, end, suffix = periods.get_period_info(
            "MIDNIGHT", "%Y-%m-%d", datetime(2026, 6, 14, 18, 5)
        )
        self.assertEqual(start, datetime(2026, 6, 14, 0, 0, 0))
        self.assertEqual(end, datetime(2026, 6, 14, 23, 59, 59))
        self.assertEqual(suffix, "2026-06-14")

    def test_monthly_bounds_handles_december_rollover(self):
        start, end, suffix = periods.get_period_info("MONTHLY", "%Y-%m", datetime(2026, 12, 20))
        self.assertEqual(start, datetime(2026, 12, 1, 0, 0, 0))
        self.assertEqual(end, datetime(2026, 12, 31, 23, 59, 59))
        self.assertEqual(suffix, "2026-12")

    def test_weekly_bounds(self):
        start, end, _ = periods.get_period_info("WEEKLY", "%Y-W%U", datetime(2026, 6, 10))
        self.assertEqual(start, datetime(2026, 6, 7, 0, 0, 0))
        self.assertEqual(end, datetime(2026, 6, 13, 23, 59, 59))


class PeriodCompleteTests(unittest.TestCase):
    def test_daily_past_is_complete(self):
        ps, pe, _ = periods.get_period_info("MIDNIGHT", "%Y-%m-%d", datetime(2026, 6, 12))
        self.assertTrue(periods.is_period_complete("MIDNIGHT", ps, pe, datetime(2026, 6, 14, 9)))

    def test_daily_today_is_incomplete(self):
        ps, pe, _ = periods.get_period_info("MIDNIGHT", "%Y-%m-%d", datetime(2026, 6, 14))
        self.assertFalse(periods.is_period_complete("MIDNIGHT", ps, pe, datetime(2026, 6, 14, 9)))

    def test_monthly_previous_month_is_complete(self):
        ps, pe, _ = periods.get_period_info("MONTHLY", "%Y-%m", datetime(2026, 5, 3))
        self.assertTrue(periods.is_period_complete("MONTHLY", ps, pe, datetime(2026, 6, 14)))


class NextRolloverTests(unittest.TestCase):
    def test_next_rollover_is_in_the_future(self):
        import time

        now = time.time()
        for when in ("MIDNIGHT", "WEEKLY", "MONTHLY"):
            self.assertGreater(periods.next_rollover_at(when, 86400), now)

    def test_unknown_mode_falls_back_to_interval(self):
        import time

        before = time.time()
        nr = periods.next_rollover_at("HOURLY", 3600)
        self.assertGreaterEqual(nr, before + 3600 - 1)


if __name__ == "__main__":
    unittest.main()
