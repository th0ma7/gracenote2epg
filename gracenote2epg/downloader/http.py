"""
gracenote2epg.downloader.http - Gracenote HTTP adapter for the worker pool

A per-worker keep-alive session factory and a single-request ``execute`` function
the PacedWorkerPool drives. All three known scrapers (gracenote2epg, zap2epg,
zap2it-GuideScraping) hit the same single host, so there is no alternate data
source to configure (unlike images). Live testing showed keep-alive cuts
per-request latency ~2.5x and a single User-Agent is sufficient.
"""

import logging
import time

import requests
from requests.adapters import HTTPAdapter

from .tasks import DownloadResult, DownloadTask

# A single, stable, browser-like User-Agent (rotation proved unnecessary).
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"

_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json, text/html, application/xhtml+xml, */*",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Keep-Alive": "timeout=60, max=100",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

# AWS WAF / challenge markers (same set the legacy engine watches for).
_WAF_MARKERS = (
    "Human Verification",
    "captcha-container",
    "AwsWafIntegration",
    "Access Denied",
    "challenge.js",
)


def make_session() -> requests.Session:
    """Create a persistent keep-alive session (one reused connection)."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    adapter = HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0, pool_block=True)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _looks_blocked(status_code: int, text: str) -> bool:
    if status_code in (403, 429, 503):
        return True
    return any(marker in text for marker in _WAF_MARKERS)


def execute(session, task: DownloadTask, timeout: float = 15.0) -> DownloadResult:
    """Perform one download for *task* over the worker's persistent *session*.

    POST when the task carries a body (series details), GET otherwise (guide
    blocks). Returns a DownloadResult; ``rate_limited`` flags a 429/WAF signal so
    the pool's shared governor can back off.
    """
    t0 = time.monotonic()
    try:
        if task.data is not None:
            response = session.post(
                task.url,
                data=task.data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=timeout,
            )
        else:
            response = session.get(task.url, timeout=timeout)
        duration = time.monotonic() - t0

        if _looks_blocked(response.status_code, response.text[:2000]):
            logging.debug(
                "Task %s rate-limited/blocked (HTTP %s)", task.task_id, response.status_code
            )
            return DownloadResult(
                task.task_id,
                success=False,
                http_code=response.status_code,
                duration=duration,
                rate_limited=True,
            )

        return DownloadResult(
            task.task_id,
            success=True,
            content=response.content,
            http_code=response.status_code,
            duration=duration,
        )
    except Exception as e:
        return DownloadResult(
            task.task_id, success=False, error=str(e), duration=time.monotonic() - t0
        )
