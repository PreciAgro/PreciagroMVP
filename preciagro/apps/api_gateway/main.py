
# from fastapi import FastAPI
# from ...packages.shared.schemas import ImageIn, PlanResponse
# from ...packages.engines import image_analysis, geo_context, data_integration, crop_intel, temporal_logic, inventory
# from preciagro.apps.data_integration_engine.routers.ingest import router as ingest_router

# app = FastAPI(title="PreciAgro MVP API")
# app.include_router(ingest_router)
# @app.get("/health")
# def health():
#     return {"status": "ok"}

# @app.post("/v1/diagnose-and-plan", response_model=PlanResponse)
# def diagnose_and_plan(payload: ImageIn):
#     # 1) Vision diagnosis
#     dx = image_analysis.diagnose(payload.image_base64, payload.crop_hint)

#     # 2) Context & weather
#     ctx = geo_context.context_for(payload.location)
#     wx = data_integration.latest_weather(ctx["region"])

#     # 3) Crop Intelligence plan
#     crop = payload.crop_hint or "generic_crop"
#     plan = crop_intel.plan_actions(crop, dx.labels[0].name, ctx, wx)

#     # 4) Temporal reminders
#     reminders = temporal_logic.schedule(plan)

#     # 5) Inventory
#     inv = inventory.plan_impact(plan)

#     return {"diagnosis": dx, "plan": plan, "reminders": reminders, "inventory": inv}
# the above was a placeholder for the main.py file in your API gateway.


from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherClient
from fastapi import FastAPI
import os
from preciagro.packages.engines.data_integration.routers import ingest as ingest_router
from preciagro.packages.engines.data_integration.connectors.openweather import OpenWeatherConnector


app = FastAPI()


# Use the real OpenWeatherClient implementation

ow_client = OpenWeatherClient(api_key=os.getenv("OPENWEATHER_API_KEY"))
connector = OpenWeatherConnector(ow_client)
ingest_router.openweather_client_singleton = connector

app.include_router(ingest_router.router)
