
# connectors/openweather.py
# Implements a connector for the OpenWeather API, wrapping an existing client.

import httpx
from .base import IngestConnector
from typing import Dict, Any, Iterable, Literal, AsyncIterable
import asyncio
from concurrent.futures import ThreadPoolExecutor


class OpenWeatherClient:
    """Client wrapper for OpenWeather One Call API.

    This class uses httpx.AsyncClient for non-blocking HTTP calls within
    async contexts. For sync compatibility, we provide a fallback that runs
    the sync client in a thread executor to avoid blocking the event loop.

    TODOs:
    - Support retries/backoff for transient HTTP errors.
    - Add circuit-breaker integration to protect API usage.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Updated to One Call API 3.0 endpoint
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"
        self._thread_executor = ThreadPoolExecutor(max_workers=4)

    def _sync_one_call(self, lat, lon, units="metric", exclude=""):
        """Synchronous HTTP call (used in thread executor)."""
        params = {
            "lat": lat,
            "lon": lon,
            "units": units,
            "exclude": exclude,
            "appid": self.api_key
        }
        with httpx.Client(timeout=20) as client:
            resp = client.get(self.base_url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def one_call_async(self, lat, lon, units="metric", exclude=""):
        """Async HTTP call using AsyncClient."""
        params = {
            "lat": lat,
            "lon": lon,
            "units": units,
            "exclude": exclude,
            "appid": self.api_key
        }
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def one_call(self, lat, lon, units="metric", exclude=""):
        """Use async client by default."""
        return await self.one_call_async(lat, lon, units, exclude)


class OpenWeatherConnector(IngestConnector):
    """Connector exposing OpenWeather OneCall records as flat dicts.

    The connector accepts a client (above) and yields flattened records which
    the normalizer can convert into `NormalizedItem`. Keeping connectors and
    normalizers separate simplifies testing and reuse.

    Supports both sync and async fetch methods to integrate with different
    orchestration contexts.
    """

    def __init__(self, client: OpenWeatherClient, *, name: str = "openweather.onecall"):
        """Create connector instance.

        Keep the connector minimal: it only calls the client and yields raw
        payloads. The orchestrator controls retries, caching and persistence.
        """
        self.client = client
        self.name = name

    def fetch(
        self,
        *,
        cursor: Dict[str, Any] | None,
        lat: float,
        lon: float,
        scope: Literal["current", "hourly", "daily"] = "hourly",
        units: str = "metric",
        exclude: str = ""  # e.g., "minutely,alerts"
    ) -> Iterable[Dict[str, Any]]:
        """Fetch weather data and yield raw records for normalization.

        Sync version for backwards compatibility. For async contexts,
        use fetch_async() instead.

        The output shape varies by scope; normalizers must handle these
        differences (see `pipeline/normalize_openweather.py`).
        """
        # Run async fetch in a new event loop (for sync contexts)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in an async context; this shouldn't be called
                raise RuntimeError("Use fetch_async() in async contexts")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        resp = loop.run_until_complete(
            self.client.one_call(
                lat=lat, lon=lon, units=units, exclude=exclude)
        )

        # Attach coordinates and source name to each record
        base = {"lat": resp.get("lat"), "lon": resp.get(
            "lon"), "_source": self.name}

        if scope == "current" and "current" in resp:
            # Yield the current weather record
            yield {**base, **resp["current"]}

        elif scope == "hourly" and "hourly" in resp:
            # Yield each hourly weather record
            for r in resp["hourly"]:
                yield {**base, **r}

        elif scope == "daily" and "daily" in resp:
            # Yield each daily weather record (temp is a dict)
            for r in resp["daily"]:
                yield {**base, **r}

    async def fetch_async(
        self,
        *,
        cursor: Dict[str, Any] | None,
        lat: float,
        lon: float,
        scope: Literal["current", "hourly", "daily"] = "hourly",
        units: str = "metric",
        exclude: str = ""
    ) -> AsyncIterable[Dict[str, Any]]:
        """Async version of fetch; preferred for use in async orchestration."""
        resp = await self.client.one_call(
            lat=lat, lon=lon, units=units, exclude=exclude
        )

        # Attach coordinates and source name to each record
        base = {"lat": resp.get("lat"), "lon": resp.get(
            "lon"), "_source": self.name}

        if scope == "current" and "current" in resp:
            yield {**base, **resp["current"]}

        elif scope == "hourly" and "hourly" in resp:
            for r in resp["hourly"]:
                yield {**base, **r}

        elif scope == "daily" and "daily" in resp:
            for r in resp["daily"]:
                yield {**base, **r}
