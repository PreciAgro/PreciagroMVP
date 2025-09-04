#!/usr/bin/env python3
"""Test script for ClimateResolver import issues."""

print("Testing ClimateResolver imports step by step...")

try:
    print("1. Testing typing imports...")
    from typing import Dict, Optional
    print("✅ Typing imports OK")
except Exception as e:
    print(f"❌ Typing imports failed: {e}")
    exit(1)

try:
    print("2. Testing math imports...")
    import math
    print("✅ Math imports OK")
except Exception as e:
    print(f"❌ Math imports failed: {e}")
    exit(1)

try:
    print("3. Testing datetime imports...")
    from datetime import datetime, timedelta
    print("✅ Datetime imports OK")
except Exception as e:
    print(f"❌ Datetime imports failed: {e}")
    exit(1)

try:
    print("4. Testing ClimateData contract import...")
    from preciagro.packages.engines.geo_context.contracts.v1.fco import ClimateData
    print("✅ ClimateData contract OK")
except Exception as e:
    print(f"❌ ClimateData contract failed: {e}")
    exit(1)

try:
    print("5. Testing storage query function import...")
    from preciagro.packages.engines.geo_context.storage.db import query_climate_data
    print("✅ Storage query function OK")
except Exception as e:
    print(f"❌ Storage query function failed: {e}")
    exit(1)

try:
    print("6. Testing config settings import...")
    from preciagro.packages.engines.geo_context.config import settings
    print("✅ Config settings OK")
except Exception as e:
    print(f"❌ Config settings failed: {e}")
    exit(1)

try:
    print("7. Testing direct module import...")
    import preciagro.packages.engines.geo_context.pipeline.climate_resolver
    print("✅ Direct module import OK")
    print(
        f"   Module contents: {dir(preciagro.packages.engines.geo_context.pipeline.climate_resolver)}")
except Exception as e:
    print(f"❌ Direct module import failed: {e}")
    exit(1)

try:
    print("8. Testing ClimateResolver class import...")
    from preciagro.packages.engines.geo_context.pipeline.climate_resolver import ClimateResolver
    print("✅ ClimateResolver import OK")
except Exception as e:
    print(f"❌ ClimateResolver import failed: {e}")
    exit(1)

print("All imports successful!")
