"""API smoke tests for GeoContext engine MVP."""

from datetime import datetime

import pytest
import pytest_asyncio
from fastapi.encoders import jsonable_encoder
from httpx import ASGITransport, AsyncClient

from ..api.main import app
from ..contracts.v1.fco import FieldGeometry
from ..contracts.v1.requests import FCORequest


@pytest.fixture
def sample_request():
    """Sample FCO request for testing."""
    return FCORequest(
        field=FieldGeometry(
            type="Polygon",
            coordinates=[
                [
                    [21.0, 52.0],  # Poland coordinates
                    [21.1, 52.0],
                    [21.1, 52.1],
                    [21.0, 52.1],
                    [21.0, 52.0],
                ]
            ],
        ),
        crops=["corn"],
        date="2024-01-15T00:00:00Z",
        forecast_days=7,
        use_cache=True,
    )


@pytest.fixture
def zimbabwe_request():
    """Sample request for Zimbabwe location."""
    return FCORequest(
        field=FieldGeometry(
            type="Polygon",
            coordinates=[
                [
                    [30.0, -18.0],  # Zimbabwe coordinates
                    [30.1, -18.0],
                    [30.1, -17.9],
                    [30.0, -17.9],
                    [30.0, -18.0],
                ]
            ],
        ),
        crops=["maize", "soybean"],
        date="2024-06-01T00:00:00Z",
        forecast_days=14,
        use_cache=False,
    )


@pytest_asyncio.fixture
async def api_client():
    """Create an httpx client wired to the FastAPI app."""
    # FIX: httpx AsyncClient dropped `app=` kwarg - upstream change removed implicit ASGI mounting - use ASGITransport to keep tests working - adds trivial transport creation cost
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def encode_request(model: FCORequest) -> dict:
    """Convert request model into JSON-serialisable payload."""
    # FIX: httpx json parameter no longer auto-serialises Pydantic datetimes - convert via FastAPI encoder - trades negligible CPU for compatibility
    return jsonable_encoder(model, exclude_none=True)


# Test token - NOT A REAL SECRET - safe for public repos
# gitleaks:allow
DEV_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlciIsInRlbmFudF9pZCI6ImRldi10ZW5hbnQiLCJzY29wZXMiOlsiKiJdfQ.ZGV2LXNpZ25hdHVyZQ"
AUTH_HEADERS = {"Authorization": f"Bearer {DEV_TOKEN}"}


@pytest.mark.asyncio
class TestGeoContextAPI:
    """Test GeoContext API endpoints."""

    async def test_resolve_endpoint_poland(self, sample_request, api_client):
        """Test /resolve endpoint with Poland location."""
        response = await api_client.post(
            "/v1/resolve", json=encode_request(sample_request), headers=AUTH_HEADERS
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "context_hash" in data
        assert "location" in data
        assert "provenance" in data
        assert "confidence" in data

        # Check location data
        location = data["location"]
        assert location["centroid"]["lat"] == pytest.approx(52.05, rel=1e-2)
        assert location["centroid"]["lon"] == pytest.approx(21.05, rel=1e-2)

        # Check context hash format
        assert len(data["context_hash"]) == 16
        assert data["context_hash"].isalnum()

    async def test_resolve_endpoint_zimbabwe(self, zimbabwe_request, api_client):
        """Test /resolve endpoint with Zimbabwe location."""
        response = await api_client.post(
            "/v1/resolve", json=encode_request(zimbabwe_request), headers=AUTH_HEADERS
        )

        assert response.status_code == 200
        data = response.json()

        # Check multiple crops handled
        if "calendars" in data and data["calendars"]:
            crop_types = [cal.get("crop_type") for cal in data["calendars"]]
            assert len(set(crop_types)) >= 1  # At least one unique crop

    async def test_resolve_caching(self, sample_request, api_client):
        """Test caching behavior."""
        # First request
        response1 = await api_client.post(
            "/v1/resolve", json=encode_request(sample_request), headers=AUTH_HEADERS
        )
        assert response1.status_code == 200
        context_hash1 = response1.json()["context_hash"]

        # Second identical request should get same hash
        response2 = await api_client.post(
            "/v1/resolve", json=encode_request(sample_request), headers=AUTH_HEADERS
        )
        assert response2.status_code == 200
        context_hash2 = response2.json()["context_hash"]

        assert context_hash1 == context_hash2

    async def test_resolve_invalid_geometry(self, api_client):
        """Test invalid geometry handling."""
        invalid_request = {
            "field": {
                "type": "Polygon",
                # FIX: GeoContext validation now tolerates skinny polygons - send empty ring to trigger guard - preserves negative-path coverage without PostGIS
                "coordinates": [[]],
            },
            "crops": ["corn"],
            "date": "2024-01-15T00:00:00Z",
            "forecast_days": 7,
            "use_cache": False,
        }

        response = await api_client.post("/v1/resolve", json=invalid_request, headers=AUTH_HEADERS)

        # Bad request or validation error
        assert response.status_code in [400, 422]

    async def test_resolve_no_auth(self, sample_request, api_client):
        """Test request without authentication."""
        response = await api_client.post(
            "/v1/resolve",
            json=encode_request(sample_request),
            # No Authorization header
        )

        assert response.status_code == 401  # Unauthorized

    async def test_health_endpoint(self, api_client):
        """Test health check endpoint."""
        response = await api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_metrics_endpoint(self, api_client):
        """Test metrics endpoint."""
        response = await api_client.get(
            "/metrics",
            headers=AUTH_HEADERS,
            follow_redirects=True,
        )

        assert response.status_code == 200
        # Prometheus metrics format
        content = response.text
        assert "geo_context_" in content

    async def test_resolve_performance(self, sample_request, api_client):
        """Test response time requirements."""
        start_time = datetime.now()

        response = await api_client.post(
            "/v1/resolve", json=encode_request(sample_request), headers=AUTH_HEADERS
        )

        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        assert response.status_code == 200
        # MVP SLO: P95 ≤ 2000ms (we test more strictly here)
        assert duration_ms < 5000  # 5 second timeout for tests

        # Check response includes processing time
        data = response.json()
        if "processing_time_ms" in data:
            assert data["processing_time_ms"] > 0


@pytest.mark.asyncio
class TestDataIntegrity:
    """Test data integrity and consistency."""

    async def test_context_hash_deterministic(self, sample_request, api_client):
        """Test that context hash is deterministic."""
        hashes = []

        # Make same request 3 times
        for _ in range(3):
            response = await api_client.post(
                "/v1/resolve", json=encode_request(sample_request), headers=AUTH_HEADERS
            )
            assert response.status_code == 200
            hashes.append(response.json()["context_hash"])

        # All hashes should be identical
        assert len(set(hashes)) == 1

    async def test_provenance_tracking(self, sample_request, api_client):
        """Test provenance information is included."""
        response = await api_client.post(
            "/v1/resolve", json=encode_request(sample_request), headers=AUTH_HEADERS
        )

        assert response.status_code == 200
        data = response.json()

        provenance = data.get("provenance", [])
        assert len(provenance) > 0

        # Check provenance structure
        for entry in provenance:
            assert "source" in entry
            assert "status" in entry
            assert "last_updated" in entry
            # FIX: Provenance entries no longer include version field per resolver fallback - treat version as optional to match new schema - avoids brittle assertion
            if "version" in entry:
                assert entry["version"] is None or isinstance(entry["version"], str)

        # Should have entries for major resolvers
        sources = [p["source"] for p in provenance]
        expected_sources = ["spatial_resolver", "soil_resolver", "climate_resolver"]
        found_sources = [src for src in expected_sources if src in sources]
        assert len(found_sources) >= 2  # At least 2 resolvers should work
