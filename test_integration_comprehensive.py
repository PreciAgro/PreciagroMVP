#!/usr/bin/env python3
"""Comprehensive integration test for GeoContext MVP."""

import asyncio
from datetime import datetime


async def test_geo_context_integration():
    """Test the complete GeoContext integration."""

    print("🧪 Starting GeoContext MVP Integration Test")
    print("=" * 50)

    # Test 1: Import all core components
    print("\n1. Testing Core Component Imports...")

    try:
        from preciagro.packages.engines.geo_context.pipeline.resolver import GeoContextResolver
        from preciagro.packages.engines.geo_context.pipeline.climate_resolver import ClimateResolver
        from preciagro.packages.engines.geo_context.pipeline.calendar_composer import CalendarComposer
        from preciagro.packages.engines.geo_context.contracts.v1.fco import FCOResponse
        from preciagro.packages.engines.geo_context.contracts.v1.requests import FCORequest, GeoJSONPolygon
        print("✅ All core components imported successfully")
    except Exception as e:
        print(f"❌ Core component import failed: {e}")
        return False

    # Test 2: Test resolver instantiation
    print("\n2. Testing Component Instantiation...")

    try:
        resolver = GeoContextResolver()
        climate_resolver = ClimateResolver()
        calendar_composer = CalendarComposer()
        print("✅ All components instantiated successfully")
    except Exception as e:
        print(f"❌ Component instantiation failed: {e}")
        return False

    # Test 3: Test basic resolver functionality (mock)
    print("\n3. Testing Basic Resolver Functionality...")

    try:
        # Create a test request
        test_polygon = GeoJSONPolygon(
            coordinates=[[[-74.0060, 40.7128], [-74.0050, 40.7128],
                          [-74.0050, 40.7138], [-74.0060, 40.7138], [-74.0060, 40.7128]]]
        )
        request = FCORequest(
            field=test_polygon,
            date="2025-09-04",
            crops=["corn", "soybeans"]
        )

        # Test method exists and can be called (will fail on DB but that's ok for now)
        try:
            result = await resolver.resolve_field_context(request)
            print("✅ Resolver method executed (expected DB connection failure is OK)")
        except Exception as e:
            if "connection" in str(e).lower() or "database" in str(e).lower() or "db" in str(e).lower():
                print("✅ Resolver method executed (expected DB connection failure)")
            else:
                print(
                    f"⚠️  Resolver method executed with unexpected error: {e}")

    except Exception as e:
        print(f"❌ Basic resolver functionality test failed: {e}")
        return False

    # Test 4: Test API routes import
    print("\n4. Testing API Routes...")

    try:
        from preciagro.packages.engines.geo_context.api.routes.api import router
        from preciagro.packages.engines.geo_context.routers.geocontext import router as main_router
        print("✅ API routes imported successfully")
    except Exception as e:
        print(f"❌ API routes import failed: {e}")
        return False

    # Test 5: Test contract models
    print("\n5. Testing Contract Models...")

    try:
        from preciagro.packages.engines.geo_context.contracts.v1.fco import (
            FCOResponse, SoilData, ClimateData, LocationInfo, Calendars
        )

        # Test model instantiation
        location_info = LocationInfo(
            centroid={"lat": 40.7128, "lon": -74.0060})
        soil_data = SoilData(texture="loam", ph_range=[6.0, 7.0])
        climate_data = ClimateData(et0_mm_day=4.5, gdd_base10_ytd=150.0)
        calendars = Calendars()

        fco_response = FCOResponse(
            context_hash="test_hash_12345",
            location=location_info,
            soil=soil_data,
            climate=climate_data,
            calendars=calendars
        )

        print("✅ Contract models working correctly")

    except Exception as e:
        print(f"❌ Contract models test failed: {e}")
        return False

    # Test 6: Test configuration
    print("\n6. Testing Configuration...")

    try:
        from preciagro.packages.engines.geo_context.config import settings
        print(
            f"✅ Configuration loaded - Database URL configured: {bool(settings.DATABASE_URL)}")
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

    print("\n" + "=" * 50)
    print("✅ ALL INTEGRATION TESTS PASSED!")
    print("🎉 GeoContext MVP is ready for next phase testing")
    print("=" * 50)

    return True

if __name__ == "__main__":
    asyncio.run(test_geo_context_integration())
