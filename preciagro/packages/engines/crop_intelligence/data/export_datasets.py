from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Tuple

import pandas as pd
from sqlalchemy import create_engine, text

from ..app.core.config import settings


BASE_DIR = Path(__file__).resolve().parents[3]


ACTIONS_QUERY = """
SELECT
    r.id AS recommendation_id,
    r.field_id,
    f.crop,
    f.region,
    r.action AS action_type,
    r.created_at,
    r.payload,
    fs.stage_code,
    fs.stage_confidence,
    fb.decision,
    fb.note AS feedback_note,
    fb.recorded_at AS feedback_at
FROM cie_recommendations r
JOIN cie_fields f ON f.field_id = r.field_id
LEFT JOIN cie_field_state fs ON fs.field_id = r.field_id
LEFT JOIN cie_action_feedback fb ON fb.recommendation_id = r.id
"""

TELEMETRY_QUERY = """
WITH rain AS (
    SELECT
        field_id,
        DATE(ts) AS day,
        SUM(COALESCE(rain_mm, 0)) AS rain_mm,
        AVG(tmax_c) AS tmax_avg,
        AVG(tmin_c) AS tmin_avg
    FROM cie_telemetry_weather
    GROUP BY field_id, DATE(ts)
),
vi AS (
    SELECT
        field_id,
        date,
        MAX(ndvi) AS ndvi_max
    FROM cie_telemetry_vi
    GROUP BY field_id, date
)
SELECT
    f.field_id,
    f.crop,
    r.day,
    r.rain_mm,
    r.tmax_avg,
    r.tmin_avg,
    vi.ndvi_max,
    (
        SELECT whc_mm
        FROM cie_soil_baseline sb
        WHERE sb.field_id = f.field_id
        ORDER BY sb.recorded_at DESC
        LIMIT 1
    ) AS whc_mm
FROM cie_fields f
LEFT JOIN rain r ON r.field_id = f.field_id
LEFT JOIN vi ON vi.field_id = f.field_id AND vi.date = r.day
WHERE r.day IS NOT NULL
"""


def _load_dataframe(engine, query: str) -> pd.DataFrame:
    return pd.read_sql_query(text(query), engine)


def _normalize_payload_column(df: pd.DataFrame) -> pd.DataFrame:
    if "payload" not in df.columns:
        return df
    payload_cols = []
    for _, row in df.iterrows():
        payload = row.get("payload")
        if isinstance(payload, dict):
            payload_cols.append(payload)
        else:
            try:
                payload_cols.append(json.loads(payload) if payload else {})
            except Exception:
                payload_cols.append({})
    payload_df = pd.json_normalize(payload_cols)
    payload_df.columns = [f"payload.{c}" for c in payload_df.columns]
    return pd.concat([df.drop(columns=["payload"]), payload_df], axis=1)


def export_actions(engine, output_dir: Path) -> Path:
    df = _load_dataframe(engine, ACTIONS_QUERY)
    df = _normalize_payload_column(df)
    path = output_dir / "cie_actions_dataset.csv"
    df.to_csv(path, index=False)
    return path


def export_telemetry(engine, output_dir: Path) -> Path:
    df = _load_dataframe(engine, TELEMETRY_QUERY)
    path = output_dir / "cie_telemetry_daily.csv"
    df.to_csv(path, index=False)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export CIE datasets for model retraining.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=BASE_DIR / "artifacts",
        help="Directory to write CSV exports (default: ./artifacts)",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=["actions", "telemetry", "all"],
        default=["all"],
        help="Datasets to export",
    )
    args = parser.parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    datasets = set(args.datasets)
    if "all" in datasets:
        datasets = {"actions", "telemetry"}

    engine = create_engine(settings.DATABASE_URL)
    produced: list[Tuple[str, Path]] = []

    if "actions" in datasets:
        produced.append(("actions", export_actions(engine, output_dir)))
    if "telemetry" in datasets:
        produced.append(("telemetry", export_telemetry(engine, output_dir)))

    for name, path in produced:
        print(f"[cie-export] wrote {name} dataset -> {path}")


if __name__ == "__main__":
    main()
