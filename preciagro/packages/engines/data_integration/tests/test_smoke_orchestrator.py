# tests/test_smoke_orchestrator.py
import asyncio
from types import SimpleNamespace

from preciagro.packages.engines.data_integration.pipeline.orchestrator import run_job
from preciagro.packages.engines.data_integration.pipeline.normalize_openweather import normalize_openweather


class MockConnector:
    def __init__(self, items):
        self._items = items

    def fetch(self, *, cursor=None, lat=None, lon=None, scope=None, units=None):
        for it in self._items:
            yield it


def test_run_job_smoke(monkeypatch):
    # sample raw item similar to openweather hourly/current
    raw = {"dt": 1600000000, "temp": 20.5, "humidity": 50, "weather": [
        {"description": "clear"}], "lat": -33.0, "lon": -70.0}
    connector = MockConnector([raw])

    # capture calls to upsert and publish
    called = {"upsert": 0, "publish": 0}

    async def fake_upsert(item):
        called["upsert"] += 1

    def fake_publish(item):
        called["publish"] += 1

    # patch the references used by the orchestrator module directly
    monkeypatch.setattr(
        "preciagro.packages.engines.data_integration.pipeline.orchestrator.upsert_normalized", fake_upsert)
    monkeypatch.setattr(
        "preciagro.packages.engines.data_integration.pipeline.orchestrator.publish_ingest_created", fake_publish)

    # run the async job runner in the event loop
    asyncio.run(run_job(connector, normalize_openweather, lat=-33.0, lon=-
                70.0, scope="hourly", source_id="test.openweather", cache_ttl=1))

    assert called["upsert"] == 1
    assert called["publish"] == 1
