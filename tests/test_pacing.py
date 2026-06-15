"""Tests for the AIMD RateController and the download task abstractions."""

import unittest

from gracenote2epg.downloader.pacing import RateController
from gracenote2epg.downloader.tasks import DownloadResult, TaskMetrics


class FakeTime:
    """Manually-advanced clock + sleep that advances it."""

    def __init__(self):
        self.now = 0.0
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


class RateControllerBasicsTests(unittest.TestCase):
    def _rc(self, **kw):
        self.t = FakeTime()
        return RateController(clock=self.t.clock, sleep=self.t.sleep, **kw)

    def test_additive_increase_after_threshold(self):
        rc = self._rc(initial_rate=2.0, increase_step=0.5, success_threshold=3, max_rate=10)
        for _ in range(2):
            rc.on_success()
        self.assertEqual(rc.rate, 2.0)  # not yet
        rc.on_success()  # 3rd -> increase
        self.assertEqual(rc.rate, 2.5)

    def test_multiplicative_decrease_on_rate_limit(self):
        rc = self._rc(initial_rate=4.0, decrease_factor=0.5, min_rate=0.3)
        rc.on_rate_limited()
        self.assertEqual(rc.rate, 2.0)

    def test_rate_is_clamped(self):
        rc = self._rc(initial_rate=1.0, min_rate=0.5, max_rate=3.0, increase_step=5)
        for _ in range(100):
            rc.on_success()
        self.assertLessEqual(rc.rate, 3.0)
        for _ in range(100):
            rc.on_rate_limited()
        self.assertGreaterEqual(rc.rate, 0.5)

    def test_a_429_resets_the_success_streak(self):
        rc = self._rc(initial_rate=2.0, increase_step=0.5, success_threshold=3)
        rc.on_success()
        rc.on_success()
        rc.on_rate_limited()  # resets streak (and halves)
        rc.on_success()
        rc.on_success()
        self.assertEqual(rc.rate, 1.0)  # only the 429's halving applied, no increase yet


class RateControllerPacingTests(unittest.TestCase):
    def test_wait_respects_the_interval(self):
        t = FakeTime()
        rc = RateController(initial_rate=2.0, clock=t.clock, sleep=t.sleep)  # interval 0.5s
        rc.wait()  # first call: nothing to wait
        self.assertEqual(t.slept, [])
        # no real time passed -> next wait must sleep a full interval
        rc.wait()
        self.assertAlmostEqual(t.slept[-1], 0.5, places=6)

    def test_wait_accounts_for_elapsed_time(self):
        t = FakeTime()
        rc = RateController(initial_rate=2.0, clock=t.clock, sleep=t.sleep)  # interval 0.5
        rc.wait()
        t.now += 0.2  # 0.2s already elapsed
        rc.wait()
        self.assertAlmostEqual(t.slept[-1], 0.3, places=6)  # only the remainder

    def test_waf_block_backs_off_and_cools_down(self):
        t = FakeTime()
        rc = RateController(
            initial_rate=4.0,
            decrease_factor=0.5,
            waf_cooldown=15.0,
            clock=t.clock,
            sleep=t.sleep,
        )
        rc.on_waf_block()
        self.assertEqual(rc.rate, 2.0)  # backed off
        self.assertIn(15.0, t.slept)  # cooled down


class RateControllerConvergenceTests(unittest.TestCase):
    def test_converges_to_a_band_just_under_the_server_ceiling(self):
        """Simulate a server that blocks above a hidden sustainable ceiling."""
        t = FakeTime()
        ceiling = 5.0
        rc = RateController(
            initial_rate=1.0,
            min_rate=0.3,
            max_rate=12.0,
            increase_step=0.3,
            decrease_factor=0.5,
            success_threshold=5,
            clock=t.clock,
            sleep=t.sleep,
        )
        observed = []
        for _ in range(2000):
            rc.wait()
            t.now += 0.0001  # tiny processing time
            if rc.rate > ceiling:
                rc.on_rate_limited()
            else:
                rc.on_success()
            observed.append(rc.rate)

        tail = observed[-300:]
        # Never runs away above the ceiling by more than one increase step.
        self.assertLessEqual(max(tail), ceiling + 0.3 + 1e-6)
        # Keeps probing near the ceiling (doesn't collapse to the floor).
        self.assertGreaterEqual(max(tail), ceiling * 0.8)
        # Stays well above the minimum on average.
        self.assertGreater(sum(tail) / len(tail), ceiling * 0.45)


class TaskAbstractionTests(unittest.TestCase):
    def test_bytes_downloaded(self):
        self.assertEqual(DownloadResult("a", True, content=b"hello").bytes_downloaded, 5)
        self.assertEqual(DownloadResult("a", False).bytes_downloaded, 0)

    def test_metrics_success_and_cache_rates(self):
        m = TaskMetrics()
        m.record(DownloadResult("1", True, content=b"x" * 100, duration=1.0))
        m.record(DownloadResult("2", False, rate_limited=True))
        m.record_cached()
        m.record_cached()
        self.assertEqual(m.attempted, 2)
        self.assertEqual(m.success_rate, 50.0)
        self.assertEqual(m.rate_limited, 1)
        self.assertAlmostEqual(m.cache_hit_rate, 50.0)  # 2 cached of 4 processed


if __name__ == "__main__":
    unittest.main()
