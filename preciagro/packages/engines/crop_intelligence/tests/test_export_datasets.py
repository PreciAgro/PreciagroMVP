from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from preciagro.packages.engines.crop_intelligence.app.core.config import settings
from preciagro.packages.engines.crop_intelligence.data import export_datasets
from .test_smoke import register_field, post_basic_telemetry


def seed_basic_data(client: TestClient) -> str:
    register_field(client, "field_ds")
    post_basic_telemetry(client, "field_ds")
    actions = client.get("/cie/field/actions", params={"field_id": "field_ds"}).json()["items"]
    client.post(
        "/cie/feedback",
        json={
            "field_id": "field_ds",
            "action_id": actions[0]["action_id"],
            "decision": "accepted",
            "note": "dataset test",
        },
    )
    return "field_ds"


def test_dataset_exports(tmp_path: Path, client: TestClient):
    seed_basic_data(client)

    engine = create_engine(settings.DATABASE_URL)
    actions_csv = export_datasets.export_actions(engine, tmp_path)
    telemetry_csv = export_datasets.export_telemetry(engine, tmp_path)

    assert actions_csv.exists()
    assert telemetry_csv.exists()

    actions_df = pd.read_csv(actions_csv)
    telemetry_df = pd.read_csv(telemetry_csv)

    assert {"field_id", "action_type", "decision"}.issubset(set(actions_df.columns))
    assert not actions_df.empty
    assert {"field_id", "day", "rain_mm"}.issubset(set(telemetry_df.columns))
