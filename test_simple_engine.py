"""Simple engine test to avoid Redis dependencies."""
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine, text
from preciagro.packages.engines.temporal_logic.models import ScheduleItem, Base
from preciagro.packages.engines.temporal_logic.contracts import EngineEvent
from preciagro.packages.engines.temporal_logic.dispatcher_minimal import TemporalLogicEngine
import asyncio
import sys
import os
import logging
sys.path.insert(0, os.path.abspath('.'))


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_simple_engine():
    """Test the engine with its own database setup."""

    print("🔧 Testing simple engine setup...")

    # Create an in-memory database and tables
    db_url = "sqlite+aiosqlite:///:memory:"
    async_engine = create_async_engine(db_url, echo=False)

    # Create tables manually
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Database tables created")

    # Create engine instance
    engine_instance = TemporalLogicEngine()

    # Create a test event
    event = EngineEvent(
        topic="weather.forecast",
        id="simple_test_001",
        ts_utc=datetime.fromisoformat(
            "2025-09-03T10:00:00.000Z".replace("Z", "+00:00")),
        farm_id="farm_simple",
        farmer_tz="America/New_York",
        payload={"temperature": 35, "humidity": 45}
    )

    print(f"🎯 Testing with event: {event.topic}")
    print(f"📊 Event payload: {event.payload}")

    # Test rule matching
    matching_rules = engine_instance._find_matching_rules(event)
    print(
        f"🔍 Found {len(matching_rules)} matching rules: {[r.id for r in matching_rules]}")

    if not matching_rules:
        print("❌ No rules matched - cannot proceed")
        return

    # Create session and test task creation
    async_session = sessionmaker(async_engine, class_=AsyncSession)

    async with async_session() as session:
        # Test individual task creation method
        rule = matching_rules[0]
        print(f"🔨 Testing task creation for rule: {rule.id}")

        # Mock the database session in the engine for testing
        task_id = await engine_instance._create_scheduled_task(rule, event, session)
        print(f"📝 Task creation result: {task_id}")

        if task_id:
            print("✅ Task created successfully!")
            # Query the database to verify
            result = await session.execute(text("SELECT * FROM schedule_item"))
            items = result.fetchall()
            print(f"💾 Items in database: {len(items)}")
            for item in items:
                print(f"   - ID: {item[0]}, Rule: {item[2]}, Time: {item[3]}")
        else:
            print("❌ Task creation failed")

    await async_engine.dispose()
    print("🏁 Test complete")

if __name__ == "__main__":
    asyncio.run(test_simple_engine())
