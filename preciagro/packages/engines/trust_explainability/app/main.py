"""Trust & Explainability Engine FastAPI Application.

Main entry point for the TEE microservice.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..api.routes import router
from ..config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    settings = get_settings()
    logger.info(
        f"Starting Trust & Explainability Engine on port {settings.api_port}"
    )
    logger.info(f"API prefix: {settings.api_prefix}")
    logger.info(f"SHAP enabled: {settings.enable_shap}")
    logger.info(f"GradCAM enabled: {settings.enable_gradcam}")
    logger.info(f"Safety gate strict: {settings.safety_gate_strict}")
    
    yield
    
    logger.info("Shutting down Trust & Explainability Engine")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Trust & Explainability Engine",
        description=(
            "Model-agnostic explainability, confidence quantification, "
            "safety validation, and audit trail generation for PreciAgro."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "engine": "trust_explainability",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "preciagro.packages.engines.trust_explainability.app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True
    )
