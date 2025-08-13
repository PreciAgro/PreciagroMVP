
from preciagro.packages.shared.schemas import ActionPlan, Reminder

# Convert tasks to simple reminders in hours (24 * day_offset).


def schedule(plan: ActionPlan) -> list[Reminder]:
    reminders = []
    for t in plan.tasks:
        reminders.append(Reminder(in_hours=24 * t.day_offset,
                         message=f"{t.title}: {t.instructions}"))
    return reminders
