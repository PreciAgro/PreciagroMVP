"""Main FastAPI application for Security & Access Engine."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router import router
from .core.config import settings
from .db.base import init_db
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PreciAgro Security & Access Engine",
    description="Enterprise-grade security, authentication, authorization, and encryption engine",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        await init_db()
        logger.info("Security & Access Engine database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "engine": "security_access",
        "version": "1.0.0",
        "status": "operational",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8105)
