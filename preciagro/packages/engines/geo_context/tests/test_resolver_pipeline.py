"""Test resolver pipeline for geo_context engine."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from ..pipeline.resolver import GeoContextResolver
from ..pipeline.spatial_resolver import SpatialResolver
from ..pipeline.soil_resolver import SoilResolver
from ..pipeline.climate_resolver import ClimateResolver
from ..pipeline.calendar_composer import CalendarComposer
from ..contracts.v1.requests import FCORequest, LocationPoint
from ..contracts.v1.fco import SoilData, ClimateData, SpatialContext, CalendarEvent


class TestGeoContextResolver:
    """Test cases for main GeoContextResolver."""

    @pytest.mark.asyncio
    async def test_resolve_point_location(self, sample_fco_request, mock_db_session):
        """Test resolving context for a point location."""
        resolver = GeoContextResolver()

        # Mock all sub-resolvers
        with patch.object(resolver, 'spatial_resolver') as mock_spatial, \
                patch.object(resolver, 'soil_resolver') as mock_soil, \
                patch.object(resolver, 'climate_resolver') as mock_climate, \
                patch.object(resolver, 'calendar_composer') as mock_calendar, \
                patch.object(resolver, 'rules_engine') as mock_rules:

            # Setup mocks
            mock_spatial.resolve.return_value = SpatialContext(elevation=106)
            mock_soil.resolve.return_value = SoilData(ph=6.5)
            mock_climate.resolve.return_value = ClimateData(
                temperature_avg=15.5)
            mock_calendar.compose.return_value = [
                CalendarEvent(event_type="planting",
                              crop_type="wheat", confidence=0.8)
            ]
            mock_rules.get_planting_recommendations.return_value = [
                {"crop_type": "wheat", "recommendation": "suitable", "confidence": 0.9}
            ]
            mock_rules.get_spray_recommendations.return_value = []

            result = await resolver.resolve_field_context(sample_fco_request)

            assert result is not None
            assert result.location["lat"] == 52.2297
            assert result.location["lon"] == 21.0122
            assert result.spatial is not None
            assert result.soil is not None
            assert result.climate is not None
            assert len(result.calendar_events) == 1
            assert len(result.planting_recommendations) == 1
            assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_resolve_polygon_location(self):
        """Test resolving context for a polygon location."""
        from ..contracts.v1.requests import LocationPolygon

        request = FCORequest(
            polygon=LocationPolygon(
                coordinates=[[21.0, 52.2], [21.1, 52.2], [21.0, 52.2]]),
            include_soil=True,
            use_cache=False
        )

        resolver = GeoContextResolver()

        with patch.object(resolver, 'spatial_resolver') as mock_spatial, \
                patch.object(resolver, 'soil_resolver') as mock_soil:

            mock_spatial.resolve.return_value = None
            mock_soil.resolve.return_value = SoilData(ph=6.8)

            result = await resolver.resolve_field_context(request)

            assert result is not None
            # Should calculate centroid
            assert abs(result.location["lat"] - 52.2) < 0.01
            assert abs(result.location["lon"] - 21.033) < 0.01

    @pytest.mark.asyncio
    async def test_resolve_no_location_error(self):
        """Test error when no location provided."""
        request = FCORequest(use_cache=False)  # No point or polygon
        resolver = GeoContextResolver()

        with pytest.raises(ValueError, match="Either point or polygon must be provided"):
            await resolver.resolve_field_context(request)

    @pytest.mark.asyncio
    async def test_partial_resolver_failures(self, sample_fco_request):
        """Test handling partial resolver failures."""
        resolver = GeoContextResolver()

        with patch.object(resolver, 'spatial_resolver') as mock_spatial, \
                patch.object(resolver, 'soil_resolver') as mock_soil, \
                patch.object(resolver, 'climate_resolver') as mock_climate:

            # Simulate some resolvers failing
            mock_spatial.resolve.side_effect = Exception("Spatial error")
            mock_soil.resolve.return_value = SoilData(ph=6.5)
            mock_climate.resolve.return_value = None

            result = await resolver.resolve_field_context(sample_fco_request)

            assert result is not None
            assert result.spatial is None  # Failed
            assert result.soil is not None  # Succeeded
            assert result.climate is None  # Returned None
            assert "soil_resolver" in result.data_sources
            assert "spatial_resolver" not in result.data_sources

    def test_calculate_centroid(self):
        """Test centroid calculation for polygons."""
        resolver = GeoContextResolver()

        coordinates = [
            [20.0, 50.0],
            [22.0, 50.0],
            [22.0, 52.0],
            [20.0, 52.0]
        ]

        centroid = resolver._calculate_centroid(coordinates)

        assert centroid["lat"] == 51.0
        assert centroid["lon"] == 21.0

    def test_calculate_confidence_complete_data(self):
        """Test confidence calculation with complete data."""
        from ..contracts.v1.fco import FCOResponse

        resolver = GeoContextResolver()

        response = FCOResponse(
            location={"lat": 52.0, "lon": 21.0},
            timestamp=datetime.now(),
            soil=SoilData(ph=6.5, organic_matter=3.0,
                          nitrogen=120, soil_type="loam"),
            climate=ClimateData(temperature_avg=15.0,
                                precipitation=50.0, humidity=65.0),
            spatial=SpatialContext(elevation=100, land_use="agricultural"),
            calendar_events=[
                CalendarEvent(event_type="planting", confidence=0.8),
                CalendarEvent(event_type="harvesting", confidence=0.9)
            ]
        )

        confidence = resolver._calculate_confidence(response)

        assert 0.7 <= confidence <= 1.0  # Should be high with complete data

    def test_calculate_confidence_partial_data(self):
        """Test confidence calculation with partial data."""
        from ..contracts.v1.fco import FCOResponse

        resolver = GeoContextResolver()

        response = FCOResponse(
            location={"lat": 52.0, "lon": 21.0},
            timestamp=datetime.now(),
            soil=SoilData(ph=6.5),  # Incomplete soil data
            climate=None,  # No climate data
            calendar_events=[]  # No calendar events
        )

        confidence = resolver._calculate_confidence(response)

        assert 0.0 <= confidence <= 0.5  # Should be low with incomplete data


class TestSpatialResolver:
    """Test cases for SpatialResolver."""

    @pytest.mark.asyncio
    async def test_resolve_spatial_success(self, sample_spatial_data):
        """Test successful spatial resolution."""
        resolver = SpatialResolver()
        location = {"lat": 52.2297, "lon": 21.0122}

        with patch('preciagro.packages.engines.geo_context.pipeline.spatial_resolver.query_spatial_data') as mock_query, \
                patch('preciagro.packages.engines.geo_context.pipeline.spatial_resolver.get_nearest_weather_station') as mock_station:

            mock_query.return_value = sample_spatial_data
            mock_station.return_value = {"name": "Warsaw Central"}

            result = await resolver.resolve(location)

            assert result is not None
            assert result.elevation == 106
            assert result.land_use == "agricultural"
            assert result.nearest_weather_station == "Warsaw Central"

    @pytest.mark.asyncio
    async def test_resolve_spatial_error(self):
        """Test spatial resolution with error."""
        resolver = SpatialResolver()
        location = {"lat": 52.2297, "lon": 21.0122}

        with patch('preciagro.packages.engines.geo_context.pipeline.spatial_resolver.query_spatial_data') as mock_query:
            mock_query.side_effect = Exception("Database error")

            result = await resolver.resolve(location)

            assert result is None


class TestSoilResolver:
    """Test cases for SoilResolver."""

    @pytest.mark.asyncio
    async def test_resolve_soil_success(self, sample_soil_data):
        """Test successful soil resolution."""
        resolver = SoilResolver()
        location = {"lat": 52.2297, "lon": 21.0122}

        with patch('preciagro.packages.engines.geo_context.pipeline.soil_resolver.query_soil_data') as mock_query:
            mock_query.return_value = sample_soil_data

            result = await resolver.resolve(location)

            assert result is not None
            assert result.ph == 6.5
            assert result.organic_matter == 3.2
            assert result.soil_type == "loam"

    @pytest.mark.asyncio
    async def test_resolve_soil_no_data(self):
        """Test soil resolution with no data."""
        resolver = SoilResolver()
        location = {"lat": 52.2297, "lon": 21.0122}

        with patch('preciagro.packages.engines.geo_context.pipeline.soil_resolver.query_soil_data') as mock_query, \
                patch.object(resolver, '_query_external_soil_api') as mock_external:

            mock_query.return_value = None
            mock_external.return_value = None

            result = await resolver.resolve(location)

            assert result is None


class TestClimateResolver:
    """Test cases for ClimateResolver."""

    @pytest.mark.asyncio
    async def test_resolve_climate_success(self, sample_climate_data):
        """Test successful climate resolution."""
        resolver = ClimateResolver()
        location = {"lat": 52.2297, "lon": 21.0122}

        with patch('preciagro.packages.engines.geo_context.pipeline.climate_resolver.query_climate_data') as mock_query, \
                patch.object(resolver, '_fetch_current_weather') as mock_weather:

            mock_query.return_value = sample_climate_data
            mock_weather.return_value = {
                "main": {"temp": 16.0, "humidity": 60},
                "wind": {"speed": 5.0}
            }

            result = await resolver.resolve(location)

            assert result is not None
            assert result.temperature_avg == 16.0  # From current weather
            assert result.humidity == 60
            assert result.growing_degree_days == 6.0  # 16 - 10 base temp

    @pytest.mark.asyncio
    async def test_resolve_climate_historical_only(self, sample_climate_data):
        """Test climate resolution with only historical data."""
        resolver = ClimateResolver()
        location = {"lat": 52.2297, "lon": 21.0122}

        with patch('preciagro.packages.engines.geo_context.pipeline.climate_resolver.query_climate_data') as mock_query, \
                patch.object(resolver, '_fetch_current_weather') as mock_weather:

            mock_query.return_value = sample_climate_data
            mock_weather.return_value = None  # No current weather

            result = await resolver.resolve(location)

            assert result is not None
            assert result.temperature_avg == 15.5  # From historical
            assert result.humidity == 65


class TestCalendarComposer:
    """Test cases for CalendarComposer."""

    @pytest.mark.asyncio
    async def test_compose_calendar_with_crops(self):
        """Test calendar composition with specific crops."""
        composer = CalendarComposer()
        location = {"lat": 52.2297, "lon": 21.0122}
        crop_types = ["wheat"]

        mock_events = [
            {
                "event_type": "planting",
                "crop_type": "wheat",
                "recommended_date": datetime(2024, 4, 15).date(),
                "confidence": 0.8
            }
        ]

        with patch('preciagro.packages.engines.geo_context.pipeline.calendar_composer.query_calendar_events') as mock_query:
            mock_query.return_value = mock_events

            result = await composer.compose(location, crop_types)

            assert len(result) == 1
            assert result[0].event_type == "planting"
            assert result[0].crop_type == "wheat"
            assert result[0].confidence == 0.8

    def test_determine_region(self):
        """Test region determination from coordinates."""
        composer = CalendarComposer()

        # Test Central Europe
        region = asyncio.run(composer._determine_region(52.2297, 21.0122))
        assert region == "Central Europe"

        # Test Southern Africa
        region = asyncio.run(composer._determine_region(-17.6333, 31.7833))
        assert region == "Southern Africa"

        # Test unknown region
        region = asyncio.run(composer._determine_region(0, 0))
        assert region == "Unknown"
