"""
gracenote2epg.cache - Cache management

Manages all caching operations for gracenote2epg. The cache is organised in
subdirectories: guide/ for guide blocks, series/ for TV series details (SH*),
movies/ for movie details (MV*); XMLTV files and their backups stay at the
cache root. Includes unified retention policies.
"""

import gzip
import json
import logging
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .utils import TimeUtils


class CacheManager:
    """Manages all caching operations for gracenote2epg with unified retention policies"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        # Organise the cache into focused subdirectories so the root stays clean
        # and manual inspection is easy:
        #   guide/  -> guide blocks (YYYYMMDDHH.json.gz)
        #   series/ -> TV series details (SH*)
        #   movies/ -> movie details (MV*)
        # (xmltv.xml and its backups stay at the cache root.)
        self.guide_dir = self.cache_dir / "guide"
        self.series_dir = self.cache_dir / "series"
        self.movies_dir = self.cache_dir / "movies"
        # Create cache directories with proper 755 permissions (rwxr-xr-x)
        for directory in (self.cache_dir, self.guide_dir, self.series_dir, self.movies_dir):
            try:
                directory.mkdir(parents=True, exist_ok=True, mode=0o755)
            except Exception:
                # Fallback: create without mode specification (depends on umask)
                directory.mkdir(parents=True, exist_ok=True)
        # One-time migration of older cache layouts (no re-download).
        self._migrate_cache_layout()

    def _details_dir(self, series_id: str) -> Path:
        """Subdirectory for a program's details: movies/ for MV*, else series/."""
        return self.movies_dir if str(series_id).upper().startswith("MV") else self.series_dir

    def _move_into(self, src: Path, dest_dir: Path) -> int:
        """Move *src* into *dest_dir* unless already there; returns 1 if moved."""
        target = dest_dir / src.name
        try:
            if src.resolve() == target.resolve():
                return 0
            src.replace(target)
            return 1
        except Exception as e:
            logging.debug("Could not migrate %s: %s", src.name, e)
            return 0

    def _migrate_cache_layout(self):
        """Relocate files from older cache layouts into guide/series/movies."""
        try:
            moved = 0
            # Guide blocks previously stored at the cache root -> guide/
            for f in self.cache_dir.glob("*.json.gz"):
                if f.is_file():
                    moved += self._move_into(f, self.guide_dir)
            # Detail files: legacy flat *.json at the root, plus MV* left in
            # series/ by the first series/ layout -> the right subdirectory.
            details = [
                f
                for f in self.cache_dir.glob("*.json")
                if f.is_file() and not f.name.endswith(".json.gz")
            ]
            details += list(self.series_dir.glob("MV*.json"))
            for f in details:
                moved += self._move_into(f, self._details_dir(f.stem))
            if moved:
                logging.info(
                    "Migrated %d cached file(s) into the guide/series/movies layout", moved
                )
        except Exception as e:
            logging.debug("Cache layout migration skipped: %s", e)

    def backup_xmltv(self, xmltv_file: Path) -> Optional[Path]:
        """XMLTV: Always backup previous version"""
        try:
            if xmltv_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = xmltv_file.with_suffix(f".xml.{timestamp}")

                shutil.copy2(xmltv_file, backup_file)
                logging.info("XMLTV backed up: %s", backup_file.name)
                return backup_file
            else:
                logging.info("No existing XMLTV file to backup - first run")
                return None
        except Exception as e:
            logging.warning("Error backing up XMLTV: %s", str(e))
            return None

    def clean_old_xmltv_backups(self, xmltv_file: Path, retention_days: int):
        """XMLTV: Remove backups older than retention period using unified retention policy"""
        try:
            xmltv_dir = xmltv_file.parent
            xmltv_basename = xmltv_file.stem  # filename without .xml

            if not xmltv_dir.exists():
                return

            # Handle unlimited retention
            if retention_days == 0:
                logging.debug("XMLTV backup retention: unlimited - no cleanup performed")
                return

            # Keep backups for retention period
            cutoff_time = time.time() - (retention_days * 24 * 3600)

            cleaned_count = 0
            kept_count = 0
            pattern = f"{xmltv_basename}.xml.*"

            for backup_file in xmltv_dir.glob(pattern):
                try:
                    file_mtime = backup_file.stat().st_mtime
                    if file_mtime < cutoff_time:
                        backup_file.unlink()
                        logging.debug("Deleted old XMLTV backup: %s", backup_file.name)
                        cleaned_count += 1
                    else:
                        kept_count += 1
                        logging.debug("Kept XMLTV backup: %s", backup_file.name)
                except OSError as e:
                    logging.warning("Error deleting backup %s: %s", backup_file.name, str(e))

            if cleaned_count > 0 or kept_count > 0:
                if retention_days == 1:
                    retention_desc = "1 day"
                else:
                    retention_desc = f"{retention_days} days"

                logging.info(
                    "XMLTV backup cleanup: %d removed, %d kept (retention: %s)",
                    cleaned_count,
                    kept_count,
                    retention_desc,
                )

        except Exception as e:
            logging.warning("Error cleaning XMLTV backups: %s", str(e))

    def clean_guide_cache(self, grid_time_start: float, guide_days: int):
        """Guide: Keep only blocks corresponding to target period"""
        try:
            logging.info("Cleaning guide cache: keeping blocks for %d days", guide_days)

            # Calculate guide time range
            guide_start_dt, guide_end_dt = TimeUtils.calculate_guide_time_range(
                grid_time_start, guide_days
            )

            logging.debug(
                "Guide range: %s to %s",
                guide_start_dt.strftime("%Y-%m-%d %H:00"),
                guide_end_dt.strftime("%Y-%m-%d %H:00"),
            )

            cleaned_count = 0
            kept_count = 0
            invalid_count = 0

            # Process guide block files (format: YYYYMMDDHH.json.gz)
            for cache_file in self.guide_dir.glob("*.json.gz"):
                if len(cache_file.stem) == 10:  # YYYYMMDDHH
                    try:
                        date_str = cache_file.stem  # YYYYMMDDHH
                        file_dt = datetime.strptime(date_str, "%Y%m%d%H")

                        # Verify it's a valid 3h block (0,3,6,9,12,15,18,21)
                        if file_dt.hour % 3 != 0:
                            # Invalid block - remove
                            cache_file.unlink()
                            logging.debug(
                                "Deleted invalid block: %s (hour %d)", cache_file.name, file_dt.hour
                            )
                            invalid_count += 1
                            continue

                        # Check if block is within guide range
                        if guide_start_dt <= file_dt < guide_end_dt:
                            # Keep
                            kept_count += 1
                            logging.debug("Keeping: %s", cache_file.name)
                        else:
                            # Remove - outside range
                            cache_file.unlink()
                            logging.debug("Deleted out of range: %s", cache_file.name)
                            cleaned_count += 1

                    except (ValueError, OSError) as e:
                        logging.warning("Error processing block %s: %s", cache_file.name, str(e))

            total_processed = cleaned_count + kept_count + invalid_count
            if total_processed > 0:
                logging.info(
                    "Guide cache cleanup: %d removed, %d kept, %d invalid blocks removed",
                    cleaned_count,
                    kept_count,
                    invalid_count,
                )
            else:
                logging.info("No guide cache files found to process")

        except Exception as e:
            logging.warning("Error cleaning guide cache: %s", str(e))

    def clean_show_cache(self, active_series_list: Optional[List[str]] = None):
        """Show details: Keep only those still active in current xmltv.xml"""
        try:
            if active_series_list is None:
                active_series_list = []

            # Convert to set for fast lookup
            active_series = set(active_series_list)

            cleaned_count = 0
            kept_count = 0

            # Process show/movie detail files (series/ and movies/ subdirectories)
            detail_files = list(self.series_dir.glob("*.json")) + list(
                self.movies_dir.glob("*.json")
            )
            for cache_file in detail_files:
                series_id = cache_file.stem  # filename without .json

                if series_id in active_series:
                    kept_count += 1
                    logging.debug("Show details kept: %s", series_id)
                else:
                    try:
                        cache_file.unlink()
                        logging.debug("Show details removed: %s", series_id)
                        cleaned_count += 1
                    except OSError as e:
                        logging.warning(
                            "Error removing show details %s: %s", cache_file.name, str(e)
                        )

            if cleaned_count > 0 or kept_count > 0:
                logging.info("Show cache cleanup: %d removed, %d kept", cleaned_count, kept_count)

        except Exception as e:
            logging.warning("Error cleaning show cache: %s", str(e))

    def save_guide_block(self, filename: str, data: bytes) -> bool:
        """Save compressed guide block data"""
        try:
            file_path = self.guide_dir / filename
            with gzip.open(file_path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            logging.warning("Error saving guide block %s: %s", filename, str(e))
            return False

    def load_guide_block(self, filename: str) -> Optional[bytes]:
        """Load compressed guide block data"""
        try:
            file_path = self.guide_dir / filename
            if file_path.exists():
                with gzip.open(file_path, "rb") as f:
                    return f.read()
        except Exception as e:
            logging.warning("Error loading guide block %s: %s", filename, str(e))
        return None

    def save_series_details(self, series_id: str, data: bytes) -> bool:
        """Save series details JSON data"""
        try:
            file_path = self._details_dir(series_id) / f"{series_id}.json"
            with open(file_path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:
            logging.warning("Error saving series details %s: %s", series_id, str(e))
            return False

    def load_series_details(self, series_id: str) -> Optional[Dict]:
        """Load series details JSON data"""
        file_path = self._details_dir(series_id) / f"{series_id}.json"
        try:
            if file_path.exists() and file_path.stat().st_size > 0:
                with open(file_path, "rb") as f:
                    return json.loads(f.read())
        except (json.JSONDecodeError, OSError) as e:
            logging.warning("Error loading series details %s: %s", series_id, str(e))
            # Remove corrupted file
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass
        return None

    def validate_and_save_guide_block(self, content: bytes, filename: str) -> bool:
        """Validate JSON content and save guide block"""
        try:
            # Validate JSON
            json.loads(content)

            # Save compressed
            return self.save_guide_block(filename, content)

        except json.JSONDecodeError:
            logging.warning("Invalid JSON received for %s", filename)
            return False
        except Exception as e:
            logging.warning("Error validating/saving %s: %s", filename, str(e))
            return False

    def guide_block_status(self, grid_time: float, filename: str, refresh_hours: int = 48) -> str:
        """Decide what a guide block needs without downloading.

        Returns "cached" (up to date), "fetch" (new or refresh-due) or "missing"
        (absent while --norefresh prevents downloading). Mirrors the decision in
        download_guide_block_safe so the parallel path stays consistent.
        """
        file_exists = (self.guide_dir / filename).exists()
        if refresh_hours == 0:
            return "cached" if file_exists else "missing"
        if not file_exists:
            return "fetch"
        force_refresh = (grid_time - time.time()) < (refresh_hours * 3600)
        return "fetch" if force_refresh else "cached"

    def download_guide_block_safe(
        self, downloader, grid_time: float, filename: str, url: str, refresh_hours: int = 48
    ) -> bool:
        """Safe download of guide block with automatic backup"""
        file_path = self.guide_dir / filename
        file_exists = file_path.exists()

        # Handling for --norefresh (refresh_hours == 0)
        # Never download anything when refresh is disabled
        if refresh_hours == 0:
            if file_exists:
                # Use cached version
                block_time = TimeUtils.get_standard_block_time(grid_time)
                block_end = (block_time.hour + 3) % 24
                block_display = f"{block_time.strftime('%Y-%m-%d %H:00')}-{block_end:02d}:00"
                logging.debug("Using cached: %s [--norefresh mode]", block_display)
                return True
            else:
                # No cache available and can't download with --norefresh
                logging.warning("Block %s not in cache and --norefresh prevents download", filename)
                return False
        else:
            # Determine if refresh needed (first X hours)
            time_from_now = grid_time - time.time()
            force_refresh = time_from_now < (refresh_hours * 3600)

            block_time = TimeUtils.get_standard_block_time(grid_time)
            block_end = (block_time.hour + 3) % 24
            block_display = f"{block_time.strftime('%Y-%m-%d %H:00')}-{block_end:02d}:00"

            if not file_exists:
                # New block to download
                logging.info("Downloading new block: %s", block_display)
                content = downloader.download_with_retry(url, method="GET", timeout=8)

                if content and self.validate_and_save_guide_block(content, filename):
                    logging.info("  Success: %s (%d bytes)", filename, len(content))
                    return True
                else:
                    logging.warning("  Failed download: %s", filename)
                    return False

            elif force_refresh:
                # Existing block to refresh
                logging.info("Refreshing block: %s [REFRESH]", block_display)

                # Create temporary backup
                backup_file = file_path.with_suffix(".backup_temp")
                try:
                    shutil.copy2(file_path, backup_file)
                    logging.debug("  Backup created: %s", backup_file.name)
                except Exception as e:
                    logging.warning("  Cannot create backup: %s", str(e))
                    backup_file = None

                # Download new version
                logging.info("Downloading refresh block: %s", block_display)
                content = downloader.download_with_retry(url, method="GET", timeout=8)

                if content and self.validate_and_save_guide_block(content, filename):
                    # Success - remove backup
                    if backup_file and backup_file.exists():
                        backup_file.unlink()
                    logging.info("  Refresh success: %s (%d bytes)", filename, len(content))
                    return True
                else:
                    # Failed - restore backup
                    if backup_file and backup_file.exists():
                        shutil.move(str(backup_file), str(file_path))
                        logging.info("  Backup restored after failed refresh: %s", filename)
                        return True  # We still have the file
                    else:
                        logging.warning("  Refresh failed and no backup: %s", filename)
                        return False
            else:
                # Use cached version
                logging.debug("Using cached: %s", block_display)
                return True

    def perform_initial_cleanup(
        self, grid_time_start: float, guide_days: int, xmltv_file: Path, xmltv_retention_days: int
    ):
        """Perform initial cache cleanup with unified retention policy"""
        logging.info("=== Initial Cache Cleanup ===")

        # 1. Clean guide cache - keep only blocks for target period
        self.clean_guide_cache(grid_time_start, guide_days)

        # 2. Clean XMLTV backups using unified retention policy
        self.clean_old_xmltv_backups(xmltv_file, xmltv_retention_days)

        logging.info(
            "Initial cache cleanup completed (show cache will be cleaned after parsing episodes)"
        )

    def perform_show_cleanup(self, active_series: List[str]):
        """Clean show cache after episodes are parsed"""
        logging.info("=== Show Cache Cleanup ===")

        if active_series:
            logging.info("Found %d active series in current schedule", len(active_series))
            self.clean_show_cache(active_series)
        else:
            logging.warning(
                "No active series found - skipping show cache cleanup to preserve existing cache"
            )

        logging.info("Show cache cleanup completed")
