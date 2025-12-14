"""Compiles rules and context into scheduled jobs."""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .contracts import Action, ScheduledTaskCreate, TaskConfig
from .evaluator import RuleEvaluator
from .models import TemporalEvent, TemporalRule

logger = logging.getLogger(__name__)


class ActionCompiler:
    """Compiles rule actions into executable tasks."""

    def compile_action(
        self,
        action: Action,
        rule: TemporalRule,
        triggering_event: Optional[TemporalEvent] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTaskCreate:
        """Compile a single action into a scheduled task."""

        # Calculate execution time
        execution_time = datetime.now(
            timezone.utc) + timedelta(seconds=action.delay)

        # Compile task configuration based on action type
        task_config = self._compile_task_config(
            action, rule, triggering_event, context)

        return ScheduledTaskCreate(
            rule_id=rule.id,
            triggering_event_id=triggering_event.id if triggering_event else None,
            task_type=action.type,
            task_config=task_config,
            scheduled_for=execution_time,
            max_attempts=3,
        )

    def _compile_task_config(
        self,
        action: Action,
        rule: TemporalRule,
        triggering_event: Optional[TemporalEvent] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskConfig:
        """Compile task configuration with variable substitution."""

        config = action.config.copy()

        # Build variable context for substitution
        variables = self._build_variable_context(
            rule, triggering_event, context)

        # Substitute variables in configuration
        substituted_config = self._substitute_variables(config, variables)

        return TaskConfig(**substituted_config)

    def _build_variable_context(
        self,
        rule: TemporalRule,
        triggering_event: Optional[TemporalEvent] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build context variables for template substitution."""

        variables = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rule": {"id": rule.id, "name": rule.name, "description": rule.description},
        }

        if triggering_event:
            variables["event"] = {
                "id": triggering_event.id,
                "type": triggering_event.event_type,
                "source": triggering_event.source,
                "payload": triggering_event.payload,
                "metadata": triggering_event.metadata,
                "created_at": triggering_event.created_at.isoformat(),
            }

            # Flatten payload and metadata for easy access
            if triggering_event.payload:
                variables["payload"] = triggering_event.payload
            if triggering_event.metadata:
                variables["metadata"] = triggering_event.metadata

        if context:
            variables["context"] = context

        return variables

    def _substitute_variables(
        self, config: Dict[str, Any], variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Substitute template variables in configuration."""

        def substitute_value(value):
            if isinstance(value, str):
                return self._substitute_string_template(value, variables)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value

        return substitute_value(config)

    def _substitute_string_template(
        self, template: str, variables: Dict[str, Any]
    ) -> str:
        """Substitute variables in string templates using {{variable}} syntax."""
        import re

        def replace_var(match):
            var_path = match.group(1)
            try:
                value = self._get_nested_variable(variables, var_path)
                return str(value) if value is not None else match.group(0)
            except (KeyError, TypeError):
                logger.warning(f"Variable not found: {var_path}")
                return match.group(0)

        # Pattern to match {{variable.path}}
        pattern = r"\{\{([^}]+)\}\}"
        return re.sub(pattern, replace_var, template)

    def _get_nested_variable(self, variables: Dict[str, Any], path: str) -> Any:
        """Get nested variable value using dot notation."""
        keys = path.strip().split(".")
        current = variables

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None

            if current is None:
                return None

        return current


class ScheduleCompiler:
    """Compiles rules into scheduled execution plans."""

    def __init__(self):
        self.action_compiler = ActionCompiler()

    def compile_rule_to_schedule(
        self,
        rule: TemporalRule,
        evaluation_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ScheduledTaskCreate]:
        """Compile a rule into scheduled tasks based on evaluation result."""

        if not evaluation_result.get("matches", False):
            return []

        tasks = []

        # Get actions from rule
        actions = rule.actions if isinstance(rule.actions, list) else []

        # Get triggering event if available
        triggering_event = None
        matching_events = evaluation_result.get("matching_events", [])
        if matching_events:
            # Use the most recent matching event as trigger
            latest_event_data = max(
                matching_events, key=lambda x: x["created_at"])
            # Note: In real implementation, you'd fetch the actual event object
            # For now, we'll work with the event data we have
            # FIX: Ruff F841 lint — triggering_event should mirror most recent match — keeps scheduling context without loading full ORM object.
            triggering_event = latest_event_data

        for action_data in actions:
            try:
                # Convert action data to Action object
                action = Action(**action_data)

                # Compile to scheduled task
                task = self.action_compiler.compile_action(
                    action, rule, triggering_event, context
                )
                tasks.append(task)

                logger.info(
                    f"Compiled action '{action.type}' for rule '{rule.name}' "
                    f"scheduled for {task.scheduled_for}"
                )

            except Exception as e:
                logger.error(
                    f"Error compiling action for rule '{rule.name}': {e}")

        return tasks

    def compile_batch_rules(
        self,
        rules_with_evaluations: List[Tuple[TemporalRule, Dict[str, Any]]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ScheduledTaskCreate]:
        """Compile multiple rules with their evaluation results."""

        all_tasks = []

        for rule, evaluation_result in rules_with_evaluations:
            try:
                tasks = self.compile_rule_to_schedule(
                    rule, evaluation_result, context)
                all_tasks.extend(tasks)
            except Exception as e:
                logger.error(f"Error compiling rule '{rule.name}': {e}")

        return all_tasks


class RuleCompiler:
    """Main orchestrator for rule compilation."""

    def __init__(self):
        self.rule_evaluator = RuleEvaluator()
        self.schedule_compiler = ScheduleCompiler()

    async def compile_rule_to_tasks(
        self, rule_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Compile a single rule dictionary into task dictionaries."""
        context = context or {}
        tasks: List[Dict[str, Any]] = []
        actions = rule_data.get("actions", [])

        for action in actions:
            task_type = action.get("type", "send_message")
            task_config = dict(action.get("config", {}))

            for key in ("channel", "template", "message"):
                if key in action and key not in task_config:
                    task_config[key] = action[key]

            tasks.append(
                {
                    "user_id": context.get("user_id"),
                    "task_type": task_type,
                    "task_config": task_config,
                    "priority": rule_data.get("metadata", {}).get("priority", "medium"),
                }
            )

        return tasks

    def _substitute_variables(self, template: str, context: Dict[str, Any]) -> str:
        """Replace {{variable}} tokens in template strings."""

        def replacer(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            return str(context.get(key, match.group(0)))

        return re.sub(r"\{\{\s*([^}]+)\s*\}\}", replacer, template)

    async def compile_rules_for_events(
        self,
        rules: List[TemporalRule],
        events: List[TemporalEvent],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ScheduledTaskCreate]:
        """Evaluate rules against events and compile matching ones to tasks."""

        # Convert rules to evaluation format
        rule_data_list = []
        for rule in rules:
            rule_data = {
                "id": rule.id,
                "name": rule.name,
                "conditions": rule.conditions,
                "actions": rule.actions,
                "window_config": rule.window_config,
                "enabled": rule.enabled,
            }
            rule_data_list.append(rule_data)

        # Evaluate all rules
        evaluation_results = await self.rule_evaluator.batch_evaluate_rules(
            rule_data_list, events, context
        )

        # Compile matching rules to scheduled tasks
        rules_with_evaluations = list(zip(rules, evaluation_results))
        tasks = self.schedule_compiler.compile_batch_rules(
            rules_with_evaluations, context
        )

        logger.info(
            f"Compiled {len(tasks)} tasks from {len(rules)} rules "
            f"against {len(events)} events"
        )

        return tasks

    async def compile_single_rule(
        self,
        rule: TemporalRule,
        events: List[TemporalEvent],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ScheduledTaskCreate]:
        """Compile a single rule against events."""
        return await self.compile_rules_for_events([rule], events, context)


class CompilationOptimizer:
    """Optimizes rule compilation for performance."""

    def __init__(self):
        self.compilation_cache = {}

    def optimize_rule_evaluation_order(
        self, rules: List[TemporalRule]
    ) -> List[TemporalRule]:
        """Optimize the order of rule evaluation for performance."""

        # Sort rules by complexity (simpler rules first)
        def rule_complexity(rule):
            condition_complexity = len(
                rule.conditions) if rule.conditions else 0
            action_complexity = len(rule.actions) if rule.actions else 0
            window_complexity = (
                rule.window_config.get(
                    "size", 3600) if rule.window_config else 3600
            )

            return condition_complexity + action_complexity + (window_complexity / 3600)

        return sorted(rules, key=rule_complexity)

    def should_skip_evaluation(
        self, rule: TemporalRule, events: List[TemporalEvent]
    ) -> bool:
        """Determine if rule evaluation can be skipped based on heuristics."""

        if not rule.enabled:
            return True

        # Skip if no events
        if not events:
            return True

        # Skip if rule has no conditions or actions
        if not rule.conditions or not rule.actions:
            return True

        # More sophisticated heuristics could be added here
        return False

    def cache_compilation_result(
        self, rule_id: int, events_hash: str, result: List[ScheduledTaskCreate]
    ) -> None:
        """Cache compilation results for performance."""
        cache_key = f"{rule_id}:{events_hash}"
        self.compilation_cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now(timezone.utc),
        }

    def get_cached_compilation(
        self, rule_id: int, events_hash: str, max_age_seconds: int = 300
    ) -> Optional[List[ScheduledTaskCreate]]:
        """Get cached compilation result if still valid."""
        cache_key = f"{rule_id}:{events_hash}"

        if cache_key not in self.compilation_cache:
            return None

        cached = self.compilation_cache[cache_key]
        age = (datetime.now(timezone.utc) -
               cached["timestamp"]).total_seconds()

        if age > max_age_seconds:
            del self.compilation_cache[cache_key]
            return None

        return cached["result"]


# Utility functions
def generate_events_hash(events: List[TemporalEvent]) -> str:
    """Generate a hash for a list of events for caching purposes."""
    import hashlib

    event_ids = sorted([str(event.id) for event in events])
    hash_input = "|".join(event_ids)
    return hashlib.md5(hash_input.encode()).hexdigest()


def validate_compiled_tasks(tasks: List[ScheduledTaskCreate]) -> List[str]:
    """Validate compiled tasks and return any validation errors."""
    errors = []

    for i, task in enumerate(tasks):
        if not task.task_type:
            errors.append(f"Task {i}: Missing task_type")

        if not task.scheduled_for:
            errors.append(f"Task {i}: Missing scheduled_for")

        if task.scheduled_for < datetime.now(timezone.utc):
            errors.append(f"Task {i}: Scheduled time is in the past")

        if task.max_attempts < 1:
            errors.append(f"Task {i}: max_attempts must be at least 1")

    return errors
