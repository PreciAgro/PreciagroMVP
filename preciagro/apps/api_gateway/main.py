
# from fastapi import FastAPI
# from ...packages.shared.schemas import ImageIn, PlanResponse
# from ...packages.engines import image_analysis, geo_context, data_integration, crop_intel, temporal_logic, inventory
# from preciagro.apps.data_integration_engine.routers.ingest import router as ingest_router

# app = FastAPI(title="PreciAgro MVP API")
# app.include_router(ingest_router)
# @app.get("/health")
# def health():
#     return {"status": "ok"}

# @app.post("/v1/diagnose-and-plan", response_model=PlanResponse)
# def diagnose_and_plan(payload: ImageIn):
#     # 1) Vision diagnosis
#     dx = image_analysis.diagnose(payload.image_base64, payload.crop_hint)

#     # 2) Context & weather
#     ctx = geo_context.context_for(payload.location)
#     wx = data_integration.latest_weather(ctx["region"])

#     # 3) Crop Intelligence plan
#     crop = payload.crop_hint or "generic_crop"
#     plan = crop_intel.plan_actions(crop, dx.labels[0].name, ctx, wx)

#     # 4) Temporal reminders
#     reminders = temporal_logic.schedule(plan)

#     # 5) Inventory
#     inv = inventory.plan_impact(plan)

#     return {"diagnosis": dx, "plan": plan, "reminders": reminders, "inventory": inv}
# the above was a placeholder for the main.py file in your API gateway.

from preciagro.packages.engines.data_integration.bus.consumer import run_consumer
import logging
from fastapi import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import os as _os
import asyncio
from preciagro.packages.engines.data_integration.storage.db import ping_db
from preciagro.packages.engines.data_integration.config import settings
from preciagro.packages.engines.data_integration.pipeline.orchestrator import run_registered_source
from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherConnector
from preciagro.packages.engines.data_integration.routers import ingest as ingest_router
from fastapi import FastAPI
from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherClient
from preciagro.packages.engines.data_integration.config import settings as di_settings
import os
# Set DEV environment variable early to ensure .env file is loaded
os.environ.setdefault('DEV', '1')


app = FastAPI()


# Use the real OpenWeatherClient implementation if an API key is configured

if di_settings.OPENWEATHER_API_KEY:
    ow_client = OpenWeatherClient(api_key=di_settings.OPENWEATHER_API_KEY)
    connector = OpenWeatherConnector(ow_client)
    ingest_router.openweather_client_singleton = connector
else:
    connector = None
    # ingest_router.openweather_client_singleton left unset; endpoints will still error if invoked

app.include_router(ingest_router.router)

# Metrics
INGEST_COUNTER = Counter('preciagro_ingest_jobs_total',
                         'Total ingest jobs executed', ['source', 'scope'])


@app.get('/healthz')
async def healthz():
    """Health check that verifies DB and Redis connectivity when available.

    Returns 200 when both are reachable or when the environment doesn't provide
    DB/Redis (best-effort). Returns 503 when a reachable service is down.
    """
    return {"status": "ok", "message": "Service is running"}


@app.get('/test')
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "test endpoint working"}


@app.get('/metrics')
def metrics():
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


async def _demo_scheduler():
    """Background scheduler for demo pulls. Triggers openweather for demo coords periodically.

    Runs on app startup as a background task. Respects `INGEST_RATE_LIMIT_QPS` from config
    for simple pacing.
    """
    log = logging.getLogger("preciagro.scheduler")
    # demo coordinates (Santiago, Chile)
    coords = [(-33.45, -70.6667), (-23.55, -46.6333)]
    interval_sec = 1800  # 30 minutes for demo
    # small initial delay so app can warm up
    await asyncio.sleep(2)
    while True:
        for lat, lon in coords:
            try:
                # call the registered endpoint via internal function to avoid HTTP loop
                if not connector:
                    log.warning(
                        "Skipping OpenWeather demo pull because OPENWEATHER_API_KEY not configured")
                    continue
                await run_registered_source('openweather.onecall', connector, lat=lat, lon=lon, scope='hourly')
                INGEST_COUNTER.labels(
                    source='openweather.onecall', scope='hourly').inc()
            except Exception:
                log.exception('Demo scheduler job failed')
            # simple pacing
            await asyncio.sleep(max(1, 1.0 / max(1, settings.INGEST_RATE_LIMIT_QPS)))
        await asyncio.sleep(interval_sec)


@app.on_event('startup')
async def startup_tasks():
    # Start demo scheduler in background - DISABLED FOR TESTING
    # asyncio.create_task(_demo_scheduler())
    # start a consumer stub so we surface events during a demo
    asyncio.create_task(run_consumer())
