"""Comprehensive test suite for Temporal Logic Engine."""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from ..models import (
    Base, TemporalEvent, TemporalRule, ScheduledTask,
    TaskOutcome, UserIntent, RateLimitBucket
)
from ..contracts import (
    EventCreate, EventResponse, RuleCreate, RuleResponse,
    TaskCreate, TaskResponse, OutcomeCreate, IntentCreate
)
from ..evaluator import PredicateEvaluator
from ..compiler import RuleCompiler
from ..dsl_loader import DSLLoader
from ..policies.quiet_hours import QuietHoursPolicy
from ..policies.rate_limits import RateLimitPolicy
from ..security.auth import security_middleware
from ..telemetry.metrics import engine_metrics
from ..channels.whatsapp_meta import WhatsAppChannel
from ..channels.sms_twilio import SMSChannel
from ..due_queue.dispatcher import TaskDispatcher
from ..due_queue.worker import TaskWorker


# Test Database Setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine):
    """Create test database session."""
    async with AsyncSession(async_engine) as session:
        yield session


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "user_id": "test_user_001",
        "event_type": "weather_data",
        "event_data": {
            "temperature": 25.5,
            "humidity": 60,
            "pressure": 1013.2
        },
        "context_data": {
            "location": "field_001",
            "sensor_id": "weather_sensor_001"
        },
        "source": "weather_station"
    }


@pytest.fixture
def sample_rule_data():
    """Sample rule data for testing."""
    return {
        "name": "test_weather_alert",
        "description": "Test weather alert rule",
        "conditions": [
            {
                "type": "weather",
                "predicate": "temperature > 30",
                "window": "current"
            }
        ],
        "actions": [
            {
                "type": "send_message",
                "channel": "whatsapp",
                "template": "high_temperature_alert"
            }
        ],
        "metadata": {
            "category": "weather",
            "priority": "high"
        }
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for testing."""
    return {
        "user_id": "test_user_001",
        "task_type": "send_message",
        "task_config": {
            "channel": "whatsapp",
            "template": "test_template",
            "message": "Test message"
        },
        "scheduled_for": datetime.utcnow() + timedelta(hours=1),
        "priority": "medium"
    }


class TestModels:
    """Test database models."""

    @pytest_asyncio.async_test
    async def test_temporal_event_creation(self, async_session, sample_event_data):
        """Test TemporalEvent model creation."""
        event = TemporalEvent(**sample_event_data)
        async_session.add(event)
        await async_session.commit()
        await async_session.refresh(event)

        assert event.id is not None
        assert event.user_id == sample_event_data["user_id"]
        assert event.event_type == sample_event_data["event_type"]
        assert event.created_at is not None

    @pytest_asyncio.async_test
    async def test_temporal_rule_creation(self, async_session, sample_rule_data):
        """Test TemporalRule model creation."""
        rule = TemporalRule(**sample_rule_data)
        async_session.add(rule)
        await async_session.commit()
        await async_session.refresh(rule)

        assert rule.id is not None
        assert rule.name == sample_rule_data["name"]
        assert rule.is_active is True
        assert len(rule.conditions) > 0

    @pytest_asyncio.async_test
    async def test_scheduled_task_creation(self, async_session, sample_task_data):
        """Test ScheduledTask model creation."""
        task = ScheduledTask(
            task_id="test_task_001",
            **sample_task_data
        )
        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        assert task.id is not None
        assert task.task_id == "test_task_001"
        assert task.status == "pending"
        assert task.attempts == 0


class TestEvaluator:
    """Test predicate evaluator."""

    def test_simple_predicate_evaluation(self):
        """Test simple predicate evaluation."""
        evaluator = PredicateEvaluator()

        context = {"temperature": 25, "humidity": 60}

        # Test simple comparisons
        assert evaluator.evaluate("temperature > 20", context) is True
        assert evaluator.evaluate("temperature < 20", context) is False
        assert evaluator.evaluate("humidity == 60", context) is True
        assert evaluator.evaluate(
            "temperature >= 25 AND humidity < 70", context) is True

    def test_complex_predicate_evaluation(self):
        """Test complex predicate evaluation."""
        evaluator = PredicateEvaluator()

        context = {
            "temperature": 25,
            "humidity": 80,
            "pressure": 1013,
            "wind_speed": 5
        }

        # Test complex expressions
        predicate = "temperature > 20 AND humidity > 70 OR pressure < 1000"
        assert evaluator.evaluate(predicate, context) is True

        predicate = "temperature > 30 AND (humidity > 90 OR wind_speed > 10)"
        assert evaluator.evaluate(predicate, context) is False

    def test_window_evaluation(self):
        """Test time window evaluation."""
        evaluator = PredicateEvaluator()

        # Mock time-based context
        now = datetime.utcnow()
        context = {
            "current_time": now,
            "last_rain": now - timedelta(hours=2)
        }

        # This would need more complex implementation
        # For now, just test the basic structure
        assert evaluator._validate_predicate("temperature > 20") is True
        assert evaluator._validate_predicate("invalid_syntax >") is False


class TestCompiler:
    """Test rule compiler."""

    @pytest_asyncio.async_test
    async def test_rule_compilation(self, sample_rule_data):
        """Test rule compilation to scheduled tasks."""
        compiler = RuleCompiler()

        rule = sample_rule_data
        context = {
            "user_id": "test_user",
            "temperature": 35,  # Above threshold
            "location": "field_001"
        }

        tasks = await compiler.compile_rule_to_tasks(rule, context)

        assert len(tasks) > 0
        assert all(task["user_id"] == "test_user" for task in tasks)
        assert all("task_config" in task for task in tasks)

    def test_variable_substitution(self):
        """Test variable substitution in task configs."""
        compiler = RuleCompiler()

        template = "Temperature is {{temperature}}°C at {{location}}"
        context = {"temperature": 25, "location": "Field A"}

        result = compiler._substitute_variables(template, context)
        expected = "Temperature is 25°C at Field A"

        assert result == expected


class TestDSLLoader:
    """Test DSL rule loader."""

    @pytest_asyncio.async_test
    async def test_rule_loading(self):
        """Test loading rules from YAML."""
        loader = DSLLoader()

        # Mock YAML content
        yaml_content = """
        rules:
          - name: "test_rule"
            description: "Test rule"
            conditions:
              - type: "weather"
                predicate: "temperature > 25"
                window: "current"
            actions:
              - type: "send_message"
                channel: "whatsapp"
                template: "test"
        """

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            rules = await loader.load_rules()

            assert len(rules) == 1
            assert rules[0]["name"] == "test_rule"
            assert len(rules[0]["conditions"]) == 1

    def test_rule_validation(self):
        """Test rule validation."""
        loader = DSLLoader()

        # Valid rule
        valid_rule = {
            "name": "test_rule",
            "conditions": [{"type": "weather", "predicate": "temp > 20", "window": "current"}],
            "actions": [{"type": "send_message", "channel": "whatsapp"}]
        }

        assert loader._validate_rule(valid_rule) is True

        # Invalid rule (missing required fields)
        invalid_rule = {
            "name": "test_rule"
            # Missing conditions and actions
        }

        assert loader._validate_rule(invalid_rule) is False


class TestPolicies:
    """Test policy implementations."""

    def test_quiet_hours_policy(self):
        """Test quiet hours policy."""
        policy = QuietHoursPolicy(
            start_time="22:00",
            end_time="06:00",
            timezone="UTC"
        )

        # Test during quiet hours
        quiet_time = datetime(2024, 1, 1, 23, 0)  # 11 PM
        assert policy.is_quiet_time(quiet_time) is True

        # Test during active hours
        active_time = datetime(2024, 1, 1, 12, 0)  # 12 PM
        assert policy.is_quiet_time(active_time) is False

    @pytest_asyncio.async_test
    async def test_rate_limit_policy(self):
        """Test rate limiting policy."""
        # Mock database session
        mock_session = AsyncMock()

        policy = RateLimitPolicy(mock_session)

        user_id = "test_user"
        channel = "whatsapp"
        message_type = "medium"

        # First message should be allowed
        with patch.object(policy, '_get_current_usage', return_value=0):
            with patch.object(policy, '_get_rate_limit', return_value=5):
                allowed = await policy.check_rate_limit(user_id, channel, message_type)
                assert allowed is True

        # Exceeding rate limit should be denied
        with patch.object(policy, '_get_current_usage', return_value=6):
            with patch.object(policy, '_get_rate_limit', return_value=5):
                allowed = await policy.check_rate_limit(user_id, channel, message_type)
                assert allowed is False


class TestChannels:
    """Test communication channels."""

    @pytest_asyncio.async_test
    async def test_whatsapp_channel(self):
        """Test WhatsApp channel."""
        # Mock configuration
        config = {
            "access_token": "test_token",
            "phone_number_id": "test_phone_id",
            "webhook_verify_token": "test_verify_token"
        }

        channel = WhatsAppChannel(config)

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 200
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(
                return_value={"messages": [{"id": "test_msg_id"}]}
            )

            result = await channel.send_message(
                recipient="+1234567890",
                template="test_template",
                variables={"name": "John"}
            )

            assert result["success"] is True
            assert "message_id" in result

    @pytest_asyncio.async_test
    async def test_sms_channel(self):
        """Test SMS channel."""
        # Mock configuration
        config = {
            "account_sid": "test_sid",
            "auth_token": "test_token",
            "from_number": "+1234567890"
        }

        channel = SMSChannel(config)

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 201
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(
                return_value={"sid": "test_sms_id", "status": "queued"}
            )

            result = await channel.send_message(
                recipient="+1234567890",
                message="Test SMS message"
            )

            assert result["success"] is True
            assert "message_id" in result


class TestQueueSystem:
    """Test task queue and worker system."""

    @pytest_asyncio.async_test
    async def test_task_dispatcher(self, async_session):
        """Test task dispatcher."""
        dispatcher = TaskDispatcher(async_session)

        # Create sample task
        task = ScheduledTask(
            task_id="test_task",
            user_id="test_user",
            task_type="send_message",
            task_config={"message": "test"},
            scheduled_for=datetime.utcnow() - timedelta(minutes=1)  # Due now
        )

        async_session.add(task)
        await async_session.commit()

        # Mock policy checks
        with patch.object(dispatcher, '_check_quiet_hours', return_value=False):
            with patch.object(dispatcher, '_check_rate_limits', return_value=True):
                due_tasks = await dispatcher.get_due_tasks(limit=10)

                assert len(due_tasks) > 0
                assert due_tasks[0].task_id == "test_task"

    @pytest_asyncio.async_test
    async def test_task_worker(self):
        """Test task worker execution."""
        # Mock database session
        mock_session = AsyncMock()

        worker = TaskWorker(mock_session)

        task_data = {
            "id": 1,
            "task_type": "send_message",
            "task_config": {
                "channel": "whatsapp",
                "recipient": "+1234567890",
                "message": "Test message"
            },
            "user_id": "test_user"
        }

        # Mock channel execution
        with patch.object(worker, '_get_channel') as mock_get_channel:
            mock_channel = Mock()
            mock_channel.send_message = AsyncMock(
                return_value={"success": True, "message_id": "msg_123"})
            mock_get_channel.return_value = mock_channel

            result = await worker.execute_task(task_data)

            assert result["success"] is True
            assert result["message_id"] == "msg_123"


class TestSecurity:
    """Test security middleware."""

    def test_jwt_token_creation(self):
        """Test JWT token creation and validation."""
        # Mock user data
        user_data = {
            "user_id": "test_user",
            "roles": ["farmer"],
            "permissions": ["read_events", "create_events"]
        }

        # Create token
        token = security_middleware.create_access_token(user_data)
        assert token is not None

        # Validate token
        decoded_data = security_middleware.decode_token(token)
        assert decoded_data["user_id"] == "test_user"
        assert "farmer" in decoded_data["roles"]

    def test_permission_checking(self):
        """Test permission authorization."""
        user_data = {
            "user_id": "test_user",
            "roles": ["farmer"],
            "permissions": ["read_events", "create_events"]
        }

        # Should allow permitted action
        assert security_middleware.check_permission(
            user_data, "read_events") is True

        # Should deny unpermitted action
        assert security_middleware.check_permission(
            user_data, "delete_events") is False


class TestMetrics:
    """Test telemetry and metrics."""

    def test_metrics_collection(self):
        """Test metrics collection."""
        # Test system metrics
        system_metrics = engine_metrics.get_system_metrics()
        assert "cpu_usage" in system_metrics
        assert "memory_usage" in system_metrics

        # Test business metrics recording
        engine_metrics.event_processed("weather_data", "success")
        engine_metrics.task_executed("send_message", "completed")
        engine_metrics.message_sent("whatsapp", "success")

        business_metrics = engine_metrics.get_business_metrics()
        assert business_metrics is not None


class TestIntegration:
    """Integration tests."""

    @pytest_asyncio.async_test
    async def test_end_to_end_workflow(self, async_session, sample_event_data, sample_rule_data):
        """Test complete workflow from event to task execution."""
        # 1. Create event
        event = TemporalEvent(**sample_event_data)
        async_session.add(event)

        # 2. Create rule
        rule = TemporalRule(**sample_rule_data)
        async_session.add(rule)

        await async_session.commit()
        await async_session.refresh(event)
        await async_session.refresh(rule)

        # 3. Evaluate rule against event
        evaluator = PredicateEvaluator()
        compiler = RuleCompiler()

        # Mock high temperature to trigger rule
        context = {
            "user_id": event.user_id,
            "temperature": 35,  # Above threshold
            "event_id": event.id
        }

        # Check if rule conditions are met
        conditions_met = all(
            evaluator.evaluate(condition["predicate"], context)
            for condition in rule.conditions
        )

        assert conditions_met is True

        # 4. Compile rule to tasks
        tasks = await compiler.compile_rule_to_tasks(sample_rule_data, context)
        assert len(tasks) > 0

        # 5. Create scheduled task
        task_data = tasks[0]
        task = ScheduledTask(
            task_id=f"task_{event.id}_{rule.id}",
            user_id=task_data["user_id"],
            rule_id=rule.id,
            task_type=task_data["task_type"],
            task_config=task_data["task_config"],
            scheduled_for=datetime.utcnow(),
            priority=task_data.get("priority", "medium")
        )

        async_session.add(task)
        await async_session.commit()
        await async_session.refresh(task)

        # 6. Verify task was created correctly
        assert task.user_id == event.user_id
        assert task.rule_id == rule.id
        assert task.status == "pending"


# Test fixtures and utilities
def mock_open(read_data=""):
    """Mock open function for file operations."""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
