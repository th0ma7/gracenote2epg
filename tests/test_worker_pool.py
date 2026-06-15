"""Tests for the PacedWorkerPool (keep-alive workers + shared governor)."""

import threading
import unittest

from gracenote2epg.downloader.pacing import RateController
from gracenote2epg.downloader.worker_pool import PacedWorkerPool
from gracenote2epg.downloader.tasks import DownloadResult, DownloadTask


def instant_governor(**kw):
    """A RateController whose wait() never actually sleeps (test-fast)."""
    return RateController(clock=lambda: 0.0, sleep=lambda s: None, **kw)


def tasks(n):
    return [DownloadTask(task_id=str(i), url="u", task_type="series_details") for i in range(n)]


class FakeSession:
    _counter = 0
    _lock = threading.Lock()

    def __init__(self):
        with FakeSession._lock:
            FakeSession._counter += 1
            self.id = FakeSession._counter
        self.handled = 0
        self.closed = False

    def close(self):
        self.closed = True


class CompletenessTests(unittest.TestCase):
    def test_all_tasks_get_a_result(self):
        def execute(session, task):
            return DownloadResult(task.task_id, success=True, content=b"x")

        pool = PacedWorkerPool(execute, workers=4, governor=instant_governor())
        results = pool.run(tasks(50))
        self.assertEqual(len(results), 50)
        self.assertEqual({r.task_id for r in results}, {str(i) for i in range(50)})
        self.assertTrue(all(r.success for r in results))

    def test_empty_tasks(self):
        pool = PacedWorkerPool(lambda s, t: None, governor=instant_governor())
        self.assertEqual(pool.run([]), [])

    def test_single_worker(self):
        pool = PacedWorkerPool(
            lambda s, t: DownloadResult(t.task_id, True), workers=1, governor=instant_governor()
        )
        self.assertEqual(len(pool.run(tasks(10))), 10)

    def test_a_failing_task_does_not_kill_the_worker(self):
        def execute(session, task):
            if task.task_id == "3":
                raise RuntimeError("boom")
            return DownloadResult(task.task_id, success=True)

        results = PacedWorkerPool(execute, workers=2, governor=instant_governor()).run(tasks(10))
        self.assertEqual(len(results), 10)  # all accounted for
        self.assertFalse(next(r for r in results if r.task_id == "3").success)


class KeepAliveTests(unittest.TestCase):
    def test_workers_reuse_one_session_each(self):
        FakeSession._counter = 0
        created = []
        clock = threading.Lock()

        def factory():
            s = FakeSession()
            with clock:
                created.append(s)
            return s

        def execute(session, task):
            session.handled += 1
            return DownloadResult(task.task_id, success=True)

        pool = PacedWorkerPool(
            execute, workers=4, session_factory=factory, governor=instant_governor()
        )
        pool.run(tasks(60))
        # At most one session per worker (persistent, reused), not one per task.
        self.assertLessEqual(len(created), 4)
        self.assertEqual(sum(s.handled for s in created), 60)
        self.assertTrue(all(s.closed for s in created))  # sessions closed at the end


class ProgressTests(unittest.TestCase):
    def test_progress_reaches_total(self):
        seen = []
        lock = threading.Lock()

        def on_progress(done, total):
            with lock:
                seen.append((done, total))

        pool = PacedWorkerPool(
            lambda s, t: DownloadResult(t.task_id, True),
            workers=3,
            governor=instant_governor(),
            on_progress=on_progress,
        )
        pool.run(tasks(20))
        self.assertEqual(len(seen), 20)
        self.assertEqual(max(d for d, _ in seen), 20)
        self.assertTrue(all(total == 20 for _, total in seen))


class GovernorBackstopTests(unittest.TestCase):
    def test_governor_backs_off_on_rate_limits_but_pool_completes(self):
        # Fake server: rate-limits the first few requests, then succeeds.
        state = {"n": 0}
        lock = threading.Lock()

        def execute(session, task):
            with lock:
                state["n"] += 1
                limited = state["n"] <= 5
            return DownloadResult(task.task_id, success=not limited, rate_limited=limited)

        gov = instant_governor(initial_rate=8.0, decrease_factor=0.5, min_rate=0.5)
        pool = PacedWorkerPool(execute, workers=4, governor=gov)
        results = pool.run(tasks(40))
        self.assertEqual(len(results), 40)  # all processed, no deadlock
        # The governor reacted to the early 429s (rate pulled below the start).
        self.assertLess(gov.rate, 8.0)


class RetryTests(unittest.TestCase):
    def test_failed_task_is_retried_and_can_succeed(self):
        attempts = {}
        lock = threading.Lock()

        def execute(session, task):
            with lock:
                attempts[task.task_id] = attempts.get(task.task_id, 0) + 1
                n = attempts[task.task_id]
            # task "2" fails on its first attempt, succeeds on the retry
            ok = not (task.task_id == "2" and n == 1)
            return DownloadResult(task.task_id, success=ok, rate_limited=not ok)

        pool = PacedWorkerPool(execute, workers=1, governor=instant_governor())
        results = pool.run(tasks(3), max_attempts=2)
        self.assertEqual(len(results), 3)
        self.assertTrue(next(r for r in results if r.task_id == "2").success)
        self.assertEqual(attempts["2"], 2)  # retried once

    def test_exhausted_retries_finalise_as_failure(self):
        def execute(session, task):
            return DownloadResult(task.task_id, success=False)

        pool = PacedWorkerPool(execute, workers=2, governor=instant_governor())
        results = pool.run(tasks(5), max_attempts=2)
        self.assertEqual(len(results), 5)  # no deadlock; all finalised
        self.assertTrue(all(not r.success for r in results))
        self.assertEqual(pool.requests, 10)  # 5 tasks x 2 attempts

    def test_default_is_no_retry(self):
        def execute(session, task):
            return DownloadResult(task.task_id, success=False)

        pool = PacedWorkerPool(execute, workers=2, governor=instant_governor())
        pool.run(tasks(4))
        self.assertEqual(pool.requests, 4)  # one attempt each

    def test_stats_count_requests_and_rate_limited(self):
        def execute(session, task):
            return DownloadResult(task.task_id, success=False, rate_limited=True)

        pool = PacedWorkerPool(execute, workers=2, governor=instant_governor())
        pool.run(tasks(4), max_attempts=1)
        self.assertEqual(pool.requests, 4)
        self.assertEqual(pool.rate_limited, 4)


if __name__ == "__main__":
    unittest.main()
