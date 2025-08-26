# routers/ingest.py
from fastapi import APIRouter, Query
from typing import Literal
from ..connectors.openweather import OpenWeatherConnector
from ..pipeline.orchestrator import run_registered_source
from ..storage.db import get_items


router = APIRouter(prefix="/ingest", tags=["ingest"])

# Provide your OpenWeatherClient when wiring the router.
openweather_client_singleton = None  # set from app startup


@router.post("/run/openweather")
async def run_openweather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    scope: Literal["current", "hourly", "daily"] = "hourly"
):
    connector = OpenWeatherConnector(openweather_client_singleton)
    # run_registered_source will lookup the normalizer from the registry
    # and run the generic job runner.
    await run_registered_source("openweather.onecall", connector, lat=lat, lon=lon, scope=scope)
    return {"status": "ok", "source": "openweather.onecall", "scope": scope, "lat": lat, "lon": lon}


@router.get("/items")
async def list_items(kind: str | None = Query(None), limit: int = Query(50)):
    rows = await get_items(kind=kind, limit=limit)
    return {"count": len(rows), "items": rows}
