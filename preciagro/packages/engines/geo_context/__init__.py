
from preciagro.packages.shared.schemas import GeoPoint
# Stub: attach a fake agro-zone & season from lat/lng.


def context_for(point: GeoPoint | None) -> dict:
    if not point:
        return {"region": "unknown", "season": "unknown", "soil_zone": "unknown"}
    region = "zim-mashonaland" if point.lat < 0 else "pl-mazowieckie"
    season = "dry" if point.lat < 0 else "summer"
    return {"region": region, "season": season, "soil_zone": "loam"}
