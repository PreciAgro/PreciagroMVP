# GeoContext Engine API Reference

Base URL: `http://localhost:8102`
Authentication: JWT bearer tokens. With `DEV_MODE=true` an unsigned dev token is accepted.

## 1. Resolve Field Context
```
POST /v1/resolve
```
Example body:
```json
{
  "field": {
    "type": "Polygon",
    "coordinates": [[[21.0, 52.0], [21.1, 52.0], [21.1, 52.1], [21.0, 52.1], [21.0, 52.0]]]
  },
  "crops": ["corn"],
  "date": "2024-06-15T12:00:00Z",
  "forecast_days": 7,
  "use_cache": true,
  "include_spatial": true,
  "include_soil": true,
  "include_climate": true,
  "include_calendar": true,
  "include_rules": true
}
```
Success (200) returns an FCO payload containing `location`, `soil`, `climate`, `calendar_events`, and `spray_recommendations`. Errors:
- 401 missing/invalid JWT
- 403 insufficient scope
- 422 invalid polygon or payload
- 500 resolver failure (see logs)

## 2. Retrieve Cached FCO
```
GET /geo-context/fco/{context_hash}
GET /v1/resolve/{context_hash}
```
Returns the cached payload for a previous resolve call. Responds with 404 when the hash is unknown or expired.

## 3. Health and Metrics
- `GET /health`
- `GET /metrics` (Prometheus)

## 4. Authentication Notes
- `DEV_MODE=true` bypasses signature checks and accepts any token.
- In production set `JWT_PUBKEY` to the RSA public key and disable `DEV_MODE`.
- Required scopes: `geo-context:resolve` or the catch-all `*`.

## 5. Curl Examples
```
TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlciIsInRlbmFudF9pZCI6ImRldi10ZW5hbnQiLCJzY29wZXMiOlsiKiJdfQ.ZGV2LXNpZ25hdHVyZQ"

curl -X POST http://localhost:8102/v1/resolve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"field":{"type":"Polygon","coordinates":[[[21.0,52.0],[21.1,52.0],[21.1,52.1],[21.0,52.1],[21.0,52.0]]]},"crops":["corn"],"date":"2024-06-15T12:00:00Z"}'

curl -H "Authorization: Bearer $TOKEN" http://localhost:8102/geo-context/fco/6c9c26ad817bbf22
```

## 6. Roadmap Notes
- Additional policy enforcement (rate limits, quiet hours) lives in `policies/` and can be wired into the router as needed.
- When `ENABLE_POSTGIS=true`, ensure GDAL/PROJ and PostGIS extensions are installed.
