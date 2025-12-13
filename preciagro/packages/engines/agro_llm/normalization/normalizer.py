"""Input Normalization Layer - Validates and normalizes inputs."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ..contracts.v1.schemas import FarmerRequest, GeoContext

logger = logging.getLogger(__name__)


class InputNormalizer:
    """Normalizes and validates farmer requests."""
    
    def __init__(self):
        """Initialize input normalizer."""
        logger.info("InputNormalizer initialized")
    
    def normalize(self, raw_input: Dict[str, Any]) -> FarmerRequest:
        """Normalize and validate raw input.
        
        Args:
            raw_input: Raw input dictionary
            
        Returns:
            Normalized FarmerRequest
        """
        # Normalize timestamp
        if "timestamp" in raw_input:
            raw_input["timestamp"] = self._normalize_timestamp(raw_input["timestamp"])
        else:
            raw_input["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Normalize geo fields
        if "geo" in raw_input:
            raw_input["geo"] = self._normalize_geo(raw_input["geo"])
        
        # Normalize units (if needed)
        if "soil" in raw_input and raw_input["soil"]:
            raw_input["soil"] = self._normalize_soil(raw_input["soil"])
        
        if "weather" in raw_input and raw_input["weather"]:
            raw_input["weather"] = self._normalize_weather(raw_input["weather"])
        
        # Normalize language
        if "language" in raw_input:
            raw_input["language"] = self._normalize_language(raw_input["language"])
        
        # Create and validate request
        try:
            request = FarmerRequest(**raw_input)
            return request
        except Exception as e:
            logger.error(f"Input normalization failed: {e}")
            raise ValueError(f"Invalid input: {e}") from e
    
    def _normalize_timestamp(self, timestamp: Any) -> str:
        """Normalize timestamp to ISO8601 format."""
        if isinstance(timestamp, str):
            # Try to parse and reformat
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return dt.isoformat() + "Z"
            except (ValueError, AttributeError):
                logger.warning(f"Could not parse timestamp: {timestamp}, using current time")
                return datetime.utcnow().isoformat() + "Z"
        elif isinstance(timestamp, datetime):
            return timestamp.isoformat() + "Z"
        else:
            return datetime.utcnow().isoformat() + "Z"
    
    def _normalize_geo(self, geo: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize geographic fields."""
        # Ensure lat/lon are floats and within valid ranges
        if "lat" in geo:
            geo["lat"] = float(geo["lat"])
            if not (-90.0 <= geo["lat"] <= 90.0):
                raise ValueError(f"Invalid latitude: {geo['lat']}")
        
        if "lon" in geo:
            geo["lon"] = float(geo["lon"])
            if not (-180.0 <= geo["lon"] <= 180.0):
                raise ValueError(f"Invalid longitude: {geo['lon']}")
        
        # Ensure region_code is string
        if "region_code" in geo:
            geo["region_code"] = str(geo["region_code"]).strip().upper()
        
        return geo
    
    def _normalize_soil(self, soil: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize soil measurements."""
        # Ensure pH is in valid range
        if "pH" in soil and soil["pH"] is not None:
            soil["pH"] = float(soil["pH"])
            if not (0.0 <= soil["pH"] <= 14.0):
                logger.warning(f"pH out of normal range: {soil['pH']}")
        
        # Ensure moisture is percentage
        if "moisture" in soil and soil["moisture"] is not None:
            soil["moisture"] = float(soil["moisture"])
            if soil["moisture"] > 100.0:
                logger.warning(f"Moisture > 100%: {soil['moisture']}")
        
        return soil
    
    def _normalize_weather(self, weather: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize weather data."""
        # Ensure humidity is percentage
        if "humidity" in weather and weather["humidity"] is not None:
            weather["humidity"] = float(weather["humidity"])
            if not (0.0 <= weather["humidity"] <= 100.0):
                logger.warning(f"Humidity out of range: {weather['humidity']}")
        
        # Normalize temperature
        if "temp" in weather and weather["temp"] is not None:
            weather["temp"] = float(weather["temp"])
        
        return weather
    
    def _normalize_language(self, language: Any) -> str:
        """Normalize language code."""
        lang_map = {
            "en": "en",
            "english": "en",
            "sn": "sn",
            "sinhala": "sn",
            "pl": "pl",
            "polish": "pl"
        }
        
        lang_str = str(language).lower().strip()
        return lang_map.get(lang_str, "en")  # Default to English





