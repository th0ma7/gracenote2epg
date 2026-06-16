"""
gracenote2epg.downloader.series - Series details downloader

Handles downloading of extended series details from Gracenote API with intelligent
caching and comprehensive error handling for enhanced program information.
"""

import json
import logging
from typing import Dict, List, Optional, Set

from .base import OptimizedDownloader, DownloaderStatsMixin
from ..cache import CacheManager


class SeriesDownloader(DownloaderStatsMixin):
    """Downloads extended series details with intelligent caching"""

    def __init__(self, http_engine: OptimizedDownloader, cache_manager: CacheManager):
        self.http_engine = http_engine
        self.cache_manager = cache_manager
        self.base_url = "https://tvlistings.gracenote.com/api/program/overviewDetails"

        # Statistics
        self.downloaded_count = 0
        self.cached_count = 0
        self.failed_count = 0
        self.failed_series: List[str] = []
        self.cached_series: Set[str] = set()

    def download_series_details(
        self, series_list: List[str], workers: int = 1, threshold: Optional[int] = None
    ) -> bool:
        """
        Download extended details for series with intelligent caching

        Args:
            series_list: List of series IDs to download
            workers: parallel download workers (1 = sequential)
            threshold: if >0 and the number of downloads needed reaches it, fall
                back to a single sequential connection (which the Gracenote WAF
                never rate-limits) instead of the parallel pool

        Returns:
            bool: True if 70%+ successful
        """
        logging.info("Starting extended series details download")

        # Reset statistics
        self.downloaded_count = 0
        self.cached_count = 0
        self.failed_count = 0
        self.failed_series.clear()
        self.cached_series.clear()

        # Get unique series and identify what needs downloading
        unique_series = set(series_list)
        to_download = self._identify_series_to_download(unique_series)

        logging.info(
            "Extended details: %d unique series found, %d downloads needed (workers=%d)",
            len(unique_series),
            len(to_download),
            workers,
        )

        # With an explicit dlthreshold, large cold-cache batches download
        # sequentially (the WAF never blocks a single connection). With
        # dlthreshold=auto (threshold is None) we stay parallel and let the
        # adaptive concurrency limiter ride out any 429s instead.
        if workers > 1 and threshold is not None and len(to_download) >= threshold:
            logging.warning(
                "Large batch (%d ≥ dlthreshold %d): downloading sequentially to avoid the "
                "Gracenote rate-limit wall (HTTP 429); this is slower but reliable.",
                len(to_download),
                threshold,
            )
            workers = 1

        if workers > 1 and to_download:
            self._download_parallel(to_download, workers)
        else:
            # Sequential: download each series that needs it
            for index, series_id in enumerate(to_download, 1):
                success = self._download_single_series(series_id, index, len(to_download))

                if success:
                    self.downloaded_count += 1
                else:
                    self.failed_count += 1
                    self.failed_series.append(series_id)

        # Count cached series
        self.cached_count = len(self.cached_series)

        # Log comprehensive statistics
        self._log_statistics()

        # Judge success on the *download* operation only: cached series are not a
        # download outcome, so counting them (as _calculate_success_rate does for
        # the stats display) would let a cache-dominated run mask a total
        # fresh-download failure. Mirror the pre-refactor success/attempted rule.
        attempted = self.downloaded_count + self.failed_count
        download_success_rate = (self.downloaded_count / attempted * 100) if attempted else 100.0
        return download_success_rate >= 70 or attempted == 0

    def _download_parallel(self, to_download: List[str], workers: int) -> None:
        """Download series details with a bounded keep-alive worker pool.

        Each result is saved as soon as it finalises (save-as-you-go), so an
        interrupted or early-aborted run keeps everything fetched so far.
        """
        import threading

        from .http import make_session, execute
        from .tasks import DownloadTask
        from .worker_pool import PacedWorkerPool

        total = len(to_download)
        tally_lock = threading.Lock()

        def on_progress(done: int, _total: int):
            if done == 1 or done % max(1, total // 10) == 0 or done == total:
                logging.info("  Extended details: %d/%d", done, total)

        def on_result(result) -> None:
            # Runs in worker threads as each download finalises.
            saved = False
            if result.success and result.content:
                try:
                    json.loads(result.content)  # validate JSON
                    saved = self.cache_manager.save_series_details(result.task_id, result.content)
                except json.JSONDecodeError:
                    logging.warning("  Invalid JSON received for: %s", result.task_id)
            with tally_lock:
                if saved:
                    self.downloaded_count += 1
                else:
                    self.failed_count += 1
                    self.failed_series.append(result.task_id)

        tasks = [
            DownloadTask(
                task_id=sid,
                url=self.base_url,
                task_type="series_details",
                data=f"programSeriesID={sid}".encode("utf-8"),
            )
            for sid in to_download
        ]

        pool = PacedWorkerPool(
            execute,
            workers=workers,
            session_factory=make_session,
            on_progress=on_progress,
            on_result=on_result,
        )
        # Series details are non-critical: one best-effort retry (re-queued at
        # the end). If the server keeps rate-limiting, the pool aborts early and
        # anything still missing is simply re-fetched on the next run.
        pool.run(tasks, max_attempts=2)
        self.http_requests = pool.requests
        self.rate_limited = pool.rate_limited

        self.http_requests = pool.requests
        self.rate_limited = pool.rate_limited

    def _identify_series_to_download(self, unique_series: Set[str]) -> List[str]:
        """Identify which series need to be downloaded vs cached"""
        to_download = []

        for series_id in unique_series:
            if not series_id:
                continue

            # Check cache
            cached_details = self.cache_manager.load_series_details(series_id)
            if cached_details is None:
                to_download.append(series_id)
            else:
                self.cached_series.add(series_id)
                logging.debug("Found cached details for: %s", series_id)

        return to_download

    def _download_single_series(self, series_id: str, index: int, total: int) -> bool:
        """Download details for a single series"""
        logging.info(
            "Downloading extended details for: %s (%d/%d)",
            series_id,
            index,
            total,
        )

        # Prepare POST data
        data = f"programSeriesID={series_id}".encode("utf-8")

        logging.debug("  URL: %s?programSeriesID=%s", self.base_url, series_id)

        # Download using urllib method (works better for POST requests)
        content = self.http_engine.download_with_retry_urllib(self.base_url, data=data, timeout=6)

        if content:
            try:
                # Validate JSON
                json.loads(content)

                # Save to cache
                if self.cache_manager.save_series_details(series_id, content):
                    logging.info(
                        "  Successfully downloaded: %s.json (%d bytes)",
                        series_id,
                        len(content),
                    )
                    return True
                else:
                    logging.warning("  Error saving details for: %s", series_id)
                    return False

            except json.JSONDecodeError:
                logging.warning("  Invalid JSON received for: %s", series_id)
                return False
        else:
            logging.warning("  Failed to download details for: %s", series_id)
            return False

    def get_cached_series_details(self, series_id: str) -> Optional[Dict]:
        """Get cached series details by ID"""
        return self.cache_manager.load_series_details(series_id)

    def _log_statistics(self):
        """Log comprehensive download statistics"""
        success_rate = self._calculate_success_rate()

        logging.info("Extended details processing completed:")
        logging.info("  Downloads attempted: %d", self.downloaded_count)
        logging.info("  Successful downloads: %d", self.downloaded_count)
        logging.info("  Unique series from cache: %d", self.cached_count)
        logging.info("  Failed downloads: %d", self.failed_count)

        if self.downloaded_count > 0:
            logging.info("  Download success rate: %.1f%%", success_rate)

        # Cache efficiency calculation
        total_series = self.cached_count + self.downloaded_count
        if total_series > 0:
            cache_efficiency = self.cached_count / total_series * 100
            logging.info("  Cache efficiency: %.1f%% reused", cache_efficiency)

            if cache_efficiency > 70:
                logging.info("  Excellent cache performance - most series were reused!")
            elif cache_efficiency > 30:
                logging.info("  Good cache performance - significant bandwidth saved")
            else:
                logging.info("  Low cache efficiency - mostly new content")

        # Log some failed series for debugging
        if self.failed_series:
            logging.info(
                "  Failed series (first 10): %s",
                ", ".join(self.failed_series[:10]),
            )

        # Log HTTP engine statistics
        http_stats = self.http_engine.get_statistics()
        logging.debug(
            "  HTTP requests: %d total, %d WAF blocks during series download",
            http_stats["total_requests"],
            http_stats["waf_blocks"],
        )
