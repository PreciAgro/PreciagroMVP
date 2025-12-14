"""Minimal test of dispatcher imports."""

import sys
import os
sys.path.insert(0, os.path.abspath('..'))

print("Testing imports...")

try:
    from typing import Dict, Any, List
    print("✓ typing")
except Exception as e:
    print("✗ typing:", e)

try:
    from datetime import datetime, timezone, timedelta
    print("✓ datetime")
except Exception as e:
    print("✗ datetime:", e)

try:
    from sqlalchemy import select, and_
    print("✓ sqlalchemy")
except Exception as e:
    print("✗ sqlalchemy:", e)

try:
    from preciagro.packages.engines.temporal_logic.contracts import EngineEvent
    print("✓ EngineEvent")
except Exception as e:
    print("✗ EngineEvent:", e)

try:
    from preciagro.packages.engines.temporal_logic.models import ScheduleItem, TaskOutcome, async_session
    print("✓ models")
except Exception as e:
    print("✗ models:", e)

try:
    from preciagro.packages.engines.temporal_logic.dsl.loader import DSLLoader
    print("✓ DSLLoader")
except Exception as e:
    print("✗ DSLLoader:", e)

try:
    from preciagro.packages.engines.temporal_logic.evaluator import RuleEvaluator
    print("✓ RuleEvaluator")
except Exception as e:
    print("✗ RuleEvaluator:", e)

try:
    from preciagro.packages.engines.temporal_logic.compiler import TaskCompiler
    print("✓ TaskCompiler")
except Exception as e:
    print("✗ TaskCompiler:", e)

try:
    from preciagro.packages.engines.temporal_logic.telemetry.metrics import events_processed, tasks_created
    print("✓ metrics")
except Exception as e:
    print("✗ metrics:", e)

try:
    import logging
    logger = logging.getLogger(__name__)
    print("✓ logging")
except Exception as e:
    print("✗ logging:", e)

print("\nDefining EventDispatcher class...")


class EventDispatcher:
    """Main dispatcher for processing events and creating scheduled tasks."""

    def __init__(self):
        print("Initializing EventDispatcher...")
        self.loader = DSLLoader()
        self.evaluator = RuleEvaluator()
        self.compiler = TaskCompiler()
        print("EventDispatcher initialized successfully")


print("Creating dispatcher instance...")
dispatcher = EventDispatcher()
print("✓ Dispatcher created successfully")
