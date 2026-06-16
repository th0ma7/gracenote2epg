"""
gracenote2epg.downloader.concurrency - adaptive concurrency limiter (AIMD)

Complements the rate governor on a second axis: how MANY requests may be in
flight at once. It starts at the worker count, halves on a rate-limit / WAF
signal (collapsing toward a single worker), and ramps back up one slot at a time
after a streak of clean requests — a "wave" that rides just under the server's
concurrency tolerance. Workers acquire a slot before each request; the extras
block until a slot frees or the limit grows again.

Thread-safe via a single Condition. Fully synchronous and deterministic (no
sleeping), so it is testable without real threads beyond the ones under test.
"""

import threading


class ConcurrencyLimiter:
    """AIMD limiter on the number of concurrently in-flight requests."""

    def __init__(self, max_concurrency: int, *, success_threshold: int = 10):
        self._max = max(1, max_concurrency)
        self._limit = self._max
        self._active = 0
        self._successes = 0
        self._success_threshold = max(1, success_threshold)
        self._cond = threading.Condition()

    @property
    def limit(self) -> int:
        with self._cond:
            return self._limit

    @property
    def max_concurrency(self) -> int:
        return self._max

    def acquire(self) -> None:
        """Block until an in-flight slot is available, then take it."""
        with self._cond:
            while self._active >= self._limit:
                self._cond.wait()
            self._active += 1

    def release(self) -> None:
        """Return a slot and wake a waiter."""
        with self._cond:
            self._active -= 1
            self._cond.notify_all()

    def on_rate_limited(self) -> None:
        """Multiplicative decrease: collapse the in-flight ceiling toward 1."""
        with self._cond:
            self._successes = 0
            self._limit = max(1, self._limit // 2)
            # Ceiling lowered: current holders drain naturally; nothing to wake.

    def on_success(self) -> None:
        """Additive increase: re-open one slot after a clean streak."""
        with self._cond:
            self._successes += 1
            if self._successes >= self._success_threshold and self._limit < self._max:
                self._successes = 0
                self._limit += 1
                self._cond.notify_all()
