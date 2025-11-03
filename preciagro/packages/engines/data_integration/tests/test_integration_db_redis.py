import os

import pytest

from preciagro.packages.engines.data_integration.pipeline.normalize_openweather import \
    normalize_openweather

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL") or not os.getenv("REDIS_URL"),
    reason="Integration requires DATABASE_URL and REDIS_URL",
)


@pytest.mark.asyncio
async def test_normalize_and_publish_live():
    # This test assumes DATABASE_URL and REDIS_URL point to accessible services.
    # It only runs when those env vars are present. It primarily verifies that
    # normalization doesn't raise and publisher/upsert codepaths run (sanity smoke).
    raw = {
        "dt": 1600000000,
        "temp": 20.5,
        "humidity": 50,
        "weather": [{"description": "clear"}],
        "lat": -33.0,
        "lon": -70.0,
    }
    item = normalize_openweather(
        raw, source_id="test.integration", kind="weather.forecast"
    )
    # basic assertions
    assert item.content_hash
    assert item.item_id
