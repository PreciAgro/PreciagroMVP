"""
Weather module — fetches 3-day forecast from Open-Meteo (no API key required).
Results are cached in the weather_cache table with a 6-hour TTL.
"""
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta

import httpx
import psycopg2
import psycopg2.extras

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL_HOURS = 6


def _get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _location_hash(lat: float, lon: float) -> str:
    # Round to 2 decimal places (~1 km precision) before hashing
    key = f"{round(lat, 2)},{round(lon, 2)}"
    return hashlib.md5(key.encode()).hexdigest()


def _load_cache(location_hash: str) -> dict | None:
    try:
        conn = _get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT forecast_json, expires_at FROM weather_cache WHERE location_hash = %s",
            (location_hash,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row["expires_at"] > datetime.now(timezone.utc):
            return row["forecast_json"]
    except Exception:
        pass
    return None


def _save_cache(location_hash: str, forecast: dict) -> None:
    try:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=CACHE_TTL_HOURS)
        conn = _get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO weather_cache (location_hash, forecast_json, fetched_at, expires_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (location_hash) DO UPDATE
              SET forecast_json = EXCLUDED.forecast_json,
                  fetched_at   = EXCLUDED.fetched_at,
                  expires_at   = EXCLUDED.expires_at
            """,
            (location_hash, json.dumps(forecast), now, expires),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass


async def get_forecast(lat: float, lon: float) -> dict:
    """
    Returns a dict with:
      - current_temp_c: float
      - current_humidity_pct: float
      - days: list of 3 dicts, each with:
          date, max_temp_c, min_temp_c, precip_prob_pct, precip_mm
      - summary: plain-English 3-day summary string
    """
    loc_hash = _location_hash(lat, lon)
    cached = _load_cache(loc_hash)
    if cached:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m"],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
        ],
        "timezone": "auto",
        "forecast_days": 3,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current", {})
    daily = data.get("daily", {})

    days = []
    for i in range(3):
        precip_prob = daily.get("precipitation_probability_max", [0, 0, 0])[i] or 0
        precip_mm = daily.get("precipitation_sum", [0, 0, 0])[i] or 0
        days.append(
            {
                "date": daily["time"][i],
                "max_temp_c": daily["temperature_2m_max"][i],
                "min_temp_c": daily["temperature_2m_min"][i],
                "precip_prob_pct": precip_prob,
                "precip_mm": precip_mm,
            }
        )

    # Build a plain-English summary
    rain_days = [d for d in days if d["precip_prob_pct"] >= 40]
    if not rain_days:
        rain_text = "No significant rainfall expected over the next 3 days."
    elif len(rain_days) == 3:
        rain_text = "Rain likely all 3 days."
    else:
        rain_text = f"Rain likely on {len(rain_days)} of the next 3 days."

    avg_max = sum(d["max_temp_c"] for d in days) / 3
    temp_text = f"Average daytime high of {avg_max:.0f}°C."

    summary = f"{rain_text} {temp_text}"

    forecast = {
        "current_temp_c": current.get("temperature_2m"),
        "current_humidity_pct": current.get("relative_humidity_2m"),
        "days": days,
        "summary": summary,
    }

    _save_cache(loc_hash, forecast)
    return forecast
