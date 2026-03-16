"""
Crop calendar utilities — growth stage calculation and seasonal disease risk lookup.

Data is stored in the crop_calendar table as JSONB:
  growth_stages: list of {"stage": str, "start_day": int, "end_day": int, "description": str}
  disease_risk_periods: dict of {disease_name: {"months": [int, ...], "risk": str}}
"""
import json
import os
from datetime import date
from typing import Optional

import psycopg2
import psycopg2.extras


def _get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _load_calendar(crop_type: str, region: str) -> Optional[dict]:
    """Fetch growth_stages and disease_risk_periods from DB. Returns None if not found."""
    conn = _get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT growth_stages, disease_risk_periods
            FROM crop_calendar
            WHERE LOWER(crop_type) = LOWER(%s) AND LOWER(region) = LOWER(%s)
            LIMIT 1
            """,
            (crop_type, region),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
        return None

    stages = row["growth_stages"]
    risks = row["disease_risk_periods"]
    if isinstance(stages, str):
        stages = json.loads(stages)
    if isinstance(risks, str):
        risks = json.loads(risks)

    return {"growth_stages": stages, "disease_risk_periods": risks}


def calculate_growth_stage(
    crop_type: str,
    planting_date: date,
    region: str = "zimbabwe",
) -> dict:
    """
    Calculate the current growth stage for a crop based on days since planting.

    Returns:
        {"stage": str, "description": str, "days_since_planting": int}
    """
    days = (date.today() - planting_date).days

    calendar = _load_calendar(crop_type, region)
    if not calendar or not calendar["growth_stages"]:
        return {
            "stage": f"Day {days} after planting",
            "description": "No calendar data available",
            "days_since_planting": days,
        }

    for entry in calendar["growth_stages"]:
        start = entry.get("start_day", 0)
        end = entry.get("end_day", 9999)
        if start <= days <= end:
            return {
                "stage": entry.get("stage", f"Day {days}"),
                "description": entry.get("description", ""),
                "days_since_planting": days,
            }

    return {
        "stage": "Mature / Post-harvest",
        "description": "Crop has reached or exceeded physiological maturity",
        "days_since_planting": days,
    }


def get_seasonal_disease_risks(
    crop_type: str,
    current_month: int,
    region: str = "zimbabwe",
) -> list:
    """
    Return diseases that are active in the given calendar month.

    Returns:
        [{"disease": str, "risk_level": str}, ...]
    """
    calendar = _load_calendar(crop_type, region)
    if not calendar or not calendar["disease_risk_periods"]:
        return []

    active = []
    for disease, info in calendar["disease_risk_periods"].items():
        if current_month in info.get("months", []):
            active.append({"disease": disease, "risk_level": info.get("risk", "medium")})

    return active
