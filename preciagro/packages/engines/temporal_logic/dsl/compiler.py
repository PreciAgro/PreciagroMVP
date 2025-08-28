"""Task compiler for generating scheduled notifications."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple
from ..contracts import Rule, EngineEvent, ScheduleWindow
from ..models import ScheduleItem

class TaskCompiler:
    """Compiles rules into scheduled notification tasks."""
    
    def compile_tasks(self, rule: Rule, event: EngineEvent, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Compile rule into scheduled tasks."""
        context = context or {}
        
        tasks = []
        for window in rule.windows:
            task_data = self._compile_window_task(rule, event, window, context)
            if task_data:
                tasks.append(task_data)
        
        return tasks
    
    def _compile_window_task(self, rule: Rule, event: EngineEvent, window: ScheduleWindow, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compile single window into a task."""
        now = datetime.now(timezone.utc)
        
        # Calculate schedule time
        schedule_time = self._calculate_schedule_time(window, now)
        
        # Build task payload
        payload = {
            "short_text": window.message.format(**self._get_template_vars(event, context)),
            "channel": window.channel,
            "metadata": {
                "rule_id": rule.id,
                "window_id": window.id,
                "event_id": event.event_id,
                "user_id": event.user_id,
                "farm_id": event.farm_id
            }
        }
        
        # Build target
        target = {"phone_e164": context.get("phone") or event.metadata.get("phone")}
        
        # Generate deduplication key
        dedupe_key = self._generate_dedupe_key(rule, event, window) if rule.deduplication else None
        
        return {
            "id": str(uuid.uuid4()),
            "user_id": event.user_id,
            "rule_id": rule.id,
            "schedule_time": schedule_time,
            "payload": payload,
            "target": target,
            "dedupe_key": dedupe_key,
            "status": "pending"
        }
    
    def _calculate_schedule_time(self, window: ScheduleWindow, base_time: datetime) -> datetime:
        """Calculate when to schedule the notification."""
        if window.delay:
            if window.delay.endswith("h"):
                hours = int(window.delay[:-1])
                return base_time + timedelta(hours=hours)
            elif window.delay.endswith("m"):
                minutes = int(window.delay[:-1])
                return base_time + timedelta(minutes=minutes)
            elif window.delay.endswith("d"):
                days = int(window.delay[:-1])
                return base_time + timedelta(days=days)
        
        # If specific time is set (e.g., "08:00")
        if hasattr(window, 'time') and window.time:
            hour, minute = map(int, window.time.split(":"))
            schedule_date = base_time.date()
            schedule_time = datetime.combine(schedule_date, datetime.min.time().replace(hour=hour, minute=minute))
            schedule_time = schedule_time.replace(tzinfo=timezone.utc)
            
            # If time has passed today, schedule for tomorrow
            if schedule_time <= base_time:
                schedule_time += timedelta(days=1)
            
            return schedule_time
        
        # Default: schedule immediately
        return base_time
    
    def _get_template_vars(self, event: EngineEvent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get variables for message template formatting."""
        vars_dict = {
            "user_id": event.user_id,
            "farm_id": event.farm_id,
            "event_type": event.event_type
        }
        vars_dict.update(event.metadata)
        vars_dict.update(context)
        return vars_dict
    
    def _generate_dedupe_key(self, rule: Rule, event: EngineEvent, window: ScheduleWindow) -> str:
        """Generate deduplication key."""
        key_parts = [
            rule.id,
            window.id,
            str(event.user_id),
            str(event.farm_id)
        ]
        
        # Add deduplication fields
        if rule.deduplication and rule.deduplication.fields:
            for field in rule.deduplication.fields:
                value = getattr(event, field, None) or event.metadata.get(field, "")
                key_parts.append(str(value))
        
        return "|".join(key_parts)
