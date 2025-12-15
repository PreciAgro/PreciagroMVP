"""Main resolver for Field Context Objects."""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from ..config import settings
from ..contracts.v1.fco import FCOResponse
from ..contracts.v1.requests import FCORequest
from ..storage.cache import get_cache
from ..storage.db import cache_fco
from .calendar_composer import CalendarComposer
from .climate_resolver import ClimateResolver
from .rules_engine import RulesEngine
from .soil_resolver import SoilResolver
from .spatial_resolver import SpatialResolver


class GeoContextResolver:
    """Primary orchestrator for geo-context resolutions."""

    def __init__(self) -> None:
        self.spatial_resolver = SpatialResolver()
        self.soil_resolver = SoilResolver()
        self.climate_resolver = ClimateResolver()
        self.calendar_composer = CalendarComposer()
        self.rules_engine = RulesEngine()

    async def resolve_field_context(self, request: FCORequest) -> FCOResponse:
        """Resolve the full Field Context Object for the given request."""
        start_time = datetime.now(timezone.utc)
        centroid = request.get_location()
        context_hash = self._generate_context_hash(centroid, request)

        location_payload: Dict[str, Any] = {
            "centroid": {"lat": centroid["lat"], "lon": centroid["lon"]},
            "lat": centroid["lat"],
            "lon": centroid["lon"],
            "admin_l0": None,
            "admin_l1": None,
            "admin_l2": None,
            "agro_zone": None,
        }

        cache_hit = False
        cache = None
        if request.use_cache and cache:
            try:
                cache = get_cache()
                cached = await cache.get(context_hash)
                if cached:
                    cached.cache_hit = True
                    return cached
            except Exception:
                cache = None

        soil = await self._resolve_soil(request, centroid)
        climate = await self._resolve_climate(request, centroid)
        spatial = await self._resolve_spatial(request, centroid)
        calendar_events = await self._resolve_calendar(request, centroid)
        planting_recommendations, spray_recommendations = await self._resolve_recommendations(
            request, centroid, soil, climate
        )

        data_sources = [
            source
            for source, present in [
                ("spatial_resolver", spatial is not None),
                ("soil_resolver", soil is not None),
                ("climate_resolver", climate is not None),
                ("calendar_composer", bool(calendar_events)),
                (
                    "rules_engine",
                    bool(planting_recommendations) or bool(spray_recommendations),
                ),
            ]
            if present
        ]

        provenance = []
        updated_ts = datetime.now(timezone.utc).isoformat()

        if spatial:
            location_payload.update(
                {
                    "admin_l0": spatial.admin_l0 or spatial.administrative_region,
                    "admin_l1": spatial.admin_l1 or spatial.administrative_region,
                    "admin_l2": spatial.admin_l2,
                    "agro_zone": spatial.agro_zone,
                }
            )
            provenance.append(
                {
                    "source": "spatial_resolver",
                    "status": "ok",
                    "last_updated": updated_ts,
                }
            )

        if soil:
            provenance.append(
                {"source": "soil_resolver", "status": "ok", "last_updated": updated_ts}
            )

        if climate:
            provenance.append(
                {
                    "source": "climate_resolver",
                    "status": "ok",
                    "last_updated": updated_ts,
                }
            )

        if calendar_events:
            provenance.append(
                {
                    "source": "calendar_composer",
                    "status": "ok",
                    "last_updated": updated_ts,
                }
            )

        if planting_recommendations or spray_recommendations:
            provenance.append(
                {"source": "rules_engine", "status": "ok", "last_updated": updated_ts}
            )

        response = FCOResponse(
            context_hash=context_hash,
            location=location_payload,
            soil=soil,
            climate=climate,
            spatial=spatial,
            calendar_events=calendar_events,
            planting_recommendations=planting_recommendations,
            spray_recommendations=spray_recommendations,
            data_sources=data_sources,
            cache_hit=cache_hit,
            provenance=provenance,
            timestamp=start_time,
        )
        confidence_value = self._calculate_confidence(response)
        response.confidence = confidence_value
        response.confidence_score = confidence_value
        response.processing_time_ms = (
            datetime.now(timezone.utc) - start_time
        ).total_seconds() * 1000

        if request.use_cache:
            if cache:
                try:
                    await cache.set(context_hash, response)
                except Exception:
                    pass
            elif getattr(settings, "ENABLE_POSTGIS", False):
                try:
                    await cache_fco(context_hash, response)
                except Exception:
                    pass

        return response

    async def _resolve_spatial(self, request: FCORequest, location: Dict[str, float]):
        if not request.include_spatial:
            return None
        try:
            return await self._maybe_await(self.spatial_resolver.resolve(location))
        except Exception:
            return None

    async def _resolve_soil(self, request: FCORequest, location: Dict[str, float]):
        if not request.include_soil:
            return None
        try:
            return await self._maybe_await(self.soil_resolver.resolve(location))
        except Exception:
            return None

    async def _resolve_climate(self, request: FCORequest, location: Dict[str, float]):
        if not request.include_climate:
            return None
        try:
            return await self._maybe_await(
                self.climate_resolver.resolve(
                    location,
                    reference_date=request.get_reference_date(),
                    forecast_days=request.forecast_days,
                )
            )
        except Exception:
            return None

    async def _resolve_calendar(self, request: FCORequest, location: Dict[str, float]):
        if not request.include_calendar:
            return []
        try:
            result = await self._maybe_await(
                self.calendar_composer.compose(location, request.crop_types)
            )
            return result or []
        except Exception:
            return []

    async def _resolve_recommendations(
        self,
        request: FCORequest,
        location: Dict[str, float],
        soil,
        climate,
    ):
        if not request.include_rules:
            return [], []

        try:
            planting = await self._maybe_await(
                self.rules_engine.get_planting_recommendations(
                    location, soil, climate, request.crop_types
                )
            )
        except Exception:
            planting = []
        try:
            spray = await self._maybe_await(
                self.rules_engine.get_spray_recommendations(location, climate, request.crop_types)
            )
        except Exception:
            spray = []
        return planting or [], spray or []

    def _calculate_centroid(self, coordinates: list[list[float]]) -> Dict[str, float]:
        """Calculate centroid of polygon coordinates."""
        if not coordinates:
            raise ValueError("Empty coordinates")
        lats = [coord[1] for coord in coordinates]
        lons = [coord[0] for coord in coordinates]
        return {"lat": sum(lats) / len(lats), "lon": sum(lons) / len(lons)}

    def _generate_context_hash(
        self,
        location_or_request: Union[Dict[str, float], FCORequest],
        request: Optional[FCORequest] = None,
    ) -> str:
        if isinstance(location_or_request, FCORequest) and request is None:
            request = location_or_request
            location = request.get_location()
        else:
            if request is None:
                raise ValueError("Request must be provided when passing explicit location")
            location = location_or_request  # type: ignore[assignment]

        payload = {
            "lat": round(location["lat"], 5),
            "lon": round(location["lon"], 5),
            "crops": sorted(request.crop_types),
            "date": request.get_reference_date().date().isoformat(),
            "flags": {
                "soil": request.include_soil,
                "climate": request.include_climate,
                "spatial": request.include_spatial,
                "calendar": request.include_calendar,
                "rules": request.include_rules,
            },
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    def _calculate_confidence(self, response: FCOResponse) -> float:
        """Calculate a simple confidence score based on available data."""
        score = 0.0
        total = 0.0

        if response.spatial:
            score += 0.2
            total += 0.2

        if response.soil:
            soil_score = 0.1
            if response.soil.ph is not None and response.soil.organic_matter is not None:
                soil_score = 0.2
            score += soil_score
            total += 0.2

        if response.climate:
            climate_score = 0.15
            if (
                response.climate.temperature_avg is not None
                and response.climate.humidity is not None
            ):
                climate_score = 0.2
            score += climate_score
            total += 0.2

        if response.calendar_events:
            score += 0.2
            total += 0.2

        if response.planting_recommendations:
            score += 0.15
            total += 0.15

        if response.spray_recommendations:
            score += 0.05
            total += 0.05

        if total == 0:
            return 0.0

        normalized = min(1.0, max(0.0, score / total))
        return round(normalized, 2)

    async def _maybe_await(self, candidate):
        """Await coroutine results while supporting synchronous stubs used in tests."""
        if inspect.isawaitable(candidate):
            return await candidate
        return candidate


class FieldContextResolver(GeoContextResolver):
    """Backwards-compatible alias."""

    pass
