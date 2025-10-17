
"""
Crop Intelligence Engine (CIE) - MVP

This module provides both:
1. Legacy simple action planner (backward compatible)
2. Full CIE service with FastAPI endpoints (in ./app/)

For the full CIE service, use:
    from preciagro.packages.engines.crop_intelligence.app.main import app
"""

from preciagro.packages.shared.schemas import ActionPlan, TaskItem

# ==========================================
# LEGACY SIMPLE PLANNER (Backward Compatible)
# ==========================================
# Rule-of-thumb planner that uses diagnosis + weather to create tasks.


def plan_actions(crop: str, diagnosis_label: str, context: dict, weather: dict) -> ActionPlan:
    """Legacy action planner for backward compatibility.
    
    Args:
        crop: Crop type
        diagnosis_label: Disease/issue diagnosis
        context: Context information (region, season)
        weather: Weather data (tmax_c, rain_mm)
        
    Returns:
        ActionPlan with tasks
    """
    rationale = f"Plan for {crop} in {context['region']} ({context['season']}), "                    f"weather tmax={weather['tmax_c']}C rain={weather['rain_mm']}mm."
    tasks = [
        TaskItem(day_offset=0, title="Inspect & isolate",
                 instructions="Remove heavily infected leaves."),
        TaskItem(day_offset=1, title="Apply treatment",
                 instructions=f"Use recommended fungicide for {diagnosis_label}."),
        TaskItem(day_offset=3, title="Irrigation check",
                 instructions="Adjust based on rainfall; avoid leaf wetness."),
        TaskItem(day_offset=7, title="Follow-up scan",
                 instructions="Capture new leaf photo to reassess.")
    ]
    return ActionPlan(crop=crop, diagnosis_label=diagnosis_label, rationale=rationale, tasks=tasks)


# ==========================================
# CIE MVP SERVICE
# ==========================================
# For the full Crop Intelligence Engine service with FastAPI endpoints:
# from preciagro.packages.engines.crop_intelligence.app.main import app
#
# Available endpoints:
# - POST /cie/field/register
# - POST /cie/field/telemetry
# - GET /cie/field/state
# - GET /cie/field/actions
# - POST /cie/feedback
#
# Run with: uvicorn preciagro.packages.engines.crop_intelligence.app.main:app --reload --port 8082
