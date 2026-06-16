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
        # A permanently shut wall: rides it (escalating delay), then gives up.
        def execute(session, task):
            return DownloadResult(task.task_id, success=False, rate_limited=True)

        pool = PacedWorkerPool(
            execute,
            workers=2,
            governor=instant_governor(),
            give_up_after=4,
        )
        results = pool.run(tasks(4), max_attempts=1)
        self.assertEqual(len(results), 4)
        self.assertTrue(pool.aborted)
        self.assertEqual(pool.rate_limited, pool.requests)  # every request was a 429
        self.assertGreater(pool.requests, 0)


class WallHandlingTests(unittest.TestCase):
    def test_gives_up_after_persistent_429s_and_terminates(self):
        # A server stuck behind its WAF wall: every request is rate-limited.
        def execute(session, task):
            return DownloadResult(task.task_id, success=False, rate_limited=True)

        pool = PacedWorkerPool(
            execute,
            workers=4,
            governor=instant_governor(),
            give_up_after=8,
        )
        results = pool.run(tasks(500), max_attempts=2)

        # It must STOP on its own (cooldowns that never recover -> give up)...
        self.assertTrue(pool.aborted)
        # ...account every task exactly once so run() returns...
        self.assertEqual(len(results), 500)
        self.assertEqual({r.task_id for r in results}, {str(i) for i in range(500)})
        self.assertTrue(all(not r.success for r in results))
        # ...and it must have stopped EARLY rather than hammering all 500.
        self.assertLess(pool.requests, 500)

    def test_rides_the_wall_then_recovers_without_giving_up(self):
        # First 20 requests are blocked, then the server recovers.
        state = {"n": 0}
        lock = threading.Lock()

        def execute(session, task):
            with lock:
                state["n"] += 1
                limited = state["n"] <= 20
            return DownloadResult(task.task_id, success=not limited, rate_limited=limited)

        pool = PacedWorkerPool(
            execute,
            workers=4,
            governor=instant_governor(),
            give_up_after=30,
        )
        results = pool.run(tasks(60), max_attempts=1)

        self.assertFalse(pool.aborted)  # recovered instead of giving up
        self.assertEqual(len(results), 60)
        # The blocked items were re-queued (not failed) and succeeded on retry.
        self.assertTrue(all(r.success for r in results))


class AdaptiveConcurrencyTests(unittest.TestCase):
    def test_concurrency_collapses_under_429_then_completes(self):
        # Server rate-limits the first 30 requests, then is happy.
        state = {"n": 0}
        lock = threading.Lock()
        limits = []

        def execute(session, task):
            with lock:
                state["n"] += 1
                limited = state["n"] <= 30
            limits.append(pool.concurrency_limit)
            return DownloadResult(task.task_id, success=not limited, rate_limited=limited)

        pool = PacedWorkerPool(execute, workers=8, governor=instant_governor(), give_up_after=50)
        results = pool.run(tasks(120), max_attempts=1)

        self.assertEqual(len(results), 120)  # all accounted, no deadlock
        self.assertFalse(pool.aborted)  # rode it out, recovered
        self.assertLess(min(limits), 8)  # the in-flight ceiling collapsed
        self.assertEqual(min(limits), 1)  # all the way down to a single worker

    def test_disabling_adaptive_concurrency_keeps_full_width(self):
        seen = []

        def execute(session, task):
            seen.append(pool.concurrency_limit)
            return DownloadResult(task.task_id, success=False, rate_limited=True)

        pool = PacedWorkerPool(
            execute,
            workers=4,
            governor=instant_governor(),
            adaptive_concurrency=False,
            give_up_after=8,
        )
        results = pool.run(tasks(20), max_attempts=1)
        self.assertTrue(all(limit == 4 for limit in seen))  # never collapses
        self.assertTrue(pool.aborted)  # still terminates (gives up on the wall)
        self.assertEqual(len(results), 20)


class OnResultTests(unittest.TestCase):
    def test_on_result_called_once_per_final_result(self):
        seen = []
        lock = threading.Lock()

        def on_result(result):
            with lock:
                seen.append(result.task_id)

        pool = PacedWorkerPool(
            lambda s, t: DownloadResult(t.task_id, True),
            workers=3,
            governor=instant_governor(),
            on_result=on_result,
        )
        pool.run(tasks(30))
        self.assertEqual(sorted(seen, key=int), [str(i) for i in range(30)])


if __name__ == "__main__":
    unittest.main()
