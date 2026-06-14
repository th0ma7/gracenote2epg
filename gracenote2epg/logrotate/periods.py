"""
gracenote2epg.logrotate.periods - period/date arithmetic for log rotation

Pure helpers (no I/O, no handler state) shared by the rotating handler to
compute rollover times and to classify log entries into daily/weekly/monthly
periods. ``when`` is the upper-cased mode ("MIDNIGHT"/"DAILY", "WEEKLY",
"MONTHLY") and ``suffix`` the matching strftime backup suffix.
"""

import time
from datetime import datetime, timedelta
from typing import Tuple


def next_rollover_at(when: str, interval_seconds: int) -> float:
    """Compute the next rollover timestamp for the given rotation mode."""
    now = time.time()

    if when == "MIDNIGHT" or when == "DAILY":
        # Next midnight
        current_time = datetime.fromtimestamp(now)
        next_rollover = current_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        return next_rollover.timestamp()

    elif when == "WEEKLY":
        # Next Sunday at midnight (Sunday = first day of week in US system)
        current_time = datetime.fromtimestamp(now)
        days_until_sunday = (6 - current_time.weekday()) % 7
        if days_until_sunday == 0:  # Today is Sunday
            days_until_sunday = 7  # Next Sunday
        next_rollover = current_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=days_until_sunday)
        return next_rollover.timestamp()

    elif when == "MONTHLY":
        # Next first day of month at midnight
        current_time = datetime.fromtimestamp(now)
        if current_time.month == 12:
            next_rollover = current_time.replace(
                year=current_time.year + 1,
                month=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        else:
            next_rollover = current_time.replace(
                month=current_time.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        return next_rollover.timestamp()

    return now + interval_seconds


def get_week_start(dt: datetime) -> datetime:
    """Get the start of the week (last Sunday at midnight) for given datetime"""
    # weekday() returns 0=Monday, 6=Sunday
    days_since_sunday = (dt.weekday() + 1) % 7  # Convert to days since Sunday
    week_start = dt.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=days_since_sunday
    )
    return week_start


def get_period_info(when: str, suffix: str, entry_datetime: datetime) -> Tuple[datetime, datetime, str]:
    """Get period start, end, and suffix for given datetime."""
    if when == "MIDNIGHT" or when == "DAILY":
        # Daily: midnight to midnight
        period_start = entry_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1) - timedelta(seconds=1)
        period_suffix = period_start.strftime(suffix)

    elif when == "WEEKLY":
        # Weekly: Sunday to Saturday
        period_start = get_week_start(entry_datetime)
        period_end = period_start + timedelta(days=7) - timedelta(seconds=1)
        period_suffix = period_start.strftime(suffix)

    elif when == "MONTHLY":
        # Monthly: first to last day of month
        period_start = entry_datetime.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_start.month == 12:
            next_month = period_start.replace(year=period_start.year + 1, month=1)
        else:
            next_month = period_start.replace(month=period_start.month + 1)
        period_end = next_month - timedelta(seconds=1)
        period_suffix = period_start.strftime(suffix)

    return period_start, period_end, period_suffix


def is_period_complete(
    when: str, period_start: datetime, period_end: datetime, current_datetime: datetime
) -> bool:
    """Check if a period is complete (not the current period)."""
    if when == "MIDNIGHT" or when == "DAILY":
        # Complete if not today
        return period_start.date() < current_datetime.date()

    elif when == "WEEKLY":
        # Complete if not current week
        current_week_start = get_week_start(current_datetime)
        return period_start < current_week_start

    elif when == "MONTHLY":
        # Complete if not current month
        return (period_start.year, period_start.month) < (
            current_datetime.year,
            current_datetime.month,
        )

    return False
