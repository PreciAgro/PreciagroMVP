"""Main resolver for Field Context Objects - MVP version."""
import asyncio
from datetime import datetime
from typing import Optional, Dict
import hashlib
import json

from ..contracts.v1.requests import FCORequest
from ..contracts.v1.fco import FCOResponse, LocationInfo, ProvenanceEntry
from .spatial_resolver import SpatialResolver
from .soil_resolver import SoilResolver
from .climate_resolver import ClimateResolver
from .calendar_composer import CalendarComposer
from ..storage.db import get_cached_fco, cache_fco
from ..storage.cache import get_cache
from ..telemetry.metrics import telemetry, structured_logger
from ..config import settings


class GeoContextResolver:
    """Main resolver for Field Context Objects - MVP version."""

    def __init__(self):
        self.spatial_resolver = SpatialResolver()
        self.soil_resolver = SoilResolver()
        self.climate_resolver = ClimateResolver()
        self.calendar_composer = CalendarComposer()

    async def resolve_field_context(self, request: FCORequest) -> FCOResponse:
        """Resolve complete field context for a location."""

        # Calculate centroid from field polygon
        centroid = self._calculate_centroid(request.field.coordinates[0])

        # Generate context hash for caching
        context_hash = self._generate_context_hash(request)

        # Start telemetry tracking
        async with telemetry.track_request("resolve_field_context", context_hash) as metrics:

            # Log request start
            structured_logger.log_request_start(context_hash, {
                'crops': request.crops,
                'date': request.date,
                'forecast_days': request.forecast_days
            })

            # Check cache if enabled
            cache = get_cache()
            if request.use_cache:
                cached_response = await cache.get(context_hash)
                if cached_response:
                    telemetry.track_cache_hit(context_hash)
                    structured_logger.log_cache_operation(
                        "get", context_hash, "hit")
                    metrics['cache_hit'] = True
                    structured_logger.log_request_end(context_hash, metrics)
                    return cached_response
                else:
                    telemetry.track_cache_miss(context_hash)
                    structured_logger.log_cache_operation(
                        "get", context_hash, "miss")
                    metrics['cache_hit'] = False

            # Parse reference date
            try:
                reference_date = datetime.fromisoformat(request.date)
            except:
                reference_date = datetime.now()

            # Initialize response
            response = FCOResponse(
                context_hash=context_hash,
                location=LocationInfo(
                    centroid=centroid,
                    admin_l0=None,
                    admin_l1=None,
                    admin_l2=None,
                    agro_zone=None
                ),
                provenance=[]
            )

            # Collect non-dependent data concurrently
            initial_tasks = []
            initial_tasks.append(self._resolve_spatial(centroid))
            initial_tasks.append(self._resolve_soil(centroid))
            initial_tasks.append(self._resolve_climate(
                centroid, reference_date, request.forecast_days))

            # Execute initial tasks
            initial_results = await asyncio.gather(*initial_tasks, return_exceptions=True)

            # Process initial results
            spatial_result, soil_result, climate_result = initial_results

            # Update location info with spatial data
            if not isinstance(spatial_result, Exception) and spatial_result:
                response.location.admin_l0 = spatial_result.get("admin_l0")
                response.location.admin_l1 = spatial_result.get("admin_l1")
                response.location.admin_l2 = spatial_result.get("admin_l2")
                response.location.agro_zone = spatial_result.get("agro_zone")
                response.provenance.append(ProvenanceEntry(
                    source="spatial_resolver",
                    version="v1.0",
                    resolution="1km",
                    last_updated=datetime.now()
                ))

            # Add soil data
            if not isinstance(soil_result, Exception) and soil_result:
                response.soil = soil_result
                response.provenance.append(ProvenanceEntry(
                    source="soil_resolver",
                    version="v1.0",
                    resolution="250m",
                    last_updated=datetime.now()
                ))

            # Add climate data
            climate_data_dict = {}
            if not isinstance(climate_result, Exception) and climate_result:
                response.climate = climate_result
                response.provenance.append(ProvenanceEntry(
                    source="climate_resolver",
                    version="v1.0",
                    resolution="1km",
                    last_updated=datetime.now()
                ))
                # Prepare climate data for calendar resolution
                climate_data_dict = {
                    "et0_weekly_mm": getattr(climate_result, 'et0_weekly_mm', 25.0),
                    "gdd_ytd": getattr(climate_result, 'gdd_ytd', 0),
                    "temp_min": getattr(climate_result, 'temp_min_c', 10),
                    "temp_max": getattr(climate_result, 'temp_max_c', 25)
                }

            # Now resolve calendars with climate data
            calendar_result = await self._resolve_calendars(centroid, request.crops, climate_data_dict)

            # Add calendar data
            if not isinstance(calendar_result, Exception) and calendar_result:
                response.calendars = calendar_result
                response.provenance.append(ProvenanceEntry(
                    source="calendar_composer",
                    version="v1.0",
                    resolution="rules_based",
                    last_updated=datetime.now()
                ))

            # Cache result if enabled
            if request.use_cache:
                cache_success = await cache.set(context_hash, response)
                telemetry.track_cache_set(context_hash, cache_success)
                structured_logger.log_cache_operation(
                    "set", context_hash, "success" if cache_success else "error")

            # Set completion confidence
            response.confidence = self._calculate_confidence(response)

            # Add processing time from telemetry
            response.processing_time_ms = metrics.get('duration_ms', 0)

            # Log completion
            structured_logger.log_request_end(context_hash, metrics)

            return response

    async def _resolve_spatial(self, location: Dict[str, float]):
        """Resolve spatial context."""
        try:
            return await self.spatial_resolver.resolve(location)
        except Exception as e:
            print(f"Spatial resolution failed: {e}")
            return None

    async def _resolve_soil(self, location: Dict[str, float]):
        """Resolve soil data."""
        try:
            return await self.soil_resolver.resolve(location)
        except Exception as e:
            print(f"Soil resolution failed: {e}")
            return None

    async def _resolve_climate(self, location: Dict[str, float], reference_date: datetime, forecast_days: int):
        """Resolve climate data."""
        try:
            return await self.climate_resolver.resolve(location, reference_date, forecast_days)
        except Exception as e:
            print(f"Climate resolution failed: {e}")
            return None

    async def _resolve_calendars(self, location: Dict[str, float], crops: list, climate_data: Dict = None):
        """Resolve calendar data for crops and return a single Calendars object."""
        try:
            from ..contracts.v1.fco import Calendars
            
            all_planting = []
            all_irrigation = []
            all_no_spray = []

            # Process each crop individually with the new interface
            for crop in crops:
                calendar_data = await self.calendar_composer.compose(
                    location,
                    crop,
                    climate_data or {}
                )
                if calendar_data:
                    # Aggregate windows from each crop
                    if hasattr(calendar_data, 'planting_windows'):
                        all_planting.extend(calendar_data.planting_windows)
                    if hasattr(calendar_data, 'irrigation_baseline'):
                        all_irrigation.extend(calendar_data.irrigation_baseline)
                    if hasattr(calendar_data, 'no_spray_windows'):
                        all_no_spray.extend(calendar_data.no_spray_windows)

            # Return a single Calendars object with aggregated windows
            return Calendars(
                planting_windows=all_planting,
                irrigation_baseline=all_irrigation,
                no_spray_windows=all_no_spray
            )
        except Exception as e:
            print(f"Calendar composition failed: {e}")
            # Return empty Calendars object on error
            from ..contracts.v1.fco import Calendars
            return Calendars()

    def _calculate_centroid(self, coordinates: list) -> Dict[str, float]:
        """Calculate centroid of polygon coordinates."""
        if not coordinates:
            raise ValueError("Empty coordinates")

        lons = [coord[0] for coord in coordinates]
        lats = [coord[1] for coord in coordinates]

        return {
            "lat": sum(lats) / len(lats),
            "lon": sum(lons) / len(lons)
        }

    def _generate_context_hash(self, request: FCORequest) -> str:
        """Generate deterministic context hash."""
        # Normalize geometry for consistent hashing
        normalized_coords = self._normalize_geometry(request.field.coordinates)

        # Create hash input
        hash_data = {
            "geometry": normalized_coords,
            "date_bucket": request.date[:7],  # YYYY-MM for monthly buckets
            "crops": sorted(request.crops),
            "layer_versions": {
                "spatial": "v1.0",
                "soil": "v1.0",
                "climate": "v1.0",
                "calendar": "v1.0"
            }
        }

        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()[:16]  # Short hash

    def _normalize_geometry(self, coordinates):
        """Normalize geometry for consistent hashing regardless of vertex order/winding."""
        # Simple normalization - round coordinates to reduce floating point variations
        normalized = []
        for ring in coordinates:
            ring_normalized = []
            for coord in ring:
                ring_normalized.append(
                    [round(coord[0], 6), round(coord[1], 6)])
            normalized.append(ring_normalized)
        return normalized

    def _calculate_confidence(self, response: FCOResponse) -> float:
        """Calculate overall confidence score based on data completeness."""
        scores = []

        # Spatial data confidence
        if response.location.admin_l0 and response.location.agro_zone:
            scores.append(1.0)
        elif response.location.admin_l0:
            scores.append(0.7)
        else:
            scores.append(0.3)

        # Soil data confidence
        if response.soil and response.soil.texture and response.soil.ph_range:
            scores.append(1.0)
        elif response.soil:
            scores.append(0.6)
        else:
            scores.append(0.2)

        # Climate data confidence
        if response.climate and response.climate.et0_mm_day and response.climate.gdd_base10_ytd:
            scores.append(1.0)
        elif response.climate and response.climate.forecast_summary:
            scores.append(0.8)
        else:
            scores.append(0.3)

        # Calendar data confidence
        if response.calendars and (response.calendars.planting_windows or response.calendars.irrigation_baseline):
            scores.append(0.9)
        else:
            scores.append(0.1)

        # Data recency factor (favor recent data)
        recency_score = 0.9  # Assume relatively fresh data for MVP

        # Overall score weighted by completeness and recency
        overall_score = (sum(scores) / len(scores)) * \
            recency_score if scores else 0.0

        return min(1.0, max(0.0, overall_score))
