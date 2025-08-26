
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


from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherClient
from fastapi import FastAPI
import os
from preciagro.packages.engines.data_integration.routers import ingest as ingest_router
from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherConnector
from preciagro.packages.engines.data_integration import pipeline
from preciagro.packages.engines.data_integration.config import settings
from preciagro.packages.engines.data_integration.storage.db import ping_db
import asyncio
import os as _os
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import asyncio
import logging
from preciagro.packages.engines.data_integration.bus.consumer import run_consumer


app = FastAPI()


# Use the real OpenWeatherClient implementation

ow_client = OpenWeatherClient(api_key=os.getenv("OPENWEATHER_API_KEY"))
connector = OpenWeatherConnector(ow_client)
ingest_router.openweather_client_singleton = connector

app.include_router(ingest_router.router)

# Metrics
INGEST_COUNTER = Counter('preciagro_ingest_jobs_total',
                         'Total ingest jobs executed', ['source', 'scope'])


@app.get('/healthz')
def healthz():
    """Health check that verifies DB and Redis connectivity when available.

    Returns 200 when both are reachable or when the environment doesn't provide
    DB/Redis (best-effort). Returns 503 when a reachable service is down.
    """
    status = {"ok": True, "details": {}}

    # DB check (async call run in event loop)
    try:
        loop = asyncio.new_event_loop()
        try:
            ok = loop.run_until_complete(ping_db())
        finally:
            loop.close()
        status["details"]["db"] = ok
        if not ok:
            status["ok"] = False
    except Exception as e:
        status["details"]["db"] = False
        status["ok"] = False

    # Redis check (best-effort)
    redis_ok = True
    try:
        try:
            import redis.asyncio as _redis_ai
            r = _redis_ai.from_url(_os.getenv(
                "REDIS_URL", "redis://localhost:6379/0"))
            loop = asyncio.new_event_loop()
            try:
                pong = loop.run_until_complete(r.ping())
            finally:
                loop.close()
            redis_ok = bool(pong)
        except Exception:
            try:
                import redis as _redis_sync
                r = _redis_sync.from_url(_os.getenv(
                    "REDIS_URL", "redis://localhost:6379/0"))
                redis_ok = bool(r.ping())
            except Exception:
                redis_ok = False
    except Exception:
        redis_ok = False

    status["details"]["redis"] = redis_ok
    if not redis_ok:
        status["ok"] = False

    if status["ok"]:
        return {"status": "ok", "details": status["details"]}
    else:
        from fastapi import Response
        return Response(status_code=503, content=str(status))


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
                await pipeline.run_registered_source('openweather.onecall', connector, lat=lat, lon=lon, scope='hourly')
                INGEST_COUNTER.labels(
                    source='openweather.onecall', scope='hourly').inc()
            except Exception:
                log.exception('Demo scheduler job failed')
            # simple pacing
            await asyncio.sleep(max(1, 1.0 / max(1, settings.INGEST_RATE_LIMIT_QPS)))
        await asyncio.sleep(interval_sec)


@app.on_event('startup')
async def startup_tasks():
    # Start demo scheduler in background
    asyncio.create_task(_demo_scheduler())
    # start a consumer stub so we surface events during a demo
    asyncio.create_task(run_consumer())
