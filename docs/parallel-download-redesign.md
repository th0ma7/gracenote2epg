# Download pacing redesign (WIP)

Rethink of the parallel download manager prototyped in PR #2
(`parallel_download` branch). **Work in progress** — started as a foundation to
continue from; nothing here is wired into the running downloader yet.

## Why PR #2 stalled (the diagnosis)

PR #2 built a sophisticated parallel system (~4000 lines): `UnifiedDownloadManager`
→ `PreciseWorkerPool` (ThreadPoolExecutor recreated on the fly) →
`AdaptiveStrategy` (tunes the **worker count** from success rate / latency / 429s)
→ `RateLimiter` + `WAFDetector` → `EventDrivenMonitor` (real-time, web dashboard
on port 9989). It blocked after ~300–500 series items.

The root cause is **structural, not a tuning bug**:

- The bottleneck is a **server-side cumulative volume limit** (Gracenote sits
  behind an AWS WAF). It blocks after a few hundred requests per session/IP,
  regardless of how clever the client is.
- **Concurrency reaches that ceiling *sooner*** — more workers = a higher request
  rate = the WAF's volume threshold trips faster. Hence "you had to reduce the
  parallelism before getting there."
- Reactive adaptation (cut workers when 429s appear) is **too late**: by the time
  429s show up, the burst has already tripped the WAF, and a session/IP block
  doesn't clear by simply reducing workers.

**Conclusion:** for this API the goal is **maximum *sustainable* throughput**
(stay just under the WAF's sustained-rate ceiling indefinitely), not peak
throughput. Optimizing concurrency optimizes the wrong axis.

## What to keep from PR #2

- The clean **task/result abstractions** (`DownloadTask` / `DownloadResult` /
  `TaskMetrics`) — elegant and reusable.
- The **WAF detection + backoff** idea — but applied to a single paced stream.
- The **strategy profiles** idea (conservative/balanced/aggressive) — repurposed
  as *pacing* profiles, not worker counts.
- The **progress/monitoring** idea — drastically simplified (a callback; no web
  dashboard).

## What to drop / rethink

- The worker-pool / adaptive-worker-count machinery (`worker_pool.py`,
  `adaptive.py`, the pool-recreation in `manager.py`).
- The 659-line monitoring + port-9989 web API.
- It predates the modular refactor; the redesign targets the current
  `gracenote2epg/downloader/` package.

## Proposed design

1. **Pacing, not parallelism.** A `RateController` using **AIMD** (TCP-style):
   additive-increase of the request *rate* on sustained success, multiplicative-
   decrease on a 429/WAF signal. It converges to a sawtooth just under the
   server's ceiling and stays there — the highest rate that doesn't get blocked.
2. **Tiny, targeted concurrency.** Optional 2–3 workers **only for guide blocks**
   (few, larger files → overlap latency with negligible volume). Series details
   (the 300–500 problem) stay a single paced stream.
3. **Cache is still the main lever.** After the first run, 95 %+ of series are
   cached, so only the *new* delta downloads — pacing only needs to be good
   enough for the cold run / large deltas. (Future: resume across runs so a
   blocked run continues next time.)
4. **Simple reporting:** a progress callback + a stats summary (`TaskMetrics`).

## Status / next steps

- [x] `downloader/tasks.py` — `DownloadTask` / `DownloadResult` / `TaskMetrics`.
- [x] `downloader/pacing.py` — `RateController` (AIMD) + WAF cooldown, with tests.
- [ ] `PacedDownloader` that drives tasks through the controller (single stream
      + optional small guide concurrency), reusing the existing HTTP engine /
      WAF detection in `downloader/base.py`.
- [ ] Wire into `SeriesDownloader` / `GuideDownloader` behind a flag; compare
      against the current sequential path on a cold run.
- [ ] Decide config surface (a `download` strategy profile in the config).
