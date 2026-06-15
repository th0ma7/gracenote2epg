# Download pacing redesign (WIP)

Rethink of the parallel download manager prototyped in PR #2
(`parallel_download` branch). **Work in progress** — started as a foundation to
continue from; nothing here is wired into the running downloader yet.

## Why PR #2 stalled (revised after real testing)

PR #2 built a sophisticated parallel system (~4000 lines): `UnifiedDownloadManager`
→ `PreciseWorkerPool` (ThreadPoolExecutor recreated on the fly) →
`AdaptiveStrategy` (tunes the **worker count**) → `RateLimiter` + `WAFDetector`
→ `EventDrivenMonitor` (web dashboard on port 9989). It blocked after ~300–500
series items.

**Measured against the live API** (see findings below), the likely culprit is the
**connection pattern, not request volume**:

- Sequential downloads **never block**, even for large runs — the server tolerates
  a steady stream fine.
- PR #2's series path used `urllib` with a **new TLS connection per request**, run
  **in parallel** → a *connection-churn* pattern (many simultaneous handshakes)
  that AWS WAF flags as bot/DDoS-like. That, not the request count, most plausibly
  tripped the block around 300–500.
- **Keep-alive worker connections** (a few persistent, browser-like connections,
  each reused serially) avoid that pattern.

### Live findings (gracenote overviewDetails)

- **Keep-alive is a big win**: first request ~0.38s (cold TLS), then ~0.13–0.15s
  per request on the reused connection (~2.5× faster).
- **Single User-Agent is fine** (no rotation needed): 40 sequential requests, no
  block. Rotating the UA on one session is *less* natural than a real browser.
- **Bounded parallelism works**: 4 keep-alive workers → ~24 req/s, ~3.4× speedup,
  no block.

**Conclusion:** keep parallelism — it is the real win, especially for frequent
small refreshes (6–12h) where the download delta is small and far below any wall.
Use **bounded keep-alive workers** for speed, with a shared rate governor as a
safety backstop for cold/full runs.

## What to keep from PR #2

- The clean **task/result abstractions** (`DownloadTask` / `DownloadResult` /
  `TaskMetrics`) — elegant and reusable.
- **Bounded parallelism** — it is the real win (3–4× on small/frequent refreshes).
- The **WAF detection + backoff** idea — as a shared safety governor.
- The **strategy profiles** idea — repurposed as small profiles (worker count +
  rate cap).
- The **progress** idea — a simple callback; no web dashboard.

## What to drop / rethink

- The **adaptive-worker-count + pool-recreation** machinery (`worker_pool.py`'s
  ThreadPoolExecutor churn, `adaptive.py`). Use a fixed small pool of long-lived
  keep-alive workers instead.
- The **per-request new connection** for series (`urllib`) — replace with
  keep-alive (likely the actual cause of the old parallel block).
- **User-Agent rotation** — a single constant UA is fine and more natural.
- The 659-line monitoring + port-9989 web API.
- It predates the modular refactor; the redesign targets the current
  `gracenote2epg/downloader/` package.

## Proposed design

1. **Bounded keep-alive worker pool.** A small fixed pool (default ~4), each
   worker owning **one persistent connection** (its own `requests.Session`) and
   pulling tasks from a shared queue — so each worker downloads its share
   serially over a reused connection. This is the speed win for the frequent
   small refreshes.
2. **Shared rate governor (backstop).** A single `RateController` (AIMD) shared
   by all workers caps the *combined* request rate and, on a 429/WAF signal,
   backs off globally (and may shed workers). On a normal small refresh it never
   triggers → full parallel speed; it protects cold/full runs.
3. **Cache stays the main lever.** After the first run, 95 %+ of series are
   cached, so only the *new* delta downloads.
4. **Simple reporting:** a progress callback + `TaskMetrics` summary.

## Status / next steps

- [x] `downloader/tasks.py` — `DownloadTask` / `DownloadResult` / `TaskMetrics`.
- [x] `downloader/pacing.py` — `RateController` (AIMD) shared governor, with tests.
- [x] Live validation: keep-alive ~2.5× per-request; single UA fine; 4 keep-alive
      workers ~3.4× and no block.
- [x] `PacedWorkerPool`: fixed pool of keep-alive workers sharing the governor.
- [x] Real Gracenote HTTP adapter (`http.py`); single data host confirmed (no
      mirror), so no multi-source config.
- [x] Wired into `SeriesDownloader` behind the `dlworkers` config (1=sequential,
      2-8=fixed, `auto`=4 + self-regulating governor; default `auto`). Schema
      bumped to **version 7**. Live end-to-end: 24 series 15.4s → 4.5s (~3.4×).
- [x] Extended to guide blocks (same `dlworkers`); grid switched to HTTPS.
- [x] **Stress test (500 series, 4 keep-alive workers): 498 OK, 0 rate-limited,
      no block.** The governor ramped 5→20 req/s and held at 20 through all 500.
      Confirms the old ~300-500 block was connection churn (urllib new connection
      per request × parallel), not request volume — keep-alive workers avoid it.

### Notes / possible follow-ups

- The parallel `execute()` makes a single attempt (no per-request retry); the
  sequential path retries. On a cold run ~0.4% of series may fail transiently
  (e.g. giant 1.5 MB responses exceeding the timeout); they are simply
  re-attempted on the next run (not cached). Adding a light retry to `execute`
  would close this gap if desired.
