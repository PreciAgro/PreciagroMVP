"""Climate data resolver with ET0 and GDD calculations."""
from typing import Dict, Optional
import math
from datetime import datetime, timedelta
from ..contracts.v1.fco import ClimateData
from ..storage.db import query_climate_data
from ..config import settings


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

    async def _get_forecast_data(self, lat: float, lon: float, reference_date: datetime, days: int) -> Dict:
        """Get forecast data (stubbed for MVP)."""
        # In production, this would call weather API
        return {
            "temp_avg": 22.0,
            "temp_min": 15.0,
            "temp_max": 29.0,
            "precipitation_mm": 2.5,
            "humidity_pct": 65,
            "wind_speed_ms": 3.5,
            "forecast_days": days
        }

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

        temps_avg = [d.get("temperature_avg")
                     for d in historical_data if d.get("temperature_avg")]
        temps_min = [d.get("temperature_min")
                     for d in historical_data if d.get("temperature_min")]
        temps_max = [d.get("temperature_max")
                     for d in historical_data if d.get("temperature_max")]
        precip = [d.get("precipitation")
                  for d in historical_data if d.get("precipitation")]

        return {
            "temp_avg": sum(temps_avg) / len(temps_avg) if temps_avg else 20.0,
            "temp_min": sum(temps_min) / len(temps_min) if temps_min else 10.0,
            "temp_max": sum(temps_max) / len(temps_max) if temps_max else 30.0,
            "precipitation_mm": sum(precip) if precip else 50.0
        }

    def _calculate_et0_hargreaves(self, latitude: float, temp_avg: float, temp_min: float, temp_max: float, day_of_year: int) -> float:
        """Calculate reference evapotranspiration using Hargreaves method."""
        try:
            # Convert latitude to radians
            lat_rad = latitude * math.pi / 180

            # Solar declination
            solar_dec = 0.4093 * \
                math.sin(2 * math.pi * day_of_year / 365 - 1.405)

            # Sunset hour angle
            ws = math.acos(-math.tan(lat_rad) * math.tan(solar_dec))

            # Extraterrestrial radiation
            dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
            ra = (24 * 60 / math.pi) * 0.082 * dr * (
                ws * math.sin(lat_rad) * math.sin(solar_dec) +
                math.cos(lat_rad) * math.cos(solar_dec) * math.sin(ws)
            )

            # Hargreaves equation
            et0 = 0.0023 * (temp_avg + 17.8) * \
                math.sqrt(temp_max - temp_min) * ra

            return max(0, et0)  # ET0 can't be negative

        except Exception as e:
            print(f"Error calculating ET0: {e}")
            return 4.0  # Default fallback value

    def _calculate_gdd_ytd(self, historical_data: list, base_temp: float = 10.0) -> float:
        """Calculate Growing Degree Days year-to-date."""
        try:
            gdd_total = 0.0

            for record in historical_data:
                temp_avg = record.get("temperature_avg")
                if temp_avg is not None and temp_avg > base_temp:
                    gdd_total += temp_avg - base_temp

            return gdd_total

        except Exception as e:
            print(f"Error calculating GDD: {e}")
            return 0.0
