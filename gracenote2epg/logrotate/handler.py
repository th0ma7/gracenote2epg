"""
gracenote2epg.logrotate.handler - copytruncate timed rotating file handler

Custom logging handler that rotates with a copytruncate strategy (keeps the
log file open so `tail -f` survives) and performs multi-period catch-up
rotation at startup. Period/date arithmetic lives in .periods.
"""

import logging
import logging.handlers
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple

from . import periods


class CopyTruncateTimedRotatingFileHandler(logging.handlers.BaseRotatingHandler):
    """
    Custom log rotation handler that uses copytruncate strategy.

    Compatible with 'tail -f' by keeping the original log file open and
    truncating it instead of renaming it. Performs catch-up rotation
    at startup if needed.

    ENHANCED VERSION: Multi-period rotation for daily/weekly/monthly modes.
    Updated to use unified retention policies.
    """

    def __init__(
        self,
        filename: str,
        when: str = "midnight",
        interval: int = 1,
        backup_count: int = 7,
        encoding: Optional[str] = None,
    ):
        """
        Initialize the handler.

        Args:
            filename: Log file path
            when: Rotation interval ('midnight', 'weekly', 'monthly')
            interval: Interval multiplier (usually 1)
            backup_count: Number of backup files to keep (0 = unlimited)
            encoding: File encoding
        """
        super().__init__(filename, "a", encoding=encoding)

        self.when = when.upper()
        self.interval = interval
        self.backup_count = backup_count

        # Determine rotation interval in seconds and suffix format
        if self.when == "MIDNIGHT" or self.when == "DAILY":
            self.interval_seconds = 60 * 60 * 24  # 1 day
            self.suffix = "%Y-%m-%d"
            self.period_name = "daily"
        elif self.when == "WEEKLY":
            self.interval_seconds = 60 * 60 * 24 * 7  # 1 week
            self.suffix = "%Y-W%U"  # Year-Week (Sunday as first day)
            self.period_name = "weekly"
        elif self.when == "MONTHLY":
            self.interval_seconds = 60 * 60 * 24 * 30  # Approximation for 1 month
            self.suffix = "%Y-%m"
            self.period_name = "monthly"
        else:
            raise ValueError(f"Invalid rotation interval: {when}")

        # Calculate next rotation time
        self.rollover_at = self._compute_next_rollover()

        logging.debug(
            "Log rotation initialized: %s every %s, keeping %d backups",
            filename,
            self.period_name,
            self.backup_count,
        )

        # Log next scheduled rotation
        next_rotation = datetime.fromtimestamp(self.rollover_at)
        logging.debug(
            "Next log rotation scheduled for: %s", next_rotation.strftime("%Y-%m-%d %H:%M:%S")
        )

    def _compute_next_rollover(self) -> float:
        """Compute the next rollover time."""
        return periods.next_rollover_at(self.when, self.interval_seconds)

    def _check_startup_rotation(self):
        """Check if rotation is needed at startup (catch-up rotation) - MULTI-PERIOD VERSION"""
        log_file = Path(self.baseFilename)

        if not log_file.exists():
            logging.debug("Log file does not exist yet - no startup rotation needed")
            return

        try:
            # Analyze log file and group entries by periods (daily/weekly/monthly)
            periods_data = self._analyze_log_periods(log_file)
            if periods_data:
                self._perform_multi_period_rotation(periods_data)
            else:
                logging.debug("No periods found for rotation")

        except Exception as e:
            logging.warning("Error during startup rotation check: %s", str(e))

    def _analyze_log_periods(self, log_file: Path) -> Dict[str, Dict]:
        """
        Analyze log file and group entries by periods (daily/weekly/monthly)

        Returns:
            dict: {period_suffix: {'start_date': datetime, 'end_date': datetime,
                                   'lines': [lines], 'complete': bool, 'line_range': (start, end)}}
        """
        periods_data = {}
        current_period = None
        current_datetime = datetime.now()

        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            logging.debug("Analyzing %d lines for %s rotation...", len(lines), self.period_name)

            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()

                # Skip empty lines and separators
                if not line_stripped or line_stripped.startswith("="):
                    # Add to current period if exists
                    if current_period and current_period in periods_data:
                        periods_data[current_period]["lines"].append(line)
                        periods_data[current_period]["last_line"] = line_num
                    continue

                # Look for timestamp pattern: YYYY/MM/DD HH:MM:SS
                timestamp_match = re.match(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})", line)

                if timestamp_match:
                    try:
                        timestamp_str = timestamp_match.group(1)
                        entry_datetime = datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")

                        # Determine which period this entry belongs to
                        period_start, period_end, period_suffix = self._get_period_info(
                            entry_datetime
                        )

                        # Initialize period data if not seen before
                        if period_suffix not in periods_data:
                            # Check if this period is complete (not the current period)
                            is_complete = self._is_period_complete(
                                period_start, period_end, current_datetime
                            )

                            periods_data[period_suffix] = {
                                "start_date": period_start,
                                "end_date": period_end,
                                "lines": [],
                                "complete": is_complete,
                                "first_line": line_num,
                                "last_line": line_num,
                            }

                            span = period_start.strftime("%Y-%m-%d")
                            if period_end != period_start:
                                span += " to " + period_end.strftime("%Y-%m-%d")
                            logging.debug(
                                "Found %s log period %s (%s) - %s",
                                self.period_name,
                                period_suffix,
                                span,
                                "complete" if is_complete else "current period, still in progress",
                            )

                        # Add line to this period
                        periods_data[period_suffix]["lines"].append(line)
                        periods_data[period_suffix]["last_line"] = line_num
                        current_period = period_suffix

                    except ValueError as e:
                        logging.debug('Could not parse timestamp "%s": %s', timestamp_str, e)
                        # Add to current period if exists
                        if current_period and current_period in periods_data:
                            periods_data[current_period]["lines"].append(line)
                            periods_data[current_period]["last_line"] = line_num
                else:
                    # Non-timestamped line (probably continuation) - add to current period
                    if current_period and current_period in periods_data:
                        periods_data[current_period]["lines"].append(line)
                        periods_data[current_period]["last_line"] = line_num

            # Log summary
            complete_periods = [p for p, data in periods_data.items() if data["complete"]]
            current_periods = [p for p, data in periods_data.items() if not data["complete"]]

            logging.debug("Log analysis complete (%s rotation):", self.period_name)
            logging.debug(
                "  Complete %s periods found: %d (%s)",
                self.period_name,
                len(complete_periods),
                ", ".join(complete_periods) if complete_periods else "none",
            )
            logging.debug(
                "  Current %s period: %s (stays in the current log)",
                self.period_name,
                ", ".join(current_periods) if current_periods else "none",
            )

            return periods_data

        except Exception as e:
            logging.warning("Error analyzing log %ss: %s", self.period_name, str(e))
            return {}

    def _get_period_info(self, entry_datetime: datetime) -> Tuple[datetime, datetime, str]:
        """Get period start, end, and suffix for given datetime."""
        return periods.get_period_info(self.when, self.suffix, entry_datetime)

    def _is_period_complete(
        self, period_start: datetime, period_end: datetime, current_datetime: datetime
    ) -> bool:
        """Check if a period is complete (not the current period)"""
        return periods.is_period_complete(self.when, period_start, period_end, current_datetime)

    def _get_week_start(self, dt: datetime) -> datetime:
        """Get the start of the week (last Sunday at midnight) for given datetime"""
        return periods.get_week_start(dt)

    def _perform_multi_period_rotation(self, periods_data: Dict[str, Dict]):
        """
        Perform rotation for multiple periods

        Args:
            periods_data: Period analysis from _analyze_log_periods()
        """
        try:
            # Identify periods that need to be rotated (complete periods only)
            periods_to_rotate = {
                period: data for period, data in periods_data.items() if data["complete"]
            }
            current_period_data = {
                period: data for period, data in periods_data.items() if not data["complete"]
            }

            if not periods_to_rotate:
                logging.debug("No complete %ss found - no rotation needed", self.period_name)
                return

            logging.info(
                "Multi-%s rotation starting: %d complete %ss to rotate",
                self.period_name,
                len(periods_to_rotate),
                self.period_name,
            )

            # Create backup for each complete period
            for period_suffix, period_data in periods_to_rotate.items():
                backup_filename = f"{self.baseFilename}.{period_suffix}"

                # Ensure backup filename is unique
                counter = 1
                original_backup = backup_filename
                while Path(backup_filename).exists():
                    backup_filename = f"{original_backup}.{counter}"
                    counter += 1

                # Write this period's data to backup file
                try:
                    with open(backup_filename, "w", encoding="utf-8") as backup_f:
                        backup_f.writelines(period_data["lines"])

                    start_date = period_data["start_date"].strftime("%Y-%m-%d")
                    end_date = period_data["end_date"].strftime("%Y-%m-%d")
                    line_count = len(period_data["lines"])
                    file_size_mb = Path(backup_filename).stat().st_size / (1024 * 1024)

                    logging.info(
                        "Created %s backup: %s (%.1f MB, %s to %s, %d lines)",
                        self.period_name,
                        Path(backup_filename).name,
                        file_size_mb,
                        start_date,
                        end_date,
                        line_count,
                    )

                except Exception as e:
                    logging.error("Failed to create backup %s: %s", backup_filename, str(e))
                    continue

            # Rebuild current log with only current period data
            current_lines = []
            for period_data in current_period_data.values():
                current_lines.extend(period_data["lines"])

            # Write current period data back to main log file
            try:
                with open(self.baseFilename, "w", encoding="utf-8") as current_f:
                    current_f.writelines(current_lines)

                if current_lines:
                    logging.info(
                        "Current log rebuilt with %d lines from current %s",
                        len(current_lines),
                        self.period_name,
                    )
                else:
                    logging.info(
                        "Current log truncated - no current %s data found", self.period_name
                    )

            except Exception as e:
                logging.error("Failed to rebuild current log: %s", str(e))
                return

            # Clean up old backup files
            if self.backup_count > 0:
                self._cleanup_old_backups()

            # Recalculate next rotation time
            self.rollover_at = self._compute_next_rollover()
            next_rotation = datetime.fromtimestamp(self.rollover_at)
            logging.debug(
                "Next rotation rescheduled for: %s", next_rotation.strftime("%Y-%m-%d %H:%M:%S")
            )

            logging.info("Multi-%s rotation completed successfully", self.period_name)

        except Exception as e:
            logging.error("Error during multi-%s rotation: %s", self.period_name, str(e))

    def shouldRollover(self, record) -> bool:
        """Determine if rollover should occur."""
        return time.time() >= self.rollover_at

    def doRollover(self):
        """
        Perform log rotation using copytruncate strategy.

        This maintains compatibility with 'tail -f' by:
        1. Copying current log to backup file
        2. Truncating current log file (keeping it open)
        3. Cleaning up old backup files
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        try:
            # Generate backup filename with timestamp
            current_time = datetime.now()
            backup_suffix = current_time.strftime(self.suffix)
            backup_filename = f"{self.baseFilename}.{backup_suffix}"

            # Ensure backup filename is unique
            counter = 1
            original_backup = backup_filename
            while Path(backup_filename).exists():
                backup_filename = f"{original_backup}.{counter}"
                counter += 1

            # Copy current log to backup (copytruncate strategy)
            if Path(self.baseFilename).exists():
                logging.debug("Rotating log: copying %s to %s", self.baseFilename, backup_filename)
                shutil.copy2(self.baseFilename, backup_filename)

                # Truncate original file (keeps tail -f working)
                with open(self.baseFilename, "w") as f:
                    f.truncate(0)

                logging.info(
                    "Log rotated: %s -> %s",
                    Path(self.baseFilename).name,
                    Path(backup_filename).name,
                )

            # Clean up old backup files
            if self.backup_count > 0:
                self._cleanup_old_backups()

            # Calculate next rotation time
            self.rollover_at = self._compute_next_rollover()
            next_rotation = datetime.fromtimestamp(self.rollover_at)
            logging.debug(
                "Next log rotation scheduled for: %s", next_rotation.strftime("%Y-%m-%d %H:%M:%S")
            )

        except Exception as e:
            logging.error("Error during log rotation: %s", str(e))

        # Reopen the file
        if not self.stream:
            self.stream = self._open()

    def _cleanup_old_backups(self):
        """Remove old backup files beyond backup_count."""
        try:
            log_dir = Path(self.baseFilename).parent
            log_basename = Path(self.baseFilename).name

            # Find all backup files for this log
            backup_files = []
            for file_path in log_dir.glob(f"{log_basename}.*"):
                # Skip if it's the main log file
                if str(file_path) == self.baseFilename:
                    continue

                # Add to backup list with modification time
                backup_files.append((file_path, file_path.stat().st_mtime))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # Remove old backups beyond backup_count
            files_to_remove = backup_files[self.backup_count :]
            for file_path, _ in files_to_remove:
                try:
                    file_path.unlink()
                    logging.debug("Removed old log backup: %s", file_path.name)
                except OSError as e:
                    logging.warning(
                        "Could not remove old log backup %s: %s", file_path.name, str(e)
                    )

            if files_to_remove:
                logging.info("Cleaned up %d old log backup(s)", len(files_to_remove))

        except Exception as e:
            logging.warning("Error during backup cleanup: %s", str(e))
