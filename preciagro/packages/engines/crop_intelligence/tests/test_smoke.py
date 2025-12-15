from fastapi.testclient import TestClient


def register_field(client: TestClient, field_id: str = "f_1"):
    return client.post(
        "/cie/field/register",
        json={
            "field_id": field_id,
            "boundary_geojson": {"type": "Polygon", "coordinates": []},
            "crop": "maize",
            "planting_date": "2025-11-10",
            "irrigation_access": "none",
            "target_yield_band": "2-4 t/ha",
            "budget_class": "low",
        },
    )


def post_basic_telemetry(client: TestClient, field_id: str = "f_1"):
    return client.post(
        "/cie/field/telemetry",
        json={
            "field_id": field_id,
            "weather": [
                {"ts": "2025-12-01T00:00:00", "tmax": 28.5, "tmin": 18.2, "rain": 5.0, "rh": 75},
                {"ts": "2025-12-02T00:00:00", "tmax": 29.1, "tmin": 19.0, "rain": 0.0, "rh": 60},
            ],
            "vi": [
                {"date": "2025-12-01", "ndvi": 0.3, "quality": "good"},
                {"date": "2025-12-10", "ndvi": 0.34, "quality": "good"},
            ],
            "soil": {
                "src": "soilgrids",
                "texture": "loam",
                "whc_mm": 140,
                "uncertainty": "±15%",
            },
        },
    )


def test_register_and_core_flows(client: TestClient):
    """End-to-end smoke test covering primary endpoints."""
    reg = register_field(client)
    assert reg.status_code == 200 and reg.json()["ok"]

    telemetry = post_basic_telemetry(client)
    assert telemetry.status_code == 200 and telemetry.json()["ok"]

    state_resp = client.get("/cie/field/state", params={"field_id": "f_1"})
    assert state_resp.status_code == 200
    state_data = state_resp.json()
    assert "stage" in state_data

    status_resp = client.get("/cie/status", params={"field_id": "f_1"})
    assert status_resp.status_code == 200
    assert status_resp.json()["field_id"] == "f_1"

    actions_resp = client.get("/cie/field/actions", params={"field_id": "f_1"})
    assert actions_resp.status_code == 200
    actions = actions_resp.json()["items"]
    assert actions
    action = actions[0]
    assert {"action_id", "action", "impact_score"}.issubset(action.keys())

    feedback = client.post(
        "/cie/feedback",
        json={
            "field_id": "f_1",
            "action_id": action["action_id"],
            "decision": "accepted",
            "note": "Looks good",
        },
    )
    assert feedback.status_code == 200 and feedback.json()["ok"]

    recommend = client.post("/cie/recommend-actions", json={"field_id": "f_1"})
    assert recommend.status_code == 200
    assert recommend.json()["items"]

    predict = client.post(
        "/cie/predict-yield",
        json={"field_id": "f_1", "season_features": {"cumulative_rain_mm": 120.0}},
    )
    assert predict.status_code == 200
    payload = predict.json()
    assert payload["p10"] <= payload["p50"] <= payload["p90"]
    assert isinstance(payload["model_version"], str)

    schedule = client.get("/cie/schedule", params={"field_id": "f_1"})
    assert schedule.status_code == 200
    assert schedule.json()["items"]

    crop_status = client.get("/crop/status", params={"field_id": "f_1"})
    assert crop_status.status_code == 200
    status_body = crop_status.json()
    assert "health_score" in status_body
    assert status_body["explanations"]

    crop_yield = client.post(
        "/crop/yield",
        json={
            "field_id": "f_1",
            "baseline_features": {"cumulative_rain_mm": 130},
            "scenarios": [{"name": "irrigation_on", "adjustments": {"rain_forecast_mm": 25}}],
        },
    )
    assert crop_yield.status_code == 200
    cy = crop_yield.json()
    assert cy["baseline"]["name"] == "baseline"
    assert cy["scenarios"]
    assert cy["explanations"]

    crop_plan = client.post("/crop/plan", json={"field_id": "f_1", "horizon_days": 21})
    assert crop_plan.status_code == 200
    plan_body = crop_plan.json()
    assert plan_body["items"]
    assert plan_body["explanations"]

    crop_windows = client.get("/crop/windows", params={"crop": "maize", "region": "zimbabwe_nr1"})
    assert crop_windows.status_code == 200
    assert crop_windows.json()["planting_window"]

    crop_explain = client.post("/crop/explain", json={"field_id": "f_1", "topic": "status"})
    assert crop_explain.status_code == 200
    assert crop_explain.json()["explanations"]


def test_root_endpoint(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "Crop Intelligence Engine"
    assert data["status"] == "operational"
