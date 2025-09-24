"""Minimal working test for temporal logic engine core components."""
from preciagro.packages.engines.temporal_logic.contracts import (
    EngineEvent, Rule, Trigger, Window, Message, Dedupe, Clause
)
import pytest
import os
import sys
from datetime import datetime, timezone

# Set test database URL
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

# Import only what we can safely test


class TestBasicContracts:
    """Test basic contract validation."""

    def test_engine_event_creation(self):
        """Test EngineEvent creation and validation."""
        event = EngineEvent(
            topic="weather.forecast",
            id="evt_001",
            ts_utc=datetime.now(timezone.utc),
            farm_id="farm_123",
            farmer_tz="America/New_York",
            payload={"temperature": 25.5, "humidity": 80}
        )

        assert event.topic == "weather.forecast"
        assert event.id == "evt_001"
        assert event.farm_id == "farm_123"
        assert event.payload["temperature"] == 25.5

    def test_clause_creation(self):
        """Test Clause validation."""
        clause = Clause(
            key="temperature",
            op=" >",  # Note the space before >
            value=30
        )

        assert clause.key == "temperature"
        assert clause.op == " >"
        assert clause.value == 30

    def test_trigger_creation(self):
        """Test Trigger creation."""
        trigger = Trigger(
            topic="weather.forecast",
            when=[
                # Note the space before >
                Clause(key="temperature", op=" >", value=30),
                Clause(key="humidity", op=">=", value=80)
            ]
        )

        assert trigger.topic == "weather.forecast"
        assert len(trigger.when) == 2
        assert trigger.when[0].key == "temperature"

    def test_window_creation(self):
        """Test Window creation."""
        window = Window(
            start_offset_hours=2,
            end_offset_hours=6,
            day_offset=0
        )

        assert window.start_offset_hours == 2
        assert window.end_offset_hours == 6
        assert window.day_offset == 0

    def test_rule_creation(self):
        """Test complete Rule creation."""
        rule = Rule(
            id="test_rule_001",
            trigger=Trigger(topic="weather.forecast"),
            window=Window(day_offset=1),
            dedupe=Dedupe(scope="farm_daily"),
            message=Message(short="Test alert message")
        )

        assert rule.id == "test_rule_001"
        assert rule.trigger.topic == "weather.forecast"
        assert rule.window.day_offset == 1
        assert rule.dedupe.scope == "farm_daily"
        assert rule.message.short == "Test alert message"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
