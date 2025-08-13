
# Minimal inventory calculator:
# Pretend we have everything except fungicide, which is low.
def plan_impact(plan) -> dict:
    return {
        "reservations": [{"item": "protective_gloves", "qty": 1},
                         {"item": "pruning_shears", "qty": 1}],
        "shortages": [{"item": "fungicide-X", "qty": 1, "suggested_substitute": "fungicide-Y"}]
    }
