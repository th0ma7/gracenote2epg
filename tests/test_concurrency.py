"""Tests for the adaptive ConcurrencyLimiter (the 'wave')."""

import threading
import unittest

from gracenote2epg.downloader.concurrency import ConcurrencyLimiter


class ConcurrencyLimiterTests(unittest.TestCase):
    def test_starts_at_max(self):
        self.assertEqual(ConcurrencyLimiter(4).limit, 4)

    def test_collapses_toward_one_on_rate_limit(self):
        c = ConcurrencyLimiter(8)
        c.on_rate_limited()
        self.assertEqual(c.limit, 4)
        c.on_rate_limited()
        self.assertEqual(c.limit, 2)
        c.on_rate_limited()
        self.assertEqual(c.limit, 1)
        c.on_rate_limited()
        self.assertEqual(c.limit, 1)  # floor at 1

    def test_ramps_back_up_after_success_streak(self):
        c = ConcurrencyLimiter(4, success_threshold=3)
        c.on_rate_limited()  # 4 -> 2
        c.on_rate_limited()  # 2 -> 1
        self.assertEqual(c.limit, 1)
        for _ in range(3):
            c.on_success()
        self.assertEqual(c.limit, 2)  # one slot re-opened
        for _ in range(3):
            c.on_success()
        self.assertEqual(c.limit, 3)

    def test_does_not_exceed_max(self):
        c = ConcurrencyLimiter(2, success_threshold=1)
        for _ in range(20):
            c.on_success()
        self.assertEqual(c.limit, 2)

    def test_acquire_release_bounds_inflight(self):
        # With limit collapsed to 1, only one acquire succeeds until a release.
        c = ConcurrencyLimiter(4)
        c.on_rate_limited()
        c.on_rate_limited()  # limit = 1
        c.acquire()

        got = threading.Event()

        def second():
            c.acquire()  # must block until the first releases
            got.set()
            c.release()

        t = threading.Thread(target=second, daemon=True)
        t.start()
        self.assertFalse(got.wait(0.2))  # still blocked
        c.release()  # frees the single slot
        self.assertTrue(got.wait(1.0))  # now it proceeds
        t.join(1.0)


if __name__ == "__main__":
    unittest.main()
