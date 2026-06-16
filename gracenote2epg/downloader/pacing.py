"""
gracenote2epg.downloader.pacing - adaptive request pacing (AIMD)

The Gracenote API is gated by a server-side cumulative volume limit (AWS WAF):
it blocks after a few hundred requests, and concurrency only reaches that wall
sooner. The right objective is therefore the maximum *sustainable* request rate,
not peak throughput.

``RateController`` implements TCP-style AIMD on the request rate: additive
increase while requests succeed, multiplicative decrease on a rate-limit / WAF
signal. It converges to a sawtooth just below the server's ceiling and stays
there. A per-request *jitter* spreads the spacing so the combined stream looks
organic rather than metronomic. The controller is thread-safe (the worker pool
shares one) and reserves each slot under a short lock, then sleeps *outside* it
so workers genuinely overlap. See docs/parallel-download-redesign.md.

The clock, sleep and rng functions are injectable so the controller is fully
testable without real time or randomness.
"""

import random
import threading
import time
from typing import Callable, Optional


class RateController:
    """AIMD pacer converging to the highest request rate that is not blocked."""

    def __init__(
        self,
        *,
        initial_rate: float = 2.0,
        min_rate: float = 0.3,
        max_rate: float = 8.0,
        increase_step: float = 0.2,
        decrease_factor: float = 0.5,
        success_threshold: int = 10,
        waf_cooldown: float = 20.0,
        jitter: float = 0.0,
        failure_base: float = 0.0,
        max_delay: float = 15.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ):
        if not (0 < min_rate <= max_rate):
            raise ValueError("require 0 < min_rate <= max_rate")
        self._min_rate = min_rate
        self._max_rate = max_rate
        self._increase_step = increase_step
        self._decrease_factor = decrease_factor
        self._success_threshold = max(1, success_threshold)
        self._waf_cooldown = waf_cooldown
        # Fraction (0..1) by which each gap is randomly stretched/shrunk.
        self._jitter = max(0.0, min(1.0, jitter))
        # Escalating per-request delay on a sustained wall: once past a couple of
        # consecutive 429s the gap grows ~failure_base*1.5^failures (capped at
        # max_delay), so each request is spaced increasingly far apart until one
        # lands in a reopened window — then a success resets it. 0 disables it.
        self._failure_base = max(0.0, failure_base)
        self._max_delay = max_delay
        self._clock = clock
        self._sleep = sleep
        self._rng = rng

        self._lock = threading.Lock()
        self.rate = self._clamp(initial_rate)
        self._successes = 0
        self._consecutive_failures = 0
        self._next_allowed: Optional[float] = None

    def _clamp(self, rate: float) -> float:
        return max(self._min_rate, min(self._max_rate, rate))

    @property
    def interval(self) -> float:
        """Current mean delay between requests, in seconds."""
        return 1.0 / self.rate

    def wait(self) -> float:
        """Block until the next request is allowed; returns the slept duration.

        Reserves the next slot under the lock (so the *combined* rate across
        workers is governed), jittering the gap, then sleeps outside the lock so
        workers overlap.
        """
        with self._lock:
            now = self._clock()
            gap = 1.0 / self.rate
            # On a sustained wall, escalate the per-request spacing (like a
            # backing-off client) so requests don't keep hammering the closed
            # window at the rate floor.
            if self._failure_base and self._consecutive_failures > 2:
                escalated = min(
                    self._failure_base * (1.5**self._consecutive_failures), self._max_delay
                )
                gap = max(gap, escalated)
            if self._jitter:
                gap *= 1.0 + (self._rng() * 2.0 - 1.0) * self._jitter
            start = now if self._next_allowed is None else max(now, self._next_allowed)
            self._next_allowed = start + gap
            sleep_for = start - now
        if sleep_for > 0:
            self._sleep(sleep_for)
        return sleep_for

    def on_success(self) -> None:
        """Additive increase: speed up after a streak of clean requests."""
        with self._lock:
            if self._consecutive_failures > 0:
                # Recovering from a wall: drop the long reserved gap so the next
                # request exploits the reopened window immediately instead of
                # waiting out the last escalated delay.
                self._consecutive_failures = 0
                self._next_allowed = None
            self._successes += 1
            if self._successes >= self._success_threshold:
                self._successes = 0
                self.rate = self._clamp(self.rate + self._increase_step)

    def on_rate_limited(self) -> None:
        """Multiplicative decrease: back off on a 429 / Too Many Requests."""
        with self._lock:
            self._successes = 0
            self._consecutive_failures += 1  # grows the escalating per-request delay
            self.rate = self._clamp(self.rate * self._decrease_factor)

    def on_waf_block(self) -> None:
        """A hard block: back off and pause for a cooldown before resuming."""
        self.on_rate_limited()
        if self._waf_cooldown > 0:
            self._sleep(self._waf_cooldown)
            with self._lock:
                self._next_allowed = self._clock()
