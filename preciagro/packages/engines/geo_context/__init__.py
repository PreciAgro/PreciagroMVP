"""Geo Context Engine for PreciAgro.

This engine provides comprehensive geographic and agricultural context information
for any location, including spatial data, soil information, climate data, and
agricultural calendars.
"""

# Import contracts which don't have circular dependencies
from .contracts.v1.fco import FCOResponse, SoilData, ClimateData, SpatialContext, CalendarEvent
from .contracts.v1.requests import FCORequest, LocationPoint, LocationPolygon

# Legacy compatibility
from preciagro.packages.shared.schemas import GeoPoint

# Import routers and resolvers lazily to avoid circular imports


def get_api_router():
    from .api.routes.api import router
    return router


def get_main_router():
    from .routers.geocontext import router
    return router


def get_resolver():
    from .pipeline.resolver import GeoContextResolver
    return GeoContextResolver


__version__ = "1.0.0"
__author__ = "PreciAgro Team"


# Legacy function for backward compatibility
def context_for(point: GeoPoint | None) -> dict:
    """Legacy context function - use GeoContextResolver for full functionality."""
    if not point:
        return {"region": "unknown", "season": "unknown", "soil_zone": "unknown"}
    region = "zim-mashonaland" if point.lat < 0 else "pl-mazowieckie"
    season = "dry" if point.lat < 0 else "summer"
    return {"region": region, "season": season, "soil_zone": "mixed"}


# Export main components
__all__ = [
    "api_router",
    "main_router",
    "FCOResponse",
    "SoilData",
    "ClimateData",
    "SpatialContext",
    "CalendarEvent",
    "FCORequest",
    "LocationPoint",
    "LocationPolygon",
    "GeoContextResolver",
    "context_for",  # Legacy
]
