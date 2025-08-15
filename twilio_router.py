# twilio_router.py
import os
import httpx
from fastapi import APIRouter, Form
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

router = APIRouter(prefix="/twilio", tags=["twilio"])

# ---- ENV VARS ----
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # sandbox default
WEATHER_ASK_URL = os.getenv("WEATHER_ASK_URL", "http://127.0.0.1:8000/weather/ask")

# Create Twilio client for proactive sends
_twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    _twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    print("⚠️ TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set. Proactive send disabled.")


@router.post("/webhook")
async def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(...)
):
    """
    Twilio calls this whenever a WhatsApp message comes in.
    We pass the message text to /weather/ask and respond with the AI's answer.
    """
    print(f"📩 Incoming WhatsApp from {From}: {Body}")

    # Call your weather QA endpoint
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(WEATHER_ASK_URL, params={"question": Body})
            if res.status_code == 200:
                answer = res.json().get("answer", "Sorry, I couldn’t process your question.")
            else:
                answer = f"Sorry, weather service error: {res.text}"
    except Exception as e:
        print("❌ Error querying /weather/ask:", e)
        answer = "Sorry, the weather brain is temporarily unavailable."

    # Build Twilio XML response
    twiml = MessagingResponse()
    twiml.message(answer)
    return str(twiml)


@router.get("/ping")
async def ping():
    return {"status": "ok", "service": "twilio"}


@router.post("/send")
async def send_whatsapp_message(
    to: str = Form(..., description="Recipient, e.g. whatsapp:+2637XXXXXXX"),
    body: str = Form(..., description="Message to send")
):
    """
    (Optional) Proactive send endpoint. Useful for daily scheduled summaries.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN in env.
    """
    if _twilio_client is None:
        return {"error": "Twilio client not configured. Set TWILIO_ACCOUNT_SID & TWILIO_AUTH_TOKEN."}

    try:
        msg = _twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=to,
            body=body
        )
        return {"sid": msg.sid, "status": "queued"}
    except Exception as e:
        return {"error": str(e)}
