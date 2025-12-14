#!/usr/bin/env python3
"""
Simple demo of GeoContext endpoint testing with mock responses
Shows how the testing framework validates responses
"""

import asyncio
import os
import sys
from datetime import datetime

import aiohttp
from aiohttp import web

# Mock GeoContext server for demonstration


async def mock_health(request):
    """Mock health endpoint."""
    return web.json_response(
        {"status": "healthy", "service": "geocontext", "version": "1.0.0"}
    )


async def mock_fco_resolve(request):
    """Mock FCO resolve endpoint."""
    data = await request.json()

    # Simulate different responses based on coordinates
    coords = data["field"]["coordinates"][0][0]
    lat, lon = coords[1], coords[0]

    if 52.0 <= lat <= 53.0 and 21.0 <= lon <= 22.0:  # Poland
        location_name = "Poland"
        elevation = 106
        admin_l1 = "Mazowieckie"
    elif -18.0 <= lat <= -17.0 and 31.0 <= lon <= 32.0:  # Zimbabwe
        location_name = "Zimbabwe"
        elevation = 1200
        admin_l1 = "Mashonaland East"
    else:
        location_name = "Unknown"
        elevation = 100
        admin_l1 = "Unknown"

    context_hash = f"hash_{abs(hash(str(coords)))}"[:16]

    return web.json_response(
        {
            "context_hash": context_hash,
            "location": {
                "centroid": {"lat": lat, "lon": lon},
                "admin_l0": location_name,
                "admin_l1": admin_l1,
                "elevation_m": elevation,
                "agro_zone": f"{location_name} Agricultural Zone",
            },
            "climate": {
                "et0_mm_day": 4.2,
                "gdd_base10_ytd": 1247.5,
                "normals": {
                    "temp_avg": 18.5,
                    "temp_min": 12.1,
                    "temp_max": 25.3,
                    "precipitation_mm": 65.4,
                },
                "forecast_summary": {
                    "temp_avg": 22.0,
                    "precipitation_mm": 12.5,
                    "forecast_days": data.get("forecast_days", 7),
                },
            },
            "soil": {
                "texture": "loam",
                "ph_range": [6.2, 7.1],
                "organic_matter_pct": 3.4,
                "drainage": "well-drained",
            },
            "calendars": {
                "planting_windows": [
                    {
                        "crop": "corn",
                        "activity": "planting",
                        "window_start": "2025-04-15T00:00:00Z",
                        "window_end": "2025-05-15T00:00:00Z",
                    }
                ],
                "irrigation_baseline": [
                    {
                        "crop": "irrigation",
                        "activity": "irrigation",
                        "notes": "Weekly baseline: 28.8mm, Method: drip, Kc: 0.8",
                    }
                ],
            },
            "processing_time_ms": 234,
            "confidence": 0.87,
        }
    )


async def mock_cached_fco(request):
    """Mock cached FCO endpoint."""
    context_hash = request.match_info["context_hash"]

    # Simulate cache hit for specific hashes
    if context_hash.startswith("hash_"):
        return web.json_response(
            {
                "context_hash": context_hash,
                "location": {"admin_l0": "Cached Location"},
                "cache_hit": True,
                "retrieved_at": datetime.now().isoformat(),
            }
        )
    else:
        raise web.HTTPNotFound(text="FCO not found in cache")


async def mock_metrics(request):
    """Mock metrics endpoint."""
    metrics = """# HELP geo_context_requests_total Total number of requests
# TYPE geo_context_requests_total counter
geo_context_requests_total{endpoint="/api/v1/geocontext/resolve",status="200"} 42

# HELP geo_context_request_duration_seconds Request duration in seconds
# TYPE geo_context_request_duration_seconds histogram
geo_context_request_duration_seconds_bucket{le="0.1"} 10
geo_context_request_duration_seconds_bucket{le="0.5"} 35
geo_context_request_duration_seconds_bucket{le="1.0"} 42
geo_context_request_duration_seconds_bucket{le="+Inf"} 42
geo_context_request_duration_seconds_sum 15.2
geo_context_request_duration_seconds_count 42

# HELP geo_context_cache_operations_total Cache operations
# TYPE geo_context_cache_operations_total counter
geo_context_cache_operations_total{operation="hit"} 28
geo_context_cache_operations_total{operation="miss"} 14
"""
    return web.Response(text=metrics, content_type="text/plain")


def create_mock_app():
    """Create mock GeoContext application."""
    app = web.Application()
    app.router.add_get("/health", mock_health)
    app.router.add_post("/api/v1/geocontext/resolve", mock_fco_resolve)
    app.router.add_get("/api/v1/geocontext/fco/{context_hash}", mock_cached_fco)
    app.router.add_get("/metrics", mock_metrics)
    return app


async def run_mock_server():
    """Run mock server in background."""
    app = create_mock_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8001)
    await site.start()
    print("🎭 Mock GeoContext server started on http://localhost:8001")
    return runner


# Import the tester from our main test file
sys.path.append(os.path.dirname(__file__))


class MockGeoContextTester:
    """Simple tester for demo purposes."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.test_results = []

    async def run_demo_tests(self):
        """Run demo tests against mock server."""
        print("🚀 Starting GeoContext Engine Demo Tests")
        print(f"🔗 Base URL: {self.base_url}")

        async with aiohttp.ClientSession() as session:
            # Test 1: Health Check
            print("\n🔍 Testing: Health Check")
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        print("   ✅ Health check passed")
                        print(f"   📊 Response: {data}")
                    else:
                        print(f"   ❌ Health check failed - Status: {response.status}")
            except Exception as e:
                print(f"   ❌ Health check error: {e}")

            # Test 2: Poland FCO
            print("\n🔍 Testing: FCO Resolve - Poland")
            poland_request = {
                "field": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [21.0, 52.2],
                            [21.01, 52.2],
                            [21.01, 52.21],
                            [21.0, 52.21],
                            [21.0, 52.2],
                        ]
                    ],
                },
                "date": "2025-09-05",
                "crops": ["corn", "soybeans"],
                "forecast_days": 7,
                "use_cache": True,
            }

            try:
                async with session.post(
                    f"{self.base_url}/api/v1/geocontext/resolve", json=poland_request
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("   ✅ Poland FCO resolve passed")
                        print(f"   📊 Context Hash: {data.get('context_hash')}")
                        print(
                            f"   🌍 Location: {data.get('location', {}).get('admin_l0')}"
                        )
                        print(
                            f"   🌤️ ET0: {data.get('climate', {}).get('et0_mm_day')} mm/day"
                        )
                        print(
                            f"   📈 GDD YTD: {data.get('climate', {}).get('gdd_base10_ytd')}"
                        )
                        context_hash = data.get("context_hash")
                    else:
                        print(
                            f"   ❌ Poland FCO resolve failed - Status: {response.status}"
                        )
                        context_hash = None
            except Exception as e:
                print(f"   ❌ Poland FCO resolve error: {e}")
                context_hash = None

            # Test 3: Zimbabwe FCO
            print("\n🔍 Testing: FCO Resolve - Zimbabwe")
            zimbabwe_request = {
                "field": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [31.7, -17.7],
                            [31.71, -17.7],
                            [31.71, -17.69],
                            [31.7, -17.69],
                            [31.7, -17.7],
                        ]
                    ],
                },
                "date": "2025-09-05",
                "crops": ["corn", "tobacco"],
                "forecast_days": 5,
                "use_cache": False,
            }

            try:
                async with session.post(
                    f"{self.base_url}/api/v1/geocontext/resolve", json=zimbabwe_request
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("   ✅ Zimbabwe FCO resolve passed")
                        print(f"   📊 Context Hash: {data.get('context_hash')}")
                        print(
                            f"   🌍 Location: {data.get('location', {}).get('admin_l0')}"
                        )
                        print(
                            f"   ⛰️ Elevation: {data.get('location', {}).get('elevation_m')}m"
                        )
                    else:
                        print(
                            f"   ❌ Zimbabwe FCO resolve failed - Status: {response.status}"
                        )
            except Exception as e:
                print(f"   ❌ Zimbabwe FCO resolve error: {e}")

            # Test 4: Cache retrieval
            if context_hash:
                print("\n🔍 Testing: Cached FCO Retrieval")
                try:
                    async with session.get(
                        f"{self.base_url}/api/v1/geocontext/fco/{context_hash}"
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            print("   ✅ Cache retrieval passed")
                            print(
                                f"   💾 Retrieved cached FCO for hash: {context_hash}"
                            )
                        else:
                            print(
                                f"   ❌ Cache retrieval failed - Status: {response.status}"
                            )
                except Exception as e:
                    print(f"   ❌ Cache retrieval error: {e}")

            # Test 5: Metrics
            print("\n🔍 Testing: Metrics Endpoint")
            try:
                async with session.get(f"{self.base_url}/metrics") as response:
                    if response.status == 200:
                        metrics_text = await response.text()
                        expected_metrics = [
                            "geo_context_requests_total",
                            "geo_context_request_duration_seconds",
                        ]
                        found_metrics = [
                            m for m in expected_metrics if m in metrics_text
                        ]
                        print("   ✅ Metrics endpoint passed")
                        print(f"   📊 Found metrics: {found_metrics}")
                        print(
                            f"   📈 Total metrics lines: {len(metrics_text.splitlines())}"
                        )
                    else:
                        print(
                            f"   ❌ Metrics endpoint failed - Status: {response.status}"
                        )
            except Exception as e:
                print(f"   ❌ Metrics endpoint error: {e}")


async def main():
    """Run demo with mock server."""
    # Start mock server
    runner = await run_mock_server()

    # Wait a moment for server to start
    await asyncio.sleep(1)

    # Run tests
    tester = MockGeoContextTester()
    await tester.run_demo_tests()

    print("\n✅ Demo tests completed!")
    print("🎭 This demonstrates the endpoint testing framework")
    print("📝 Replace localhost:8001 with your actual GeoContext service URL")

    # Cleanup
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
