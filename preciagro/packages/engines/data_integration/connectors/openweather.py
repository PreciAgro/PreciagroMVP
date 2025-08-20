
# connectors/openweather.py
# Implements a connector for the OpenWeather API, wrapping an existing client.

import httpx
from .base import IngestConnector
from typing import Dict, Any, Iterable, Literal


class OpenWeatherClient:
    """
    Real OpenWeather client using httpx to call the One Call API.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/onecall"

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
    """
    Wraps an OpenWeather client and yields raw weather records in a flat form
    for normalization downstream. Supports current, hourly, and daily scopes.
    """

    def __init__(self, client: OpenWeatherClient, *, name: str = "openweather.onecall"):
        """
        Args:
            client: An instance of your OpenWeather client.
            name: Optional name for the connector/source.
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
        """
        Fetch weather data from OpenWeather API and yield records for normalization.
        Args:
            cursor: Optional sync cursor (unused here).
            lat, lon: Coordinates for weather data.
            scope: "current", "hourly", or "daily".
            units: Units for temperature (default: metric).
            exclude: Comma-separated blocks to exclude from response.
        Yields:
            Dict[str, Any]: Raw weather records with coordinates and source name.
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
