from fastapi.testclient import TestClient
from preciagro.packages.engines.crop_intelligence.app.main import app


def test_register_and_actions():
    """Smoke test: register field, submit telemetry, get actions."""
    c = TestClient(app)

    # Register field
    r = c.post("/cie/field/register", json={
        "field_id": "f_1",
        "boundary_geojson": {"type": "Polygon", "coordinates": []},
        "crop": "maize",
        "planting_date": "2025-11-10",
        "irrigation_access": "none",
        "target_yield_band": "2-4 t/ha",
        "budget_class": "low"
    })
    assert r.status_code == 200
    assert r.json()["ok"] == True

    # Submit telemetry
    t = c.post("/cie/field/telemetry", json={
        "field_id": "f_1",
        "vi": [
            {"date": "2025-12-01", "ndvi": 0.3, "quality": "good"},
            {"date": "2025-12-10", "ndvi": 0.34, "quality": "good"}
        ],
        "soil": {
            "src": "soilgrids",
            "texture": "loam",
            "whc_mm": 140,
            "uncertainty": "±15%"
        }
    })
    assert t.status_code == 200
    assert t.json()["ok"] == True

    # Get field state
    s = c.get("/cie/field/state", params={"field_id": "f_1"})
    assert s.status_code == 200
    state_data = s.json()
    assert "stage" in state_data
    assert "vigor_trend" in state_data

    # Get actions
    a = c.get("/cie/field/actions", params={"field_id": "f_1"})
    assert a.status_code == 200
    data = a.json()
    assert "items" in data
    assert len(data["items"]) >= 1

    # Verify action structure
    action = data["items"][0]
    assert "action_id" in action
    assert "action" in action
    assert "impact_score" in action
    assert "why" in action
    assert isinstance(action["why"], list)

    # Submit feedback
    f = c.post("/cie/feedback", json={
        "field_id": "f_1",
        "action_id": action["action_id"],
        "decision": "accepted",
        "note": "Looks good"
    })
    assert f.status_code == 200
    assert f.json()["ok"] == True


def test_root_endpoint():
    """Test health check endpoint."""
    c = TestClient(app)
    r = c.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "Crop Intelligence Engine"
    assert data["status"] == "operational"
