from fastapi import FastAPI
from .api.rest import router as rest_router
from .api.websocket import router as ws_router

app = FastAPI(title="PreciAgro Conversational Engine")

app.include_router(rest_router)
app.include_router(ws_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
