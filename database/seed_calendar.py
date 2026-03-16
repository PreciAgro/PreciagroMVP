"""
Seed crop calendar data into the crop_calendar table.

Usage:
    python database/seed_calendar.py

Requires DATABASE_URL in environment (or .env file at project root).
Upserts each crop/region row so it is safe to run multiple times.
"""
import json
import os
import sys
from pathlib import Path

# Allow running from project root or from database/ directory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import psycopg2
import psycopg2.extras


SEED_FILE = Path(__file__).parent / "seed_data" / "crop_calendar.json"


def seed():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment.")
        sys.exit(1)

    with open(SEED_FILE) as f:
        data = json.load(f)

    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    inserted = 0
    updated = 0

    for crop_type, regions in data.items():
        for region, calendar in regions.items():
            cur.execute(
                """
                INSERT INTO crop_calendar (crop_type, region, growth_stages, disease_risk_periods)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (crop_type, region) DO UPDATE
                    SET growth_stages        = EXCLUDED.growth_stages,
                        disease_risk_periods = EXCLUDED.disease_risk_periods
                """,
                (
                    crop_type,
                    region,
                    json.dumps(calendar["growth_stages"]),
                    json.dumps(calendar["disease_risk_periods"]),
                ),
            )
            if cur.rowcount == 1:
                inserted += 1
            else:
                updated += 1
            print(f"  ✓ {crop_type}/{region}")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone. {inserted} inserted, {updated} updated.")


if __name__ == "__main__":
    seed()
