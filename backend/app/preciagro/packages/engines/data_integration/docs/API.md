# Data Integration Engine API Reference

All endpoints are served through `preciagro.apps.api_gateway.main`. Authentication is not enforced yet; lock these routes down before exposing them externally.

Base URL (local dev): `http://localhost:8101`

## 1. Trigger OpenWeather Ingest
```
POST /ingest/run/openweather
```
Query parameters:
| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| lat | float | yes | Target latitude |
| lon | float | yes | Target longitude |
| scope | `current` \| `hourly` \| `daily` | optional (default `hourly`) | Portion of the OpenWeather One Call payload |

Success (200):
```json
{
  "status": "ok",
  "source": "openweather.onecall",
  "scope": "hourly",
  "lat": -33.45,
  "lon": -70.66
}
```
Common errors:
- 400 invalid or missing coordinates
- 503 `OPENWEATHER_API_KEY` not configured
- 500 connector failure (see logs)

Example:
```
curl -X POST "http://localhost:8101/ingest/run/openweather?lat=-33.45&lon=-70.66&scope=hourly"
```

## 2. Browse Normalized Items
```
GET /ingest/items
```
Query parameters:
| Name | Type | Required | Notes |
| --- | --- | --- | --- |
| kind | string | optional | Filter by normalized kind, for example `weather.forecast` |
| limit | integer | optional (default 50) | Result cap |

Success (200):
```json
{
  "count": 2,
  "items": [
    {
      "item_id": "ow-1600000000",
      "source_id": "openweather.onecall",
      "collected_at": "2025-11-02T18:55:00+00:00",
      "observed_at": "2025-11-02T18:00:00+00:00",
      "kind": "weather.forecast",
      "location": {"lat": -33.45, "lon": -70.66},
      "tags": {"scope": "hourly"},
      "payload": {"temp": 20.5, "humidity": 50}
    }
  ]
}
```
Error (500) -> database unavailable or query failure.

## 3. Health and Diagnostics
- `GET /healthz` – simple JSON heartbeat.
- `GET /metrics` – Prometheus exposition format.
- `GET /test` – simple debug payload useful when bringing up the stack.

## 4. Notes
- Each new connector should register a matching `/ingest/run/{source}` endpoint. Keep payload validation close to the router.
- Wrap routes with the shared security middleware before exposing publicly.
- Paginate `/ingest/items` when downstream clients require deeper history.
