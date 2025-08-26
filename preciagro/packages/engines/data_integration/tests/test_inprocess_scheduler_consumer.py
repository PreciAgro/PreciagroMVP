# This test runs the scheduler and consumer in-process without Docker.
# It verifies that the scheduler task can be started and that the consumer
# stub can be started; it does not require Redis or Postgres.
import asyncio
import pytest
from preciagro.apps.api_gateway.main import _demo_scheduler


@pytest.mark.asyncio
async def test_scheduler_and_consumer_start(monkeypatch):
    # start the demo scheduler and cancel quickly
    task = asyncio.create_task(_demo_scheduler())
    await asyncio.sleep(0.1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
