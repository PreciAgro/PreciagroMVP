"""Rule evaluator with predicate and window logic."""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from .contracts import Condition, WindowConfig, EventResponse
from .models import TemporalEvent
import json
import re

logger = logging.getLogger(__name__)


class PredicateEvaluator:
    """Evaluates conditions/predicates against events."""
    
    def evaluate_condition(self, condition: Condition, event_data: Dict[str, Any]) -> bool:
        """Evaluate a single condition against event data."""
        try:
            field_value = self._get_nested_field(event_data, condition.field)
            
            if field_value is None and condition.operator != "exists":
                return False
            
            return self._apply_operator(field_value, condition.operator, condition.value)
        
        except Exception as e:
            logger.error(f"Error evaluating condition {condition.field} {condition.operator} {condition.value}: {e}")
            return False
    
    def evaluate_conditions(self, conditions: List[Condition], event_data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Evaluate all conditions against event data.
        Returns (matches, confidence_score).
        """
        if not conditions:
            return True, 1.0
        
        total_weight = sum(c.weight for c in conditions)
        if total_weight == 0:
            return False, 0.0
        
        matched_weight = 0.0
        
        for condition in conditions:
            if self.evaluate_condition(condition, event_data):
                matched_weight += condition.weight
        
        confidence = matched_weight / total_weight
        matches = confidence >= 0.5  # Require at least 50% confidence to match
        
        return matches, confidence
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation (e.g., 'payload.temperature.value')."""
        keys = field_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def _apply_operator(self, field_value: Any, operator: str, condition_value: Any) -> bool:
        """Apply comparison operator."""
        try:
            if operator == "eq":
                return field_value == condition_value
            elif operator == "ne":
                return field_value != condition_value
            elif operator == "gt":
                return float(field_value) > float(condition_value)
            elif operator == "gte":
                return float(field_value) >= float(condition_value)
            elif operator == "lt":
                return float(field_value) < float(condition_value)
            elif operator == "lte":
                return float(field_value) <= float(condition_value)
            elif operator == "in":
                return field_value in condition_value
            elif operator == "not_in":
                return field_value not in condition_value
            elif operator == "contains":
                return str(condition_value).lower() in str(field_value).lower()
            elif operator == "exists":
                return field_value is not None
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        
        except (ValueError, TypeError) as e:
            logger.warning(f"Type error in operator {operator}: {e}")
            return False


class WindowEvaluator:
    """Evaluates events within time windows."""
    
    def __init__(self):
        self.predicate_evaluator = PredicateEvaluator()
    
    def get_window_events(
        self, 
        events: List[TemporalEvent], 
        window_config: WindowConfig, 
        current_time: Optional[datetime] = None
    ) -> List[TemporalEvent]:
        """Get events that fall within the specified time window."""
        if current_time is None:
            current_time = datetime.utcnow()
        
        window_start = self._calculate_window_start(current_time, window_config)
        
        # Filter events within window
        window_events = []
        for event in events:
            if window_start <= event.created_at <= current_time:
                window_events.append(event)
        
        return window_events
    
    def evaluate_window_conditions(
        self, 
        events: List[TemporalEvent], 
        conditions: List[Condition], 
        window_config: WindowConfig
    ) -> Tuple[bool, float, List[TemporalEvent]]:
        """
        Evaluate conditions across a window of events.
        Returns (matches, confidence, matching_events).
        """
        matching_events = []
        total_confidence = 0.0
        event_count = 0
        
        for event in events:
            event_data = {
                'event_type': event.event_type,
                'source': event.source,
                'payload': event.payload,
                'metadata': event.metadata,
                'created_at': event.created_at.isoformat(),
                'id': event.id
            }
            
            matches, confidence = self.predicate_evaluator.evaluate_conditions(conditions, event_data)
            
            if matches:
                matching_events.append(event)
                total_confidence += confidence
                event_count += 1
        
        if event_count == 0:
            return False, 0.0, []
        
        avg_confidence = total_confidence / event_count
        overall_match = len(matching_events) > 0 and avg_confidence >= 0.5
        
        return overall_match, avg_confidence, matching_events
    
    def _calculate_window_start(self, current_time: datetime, window_config: WindowConfig) -> datetime:
        """Calculate the start time for the window."""
        window_size = timedelta(seconds=window_config.size)
        
        if window_config.type == "sliding":
            return current_time - window_size
        elif window_config.type == "tumbling":
            # Align to window boundaries
            seconds_since_epoch = int(current_time.timestamp())
            window_start_epoch = (seconds_since_epoch // window_config.size) * window_config.size
            return datetime.fromtimestamp(window_start_epoch)
        elif window_config.type == "session":
            # Session windows are more complex - for now, treat like sliding
            return current_time - window_size
        else:
            logger.warning(f"Unknown window type: {window_config.type}")
            return current_time - window_size


class ContextEvaluator:
    """Evaluates events with additional context."""
    
    def __init__(self):
        self.window_evaluator = WindowEvaluator()
    
    def evaluate_with_context(
        self, 
        events: List[TemporalEvent], 
        conditions: List[Condition], 
        window_config: WindowConfig,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate events with additional context information."""
        current_time = datetime.utcnow()
        
        # Get events in window
        window_events = self.window_evaluator.get_window_events(events, window_config, current_time)
        
        # Evaluate conditions
        matches, confidence, matching_events = self.window_evaluator.evaluate_window_conditions(
            window_events, conditions, window_config
        )
        
        # Build evaluation result
        result = {
            'matches': matches,
            'confidence': confidence,
            'window_events_count': len(window_events),
            'matching_events_count': len(matching_events),
            'evaluation_time': current_time.isoformat(),
            'window_config': {
                'type': window_config.type,
                'size': window_config.size,
                'advance': window_config.advance,
                'session_timeout': window_config.session_timeout
            }
        }
        
        # Add context if provided
        if context:
            result['context'] = context
        
        # Add event details if matches found
        if matching_events:
            result['matching_events'] = [
                {
                    'id': event.id,
                    'event_type': event.event_type,
                    'created_at': event.created_at.isoformat(),
                    'payload_summary': self._summarize_payload(event.payload)
                }
                for event in matching_events[-5:]  # Last 5 matching events
            ]
        
        return result
    
    def _summarize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of event payload for logging."""
        summary = {}
        
        # Include key fields if they exist
        key_fields = ['temperature', 'humidity', 'soil_moisture', 'pest_type', 'disease_type', 'location']
        
        for field in key_fields:
            if field in payload:
                summary[field] = payload[field]
        
        # Limit size to avoid huge logs
        if len(summary) == 0:
            summary = {k: v for k, v in list(payload.items())[:3]}
        
        return summary


class RuleEvaluator:
    """Main rule evaluation orchestrator."""
    
    def __init__(self):
        self.context_evaluator = ContextEvaluator()
    
    async def evaluate_rule(
        self, 
        rule_data: Dict[str, Any], 
        events: List[TemporalEvent], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate a complete rule against events."""
        try:
            # Parse rule components
            conditions = [
                Condition(**cond) for cond in rule_data.get('conditions', [])
            ]
            window_config = WindowConfig(**rule_data.get('window_config', {}))
            
            # Evaluate with context
            evaluation_result = self.context_evaluator.evaluate_with_context(
                events, conditions, window_config, context
            )
            
            # Add rule metadata
            evaluation_result['rule_name'] = rule_data.get('name', 'unknown')
            evaluation_result['rule_id'] = rule_data.get('id')
            
            logger.info(f"Rule '{rule_data.get('name')}' evaluation: "
                       f"matches={evaluation_result['matches']}, "
                       f"confidence={evaluation_result['confidence']:.2f}")
            
            return evaluation_result
        
        except Exception as e:
            logger.error(f"Error evaluating rule {rule_data.get('name', 'unknown')}: {e}")
            return {
                'matches': False,
                'confidence': 0.0,
                'error': str(e),
                'rule_name': rule_data.get('name', 'unknown'),
                'rule_id': rule_data.get('id')
            }
    
    async def batch_evaluate_rules(
        self, 
        rules: List[Dict[str, Any]], 
        events: List[TemporalEvent],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Evaluate multiple rules against the same set of events."""
        results = []
        
        for rule in rules:
            if not rule.get('enabled', True):
                continue
            
            result = await self.evaluate_rule(rule, events, context)
            results.append(result)
        
        return results
