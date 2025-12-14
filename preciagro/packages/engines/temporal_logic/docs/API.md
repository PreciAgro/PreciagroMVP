# Temporal Logic Engine API Reference

Base URL: `http://localhost:8100`
Current deployment exposes the routes without authentication. Wire in `security.auth` before going to production.

## 1. Ingest Event
```
POST /temporal/events
```
Body (EngineEvent):
```json
{
  "topic": "weather.forecast",
  "id": "wx-001",
  "ts_utc": "2025-11-02T12:00:00Z",
  "farm_id": "farm-123",
  "farmer_tz": "Africa/Johannesburg",
  "payload": {"temperature": 35, "humidity": 45}
}
```
Success (200):
```json
{
  "event_id": "wx-001",
  "tasks_created": 2,
  "task_ids": ["task-0f7f1c9d", "task-6b9a52da"]
}
```

## 2. Record Task Outcome
```
POST /temporal/outcomes
```
Body (TaskOutcomePost):
```json
{
  "task_id": "task-0f7f1c9d",
  "user_id": "farmer-123",
  "outcome": "completed",
  "timestamp": "2025-11-02T13:00:00Z",
  "metadata": {"notes": "Handled during morning round"}
}
```
Response: `{"status": "recorded"}`

## 3. Retrieve Schedule
```
GET /temporal/schedule/{user_id}?days_ahead=7
```
Returns pending tasks for the selected user. Responds with an empty list when no tasks exist.

## 4. Cancel Scheduled Task
```
DELETE /temporal/schedule/{task_id}
```
- 200 -> `{"status": "cancelled"}`
- 404 -> `{"detail": "Task not found or not cancellable"}`

## 5. Intents Catalog
```
GET /temporal/intents
```
Returns a placeholder list of conversational intents (future conversational engine integration).

## 6. Diagnostics
- `GET /temporal/health`
- `GET /` (root metadata)
- `GET /metrics` (Prometheus)

## 7. Debug Routes (enabled when `config.debug` is true)
- `GET /debug/config`
- `GET /debug/rules`
- `POST /temporal/debug/test-matching`
- `POST /temporal/debug/test-task-creation`

## 8. Notes
- Enable JWT verification via `SERVICE_JWT_PUBLIC_KEY` before exposing public endpoints.
- Twilio and WhatsApp integrations live in `channels/`; configure environment variables before enabling them in production.
