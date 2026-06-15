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

    @property
    def governor(self) -> RateController:
        return self._governor

    def run(self, tasks: List[DownloadTask]) -> List[DownloadResult]:
        """Execute *tasks*; returns their results (order not guaranteed)."""
        if not tasks:
            return []

        work: "queue.Queue[DownloadTask]" = queue.Queue()
        for task in tasks:
            work.put(task)

        results: List[DownloadResult] = []
        results_lock = threading.Lock()
        total = len(tasks)
        completed = 0

        def report(result: DownloadResult) -> None:
            nonlocal completed
            with results_lock:
                results.append(result)
                completed += 1
                progress = completed
            if self._on_progress:
                self._on_progress(progress, total)

        def worker() -> None:
            session = self._session_factory()
            try:
                while True:
                    try:
                        task = work.get_nowait()
                    except queue.Empty:
                        return
                    # Release at the governed combined rate (serialised), then
                    # run the request itself outside the lock so workers overlap.
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
                    report(result)
                    work.task_done()
            finally:
                close = getattr(session, "close", None)
                if callable(close):
                    close()

        n = min(self._workers, total)
        threads = [threading.Thread(target=worker, daemon=True) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return results
