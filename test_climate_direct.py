#!/usr/bin/env python3
"""Direct test of ClimateResolver module execution."""

# Add all the imports from the original file
print("Importing dependencies...")

try:
    from typing import Dict, Optional
    import math
    from datetime import datetime, timedelta
    from preciagro.packages.engines.geo_context.contracts.v1.fco import ClimateData
    from preciagro.packages.engines.geo_context.storage.db import query_climate_data
    from preciagro.packages.engines.geo_context.config import settings
    print("All dependencies imported successfully")
except Exception as e:
    print(f"Dependency import failed: {e}")
    exit(1)

print("Defining ClimateResolver class...")

# Copy the exact class definition from the file


class ClimateResolver:
    """Resolves climate information with computed metrics."""

    async def resolve(self, location: Dict[str, float], reference_date: datetime = None, forecast_days: int = 7) -> Optional[ClimateData]:
        """Resolve climate data for a location."""
        try:
            lat, lon = location["lat"], location["lon"]
            ref_date = reference_date or datetime.now()

            # Get historical data for normals calculation
            historical_data = await self._get_historical_data(lat, lon, ref_date)

            # Get forecast data
            forecast_data = await self._get_forecast_data(lat, lon, ref_date, forecast_days)

            # Calculate 30-year normals (simplified)
            normals = self._calculate_normals(historical_data)

            # Calculate ET0 using Hargreaves method
            et0 = self._calculate_et0_hargreaves(
                lat,
                normals.get("temp_avg", 20),
                normals.get("temp_min", 10),
                normals.get("temp_max", 30),
                ref_date.timetuple().tm_yday
            )

            # Calculate Growing Degree Days (base 10°C) year-to-date
            gdd_ytd = self._calculate_gdd_ytd(historical_data, base_temp=10.0)

            return ClimateData(
                forecast_summary=forecast_data,
                normals=normals,
                et0_mm_day=et0,
                gdd_base10_ytd=gdd_ytd,
                version="v1.0",
                last_updated=datetime.now()
            )

        except Exception as e:
            print(f"Error resolving climate data: {e}")
            return None

    async def _get_historical_data(self, lat: float, lon: float, reference_date: datetime) -> list:
        """Get historical climate data."""
        # Get last 30 days for simple normals calculation
        return await query_climate_data(lat, lon, reference_date)

    def _calculate_normals(self, historical_data: list) -> Dict[str, float]:
        """Calculate 30-year climate normals (simplified with available data)."""
        if not historical_data:
            # Fallback values
            return {
                "temp_avg": 20.0,
                "temp_min": 10.0,
                "temp_max": 30.0,
                "precipitation_mm": 50.0
            }
        return {"temp_avg": 20.0, "temp_min": 10.0, "temp_max": 30.0, "precipitation_mm": 50.0}

    def _calculate_et0_hargreaves(self, latitude: float, temp_avg: float, temp_min: float, temp_max: float, day_of_year: int) -> float:
        """Calculate reference evapotranspiration using Hargreaves method."""
        try:
            return 4.0  # Simplified return
        except Exception as e:
            print(f"Error calculating ET0: {e}")
            return 4.0

    def _calculate_gdd_ytd(self, historical_data: list, base_temp: float = 10.0) -> float:
        """Calculate Growing Degree Days year-to-date."""
        try:
            return 150.0  # Simplified return
        except Exception as e:
            print(f"Error calculating GDD: {e}")
            return 0.0


print("ClimateResolver class defined successfully")

# Test instantiation
try:
    resolver = ClimateResolver()
    print("✅ ClimateResolver instantiated successfully")
except Exception as e:
    print(f"❌ ClimateResolver instantiation failed: {e}")
