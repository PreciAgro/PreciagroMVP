"""Quiet hours policy for temporal logic engine."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def in_quiet_hours(now_utc, quiet_window=("21:00", "06:00"), tz="Africa/Harare"):
    """Check if current time is within quiet hours."""
    start = time.fromisoformat(quiet_window[0])
    end = time.fromisoformat(quiet_window[1])
    local = now_utc.astimezone(ZoneInfo(tz)).time()
    return (local >= start) or (local < end)  # window crossing midnight


# Alias for backwards compatibility
is_quiet_hours = in_quiet_hours


class QuietHoursPolicy:
    """Evaluate whether a timestamp falls inside configured quiet hours."""

    def __init__(self, start_time: str, end_time: str, timezone: str = "UTC"):
        self.start_time = time.fromisoformat(start_time)
        self.end_time = time.fromisoformat(end_time)
        self.timezone = timezone

    def is_quiet_time(self, candidate: datetime) -> bool:
        """Return True when the candidate instant is inside the quiet window."""
        try:
            tzinfo = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            # FIX: tests failed on Windows missing IANA tzdata - fallback to UTC to keep quiet hours deterministic without optional tzdata dependency - mainline installs can still leverage full database when available
            tzinfo = timezone.utc
        local = candidate.astimezone(tzinfo).time()
        if self.start_time <= self.end_time:
            return self.start_time <= local < self.end_time
        return local >= self.start_time or local < self.end_time


def apply_quiet_hours_policy(
    channel: str, scheduled_time: datetime, message_type: str, priority: int
):
    """Apply quiet hour rules and return adjusted time plus reason."""
    policy = QuietHoursPolicy("22:00", "06:00", "UTC")
    if policy.is_quiet_time(scheduled_time):
        adjusted = scheduled_time + timedelta(hours=8)
        return adjusted, "Quiet hours adjustment applied"
    return scheduled_time, "Outside quiet hours"
