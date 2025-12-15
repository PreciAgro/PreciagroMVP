"""FastAPI Application for AgroLLM Engine."""

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Dict, Any

from .pipeline import AgroLLMPipeline
from .contracts.v1.schemas import FarmerRequest, AgroLLMResponse
from .config import ConfigLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global pipeline instance
pipeline: AgroLLMPipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global pipeline
    
    # Startup
    logger.info("Starting AgroLLM Engine...")
    config_loader = ConfigLoader()
    config = config_loader.load()
    pipeline = AgroLLMPipeline(config=config)
    logger.info("AgroLLM Engine started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AgroLLM Engine...")


# Create FastAPI app
app = FastAPI(
    title="AgroLLM Engine",
    description="Agricultural Language Model Engine for PreciAgro",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "engine": "agro_llm",
        "version": "1.0.0"
    }


@app.post("/generate", response_model=AgroLLMResponse)
async def generate_response(request: Dict[str, Any]) -> AgroLLMResponse:
    """Generate response from farmer request.
    
    Args:
        request: Farmer request dictionary
        
    Returns:
        AgroLLMResponse
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    try:
        response = await pipeline.process_request(request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/v1/generate", response_model=AgroLLMResponse)
async def generate_response_v1(request: FarmerRequest) -> AgroLLMResponse:
    """Generate response from farmer request (v1 with Pydantic validation).
    
    Args:
        request: Farmer request
        
    Returns:
        AgroLLMResponse
    """
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    try:
        response = await pipeline.process_request(request.model_dump())
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get engine status."""
    return {
        "engine": "agro_llm",
        "status": "active" if pipeline is not None else "inactive",
        "version": "1.0.0",
        "config": {
            "model_mode": pipeline.config.model_provider.mode if pipeline else None,
            "features": {
                "rag": pipeline.config.feature_flags.enable_rag if pipeline else False,
                "kg": pipeline.config.feature_flags.enable_kg if pipeline else False,
                "local": pipeline.config.feature_flags.use_local if pipeline else False
            }
        } if pipeline else {}
    }








