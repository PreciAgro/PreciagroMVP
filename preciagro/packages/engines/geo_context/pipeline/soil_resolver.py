"""Soil data resolver - MVP version."""
from typing import Dict, Optional
from ..contracts.v1.fco import SoilData


class SoilResolver:
    """Resolves soil information for locations - MVP stub."""

    async def resolve(self, location: Dict[str, float]) -> Optional[SoilData]:
        """Resolve soil data for a location."""
        try:
            lat, lon = location["lat"], location["lon"]

            # MVP stub - return soil data seeded by admin zone
            soil_data = self._get_soil_by_region(lat, lon)

            return SoilData(**soil_data) if soil_data else None

        except Exception as e:
            print(f"Error resolving soil data: {e}")
            return None

    def _get_soil_by_region(self, lat: float, lon: float) -> Optional[Dict]:
        """Get soil data seeded by geographic region."""

        # Poland soil characteristics
        if 49.0 <= lat <= 55.0 and 14.0 <= lon <= 24.5:
            return {
                "texture": "loam",
                "ph_range": [6.2, 7.0],
                "organic_matter_pct": 3.2,
                "cec": 18.5,  # meq/100g
                "drainage": "well_drained",
                "resolution": "admin_zone",
                "version": "v1.0"
            }

        # Zimbabwe soil characteristics
        elif -22.5 <= lat <= -15.5 and 25.0 <= lon <= 33.5:
            return {
                "texture": "clay_loam",
                "ph_range": [5.8, 6.8],
                "organic_matter_pct": 2.8,
                "cec": 22.0,  # meq/100g
                "drainage": "moderately_drained",
                "resolution": "admin_zone",
                "version": "v1.0"
            }

        # Default/unknown region
        else:
            return {
                "texture": "loam",
                "ph_range": [6.0, 7.0],
                "organic_matter_pct": 2.5,
                "cec": 15.0,
                "drainage": "well_drained",
                "resolution": "default",
                "version": "v1.0"
            }
