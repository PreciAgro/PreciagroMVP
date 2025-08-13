
# Stub: pretend we fetched weather. Replace with real Open-Meteo, etc.
def latest_weather(region: str) -> dict:
    return {"tmax_c": 29.0 if region.startswith("zim") else 24.0,
            "rain_mm": 1.2 if region.startswith("pl") else 0.0}
