"""Database operations for Geo Context Engine."""
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from ..config import settings
from ..contracts.v1.fco import FCOResponse

# Database connection setup
DATABASE_URL = settings.DATABASE_URL

# Convert to async URL if needed
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session():
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def query_spatial_data(lat: float, lon: float) -> Dict[str, Any]:
    """Query spatial context data for a location."""
    async with AsyncSessionLocal() as session:
        query = text("""
            SELECT elevation, slope, aspect, land_use, administrative_region
            FROM spatial_context 
            WHERE ST_DWithin(location, ST_GeogFromText(:point), 1000)
            ORDER BY ST_Distance(location, ST_GeogFromText(:point))
            LIMIT 1
        """)

        point_wkt = f"POINT({lon} {lat})"
        result = await session.execute(query, {"point": point_wkt})
        row = result.fetchone()

        if row:
            return {
                "elevation": row.elevation,
                "slope": row.slope,
                "aspect": row.aspect,
                "land_use": row.land_use,
                "admin_region": row.administrative_region
            }

        return {}


async def get_nearest_weather_station(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Get nearest weather station."""
    async with AsyncSessionLocal() as session:
        query = text("""
            SELECT station_id, name, elevation,
                   ST_Distance(location, ST_GeogFromText(:point)) as distance
            FROM weather_stations 
            WHERE active = true
            ORDER BY ST_Distance(location, ST_GeogFromText(:point))
            LIMIT 1
        """)

        point_wkt = f"POINT({lon} {lat})"
        result = await session.execute(query, {"point": point_wkt})
        row = result.fetchone()

        if row:
            return {
                "station_id": row.station_id,
                "name": row.name,
                "elevation": row.elevation,
                "distance": row.distance
            }

        return None


async def query_soil_data(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Query soil data for a location."""
    async with AsyncSessionLocal() as session:
        query = text("""
            SELECT ph, organic_matter, nitrogen, phosphorus, potassium,
                   soil_type, drainage, texture, data_source
            FROM soil_data 
            WHERE ST_DWithin(location, ST_GeogFromText(:point), 5000)
            ORDER BY ST_Distance(location, ST_GeogFromText(:point)),
                     sample_date DESC
            LIMIT 1
        """)

        point_wkt = f"POINT({lon} {lat})"
        result = await session.execute(query, {"point": point_wkt})
        row = result.fetchone()

        if row:
            return {
                "ph": row.ph,
                "organic_matter": row.organic_matter,
                "nitrogen": row.nitrogen,
                "phosphorus": row.phosphorus,
                "potassium": row.potassium,
                "soil_type": row.soil_type,
                "drainage": row.drainage,
                "texture": row.texture,
                "data_source": row.data_source
            }

        return None


async def query_climate_data(
    lat: float,
    lon: float,
    reference_date: datetime
) -> List[Dict[str, Any]]:
    """Query climate data for a location."""
    async with AsyncSessionLocal() as session:
        # Get data from the last 30 days before reference date
        start_date = reference_date - timedelta(days=30)

        query = text("""
            SELECT date, temperature_avg, temperature_min, temperature_max,
                   precipitation, humidity, wind_speed, solar_radiation,
                   growing_degree_days, data_source
            FROM climate_data 
            WHERE ST_DWithin(location, ST_GeogFromText(:point), 10000)
              AND date BETWEEN :start_date AND :end_date
            ORDER BY ST_Distance(location, ST_GeogFromText(:point)), date DESC
            LIMIT 30
        """)

        point_wkt = f"POINT({lon} {lat})"
        result = await session.execute(query, {
            "point": point_wkt,
            "start_date": start_date.date(),
            "end_date": reference_date.date()
        })

        rows = result.fetchall()
        return [
            {
                "date": row.date,
                "temperature_avg": row.temperature_avg,
                "temperature_min": row.temperature_min,
                "temperature_max": row.temperature_max,
                "precipitation": row.precipitation,
                "humidity": row.humidity,
                "wind_speed": row.wind_speed,
                "solar_radiation": row.solar_radiation,
                "growing_degree_days": row.growing_degree_days,
                "data_source": row.data_source
            }
            for row in rows
        ]


async def query_calendar_events(region: str, crop_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query calendar events for a region and crop type."""
    async with AsyncSessionLocal() as session:
        if crop_type:
            query = text("""
                SELECT event_type, crop_type, recommended_date,
                       optimal_window_start, optimal_window_end, confidence
                FROM calendar_events 
                WHERE region = :region AND crop_type = :crop_type
                ORDER BY recommended_date
            """)
            result = await session.execute(query, {"region": region, "crop_type": crop_type})
        else:
            query = text("""
                SELECT event_type, crop_type, recommended_date,
                       optimal_window_start, optimal_window_end, confidence
                FROM calendar_events 
                WHERE region = :region
                ORDER BY recommended_date
            """)
            result = await session.execute(query, {"region": region})

        rows = result.fetchall()
        return [
            {
                "event_type": row.event_type,
                "crop_type": row.crop_type,
                "recommended_date": row.recommended_date,
                "optimal_window_start": row.optimal_window_start,
                "optimal_window_end": row.optimal_window_end,
                "confidence": row.confidence
            }
            for row in rows
        ]


async def get_cached_fco(cache_key: str) -> Optional[FCOResponse]:
    """Get cached Field Context Object."""
    async with AsyncSessionLocal() as session:
        query = text("""
            SELECT response_data
            FROM field_context_cache 
            WHERE location_hash = :cache_key AND expires_at > :now
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = await session.execute(query, {
            "cache_key": cache_key,
            "now": datetime.now()
        })

        row = result.fetchone()
        if row:
            try:
                response_dict = row.response_data
                return FCOResponse(**response_dict)
            except Exception:
                # Invalid cached data
                pass

        return None


async def cache_fco(cache_key: str, response: FCOResponse) -> None:
    """Cache Field Context Object."""
    async with AsyncSessionLocal() as session:
        expires_at = datetime.now() + timedelta(seconds=settings.CACHE_TTL)

        # Convert response to dict for JSON storage
        response_dict = response.dict()

        query = text("""
            INSERT INTO field_context_cache 
            (location_hash, request_params_hash, response_data, expires_at)
            VALUES (:location_hash, :params_hash, :response_data, :expires_at)
            ON CONFLICT (location_hash, request_params_hash) 
            DO UPDATE SET 
                response_data = :response_data,
                expires_at = :expires_at,
                created_at = CURRENT_TIMESTAMP
        """)

        await session.execute(query, {
            "location_hash": cache_key,
            "params_hash": cache_key,  # Using same key for simplicity
            "response_data": json.dumps(response_dict, default=str),
            "expires_at": expires_at
        })

        await session.commit()


async def cleanup_expired_cache() -> None:
    """Clean up expired cache entries."""
    async with AsyncSessionLocal() as session:
        query = text("""
            DELETE FROM field_context_cache 
            WHERE expires_at < :now
        """)

        await session.execute(query, {"now": datetime.now()})
        await session.commit()
