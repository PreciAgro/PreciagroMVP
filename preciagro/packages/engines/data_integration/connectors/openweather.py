
# connectors/openweather.py
# Implements a connector for the OpenWeather API, wrapping an existing client.

import httpx
from .base import IngestConnector
from typing import Dict, Any, Iterable, Literal


class OpenWeatherClient:
    """Client wrapper for OpenWeather One Call API.

    This class encapsulates a synchronous httpx client call. If you need to
    perform many concurrent requests consider adding an async variant or
    reusing a long-lived `httpx.Client` instance.

    TODOs:
    - Support retries/backoff for transient HTTP errors.
    - Consider swapping to `httpx.AsyncClient` for async orchestration.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Updated to One Call API 3.0 endpoint
        self.base_url = "https://api.openweathermap.org/data/3.0/onecall"

    def one_call(self, lat, lon, units="metric", exclude=""):
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


class OpenWeatherConnector(IngestConnector):
    """Connector exposing OpenWeather OneCall records as flat dicts.

    The connector accepts a client (above) and yields flattened records which
    the normalizer can convert into `NormalizedItem`. Keeping connectors and
    normalizers separate simplifies testing and reuse.

    TODOs:
    - Provide an async fetch variant.
    - Add rate-limiting / circuit-breaker integration to protect API usage.
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

        The output shape varies by scope; normalizers must handle these
        differences (see `pipeline/normalize_openweather.py`).
        """
        # Call the OpenWeather client
        resp = self.client.one_call(
            lat=lat, lon=lon, units=units, exclude=exclude)
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
