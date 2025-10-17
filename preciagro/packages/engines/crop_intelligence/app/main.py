from fastapi import FastAPI
from .api.router import router as cie_router

app = FastAPI(
    title="PreciAgro Crop Intelligence Engine (MVP)",
    description="Explainable agronomic engine delivering accurate, trustable, region-relevant recommendations",
    version="0.1.0"
)

app.include_router(cie_router)

@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "service": "Crop Intelligence Engine",
        "status": "operational",
        "version": "0.1.0"
    }
