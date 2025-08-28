"""Quiet hours policy implementation."""
import logging
from typing import Optional, Tuple
from datetime import datetime, time, timezone
import pytz
from ..config import config

logger = logging.getLogger(__name__)


class QuietHoursPolicy:
    """Enforces quiet hours for message sending."""
    
    def __init__(self, timezone_str: Optional[str] = None):
        """Initialize quiet hours policy."""
        self.timezone_str = timezone_str or config.quiet_hours_timezone
        self.start_time = self._parse_time(config.quiet_hours_start)
        self.end_time = self._parse_time(config.quiet_hours_end)
        
        try:
            self.timezone = pytz.timezone(self.timezone_str)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone: {self.timezone_str}, using UTC")
            self.timezone = pytz.UTC
    
    def is_quiet_hours(self, check_time: Optional[datetime] = None) -> bool:
        """Check if current time is within quiet hours."""
        if check_time is None:
            check_time = datetime.now(self.timezone)
        elif check_time.tzinfo is None:
            check_time = self.timezone.localize(check_time)
        else:
            check_time = check_time.astimezone(self.timezone)
        
        current_time = check_time.time()
        
        # Handle same-day quiet hours (e.g., 14:00 - 16:00)
        if self.start_time <= self.end_time:
            return self.start_time <= current_time <= self.end_time
        
        # Handle overnight quiet hours (e.g., 22:00 - 08:00)
        return current_time >= self.start_time or current_time <= self.end_time
    
    def get_next_send_time(self, proposed_time: Optional[datetime] = None) -> datetime:
        """Get the next allowable send time outside quiet hours."""
        if proposed_time is None:
            proposed_time = datetime.now(self.timezone)
        elif proposed_time.tzinfo is None:
            proposed_time = self.timezone.localize(proposed_time)
        else:
            proposed_time = proposed_time.astimezone(self.timezone)
        
        if not self.is_quiet_hours(proposed_time):
            return proposed_time
        
        # Calculate next send time (end of quiet hours)
        next_send_date = proposed_time.date()
        
        # Handle overnight quiet hours
        if self.start_time > self.end_time:
            # If we're before end time, use same day
            if proposed_time.time() <= self.end_time:
                next_send_time = datetime.combine(next_send_date, self.end_time)
            else:
                # If we're after start time, use next day's end time
                from datetime import timedelta
                next_send_date = next_send_date + timedelta(days=1)
                next_send_time = datetime.combine(next_send_date, self.end_time)
        else:
            # Same-day quiet hours - wait until end time
            next_send_time = datetime.combine(next_send_date, self.end_time)
        
        return self.timezone.localize(next_send_time)
    
    def apply_policy(
        self, 
        scheduled_time: datetime, 
        message_type: str = "default",
        priority: int = 5
    ) -> Tuple[datetime, str]:
        """
        Apply quiet hours policy to a scheduled message.
        Returns (adjusted_time, reason).
        """
        # Convert to local timezone
        if scheduled_time.tzinfo is None:
            local_time = self.timezone.localize(scheduled_time)
        else:
            local_time = scheduled_time.astimezone(self.timezone)
        
        # Check for exceptions
        if self._is_exception(message_type, priority):
            return scheduled_time, "Exception: High priority or emergency message"
        
        # Check if in quiet hours
        if not self.is_quiet_hours(local_time):
            return scheduled_time, "Outside quiet hours"
        
        # Adjust time to next allowed period
        next_send_time = self.get_next_send_time(local_time)
        delay_minutes = int((next_send_time - local_time).total_seconds() / 60)
        
        logger.info(f"Message delayed by {delay_minutes} minutes due to quiet hours policy")
        
        return next_send_time, f"Delayed {delay_minutes} minutes due to quiet hours"
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format."""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour, minute)
        except (ValueError, AttributeError):
            logger.error(f"Invalid time format: {time_str}, using 00:00")
            return time(0, 0)
    
    def _is_exception(self, message_type: str, priority: int) -> bool:
        """Check if message type/priority is exempt from quiet hours."""
        # High priority messages (8-10) bypass quiet hours
        if priority >= 8:
            return True
        
        # Emergency message types bypass quiet hours
        emergency_types = ["emergency", "alert", "critical", "pest_detection", "disease_outbreak"]
        if message_type.lower() in emergency_types:
            return True
        
        return False
    
    def get_policy_info(self) -> dict:
        """Get current policy configuration."""
        return {
            "timezone": self.timezone_str,
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
            "current_time": datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S %Z"),
            "is_currently_quiet_hours": self.is_quiet_hours()
        }


class ChannelSpecificQuietHours:
    """Manage different quiet hours for different channels."""
    
    def __init__(self):
        self.channel_policies = {}
        self.default_policy = QuietHoursPolicy()
    
    def add_channel_policy(
        self, 
        channel: str, 
        start_time: str, 
        end_time: str, 
        timezone_str: Optional[str] = None
    ):
        """Add channel-specific quiet hours policy."""
        # Temporarily create a config-like object for the channel
        class ChannelConfig:
            def __init__(self):
                self.quiet_hours_start = start_time
                self.quiet_hours_end = end_time
                self.quiet_hours_timezone = timezone_str or config.quiet_hours_timezone
        
        channel_config = ChannelConfig()
        
        # Create policy with channel-specific config
        policy = QuietHoursPolicy(timezone_str)
        policy.start_time = policy._parse_time(start_time)
        policy.end_time = policy._parse_time(end_time)
        
        self.channel_policies[channel] = policy
        logger.info(f"Added quiet hours policy for {channel}: {start_time} - {end_time}")
    
    def get_policy_for_channel(self, channel: str) -> QuietHoursPolicy:
        """Get quiet hours policy for specific channel."""
        return self.channel_policies.get(channel, self.default_policy)
    
    def apply_channel_policy(
        self, 
        channel: str, 
        scheduled_time: datetime, 
        message_type: str = "default",
        priority: int = 5
    ) -> Tuple[datetime, str]:
        """Apply channel-specific quiet hours policy."""
        policy = self.get_policy_for_channel(channel)
        return policy.apply_policy(scheduled_time, message_type, priority)


# Global quiet hours manager
quiet_hours_manager = ChannelSpecificQuietHours()

# Default channel configurations
quiet_hours_manager.add_channel_policy("sms", "22:00", "08:00")
quiet_hours_manager.add_channel_policy("whatsapp", "22:00", "07:00")
quiet_hours_manager.add_channel_policy("email", "23:00", "06:00")


def apply_quiet_hours_policy(
    channel: str,
    scheduled_time: datetime,
    message_type: str = "default",
    priority: int = 5
) -> Tuple[datetime, str]:
    """
    Convenience function to apply quiet hours policy.
    
    Args:
        channel: Communication channel (sms, whatsapp, email)
        scheduled_time: Originally scheduled time
        message_type: Type of message (for exceptions)
        priority: Message priority (1-10, higher bypasses quiet hours)
    
    Returns:
        Tuple of (adjusted_time, reason)
    """
    return quiet_hours_manager.apply_channel_policy(
        channel, scheduled_time, message_type, priority
    )
