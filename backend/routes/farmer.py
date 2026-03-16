"""
Farmer profile and field management endpoints.

POST /farmer/create              — register a new farmer
POST /farmer/{farmer_id}/field   — add a field to a farmer
GET  /farmer/{farmer_id}/profile — fetch farmer + fields + last 5 interactions

Note: Railway PostgreSQL does not have PostGIS. GPS is stored as plain lat/lng
DOUBLE PRECISION columns. Field boundaries are stored as JSONB.
"""
import json
import logging
import math
import os

import psycopg2
import psycopg2.extras
import psycopg2.errors
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.models.schemas import FarmerCreate, FieldCreate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/farmer", tags=["farmers"])


def _get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


# ---------------------------------------------------------------------------
# Area calculation (Shoelace + Haversine approximation, no PostGIS needed)
# ---------------------------------------------------------------------------

_EARTH_RADIUS_M = 6_371_000.0


def _haversine_area_hectares(boundary: list) -> float:
    """
    Approximate polygon area in hectares using the Shoelace formula projected
    onto a local flat-earth plane (good to ~1% for fields < 10 km across).

    boundary: [[lng, lat], ...] — does not need to be closed.
    """
    if len(boundary) < 3:
        return 0.0

    # Use centroid latitude for the projection
    avg_lat = sum(p[1] for p in boundary) / len(boundary)
    lat_rad = math.radians(avg_lat)

    # Convert degrees to approximate metres
    m_per_deg_lat = math.pi * _EARTH_RADIUS_M / 180.0
    m_per_deg_lng = m_per_deg_lat * math.cos(lat_rad)

    # Shoelace formula in metre-coordinates
    total = 0.0
    n = len(boundary)
    for i in range(n):
        x1 = boundary[i][0] * m_per_deg_lng
        y1 = boundary[i][1] * m_per_deg_lat
        x2 = boundary[(i + 1) % n][0] * m_per_deg_lng
        y2 = boundary[(i + 1) % n][1] * m_per_deg_lat
        total += x1 * y2 - x2 * y1

    area_m2 = abs(total) / 2.0
    return round(area_m2 / 10_000.0, 4)


# ---------------------------------------------------------------------------
# POST /farmer/create
# ---------------------------------------------------------------------------

@router.post("/create", status_code=201)
async def create_farmer(body: FarmerCreate):
    """Register a new farmer with GPS coordinates (stored as plain lat/lng)."""
    conn = _get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            INSERT INTO farmers (phone_number, name, lat, lng, language)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, phone_number, name, lat, lng, language, created_at
            """,
            (body.phone_number, body.name, body.latitude, body.longitude, body.language),
        )
        row = dict(cur.fetchone())
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="A farmer with this phone number already exists.")
    except Exception as e:
        conn.rollback()
        logger.error("create_farmer failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cur.close()
        conn.close()

    return JSONResponse(
        status_code=201,
        content={
            "id": str(row["id"]),
            "phone_number": row["phone_number"],
            "name": row["name"],
            "location": {"lat": row["lat"], "lng": row["lng"]},
            "language": row["language"],
            "created_at": row["created_at"].isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# POST /farmer/{farmer_id}/field
# ---------------------------------------------------------------------------

@router.post("/{farmer_id}/field", status_code=201)
async def create_field(farmer_id: str, body: FieldCreate):
    """Register a new field for a farmer (boundary stored as JSONB)."""
    conn = _get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify farmer exists
        cur.execute("SELECT id FROM farmers WHERE id = %s", (farmer_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Farmer not found.")

        area = body.area_hectares if body.area_hectares is not None else _haversine_area_hectares(body.boundary)

        cur.execute(
            """
            INSERT INTO fields (farmer_id, name, boundary_json, crop_type, planting_date, area_hectares)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, farmer_id, name, crop_type, planting_date, area_hectares, boundary_json, created_at
            """,
            (
                farmer_id,
                body.name,
                json.dumps(body.boundary),
                body.crop_type,
                body.planting_date,
                area,
            ),
        )
        row = dict(cur.fetchone())
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error("create_field failed for farmer %s: %s", farmer_id, e)
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cur.close()
        conn.close()

    boundary = row["boundary_json"] if isinstance(row["boundary_json"], list) else json.loads(row["boundary_json"] or "[]")

    return JSONResponse(
        status_code=201,
        content={
            "id": str(row["id"]),
            "farmer_id": str(row["farmer_id"]),
            "name": row["name"],
            "crop_type": row["crop_type"],
            "planting_date": row["planting_date"].isoformat(),
            "area_hectares": float(row["area_hectares"]) if row["area_hectares"] is not None else None,
            "boundary": boundary,
            "created_at": row["created_at"].isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# GET /farmer/{farmer_id}/profile
# ---------------------------------------------------------------------------

@router.get("/{farmer_id}/profile")
async def get_farmer_profile(farmer_id: str):
    """Return full farmer profile: farmer details, all fields, and last 5 interactions."""
    conn = _get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Farmer
        cur.execute(
            "SELECT id, phone_number, name, language, lat, lng, created_at FROM farmers WHERE id = %s",
            (farmer_id,),
        )
        farmer_row = cur.fetchone()
        if not farmer_row:
            raise HTTPException(status_code=404, detail="Farmer not found.")
        farmer_row = dict(farmer_row)

        # Fields
        cur.execute(
            """
            SELECT id, name, crop_type, planting_date, area_hectares, boundary_json, created_at
            FROM fields
            WHERE farmer_id = %s
            ORDER BY created_at ASC
            """,
            (farmer_id,),
        )
        field_rows = [dict(r) for r in cur.fetchall()]

        # Last 5 interactions
        cur.execute(
            """
            SELECT created_at, insight, action, confidence, urgency
            FROM interactions
            WHERE farmer_id = %s
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (farmer_id,),
        )
        interaction_rows = [dict(r) for r in cur.fetchall()]

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_farmer_profile failed for %s: %s", farmer_id, e)
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cur.close()
        conn.close()

    fields = []
    for f in field_rows:
        raw_boundary = f.get("boundary_json")
        boundary = raw_boundary if isinstance(raw_boundary, list) else json.loads(raw_boundary or "[]")
        fields.append({
            "id": str(f["id"]),
            "name": f["name"],
            "crop_type": f["crop_type"],
            "planting_date": f["planting_date"].isoformat(),
            "area_hectares": float(f["area_hectares"]) if f["area_hectares"] is not None else None,
            "boundary": boundary,
            "created_at": f["created_at"].isoformat(),
        })

    interactions = []
    for i in interaction_rows:
        interactions.append({
            "created_at": i["created_at"].isoformat(),
            "insight": i.get("insight"),
            "action": i.get("action"),
            "confidence": float(i["confidence"]) if i.get("confidence") is not None else None,
            "urgency": i.get("urgency"),
        })

    lat = farmer_row.get("lat")
    lng = farmer_row.get("lng")

    return {
        "farmer": {
            "id": str(farmer_row["id"]),
            "name": farmer_row["name"],
            "phone_number": farmer_row["phone_number"],
            "location": {"lat": lat, "lng": lng},
            "language": farmer_row["language"],
            "created_at": farmer_row["created_at"].isoformat(),
        },
        "fields": fields,
        "recent_interactions": interactions,
    }
