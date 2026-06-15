"""
gracenote2epg.downloader.tasks - download task / result abstractions

Small, reusable value objects for the paced download redesign (see
docs/parallel-download-redesign.md). Kept independent of any execution model.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class DownloadTask:
    """A single download to perform."""

    task_id: str
    url: str
    task_type: str  # "guide_block" | "series_details"
    data: Optional[bytes] = None  # POST body (series details)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadResult:
    """Outcome of a DownloadTask."""

    task_id: str
    success: bool
    content: Optional[bytes] = None
    error: Optional[str] = None
    http_code: Optional[int] = None
    duration: float = 0.0
    rate_limited: bool = False

    @property
    def bytes_downloaded(self) -> int:
        return len(self.content) if self.content else 0


class TaskMetrics:
    """Aggregate counters over a batch of downloads."""

    def __init__(self):
        self.downloaded = 0
        self.cached = 0
        self.failed = 0
        self.rate_limited = 0
        self.total_bytes = 0
        self.total_duration = 0.0

    def record(self, result: DownloadResult) -> None:
        if result.success:
            self.downloaded += 1
            self.total_bytes += result.bytes_downloaded
            self.total_duration += result.duration
        else:
            self.failed += 1
        if result.rate_limited:
            self.rate_limited += 1

    def record_cached(self) -> None:
        self.cached += 1

    @property
    def attempted(self) -> int:
        return self.downloaded + self.failed

    @property
    def success_rate(self) -> float:
        """Success rate over *attempted* (non-cached) downloads, as a percentage."""
        return (self.downloaded / self.attempted * 100.0) if self.attempted else 100.0

    @property
    def cache_hit_rate(self) -> float:
        processed = self.attempted + self.cached
        return (self.cached / processed * 100.0) if processed else 0.0
