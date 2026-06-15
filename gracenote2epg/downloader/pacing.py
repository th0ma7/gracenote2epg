"""
gracenote2epg.downloader.pacing - adaptive request pacing (AIMD)

The Gracenote API is gated by a server-side cumulative volume limit (AWS WAF):
it blocks after a few hundred requests, and concurrency only reaches that wall
sooner. The right objective is therefore the maximum *sustainable* request rate,
not peak throughput.

``RateController`` implements TCP-style AIMD on the request rate: additive
increase while requests succeed, multiplicative decrease on a rate-limit / WAF
signal. It converges to a sawtooth just below the server's ceiling and stays
there. See docs/parallel-download-redesign.md.

The clock and sleep functions are injectable so the controller is fully
testable without real time.
"""

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
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if not (0 < min_rate <= max_rate):
            raise ValueError("require 0 < min_rate <= max_rate")
        self._min_rate = min_rate
        self._max_rate = max_rate
        self._increase_step = increase_step
        self._decrease_factor = decrease_factor
        self._success_threshold = max(1, success_threshold)
        self._waf_cooldown = waf_cooldown
        self._clock = clock
        self._sleep = sleep

        self.rate = self._clamp(initial_rate)
        self._successes = 0
        self._last_request: Optional[float] = None

    def _clamp(self, rate: float) -> float:
        return max(self._min_rate, min(self._max_rate, rate))

    @property
    def interval(self) -> float:
        """Current minimum delay between requests, in seconds."""
        return 1.0 / self.rate

    def wait(self) -> float:
        """Block until the next request is allowed; returns the slept duration."""
        slept = 0.0
        now = self._clock()
        if self._last_request is not None:
            gap = self.interval - (now - self._last_request)
            if gap > 0:
                self._sleep(gap)
                slept = gap
        self._last_request = self._clock()
        return slept

    def on_success(self) -> None:
        """Additive increase: speed up after a streak of clean requests."""
        self._successes += 1
        if self._successes >= self._success_threshold:
            self._successes = 0
            self.rate = self._clamp(self.rate + self._increase_step)

    def on_rate_limited(self) -> None:
        """Multiplicative decrease: back off on a 429 / Too Many Requests."""
        self._successes = 0
        self.rate = self._clamp(self.rate * self._decrease_factor)

    def on_waf_block(self) -> None:
        """A hard block: back off and pause for a cooldown before resuming."""
        self.on_rate_limited()
        if self._waf_cooldown > 0:
            self._sleep(self._waf_cooldown)
            self._last_request = self._clock()
