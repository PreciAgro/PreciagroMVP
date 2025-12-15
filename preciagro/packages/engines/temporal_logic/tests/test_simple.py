"""Simple working test for temporal logic engine."""

import os
import sys
from datetime import datetime, timezone

import pytest

from preciagro.packages.engines.temporal_logic.contracts import EngineEvent
from preciagro.packages.engines.temporal_logic.dsl.compiler import TaskCompiler
from preciagro.packages.engines.temporal_logic.dsl.evaluator import RuleEvaluator

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))


class TestTemporalLogicEngine:
    """Test suite for temporal logic engine components."""

    def test_engine_event_creation(self):
        """Test EngineEvent creation and validation."""
        event = EngineEvent(
            event_id="test_001",
            event_type="weather_forecast",
            user_id="user_123",
            farm_id="farm_456",
            timestamp=datetime.now(timezone.utc),
            metadata={"temperature": 25.5, "humidity": 80},
        )

        assert event.event_id == "test_001"
        assert event.event_type == "weather_forecast"
        assert event.user_id == "user_123"
        assert event.metadata["temperature"] == 25.5

    def test_rule_evaluator_basic(self):
        """Test basic rule evaluation functionality."""
        evaluator = RuleEvaluator()

        # Create a simple test event
        event = EngineEvent(
            event_id="test_002",
            event_type="weather_forecast",
            user_id="user_123",
            farm_id="farm_456",
            timestamp=datetime.now(timezone.utc),
            metadata={"humidity": 85, "crop_type": "tomato"},
        )
        # FIX: Ruff F841 lint - ensure event instantiation is asserted so the construction remains covered and lint passes.
        assert event.metadata["humidity"] == 85

        # Test the _apply_operator method directly
        assert evaluator._apply_operator(
            85, "gt", 80
        )  # FIX: Ruff E712 lint - rely on truthiness instead of explicit True comparison.
        assert not evaluator._apply_operator(75, "gt", 80)
        assert evaluator._apply_operator("tomato", "eq", "tomato")

    def test_task_compiler_basic(self):
        """Test basic task compilation functionality."""
        compiler = TaskCompiler()

        # Test template variable generation
        event = EngineEvent(
            event_id="test_003",
            event_type="weather_forecast",
            user_id="user_123",
            farm_id="farm_456",
            timestamp=datetime.now(timezone.utc),
            metadata={"temperature": 25.5, "crop": "corn"},
        )

        context = {"phone": "+1234567890", "name": "John"}

        vars_dict = compiler._get_template_vars(event, context)

        assert vars_dict["user_id"] == "user_123"
        assert vars_dict["farm_id"] == "farm_456"
        assert vars_dict["temperature"] == 25.5
        assert vars_dict["phone"] == "+1234567890"
        assert vars_dict["name"] == "John"

    def test_dedupe_key_generation(self):
        """Test deduplication key generation."""
        from preciagro.packages.engines.temporal_logic.contracts import (
            Deduplication,
            Rule,
            ScheduleWindow,
            Trigger,
        )

        compiler = TaskCompiler()

        # Create test objects
        rule = Rule(
            id="test_rule",
            trigger=Trigger(event_type="test", filters=[]),
            windows=[ScheduleWindow(id="window1", channel="sms", message="test")],
            deduplication=Deduplication(window="24h", fields=["farm_id", "crop_type"]),
        )

        event = EngineEvent(
            event_id="test_004",
            event_type="test",
            user_id="user_123",
            farm_id="farm_456",
            timestamp=datetime.now(timezone.utc),
            metadata={"crop_type": "wheat"},
        )

        window = rule.windows[0]
        dedupe_key = compiler._generate_dedupe_key(rule, event, window)

        expected_parts = ["test_rule", "window1", "user_123", "farm_456", "wheat"]
        assert dedupe_key == "|".join(expected_parts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
