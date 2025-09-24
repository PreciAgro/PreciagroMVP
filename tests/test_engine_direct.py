"""Direct engine test to debug task creation issue."""
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from preciagro.packages.engines.temporal_logic.models import ScheduleItem, Base
from preciagro.packages.engines.temporal_logic.contracts import EngineEvent
from preciagro.packages.engines.temporal_logic.dispatcher_minimal import engine
import asyncio
import sys
import os
# Go up one level to find preciagro module
sys.path.insert(0, os.path.abspath('..'))


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_engine_directly():
    """Test the engine directly without HTTP layer."""

    print("🔧 Initializing database...")

    # Create database and tables
    db_url = "sqlite+aiosqlite:///:memory:"
    async_engine = create_async_engine(db_url, echo=False)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Database tables created")

    # Create a test event
    event = EngineEvent(
        topic="weather.forecast",
        id="direct_test_001",
        ts_utc=datetime.fromisoformat(
            "2025-09-03T10:00:00.000Z".replace("Z", "+00:00")),
        farm_id="farm_direct",
        farmer_tz="America/New_York",
        payload={"temperature": 35, "humidity": 45}
    )

    print(f"🔧 Testing engine directly with event: {event.topic}")
    print(f"📊 Event payload: {event.payload}")

    # Test rule matching
    matching_rules = engine._find_matching_rules(event)
    print(
        f"🎯 Found {len(matching_rules)} matching rules: {[r.id for r in matching_rules]}")

    if not matching_rules:
        print("❌ No rules matched - check rule definitions")
        return

    # Test full processing
    task_ids = await engine.process_event(event)
    print(f"✅ Tasks created: {len(task_ids)}")
    print(f"📝 Task IDs: {task_ids}")

    # Check what's in the database
    async_session = sessionmaker(async_engine, class_=AsyncSession)
    async with async_session() as session:
        result = await session.execute(select(ScheduleItem))
        items = result.scalars().all()
        print(f"💾 Items in database: {len(items)}")
        for item in items:
            print(
                f"   - Task: {item.id}, Rule: {item.rule_id}, Time: {item.schedule_time}")

    await async_engine.dispose()
    print("🏁 Test complete")

if __name__ == "__main__":
    asyncio.run(test_engine_directly())
