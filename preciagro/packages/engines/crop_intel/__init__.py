
from preciagro.packages.shared.schemas import ActionPlan, TaskItem

# Rule-of-thumb planner that uses diagnosis + weather to create tasks.


def plan_actions(crop: str, diagnosis_label: str, context: dict, weather: dict) -> ActionPlan:
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
