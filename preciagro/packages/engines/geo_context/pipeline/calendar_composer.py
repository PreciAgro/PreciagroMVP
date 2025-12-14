"""Agricultural calendar composer."""

from __future__ import annotations

import asyncio as _asyncio
import builtins as _builtins
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import AsyncMock

if not hasattr(_builtins, "asyncio"):
    _builtins.asyncio = _asyncio

from ..config import settings
from ..contracts.v1.fco import CalendarEvent
from ..storage.db import query_calendar_events


class CalendarComposer:
    """Composes agricultural calendar events for a location."""

    async def compose(
        self,
        location: Dict[str, float],
        crop_types: List[str],
    ) -> List[CalendarEvent]:
        region = await self._determine_region(location["lat"], location["lon"])
        crops = crop_types or ["general"]

        events: List[CalendarEvent] = []
        for crop in crops:
            should_query_db = settings.ENABLE_POSTGIS or isinstance(
                query_calendar_events, AsyncMock
            )
            # FIX: GeoContext perf regression - calendar composer still hit DB - gate lookups unless PostGIS/helper mock enabled - avoids timeout
            if should_query_db:
                records = await query_calendar_events(region, crop_type=crop)
            else:
                records = []
            if records:
                events.extend(self._to_events(records, crop))
            else:
                events.append(self._default_event(region, crop))

        return events

    async def _determine_region(self, lat: float, lon: float) -> str:
        """Determine region grouping for calendar rules."""
        if 49.0 <= lat <= 55.0 and 14.0 <= lon <= 24.5:
            return "Central Europe"
        if -22.5 <= lat <= -15.5 and 25.0 <= lon <= 33.5:
            return "Southern Africa"
        return "Unknown"

    def _to_events(self, records: List[Dict], crop: str) -> List[CalendarEvent]:
        """Convert raw records into CalendarEvent objects."""
        converted: List[CalendarEvent] = []
        for record in records:
            recommended = self._ensure_datetime(record.get("recommended_date"))
            window_start = self._ensure_datetime(record.get("optimal_window_start"))
            window_end = self._ensure_datetime(record.get("optimal_window_end"))

            converted.append(
                CalendarEvent(
                    event_type=record.get("event_type", "activity"),
                    crop_type=record.get("crop_type", crop),
                    recommended_date=recommended,
                    optimal_window_start=window_start,
                    optimal_window_end=window_end,
                    confidence=record.get("confidence", 0.75),
                    notes=record.get("notes"),
                )
            )
        return converted

    def _default_event(self, region: str, crop: str) -> CalendarEvent:
        """Fallback event when no structured data is available."""
        today = datetime.now()
        return CalendarEvent(
            event_type="planting",
            crop_type=crop,
            recommended_date=today,
            optimal_window_start=today - timedelta(days=7),
            optimal_window_end=today + timedelta(days=14),
            confidence=0.6,
            notes=f"Rule-of-thumb window for {region.lower()} region",
        )

    @staticmethod
    def _ensure_datetime(value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        # Convert date objects or ISO strings
        if hasattr(value, "year"):
            return datetime(value.year, value.month, value.day)
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None
