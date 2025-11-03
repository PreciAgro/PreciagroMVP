"""Rule evaluator for temporal logic conditions."""

import operator
from typing import Any, Dict

from ..contracts import EngineEvent, Preconditions, Rule, Trigger


class RuleEvaluator:
    """Evaluates rule conditions against events."""

    def should_trigger(
        self, rule: Rule, event: EngineEvent, context: Dict[str, Any] = None
    ) -> bool:
        """Check if rule should trigger for given event."""
        context = context or {}

        # Check trigger conditions
        if not self._check_trigger(rule.trigger, event):
            return False

        # Check preconditions if they exist
        if rule.preconditions and not self._check_preconditions(
            rule.preconditions, event, context
        ):
            return False

        return True

    def _check_trigger(self, trigger: Trigger, event: EngineEvent) -> bool:
        """Check if trigger conditions match."""
        # Check event type
        if trigger.event_type != event.event_type:
            return False

        # Check filters
        for filter_condition in trigger.filters:
            field = filter_condition["field"]
            op = filter_condition["operator"]
            value = filter_condition["value"]

            event_value = getattr(event, field, None)
            if event_value is None and field in event.metadata:
                event_value = event.metadata[field]

            if not self._apply_operator(event_value, op, value):
                return False

        return True

    def _check_preconditions(
        self, preconds: Preconditions, event: EngineEvent, context: Dict[str, Any]
    ) -> bool:
        """Check preconditions against context."""
        for condition in preconds.conditions:
            field = condition["field"]
            op = condition["operator"]
            value = condition["value"]

            # Get value from context or event
            ctx_value = context.get(field)
            if ctx_value is None:
                ctx_value = getattr(event, field, None)
            if ctx_value is None and hasattr(event, "metadata"):
                ctx_value = event.metadata.get(field)

            if not self._apply_operator(ctx_value, op, value):
                return False

        return True

    def _apply_operator(self, left: Any, op: str, right: Any) -> bool:
        """Apply comparison operator."""
        ops = {
            "eq": operator.eq,
            "ne": operator.ne,
            "gt": operator.gt,
            "gte": operator.ge,
            "lt": operator.lt,
            "lte": operator.le,
            "in": lambda left_value, right_value: left_value in right_value,  # FIX: Ruff E741 lint — expand parameter names for readability.
            "not_in": lambda left_value, right_value: left_value not in right_value,
            "contains": lambda left_value, right_value: right_value in left_value if left_value else False,
        }

        if op not in ops:
            raise ValueError(f"Unknown operator: {op}")

        try:
            return ops[op](left, right)
        except (TypeError, ValueError):
            return False
