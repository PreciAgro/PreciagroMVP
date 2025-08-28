"""Main FastAPI application for Temporal Logic Engine."""
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from prometheus_client import make_asgi_app
import redis.asyncio as redis

from .config import config
from .storage.db import init_database, close_database, get_database_session
from .api.routes import events, schedules, outcomes, intents
from .due_queue.worker import create_worker_pool
from .telemetry.metrics import engine_metrics
from .security.auth import security_middleware
from .dsl_loader import DSLLoader

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("Starting Temporal Logic Engine...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize Redis connection
        redis_client = redis.from_url(config.redis_url, decode_responses=True)
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis connection established")
        
        # Load temporal rules
        dsl_loader = DSLLoader()
        rules = await dsl_loader.load_rules()
        app.state.temporal_rules = rules
        logger.info(f"Loaded {len(rules)} temporal rules")
        
        # Start background worker pool
        if config.enable_worker:
            worker_pool = await create_worker_pool()
            app.state.worker_pool = worker_pool
            logger.info("Worker pool started successfully")
        
        # Initialize security middleware
        await security_middleware.initialize()
        logger.info("Security middleware initialized")
        
        # Record startup metrics
        engine_metrics.system_startup()
        
        logger.info("Temporal Logic Engine started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Temporal Logic Engine...")
        
        try:
            # Close Redis connection
            if hasattr(app.state, 'redis'):
                await app.state.redis.close()
                logger.info("Redis connection closed")
            
            # Stop worker pool
            if hasattr(app.state, 'worker_pool'):
                await app.state.worker_pool.close()
                logger.info("Worker pool stopped")
            
            # Close database connections
            await close_database()
            logger.info("Database connections closed")
            
            logger.info("Temporal Logic Engine shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Temporal Logic Engine",
    description="Advanced temporal event processing and rule engine for agricultural automation",
    version="1.0.0",
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=config.allowed_hosts
)


# Health check endpoints
@app.get("/health", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    try:
        # Check database connection
        async with get_database_session() as db:
            await db.execute("SELECT 1")
        
        # Check Redis connection
        if hasattr(app.state, 'redis'):
            await app.state.redis.ping()
        
        return {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": engine_metrics.get_current_timestamp(),
            "environment": config.environment
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/health/detailed", tags=["health"])
async def detailed_health_check():
    """Detailed health check with component status."""
    try:
        components = {}
        
        # Database health
        try:
            async with get_database_session() as db:
                await db.execute("SELECT 1")
            components["database"] = {"status": "healthy", "latency_ms": None}
        except Exception as e:
            components["database"] = {"status": "unhealthy", "error": str(e)}
        
        # Redis health
        try:
            if hasattr(app.state, 'redis'):
                start_time = engine_metrics.get_current_timestamp()
                await app.state.redis.ping()
                latency = engine_metrics.get_current_timestamp() - start_time
                components["redis"] = {"status": "healthy", "latency_ms": latency * 1000}
            else:
                components["redis"] = {"status": "not_configured"}
        except Exception as e:
            components["redis"] = {"status": "unhealthy", "error": str(e)}
        
        # Worker pool health
        try:
            if hasattr(app.state, 'worker_pool'):
                components["worker_pool"] = {"status": "healthy", "active": True}
            else:
                components["worker_pool"] = {"status": "not_configured"}
        except Exception as e:
            components["worker_pool"] = {"status": "unhealthy", "error": str(e)}
        
        # Rule engine health
        try:
            rules_count = len(getattr(app.state, 'temporal_rules', []))
            components["rule_engine"] = {
                "status": "healthy",
                "loaded_rules": rules_count
            }
        except Exception as e:
            components["rule_engine"] = {"status": "unhealthy", "error": str(e)}
        
        # Overall status
        all_healthy = all(
            comp["status"] == "healthy" or comp["status"] == "not_configured"
            for comp in components.values()
        )
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "version": "1.0.0",
            "timestamp": engine_metrics.get_current_timestamp(),
            "environment": config.environment,
            "components": components
        }
    
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/metrics", tags=["monitoring"])
async def get_metrics():
    """Get application metrics."""
    try:
        return {
            "system_metrics": engine_metrics.get_system_metrics(),
            "business_metrics": engine_metrics.get_business_metrics(),
            "performance_metrics": engine_metrics.get_performance_metrics()
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/prometheus", metrics_app)


# Include API routers
app.include_router(events.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(outcomes.router, prefix="/api/v1")
app.include_router(intents.router, prefix="/api/v1")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": engine_metrics.get_current_timestamp(),
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error" if not config.debug else str(exc),
                "timestamp": engine_metrics.get_current_timestamp(),
                "path": str(request.url.path)
            }
        }
    )


# Middleware for request logging and metrics
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log requests and collect metrics."""
    start_time = engine_metrics.get_current_timestamp()
    
    # Record request
    engine_metrics.request_started(
        method=request.method,
        endpoint=request.url.path
    )
    
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = engine_metrics.get_current_timestamp() - start_time
        
        # Record metrics
        engine_metrics.request_completed(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration
        )
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path} - "
            f"{response.status_code} - {duration:.3f}s"
        )
        
        return response
    
    except Exception as e:
        duration = engine_metrics.get_current_timestamp() - start_time
        
        # Record error metrics
        engine_metrics.request_failed(
            method=request.method,
            endpoint=request.url.path,
            error_type=type(e).__name__,
            duration=duration
        )
        
        logger.error(
            f"{request.method} {request.url.path} - "
            f"ERROR: {e} - {duration:.3f}s"
        )
        
        raise


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Temporal Logic Engine",
        "version": "1.0.0",
        "description": "Advanced temporal event processing and rule engine for agricultural automation",
        "environment": config.environment,
        "docs_url": "/docs" if config.debug else None,
        "status": "operational",
        "timestamp": engine_metrics.get_current_timestamp()
    }


# API information endpoint
@app.get("/api/v1", tags=["api"])
async def api_info():
    """API version information."""
    return {
        "version": "v1",
        "endpoints": {
            "events": "/api/v1/events",
            "schedules": "/api/v1/schedules", 
            "outcomes": "/api/v1/outcomes",
            "intents": "/api/v1/intents"
        },
        "documentation": "/docs" if config.debug else None,
        "health": "/health",
        "metrics": "/metrics"
    }


# Development utilities
if config.debug:
    
    @app.get("/debug/config", tags=["debug"])
    async def debug_config():
        """Get current configuration (debug only)."""
        return {
            "environment": config.environment,
            "database_url": config.database_url.replace(
                config.database_url.split("://")[1].split("@")[0], "***"
            ),
            "redis_url": config.redis_url.replace(
                config.redis_url.split("://")[1].split("@")[0], "***"
            ),
            "log_level": config.log_level,
            "enable_worker": config.enable_worker,
            "debug": config.debug
        }
    
    @app.get("/debug/rules", tags=["debug"])
    async def debug_rules():
        """Get loaded temporal rules (debug only)."""
        rules = getattr(app.state, 'temporal_rules', [])
        return {
            "rules_count": len(rules),
            "rules": [
                {
                    "name": rule.get("name"),
                    "description": rule.get("description"),
                    "conditions_count": len(rule.get("conditions", [])),
                    "actions_count": len(rule.get("actions", []))
                }
                for rule in rules
            ]
        }


def create_app() -> FastAPI:
    """Factory function to create FastAPI app."""
    return app


if __name__ == "__main__":
    # Run with uvicorn for development
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=config.debug,
        log_level=config.log_level.lower(),
        access_log=True
    )
