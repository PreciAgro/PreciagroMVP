"""
Context assembler — gathers farmer profile, fields, interactions, weather,
and crop growth stage into a single string injected into the Claude system prompt.
"""
import json
import os
from datetime import date, datetime

import psycopg2
import psycopg2.extras

from backend.core.weather import get_forecast


def _get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _growth_stage(crop_type: str, planting_date: date, conn) -> str:
    """Determine current growth stage from crop_calendar table."""
    if not crop_type or not planting_date:
        return "Unknown"

    days_since_planting = (date.today() - planting_date).days

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT growth_stages FROM crop_calendar WHERE LOWER(crop_type) = LOWER(%s) LIMIT 1",
        (crop_type,),
    )
    row = cur.fetchone()
    cur.close()

    if not row or not row["growth_stages"]:
        return f"Day {days_since_planting} after planting"

    # growth_stages is a list of {"stage": "...", "start_day": N, "end_day": N}
    stages = row["growth_stages"]
    if isinstance(stages, str):
        stages = json.loads(stages)

    current_stage = f"Day {days_since_planting} after planting"
    for stage in stages:
        start = stage.get("start_day", 0)
        end = stage.get("end_day", 9999)
        if start <= days_since_planting <= end:
            current_stage = stage.get("stage", current_stage)
            break

    return current_stage


async def assemble_context(farmer_id: str, field_id: str = None) -> str:
    """
    Assembles a structured context string for injection into the Claude system prompt.
    Returns a plain-English block covering farmer profile, active fields,
    recent interactions, weather, and crop growth stage.
    """
    conn = _get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # --- Farmer profile ---
    cur.execute(
        "SELECT id, phone_number, name, language FROM farmers WHERE id = %s",
        (farmer_id,),
    )
    farmer = cur.fetchone()
    if not farmer:
        cur.close()
        conn.close()
        return "No farmer record found. Proceed with caution."

    # GPS not available for WhatsApp-registered farmers (no PostGIS on Railway)
    lat, lon = None, None

    # --- Active fields ---
    field_query = "SELECT id, name, crop_type, planting_date, area_hectares FROM fields WHERE farmer_id = %s"
    params = [farmer_id]
    if field_id:
        field_query += " AND id = %s"
        params.append(field_id)
    cur.execute(field_query, params)
    fields = cur.fetchall()

    # --- Last 5 interactions ---
    cur.execute(
        """
        SELECT message_in, insight, action, urgency, created_at
        FROM interactions
        WHERE farmer_id = %s
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (farmer_id,),
    )
    interactions = cur.fetchall()

    # --- Crop growth stage (use first field or requested field) ---
    active_field = None
    if field_id:
        active_field = next((f for f in fields if str(f["id"]) == field_id), None)
    if not active_field and fields:
        active_field = fields[0]

    growth_stage = "Unknown"
    if active_field:
        growth_stage = _growth_stage(
            active_field.get("crop_type"), active_field.get("planting_date"), conn
        )

    cur.close()
    conn.close()

    # --- Weather ---
    weather_text = "Weather data unavailable."
    if lat is not None and lon is not None:
        try:
            forecast = await get_forecast(lat, lon)
            day_lines = []
            for d in forecast.get("days", []):
                day_lines.append(
                    f"  {d['date']}: {d['min_temp_c']}–{d['max_temp_c']}°C, "
                    f"{d['precip_prob_pct']}% rain chance, {d['precip_mm']}mm expected"
                )
            weather_text = (
                f"Current: {forecast.get('current_temp_c')}°C, "
                f"{forecast.get('current_humidity_pct')}% humidity\n"
                + "\n".join(day_lines)
                + f"\nSummary: {forecast.get('summary')}"
            )
        except Exception as e:
            weather_text = f"Weather fetch failed: {e}"

    # --- Assemble context string ---
    lines = [
        "=== FARMER CONTEXT ===",
        f"Name: {farmer.get('name') or 'Unknown'}",
        f"Phone: {farmer.get('phone_number')}",
        f"Language: {farmer.get('language', 'en')}",
        f"GPS: {f'{lat}, {lon}' if lat else 'Not set'}",
        "",
        "=== ACTIVE FIELDS ===",
    ]

    if fields:
        for f in fields:
            planted = f.get("planting_date")
            planted_str = planted.isoformat() if planted else "Unknown"
            lines.append(
                f"- {f.get('name') or 'Unnamed field'}: {f.get('crop_type') or 'Unknown crop'}, "
                f"planted {planted_str}, {f.get('area_hectares') or '?'} ha"
            )
    else:
        lines.append("No fields registered.")

    lines += [
        "",
        f"=== CURRENT GROWTH STAGE ===",
        growth_stage,
        "",
        "=== 3-DAY WEATHER FORECAST ===",
        weather_text,
        "",
        "=== LAST 5 INTERACTIONS ===",
    ]

    if interactions:
        for i, interaction in enumerate(interactions, 1):
            ts = interaction.get("created_at")
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else str(ts)
            lines.append(f"[{i}] {ts_str}")
            lines.append(f"    Farmer said: {interaction.get('message_in') or '(image only)'}")
            lines.append(f"    Insight given: {interaction.get('insight') or 'None'}")
            lines.append(f"    Action given: {interaction.get('action') or 'None'}")
            lines.append(f"    Urgency: {interaction.get('urgency') or 'N/A'}")
    else:
        lines.append("No previous interactions.")

    lines.append("=== END CONTEXT ===")

    return "\n".join(lines)
