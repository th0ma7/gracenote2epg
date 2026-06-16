"""
gracenote2epg.downloader.worker_pool - bounded keep-alive worker pool

A small, fixed pool of long-lived workers, each owning ONE persistent connection
(its own session) and pulling tasks from a shared queue, so each worker
downloads its share serially over a reused connection.

Two adaptive controls ride on top, both reacting to the server's HTTP 429 / WAF
signal:

* a shared **rate** governor (AIMD on requests/second, with per-request jitter)
  so the combined stream stays under the server's sustainable rate and looks
  organic rather than metronomic — the "adaptive delay" applied on every
  request, with one worker or several;
* an adaptive **concurrency** limiter (AIMD on how many requests are in flight)
  that collapses toward a single worker on a 429 and ramps back up after a clean
  streak — a "wave" that finds the server's concurrency tolerance.

When the server keeps refusing, the pool **rides the wall** instead of giving up:
it collapses to a single worker, **cools down** to let the server's window reopen
(re-queuing the blocked items rather than failing them), and ramps back up once
requests succeed again — repeating as needed. It only **gives up** (deferring the
rest to the next run) if several cooldowns in a row produce no success at all, so
the process always terminates without a manual kill.

The session factory and the per-task execute function are injected, so the pool
is fully testable without any network.
"""

import logging
import queue
import threading
from typing import Callable, List, Optional

from .concurrency import ConcurrencyLimiter
from .pacing import RateController
from .tasks import DownloadResult, DownloadTask

# (session, task) -> DownloadResult
ExecuteFn = Callable[[object, DownloadTask], DownloadResult]
ProgressFn = Callable[[int, int], None]
ResultFn = Callable[[DownloadResult], None]


class PacedWorkerPool:
    """Run download tasks across a fixed pool of keep-alive workers."""

    def __init__(
        self,
        execute: ExecuteFn,
        *,
        workers: int = 4,
        session_factory: Optional[Callable[[], object]] = None,
        governor: Optional[RateController] = None,
        on_progress: Optional[ProgressFn] = None,
        on_result: Optional[ResultFn] = None,
        adaptive_concurrency: bool = True,
        block_threshold: int = 8,
        max_block_cooldowns: int = 5,
    ):
        self._execute = execute
        self._workers = max(1, workers)
        self._session_factory = session_factory or (lambda: None)
        # Self-regulating rate governor: starts moderate (safe even on a cold run
        # of hundreds of new series), ramps up via AIMD while the server is
        # happy, backs off on a 429/WAF signal, jitters each gap so the stream
        # looks organic, and pauses (waf_cooldown) when asked to cool down.
        self._governor = governor or RateController(
            initial_rate=5.0,
            max_rate=20.0,
            min_rate=0.5,
            increase_step=0.5,
            success_threshold=10,
            decrease_factor=0.5,
            jitter=0.35,
            waf_cooldown=30.0,
        )
        # Adaptive concurrency: collapse the in-flight count on 429, ramp back on
        # success. Disabled -> all workers always active (fixed concurrency).
        self._limiter = ConcurrencyLimiter(self._workers) if adaptive_concurrency else None
        self._on_progress = on_progress
        self._on_result = on_result
        # Wall handling: after this many consecutive 429s, cool down to let the
        # server recover; give up only after this many cooldowns produce no
        # success (0 disables both -> never cool down / never give up).
        self._block_threshold = block_threshold
        self._max_block_cooldowns = max_block_cooldowns
        self._stats_lock = threading.Lock()
        self._cooldown_lock = threading.Lock()  # only one worker cools at a time
        self._abort = threading.Event()
        # Aggregate request stats (one entry per attempt), for reporting.
        self.requests = 0
        self.rate_limited = 0
        self._consecutive_rate_limited = 0
        self._fruitless_cooldowns = 0

    @property
    def governor(self) -> RateController:
        return self._governor

    @property
    def aborted(self) -> bool:
        return self._abort.is_set()

    @property
    def concurrency_limit(self) -> int:
        return self._limiter.limit if self._limiter else self._workers

    def run(self, tasks: List[DownloadTask], max_attempts: int = 1) -> List[DownloadResult]:
        """Execute *tasks*; returns their final results (order not guaranteed).

        Genuine errors are re-queued at the end and retried up to ``max_attempts``
        total. Rate-limited (429) results are re-queued **without** consuming that
        budget — the pool rides the wall (see module docstring) and only gives up
        after repeated fruitless cooldowns.
        """
        if not tasks:
            return []
        self.requests = 0
        self.rate_limited = 0
        self._consecutive_rate_limited = 0
        self._fruitless_cooldowns = 0
        self._abort.clear()

        # Queue carries (task, error_attempt_number).
        work: "queue.Queue" = queue.Queue()
        for task in tasks:
            work.put((task, 1))

        sink = _ResultSink(len(tasks), self._on_progress, self._on_result)
        n = min(self._workers, len(tasks))
        threads = [
            threading.Thread(target=self._worker_loop, args=(work, sink, max_attempts), daemon=True)
            for _ in range(n)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return sink.results

    def _worker_loop(self, work: "queue.Queue", sink: "_ResultSink", max_attempts: int) -> None:
        """One worker: own a persistent session, drain the queue (with requeue)."""
        session = self._session_factory()
        try:
            # Terminate on finalised count, not queue-empty, because items get
            # re-queued (a worker could otherwise exit while a requeue is pending).
            while not sink.complete:
                try:
                    task, attempt = work.get(timeout=0.1)
                except queue.Empty:
                    continue
                if self._abort.is_set():
                    # Gave up on the wall; account remaining items as failed so
                    # the pool finishes promptly (the next run picks them up).
                    sink.add(DownloadResult(task.task_id, success=False, error="deferred"))
                    continue
                result = self._process_gated(session, task)
                if result.success:
                    sink.add(result)
                elif result.rate_limited and not self._abort.is_set():
                    # Ride the wall: retry later without spending the error budget.
                    logging.debug("Requeue %s (rate-limited, riding the wall)", task.task_id)
                    work.put((task, attempt))
                elif not result.success and attempt < max_attempts and not self._abort.is_set():
                    logging.debug("Requeue %s (attempt %d/%d)", task.task_id, attempt, max_attempts)
                    work.put((task, attempt + 1))
                else:
                    sink.add(result)
        finally:
            close = getattr(session, "close", None)
            if callable(close):
                close()

    def _process_gated(self, session, task: DownloadTask) -> DownloadResult:
        """Acquire an in-flight slot (adaptive concurrency), then process."""
        if self._limiter is not None:
            self._limiter.acquire()
        try:
            result = self._process(session, task)
        finally:
            if self._limiter is not None:
                self._limiter.release()
        # Feed the concurrency wave after releasing the slot.
        if self._limiter is not None:
            if result.rate_limited:
                self._limiter.on_rate_limited()
            elif result.success:
                self._limiter.on_success()
        return result

    def _process(self, session, task: DownloadTask) -> DownloadResult:
        """Pace (governed jittered rate), run one request, feed the governor."""
        slept = self._governor.wait()
        logging.debug(
            "  Downloading %s (adaptive delay %.2fs, rate %.1f/s)",
            task.task_id,
            slept,
            self._governor.rate,
        )
        try:
            result = self._execute(session, task)
        except Exception as e:  # never let one task kill a worker
            logging.debug("Task %s raised: %s", task.task_id, e)
            result = DownloadResult(task.task_id, success=False, error=str(e))
        if result.rate_limited:
            self._governor.on_rate_limited()
        elif result.success:
            self._governor.on_success()
        self._note(result)
        return result

    def _note(self, result: DownloadResult) -> None:
        """Update stats; cool down on a sustained wall, recover on success."""
        with self._stats_lock:
            self.requests += 1
            if result.rate_limited:
                self.rate_limited += 1
                self._consecutive_rate_limited += 1
            elif result.success:
                # Recovered: forget the streak and the cooldown budget.
                self._consecutive_rate_limited = 0
                self._fruitless_cooldowns = 0
            consecutive = self._consecutive_rate_limited

        if not result.rate_limited:
            return

        logging.warning(
            "Rate-limited/blocked (HTTP %s) on %s", result.http_code or "?", result.task_id
        )
        if self._block_threshold and consecutive >= self._block_threshold:
            self._cool_down()

    def _cool_down(self) -> None:
        """Collapsed-and-still-blocked: pause to let the server's window reopen.

        Only one worker cools down at a time. After ``max_block_cooldowns``
        cooldowns without any intervening success, give up (defer the rest to the
        next run) so the run always terminates.
        """
        if not self._cooldown_lock.acquire(blocking=False):
            return  # another worker is already cooling down
        try:
            with self._stats_lock:
                self._consecutive_rate_limited = 0
                self._fruitless_cooldowns += 1
                cooldowns = self._fruitless_cooldowns
            if self._max_block_cooldowns and cooldowns > self._max_block_cooldowns:
                if not self._abort.is_set():
                    self._abort.set()
                    logging.warning(
                        "Still rate-limited after %d cooldowns; deferring the rest to the next "
                        "run (it will resume once the server's window reopens).",
                        cooldowns - 1,
                    )
                return
            logging.warning(
                "Rate-limit wall hit; collapsing to a single worker and cooling down "
                "(%d/%d) to let the server recover.",
                cooldowns,
                self._max_block_cooldowns,
            )
            self._governor.on_waf_block()  # backs off + sleeps the cooldown
        finally:
            self._cooldown_lock.release()


class _ResultSink:
    """Thread-safe result collector with progress + per-result callbacks."""

    def __init__(
        self,
        total: int,
        on_progress: Optional[ProgressFn],
        on_result: Optional[ResultFn] = None,
    ):
        self.results: List[DownloadResult] = []
        self._total = total
        self._on_progress = on_progress
        self._on_result = on_result
        self._lock = threading.Lock()

    def add(self, result: DownloadResult) -> None:
        with self._lock:
            self.results.append(result)
            done = len(self.results)
        # Persist/handle this result as soon as it is final (save-as-you-go), so
        # an interrupted or aborted run keeps everything fetched so far.
        if self._on_result:
            self._on_result(result)
        if self._on_progress:
            self._on_progress(done, self._total)

    @property
    def complete(self) -> bool:
        with self._lock:
            return len(self.results) >= self._total
