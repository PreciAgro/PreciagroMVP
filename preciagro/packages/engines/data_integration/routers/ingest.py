# routers/ingest.py
from fastapi import APIRouter, Query
from typing import Literal
from ..connectors.openweather import OpenWeatherConnector
from ..pipeline.orchestrator import run_openweather_job

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
    await run_openweather_job(connector, lat=lat, lon=lon, scope=scope)
    return {"status": "ok", "source": "openweather.onecall", "scope": scope, "lat": lat, "lon": lon}
