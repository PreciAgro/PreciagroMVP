
from preciagro.packages.engines.temporal_logic.config import config as temporal_config
from preciagro.packages.engines.geo_context.api.routes.api import router as geocontext_router
from preciagro.packages.engines.data_integration.config import settings as di_settings
from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherClient
from fastapi import FastAPI
from preciagro.packages.engines.data_integration.routers import ingest as ingest_router
from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherConnector
from preciagro.packages.engines.data_integration.pipeline.orchestrator import run_registered_source
from preciagro.packages.engines.data_integration.config import settings
from preciagro.packages.engines.data_integration.storage.db import ping_db
import os
from preciagro.packages.engines.data_integration.bus.consumer import run_consumer
import logging
from fastapi import Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import asyncio

from preciagro.packages.shared.logging import configure_logging
from preciagro.packages.shared.error_handlers import add_error_handlers
from preciagro.packages.shared.rate_limiting import create_limiter, add_rate_limiting
from preciagro.packages.shared.cors_config import get_cors_config
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
configure_logging(service_name="api-gateway")
logger = logging.getLogger(__name__)

# SECURITY: Load environment variable for .env file before importing config
# This is the only place where DEV mode affects file loading
os.environ.setdefault('DEV', '1')

# Create FastAPI application with security defaults
app = FastAPI(
    title="PreciAgro MVP API",
    description="PreciAgro MVP Backend API",
    version="1.0.0",
    # SECURITY: Disable docs in production
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc",
    openapi_url=None if os.getenv("ENVIRONMENT") == "production" else "/openapi.json",
)

# SECURITY: Add CORS with restrictive defaults
environment = os.getenv("ENVIRONMENT", "development")
cors_config = get_cors_config(environment)
app.add_middleware(
    CORSMiddleware,
    **cors_config
)
logger.info(f"CORS configured for {environment}: {cors_config['allow_origins']}")

# SECURITY: Add error handlers for sanitized error responses
is_debug = environment == "development"
add_error_handlers(app, debug=is_debug)
if is_debug:
    logger.warning("Debug mode enabled - ensure this is not production")

# SECURITY: Add rate limiting
try:
    limiter = create_limiter()
    add_rate_limiting(app, limiter)
    logger.info("Rate limiting enabled")
except Exception as e:
    logger.warning(f"Failed to enable rate limiting: {e}")

# Use the real OpenWeatherClient implementation if an API key is configured
if di_settings.OPENWEATHER_API_KEY:
    ow_client = OpenWeatherClient(api_key=di_settings.OPENWEATHER_API_KEY)
    connector = OpenWeatherConnector(ow_client)
    ingest_router.openweather_client_singleton = connector
else:
    connector = None
    # ingest_router.openweather_client_singleton left unset; endpoints will still error if invoked

app.include_router(ingest_router.router)

# Try to include temporal router, but handle import failures gracefully
try:
    from preciagro.packages.engines.temporal_logic.routes.api import router as temporal_router
    app.include_router(temporal_router)
    logger.info("Temporal Logic Engine router loaded successfully")
except Exception as e:
    logger.warning(f"Failed to load Temporal Logic Engine router: {e}")

app.include_router(geocontext_router)

# Metrics
INGEST_COUNTER = Counter('preciagro_ingest_jobs_total',
                         'Total ingest jobs executed', ['source', 'scope'])


@app.get('/healthz')
async def healthz(response: Response):
    """Health check that verifies DB connectivity when available.

    Returns 200 when reachable or when the environment doesn't provide
    DB (best-effort). Returns 503 when a reachable service is down.
    """
    db_ok = await ping_db()
    
    if not db_ok:
        response.status_code = 503
        return {"status": "error", "details": {"database": "unreachable"}}
        
    return {"status": "ok", "details": {"database": "connected"}}


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
    """Initialize application services on startup."""
    # Initialize temporal logic database tables (optional if DATABASE_URL not set)
    try:
        from preciagro.packages.engines.temporal_logic.models import init_tables
        await init_tables()
        logger.info("Temporal Logic Engine database initialized")
    except Exception as e:
        logger.warning(
            f"Failed to initialize Temporal Logic Engine database: {e}")

    # Start demo scheduler in background - DISABLED FOR TESTING
    # asyncio.create_task(_demo_scheduler())
    # start a consumer stub so we surface events during a demo
    asyncio.create_task(run_consumer())
    
    logger.info(f"PreciAgro API Gateway started in {environment} mode")

