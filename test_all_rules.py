"""Test all 3 temporal logic rules."""
import logging
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from preciagro.packages.engines.temporal_logic.models import ScheduleItem, Base
from preciagro.packages.engines.temporal_logic.contracts import EngineEvent
from preciagro.packages.engines.temporal_logic.dispatcher_minimal import TemporalLogicEngine
import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_all_rules():
    """Test all 3 farming business rules."""

    print("🚜 Testing ALL Temporal Logic Rules")

    # Create database and engine
    db_url = "sqlite+aiosqlite:///:memory:"
    async_engine = create_async_engine(db_url, echo=False)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Database setup complete")

    # Create engine instance
    engine_instance = TemporalLogicEngine()
    async_session = sessionmaker(async_engine, class_=AsyncSession)

    # Test 1: Weather Spraying Rule
    print("\n🌡️ Testing Weather Spraying Rule")
    weather_event = EngineEvent(
        topic="weather.forecast",
        id="weather_test_001",
        ts_utc=datetime.fromisoformat("2025-09-03T10:00:00+00:00"),
        farm_id="farm_weather",
        farmer_tz="America/New_York",
        payload={"temperature": 35, "humidity": 45}  # High temp, low humidity
    )

    async with async_session() as session:
        matching_rules = engine_instance._find_matching_rules(weather_event)
        print(
            f"   Found {len(matching_rules)} matching rules: {[r.id for r in matching_rules]}")

        if matching_rules:
            task_id = await engine_instance._create_scheduled_task(matching_rules[0], weather_event, session)
            print(f"   ✅ Created weather task: {task_id}")

    # Test 2: Soil Irrigation Rule
    print("\n💧 Testing Soil Irrigation Rule")
    soil_event = EngineEvent(
        topic="soil.moisture_update",
        id="soil_test_001",
        ts_utc=datetime.fromisoformat("2025-09-03T10:00:00+00:00"),
        farm_id="farm_irrigation",
        farmer_tz="America/New_York",
        payload={"moisture_level": 25, "field_zone": "A1"}  # Low moisture
    )

    async with async_session() as session:
        matching_rules = engine_instance._find_matching_rules(soil_event)
        print(
            f"   Found {len(matching_rules)} matching rules: {[r.id for r in matching_rules]}")

        if matching_rules:
            task_id = await engine_instance._create_scheduled_task(matching_rules[0], soil_event, session)
            print(f"   ✅ Created irrigation task: {task_id}")

    # Test 3: Disease Prevention Rule
    print("\n🦠 Testing Disease Prevention Rule")
    disease_event = EngineEvent(
        topic="diagnosis.outcome",
        id="disease_test_001",
        ts_utc=datetime.fromisoformat("2025-09-03T10:00:00+00:00"),
        farm_id="farm_disease",
        farmer_tz="America/New_York",
        payload={"risk_level": "high", "disease_type": "blight",
                 "confidence": 0.85}  # High risk
    )

    async with async_session() as session:
        matching_rules = engine_instance._find_matching_rules(disease_event)
        print(
            f"   Found {len(matching_rules)} matching rules: {[r.id for r in matching_rules]}")

        if matching_rules:
            task_id = await engine_instance._create_scheduled_task(matching_rules[0], disease_event, session)
            print(f"   ✅ Created disease prevention task: {task_id}")

    # Show final database state
    print("\n📊 Final Database State:")
    async with async_session() as session:
        result = await session.execute(text("SELECT rule_id, user_id, schedule_time FROM schedule_item ORDER BY created_at"))
        tasks = result.fetchall()
        print(f"   Total tasks created: {len(tasks)}")
        for task in tasks:
            rule_id, user_id, schedule_time = task
            print(f"   - {rule_id} for {user_id} at {schedule_time}")

    await async_engine.dispose()
    print("\n🎉 All tests complete!")

if __name__ == "__main__":
    asyncio.run(test_all_rules())
