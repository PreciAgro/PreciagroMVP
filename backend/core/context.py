"""
Context assembler — gathers farmer profile, fields, interactions, weather,
and crop growth stage into a single string injected into the Claude system prompt.
"""
import os
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras

from backend.core.crop_calendar import calculate_growth_stage, get_seasonal_disease_risks
from backend.core.weather import get_forecast


def _get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


async def assemble_context(farmer_id: str, field_id: Optional[str] = None) -> str:
    """
    Assembles a structured context string for injection into the Claude system prompt.
    Returns a plain-English block covering farmer profile, active fields,
    recent interactions, weather, and crop growth stage.
    """
    conn = _get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # --- Farmer profile (with GPS if available) ---
    cur.execute(
        """
        SELECT id, phone_number, name, language,
               ST_Y(location::geometry) AS lat,
               ST_X(location::geometry) AS lng
        FROM farmers
        WHERE id = %s
        """,
        (farmer_id,),
    )
    farmer = cur.fetchone()
    if not farmer:
        cur.close()
        conn.close()
        return "No farmer record found. Proceed with caution."

    farmer = dict(farmer)
    lat = farmer.get("lat")
    lon = farmer.get("lng")

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

    cur.close()
    conn.close()

    # --- Crop growth stage (use requested field or first field) ---
    active_field = None
    if field_id:
        active_field = next((f for f in fields if str(f["id"]) == field_id), None)
    if not active_field and fields:
        active_field = fields[0]

    growth_stage_text = "Unknown"
    disease_risk_text = ""
    if active_field and active_field.get("crop_type") and active_field.get("planting_date"):
        stage = calculate_growth_stage(
            crop_type=active_field["crop_type"],
            planting_date=active_field["planting_date"],
            region="zimbabwe",
        )
        growth_stage_text = f"{stage['stage']} — {stage['description']} (day {stage['days_since_planting']})"

        risks = get_seasonal_disease_risks(
            crop_type=active_field["crop_type"],
            current_month=datetime.now().month,
            region="zimbabwe",
        )
        if risks:
            risk_lines = ", ".join(
                f"{r['disease']} ({r['risk_level']} risk)" for r in risks
            )
            disease_risk_text = f"Seasonal disease alerts: {risk_lines}"

    # --- Weather ---
    weather_text = "Weather data unavailable (no GPS on record)."
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
        f"GPS: {f'{lat:.4f}, {lon:.4f}' if lat is not None and lon is not None else 'Not set'}",
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
        "=== CURRENT GROWTH STAGE ===",
        growth_stage_text,
    ]

    if disease_risk_text:
        lines.append(disease_risk_text)

    lines += [
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
