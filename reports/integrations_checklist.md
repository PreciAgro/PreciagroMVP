# Integrations Checklist

| Engine | Integration | Purpose | Required ENV | Minimal Dev Setup | Mandatory? | Health Check |
| --- | --- | --- | --- | --- | --- | --- |
| GeoContext | PostgreSQL + PostGIS | Spatial, soil, climate lookups | DATABASE_URL, ENABLE_POSTGIS | Optional in dev; resolvers fall back to seeded data when disabled | No (dev), Yes (prod) | `/health`, resolver logs |
| GeoContext | Redis | Response caching | REDIS_URL | Optional for dev | No | Cache hit ratio in logs/metrics |
| GeoContext | External Weather/Soil APIs | Live enrichments | WEATHER_API_URL, WEATHER_API_KEY, SOIL_API_URL, SOIL_API_KEY | Optional; stubs used when unset | No | Enable detailed logging once configured |
| GeoContext | GDAL / PROJ toolchain | Spatial calculations | GDAL_DATA, PROJ_LIB | Install GDAL 3.x + PROJ 9.x locally | Yes (prod) | CLI tools (`ogrinfo`), resolver warnings |
| GeoContext | JWT Authority | API auth | JWT_PUBKEY | Required outside `DEV_MODE` | Yes | 401/403 counts, auth logs |
| Data Integration | PostgreSQL | Persist normalized items and cursors | DATABASE_URL | Recommended; tests skip when absent | Yes (prod) | `/healthz`, storage logs |
| Data Integration | Redis | Event bus and consumer stub | REDIS_URL | Optional locally | Yes (prod) | Consumer logs |
| Data Integration | OpenWeather API | Weather source | OPENWEATHER_API_KEY | Optional | No | Connector logs |
| Temporal Logic | PostgreSQL | Task persistence | DATABASE_URL | Required | Yes | Startup log, DB errors |
| Temporal Logic | Redis | Queue + worker coordination | REDIS_URL | Required for worker | Yes | Worker metrics |
| Temporal Logic | Twilio SMS | SMS delivery | TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM | Optional | No | Channel logs |
| Temporal Logic | WhatsApp Business | WhatsApp channel | WHATSAPP_TOKEN, WHATSAPP_PHONE_ID | Optional | No | Channel logs |
| Temporal Logic | JWT Authority | API auth (planned) | SERVICE_JWT_PUBLIC_KEY | Optional now, required once auth enforced | Yes (prod) | Auth middleware logs |
