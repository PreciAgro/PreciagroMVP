"""
Farmer profile and field management endpoints.

POST /farmer/create              — register a new farmer
POST /farmer/{farmer_id}/field   — add a field to a farmer
GET  /farmer/{farmer_id}/profile — fetch farmer + fields + last 5 interactions
"""
import json
import logging
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
# POST /farmer/create
# ---------------------------------------------------------------------------

@router.post("/create", status_code=201)
async def create_farmer(body: FarmerCreate):
    """Register a new farmer with GPS location."""
    conn = _get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            INSERT INTO farmers (phone_number, name, location, language)
            VALUES (
                %s, %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                %s
            )
            RETURNING
                id,
                phone_number,
                name,
                ST_Y(location::geometry) AS lat,
                ST_X(location::geometry) AS lng,
                language,
                created_at
            """,
            (
                body.phone_number,
                body.name,
                body.longitude,
                body.latitude,
                body.language,
            ),
        )
        row = dict(cur.fetchone())
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="A farmer with this phone number already exists.")
    except Exception as e:
        conn.rollback()
        logger.error("create_farmer failed: %s", e)
        raise HTTPException(status_code=500, detail="Database error while creating farmer.")
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

def _boundary_to_wkt(boundary: list) -> str:
    """Convert [[lng, lat], ...] to WKT POLYGON string. Auto-closes if needed."""
    points = list(boundary)
    if points[0] != points[-1]:
        points.append(points[0])
    coords = ", ".join(f"{p[0]} {p[1]}" for p in points)
    return f"POLYGON(({coords}))"


@router.post("/{farmer_id}/field", status_code=201)
async def create_field(farmer_id: str, body: FieldCreate):
    """Register a new field for a farmer."""
    conn = _get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Verify farmer exists
        cur.execute("SELECT id FROM farmers WHERE id = %s", (farmer_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Farmer not found.")

        wkt = _boundary_to_wkt(body.boundary)

        if body.area_hectares is not None:
            cur.execute(
                """
                INSERT INTO fields (farmer_id, name, boundary, crop_type, planting_date, area_hectares)
                VALUES (
                    %s, %s,
                    ST_SetSRID(ST_GeomFromText(%s), 4326)::geography,
                    %s, %s, %s
                )
                RETURNING id, farmer_id, name, crop_type, planting_date, area_hectares,
                          ST_AsGeoJSON(boundary::geometry) AS boundary_geojson,
                          created_at
                """,
                (farmer_id, body.name, wkt, body.crop_type, body.planting_date, body.area_hectares),
            )
        else:
            # Auto-calculate area in hectares from the polygon
            cur.execute(
                """
                INSERT INTO fields (farmer_id, name, boundary, crop_type, planting_date, area_hectares)
                VALUES (
                    %s, %s,
                    ST_SetSRID(ST_GeomFromText(%s), 4326)::geography,
                    %s, %s,
                    ROUND(
                        (ST_Area(ST_SetSRID(ST_GeomFromText(%s), 4326)::geography) / 10000.0)::numeric,
                        2
                    )
                )
                RETURNING id, farmer_id, name, crop_type, planting_date, area_hectares,
                          ST_AsGeoJSON(boundary::geometry) AS boundary_geojson,
                          created_at
                """,
                (farmer_id, body.name, wkt, body.crop_type, body.planting_date, wkt),
            )

        row = dict(cur.fetchone())
        conn.commit()
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error("create_field failed for farmer %s: %s", farmer_id, e)
        raise HTTPException(status_code=500, detail="Database error while creating field.")
    finally:
        cur.close()
        conn.close()

    boundary_geojson = json.loads(row["boundary_geojson"]) if row.get("boundary_geojson") else None
    boundary_coords = (
        boundary_geojson["coordinates"][0] if boundary_geojson else body.boundary
    )

    return JSONResponse(
        status_code=201,
        content={
            "id": str(row["id"]),
            "farmer_id": str(row["farmer_id"]),
            "name": row["name"],
            "crop_type": row["crop_type"],
            "planting_date": row["planting_date"].isoformat(),
            "area_hectares": float(row["area_hectares"]) if row["area_hectares"] is not None else None,
            "boundary": boundary_coords,
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
            """
            SELECT
                id, phone_number, name, language, created_at,
                ST_Y(location::geometry) AS lat,
                ST_X(location::geometry) AS lng
            FROM farmers
            WHERE id = %s
            """,
            (farmer_id,),
        )
        farmer_row = cur.fetchone()
        if not farmer_row:
            raise HTTPException(status_code=404, detail="Farmer not found.")
        farmer_row = dict(farmer_row)

        # Fields
        cur.execute(
            """
            SELECT
                id, name, crop_type, planting_date, area_hectares,
                ST_AsGeoJSON(boundary::geometry) AS boundary_geojson,
                created_at
            FROM fields
            WHERE farmer_id = %s
            ORDER BY created_at ASC
            """,
            (farmer_id,),
        )
        field_rows = cur.fetchall()

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
        interaction_rows = cur.fetchall()

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_farmer_profile failed for %s: %s", farmer_id, e)
        raise HTTPException(status_code=500, detail="Database error while fetching profile.")
    finally:
        cur.close()
        conn.close()

    # Serialize fields
    fields = []
    for f in field_rows:
        f = dict(f)
        geojson = json.loads(f["boundary_geojson"]) if f.get("boundary_geojson") else None
        fields.append({
            "id": str(f["id"]),
            "name": f["name"],
            "crop_type": f["crop_type"],
            "planting_date": f["planting_date"].isoformat(),
            "area_hectares": float(f["area_hectares"]) if f["area_hectares"] is not None else None,
            "boundary": geojson["coordinates"][0] if geojson else [],
            "created_at": f["created_at"].isoformat(),
        })

    # Serialize interactions
    interactions = []
    for i in interaction_rows:
        i = dict(i)
        interactions.append({
            "created_at": i["created_at"].isoformat(),
            "insight": i.get("insight"),
            "action": i.get("action"),
            "confidence": float(i["confidence"]) if i.get("confidence") is not None else None,
            "urgency": i.get("urgency"),
        })

    return {
        "farmer": {
            "id": str(farmer_row["id"]),
            "name": farmer_row["name"],
            "phone_number": farmer_row["phone_number"],
            "location": {
                "lat": farmer_row["lat"],
                "lng": farmer_row["lng"],
            },
            "language": farmer_row["language"],
            "created_at": farmer_row["created_at"].isoformat(),
        },
        "fields": fields,
        "recent_interactions": interactions,
    }
