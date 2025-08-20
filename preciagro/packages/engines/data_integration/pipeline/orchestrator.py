# pipeline/orchestrator.py
from typing import Literal
from ..storage.db import upsert_normalized
from ..bus.publisher import publish_ingest_created
from .normalize_openweather import normalize_openweather


import logging


async def run_openweather_job(
    connector,
    *,
    lat: float,
    lon: float,
    scope: Literal["current", "hourly", "daily"] = "hourly",
    source_id: str = "openweather.onecall"
):
    """
    Fetches weather data from OpenWeather, normalizes, saves to DB, and publishes event.
    Args:
        connector: OpenWeatherConnector instance
        lat, lon: Coordinates
        scope: "current", "hourly", or "daily"
        source_id: Source identifier
    """
    kind = "weather.observation" if scope == "current" else "weather.forecast"
    logger = logging.getLogger("preciagro.data_integration.orchestrator")
    try:
        for raw in connector.fetch(cursor=None, lat=lat, lon=lon, scope=scope, units="metric"):
            item = normalize_openweather(raw, source_id=source_id, kind=kind)
            # de-dupe is enforced by DB unique
            await upsert_normalized(item)
            publish_ingest_created(item)
            logger.info(f"Weather item ingested: {item.item_id} ({kind})")
    except Exception as e:
        logger.error(f"OpenWeather job failed: {e}", exc_info=True)
