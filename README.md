# PreciAgro MVP Skeleton (Vertical Slice)
This is a tiny, runnable skeleton to help you understand the end-to-end flow.

## What it does
Single endpoint: **POST /v1/diagnose-and-plan**
It simulates the engine flow:
Image -> Diagnose -> GeoContext -> Weather -> Plan -> Reminders -> Inventory

## How to run (local)

```sh
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn preciagro.apps.api_gateway.main:app --reload --port 8000
```

## Try it
POST http://localhost:8000/v1/diagnose-and-plan

Example JSON body:

```json
{
  "image_base64": "BASE64_STRING_HERE",
  "crop_hint": "tomato",
  "location": {"lat": 52.23, "lng": 21.01}
}
```

You should get back: diagnosis, a 7-day style plan, reminders, and inventory impact.

## Next steps (replacing stubs with real logic)
- image_analysis: load a real ONNX model for plant disease.
- data_integration: fetch real weather (Open-Meteo) and normalize.
- geo_context: real reverse-geocode & agro-zones.
- crop_intel: rules + thresholds per disease & crop.
- temporal_logic: store schedules in DB and emit notifications.
- inventory: connect to a real inventory table.
```