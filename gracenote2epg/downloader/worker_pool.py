"""
gracenote2epg.downloader.worker_pool - bounded keep-alive worker pool

A small, fixed pool of long-lived workers, each owning ONE persistent connection
(its own session) and pulling tasks from a shared queue, so each worker
downloads its share serially over a reused connection. A single shared
``RateController`` (AIMD) caps the *combined* request rate and backs off globally
on a rate-limit / WAF signal — a safety backstop that stays out of the way on
normal small refreshes. See docs/parallel-download-redesign.md.

If the server keeps returning HTTP 429 (its cumulative-volume wall), the pool
gives up early instead of crawling forever: after a run of consecutive
rate-limited responses it aborts the remaining queue (accounting those items as
failed) so the process always terminates without a manual kill. The leftover
work is simply picked up on the next run.

The session factory and the per-task execute function are injected, so the pool
is fully testable without any network.
"""

import logging
import queue
import threading
from typing import Callable, List, Optional

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
        abort_after: int = 12,
    ):
        self._execute = execute
        self._workers = max(1, workers)
        self._session_factory = session_factory or (lambda: None)
        # Self-regulating governor: starts moderate (safe even on a cold run of
        # hundreds of new series), ramps up via AIMD while the server is happy,
        # and backs off on a 429/WAF signal.
        self._governor = governor or RateController(
            initial_rate=5.0,
            max_rate=20.0,
            min_rate=0.5,
            increase_step=0.5,
            success_threshold=10,
            decrease_factor=0.5,
        )
        self._on_progress = on_progress
        self._on_result = on_result
        # Stop hitting the server after this many consecutive rate-limited
        # responses (0 = never abort). Guards against an endless crawl when the
        # WAF wall stays shut.
        self._abort_after = abort_after
        self._gov_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        self._abort = threading.Event()
        # Aggregate request stats (one entry per attempt), for reporting.
        self.requests = 0
        self.rate_limited = 0
        self._consecutive_rate_limited = 0

    @property
    def governor(self) -> RateController:
        return self._governor

    @property
    def aborted(self) -> bool:
        return self._abort.is_set()

    def run(self, tasks: List[DownloadTask], max_attempts: int = 1) -> List[DownloadResult]:
        """Execute *tasks*; returns their final results (order not guaranteed).

        Failed tasks (including rate-limited ones) are re-queued at the **end**
        and retried up to ``max_attempts`` total, so a transient/blocked request
        is given another chance after the rest of the batch (and after the
        governor has backed off). If the server keeps rate-limiting, the pool
        aborts early (see module docstring) rather than looping.
        """
        if not tasks:
            return []
        self.requests = 0
        self.rate_limited = 0
        self._consecutive_rate_limited = 0
        self._abort.clear()

        # Queue carries (task, attempt_number).
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
            # Terminate on finalised count, not queue-empty, because failures get
            # re-queued (a worker could otherwise exit while a requeue is pending).
            while not sink.complete:
                try:
                    task, attempt = work.get(timeout=0.1)
                except queue.Empty:
                    continue
                if self._abort.is_set():
                    # Don't touch the server any more; account the item as failed
                    # so the pool finishes promptly instead of crawling.
                    sink.add(DownloadResult(task.task_id, success=False, error="aborted"))
                    continue
                result = self._process(session, task)
                if not result.success and attempt < max_attempts and not self._abort.is_set():
                    logging.debug("Requeue %s (attempt %d/%d)", task.task_id, attempt, max_attempts)
                    work.put((task, attempt + 1))
                else:
                    sink.add(result)
        finally:
            close = getattr(session, "close", None)
            if callable(close):
                close()

    def _process(self, session, task: DownloadTask) -> DownloadResult:
        """Pace (governed combined rate), run one request, feed the governor."""
        with self._gov_lock:
            self._governor.wait()
        logging.debug("Downloading %s", task.task_id)
        try:
            result = self._execute(session, task)
        except Exception as e:  # never let one task kill a worker
            logging.debug("Task %s raised: %s", task.task_id, e)
            result = DownloadResult(task.task_id, success=False, error=str(e))
        with self._gov_lock:
            if result.rate_limited:
                self._governor.on_rate_limited()
            elif result.success:
                self._governor.on_success()
        self._record(result)
        return result

    def _record(self, result: DownloadResult) -> None:
        """Update stats and trip the early-abort once the wall stays shut."""
        with self._stats_lock:
            self.requests += 1
            if result.rate_limited:
                self.rate_limited += 1
                self._consecutive_rate_limited += 1
            elif result.success:
                self._consecutive_rate_limited = 0
            consecutive = self._consecutive_rate_limited
        if result.rate_limited:
            logging.warning(
                "Rate-limited/blocked (HTTP %s) on %s",
                result.http_code or "?",
                result.task_id,
            )
        if self._abort_after and consecutive >= self._abort_after and not self._abort.is_set():
            self._abort.set()
            logging.warning(
                "Server rate-limited %d requests in a row (HTTP 429); stopping the parallel "
                "batch early. The remaining items will be downloaded on the next run.",
                consecutive,
            )


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
