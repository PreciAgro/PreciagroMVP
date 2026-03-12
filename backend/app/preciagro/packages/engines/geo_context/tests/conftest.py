"""Test configuration for geo_context engine."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_db_session(monkeypatch):
    """Mock the database session factory."""
    mock_session = AsyncMock(spec=AsyncSession)

    async def mock_session_factory():
        yield mock_session

    monkeypatch.setattr(
        "preciagro.packages.engines.geo_context.storage.db.AsyncSessionLocal",
        mock_session_factory,
    )
    return mock_session


@pytest.fixture
def sample_fco_request():
    """Sample FCO request for testing."""
    from ..contracts.v1.requests import FCORequest, LocationPoint

    return FCORequest(
        point=LocationPoint(latitude=52.2297, longitude=21.0122),
        reference_date=None,
        forecast_days=7,
        include_soil=True,
        include_climate=True,
        include_spatial=True,
        include_calendar=True,
        crop_types=["wheat"],
        use_cache=False,
    )


@pytest.fixture
def sample_soil_data():
    """Sample soil data for testing."""
    return {
        "ph": 6.5,
        "organic_matter": 3.2,
        "nitrogen": 120,
        "phosphorus": 45,
        "potassium": 250,
        "soil_type": "loam",
        "drainage": "well_drained",
        "texture": "loam",
        "data_source": "test",
    }


@pytest.fixture
def sample_climate_data():
    """Sample climate data for testing."""
    return [
        {
            "date": "2024-03-15",
            "temperature_avg": 15.5,
            "temperature_min": 8.2,
            "temperature_max": 22.8,
            "precipitation": 2.3,
            "humidity": 65,
            "wind_speed": 8.5,
            "solar_radiation": None,
            "growing_degree_days": 5.5,
            "data_source": "test",
        }
    ]


@pytest.fixture
def sample_spatial_data():
    """Sample spatial data for testing."""
    return {
        "elevation": 106,
        "slope": 2.5,
        "aspect": 180,
        "land_use": "agricultural",
        "admin_region": "Mazowieckie",
    }


@pytest.fixture
def mock_external_apis(monkeypatch):
    """Mock external API calls."""

    async def mock_weather_api(*args, **kwargs):
        return {
            "main": {"temp": 15.5, "temp_min": 8.2, "temp_max": 22.8, "humidity": 65},
            "wind": {"speed": 8.5},
        }

    monkeypatch.setattr(
        "aiohttp.ClientSession.get",
        AsyncMock(
            return_value=AsyncMock(status=200, json=AsyncMock(return_value=mock_weather_api()))
        ),
    )


@pytest.fixture
def mock_rules_engine():
    """Mock rules engine."""
    from ..pipeline.rules_engine import RulesEngine

    engine = RulesEngine()
    engine.planting_rules = {
        "crops": {
            "wheat": {
                "soil": {"ph_range": [6.0, 7.5], "min_organic_matter": 2.0},
                "climate": {"temperature_range": [15, 25], "min_gdd": 1200},
            }
        }
    }
    engine.spray_rules = {
        "conditions": {
            "max_wind_speed": 15,
            "min_temperature": 5,
            "max_temperature": 30,
            "min_humidity": 40,
        }
    }

    return engine
