"""
gracenote2epg.downloader.worker_pool - bounded keep-alive worker pool

A small, fixed pool of long-lived workers, each owning ONE persistent connection
(its own session) and pulling tasks from a shared queue, so each worker
downloads its share serially over a reused connection. A single shared
``RateController`` (AIMD) caps the *combined* request rate and backs off globally
on a rate-limit / WAF signal — a safety backstop that stays out of the way on
normal small refreshes. See docs/parallel-download-redesign.md.

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
        self._gov_lock = threading.Lock()
        self._stats_lock = threading.Lock()
        # Aggregate request stats (one entry per attempt), for reporting.
        self.requests = 0
        self.rate_limited = 0

    @property
    def governor(self) -> RateController:
        return self._governor

    def run(self, tasks: List[DownloadTask], max_attempts: int = 1) -> List[DownloadResult]:
        """Execute *tasks*; returns their final results (order not guaranteed).

        Failed tasks (including rate-limited ones) are re-queued at the **end**
        and retried up to ``max_attempts`` total, so a transient/blocked request
        is given another chance after the rest of the batch (and after the
        governor has backed off).
        """
        if not tasks:
            return []
        self.requests = 0
        self.rate_limited = 0

        # Queue carries (task, attempt_number).
        work: "queue.Queue" = queue.Queue()
        for task in tasks:
            work.put((task, 1))

        sink = _ResultSink(len(tasks), self._on_progress)
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
                result = self._process(session, task)
                if not result.success and attempt < max_attempts:
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
        with self._stats_lock:
            self.requests += 1
            if result.rate_limited:
                self.rate_limited += 1
        return result


class _ResultSink:
    """Thread-safe result collector with progress reporting."""

    def __init__(self, total: int, on_progress: Optional[ProgressFn]):
        self.results: List[DownloadResult] = []
        self._total = total
        self._on_progress = on_progress
        self._lock = threading.Lock()

    def add(self, result: DownloadResult) -> None:
        with self._lock:
            self.results.append(result)
            done = len(self.results)
        if self._on_progress:
            self._on_progress(done, self._total)

    @property
    def complete(self) -> bool:
        with self._lock:
            return len(self.results) >= self._total
