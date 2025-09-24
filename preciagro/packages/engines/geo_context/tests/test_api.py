"""Test API endpoints for geo_context engine."""
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, patch

from ..api.routes.api import router
from ..contracts.v1.requests import FCORequest, LocationPoint
from ..contracts.v1.fco import FCOResponse, SoilData, ClimateData, SpatialContext


# Create test app
app = FastAPI()
app.include_router(router)

client = TestClient(app)


class TestGeoContextAPI:
    """Test cases for Geo Context API."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/geo-context/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy",
                                   "service": "geo-context"}

    def test_version_endpoint(self):
        """Test version endpoint."""
        response = client.get("/geo-context/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "service" in data
        assert data["service"] == "geo-context"

    @patch('preciagro.packages.engines.geo_context.security.auth.jwt.decode')
    @patch('preciagro.packages.engines.geo_context.api.routes.api.GeoContextResolver')
    def test_get_field_context_success(self, mock_resolver_class, mock_jwt_decode):
        """Test successful FCO request."""
        # Mock JWT validation
        mock_jwt_decode.return_value = {"sub": "test"}

        # Mock resolver
        mock_resolver = AsyncMock()
        mock_response = FCOResponse(
            location={"lat": 52.2297, "lon": 21.0122},
            timestamp="2024-03-15T10:00:00",
            soil=SoilData(ph=6.5, organic_matter=3.2),
            confidence_score=0.85
        )
        mock_resolver.resolve_field_context.return_value = mock_response
        mock_resolver_class.return_value = mock_resolver

        # Test request
        request_data = {
            "point": {"latitude": 52.2297, "longitude": 21.0122},
            "include_soil": True,
            "include_climate": True,
            "crop_types": ["wheat"]
        }

        response = client.post(
            "/geo-context/fco",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "location" in data
        assert "timestamp" in data
        assert "confidence_score" in data
        assert data["location"]["lat"] == 52.2297
        assert data["location"]["lon"] == 21.0122

    @patch('preciagro.packages.engines.geo_context.security.auth.jwt.decode')
    def test_get_field_context_missing_location(self, mock_jwt_decode):
        """Test FCO request with missing location."""
        mock_jwt_decode.return_value = {"sub": "test"}

        request_data = {
            "include_soil": True,
            "crop_types": ["wheat"]
            # Missing point or polygon
        }

        response = client.post(
            "/geo-context/fco",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_get_field_context_missing_auth(self):
        """Test FCO request without authentication."""
        request_data = {
            "point": {"latitude": 52.2297, "longitude": 21.0122},
            "include_soil": True
        }

        response = client.post("/geo-context/fco", json=request_data)
        assert response.status_code == 401

    @patch('preciagro.packages.engines.geo_context.security.auth.jwt.decode')
    def test_get_field_context_invalid_token(self, mock_jwt_decode):
        """Test FCO request with invalid token."""
        mock_jwt_decode.side_effect = Exception("Invalid token")

        request_data = {
            "point": {"latitude": 52.2297, "longitude": 21.0122},
            "include_soil": True
        }

        response = client.post(
            "/geo-context/fco",
            json=request_data,
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401

    @patch('preciagro.packages.engines.geo_context.security.auth.jwt.decode')
    @patch('preciagro.packages.engines.geo_context.api.routes.api.GeoContextResolver')
    def test_get_field_context_server_error(self, mock_resolver_class, mock_jwt_decode):
        """Test FCO request with server error."""
        mock_jwt_decode.return_value = {"sub": "test"}

        # Mock resolver to raise exception
        mock_resolver = AsyncMock()
        mock_resolver.resolve_field_context.side_effect = Exception(
            "Database error")
        mock_resolver_class.return_value = mock_resolver

        request_data = {
            "point": {"latitude": 52.2297, "longitude": 21.0122},
            "include_soil": True
        }

        response = client.post(
            "/geo-context/fco",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    @patch('preciagro.packages.engines.geo_context.security.auth.jwt.decode')
    @patch('preciagro.packages.engines.geo_context.api.routes.api.GeoContextResolver')
    def test_get_field_context_polygon_request(self, mock_resolver_class, mock_jwt_decode):
        """Test FCO request with polygon location."""
        mock_jwt_decode.return_value = {"sub": "test"}

        mock_resolver = AsyncMock()
        mock_response = FCOResponse(
            location={"lat": 52.23, "lon": 21.01},
            timestamp="2024-03-15T10:00:00",
            confidence_score=0.75
        )
        mock_resolver.resolve_field_context.return_value = mock_response
        mock_resolver_class.return_value = mock_resolver

        request_data = {
            "polygon": {
                "coordinates": [
                    [21.0, 52.2],
                    [21.1, 52.2],
                    [21.1, 52.3],
                    [21.0, 52.3],
                    [21.0, 52.2]
                ]
            },
            "include_spatial": True,
            "crop_types": ["corn"]
        }

        response = client.post(
            "/geo-context/fco",
            json=request_data,
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "location" in data
        assert "confidence_score" in data
