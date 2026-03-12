from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from backend.routes.analyze import router as analyze_router
from backend.routes.farmer import router as farmer_router
from backend.routes.whatsapp import router as whatsapp_router

app = FastAPI(title="PreciAgro API", version="1.0.0")

app.include_router(analyze_router)
app.include_router(farmer_router)
app.include_router(whatsapp_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
