from fastapi import FastAPI
from weather_router import router as weather_router


app = FastAPI(title="PreciAgro Weather Assistant", version="1.0.0")
from twilio_router import router as twilio_router
app.include_router(weather_router, prefix="/weather")
app.include_router(twilio_router, prefix="")  # exposes /twilio/webhook, /twilio/send, etc.

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
