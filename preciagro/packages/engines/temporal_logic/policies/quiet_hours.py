"""Quiet hours policy for temporal logic engine."""
from datetime import time, datetime
from zoneinfo import ZoneInfo

def in_quiet_hours(now_utc, quiet_window=("21:00","06:00"), tz="Africa/Harare"):
    """Check if current time is within quiet hours."""
    start = time.fromisoformat(quiet_window[0])
    end = time.fromisoformat(quiet_window[1])
    local = now_utc.astimezone(ZoneInfo(tz)).time()
    return (local >= start) or (local < end)  # window crossing midnight
