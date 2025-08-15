import os
import httpx
from fastapi import APIRouter, Request

router = APIRouter()

# --- Load Environment Variables ---
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "preciagro_verify")

if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
    print("⚠️ WARNING: WhatsApp credentials not set in .env")

# --- Verify Webhook (Meta will use this when setting up) ---
@router.get("/webhook/whatsapp")
async def verify(request: Request):
    """
    Meta calls this GET endpoint when verifying the webhook URL.
    """
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return "Verification failed", 403

# --- Handle Incoming Messages ---
@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Called by Meta whenever a user sends a message to your WhatsApp number.
    """
    data = await request.json()
    try:
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            message = messages[0]
            from_number = message["from"]        # User's phone number
            text = message.get("text", {}).get("body", "")

            print(f"📩 Message from {from_number}: {text}")

            # Call your weather /ask endpoint
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "http://127.0.0.1:8000/weather/ask",
                    params={"question": text}
                )
                answer = res.json().get("answer", "Sorry, I couldn't understand your question.")

            # Send the answer back
            await send_whatsapp_message(from_number, answer)
    except Exception as e:
        print("❌ Error processing message:", e)
    return {"status": "ok"}

# --- Send a WhatsApp Message Back ---
async def send_whatsapp_message(to: str, message: str):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": message}
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code != 200:
            print(f"❌ Failed to send message: {r.text}")
