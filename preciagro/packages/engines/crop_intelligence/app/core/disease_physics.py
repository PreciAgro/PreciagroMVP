"""
Leaf-wetness proxy and disease risk calculation from weather + canopy stage.
Keeps HRS (High Risk Score) honest with physics-based disease windows.
"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class WeatherConditions:
    """Weather conditions for leaf-wetness calculation."""
    timestamp: datetime
    temp_c: float
    rh_pct: float
    wind_ms: float
    rain_mm: float = 0.0
    dew_point_c: Optional[float] = None


@dataclass
class CanopyState:
    """Canopy characteristics affecting leaf wetness."""
    stage: str  # e.g., "V6", "VT", "R1", "GS31", "GS65"
    lai: float  # Leaf Area Index (0-6)
    height_cm: float
    density: str  # "sparse", "moderate", "dense"


@dataclass
class LeafWetnessResult:
    """Leaf wetness estimation output."""
    timestamp: datetime
    wetness_hours: float  # Estimated hours of leaf wetness
    confidence: float  # 0-1
    # Contributing factors (e.g., "rain", "dew", "high_humidity")
    drivers: List[str]


@dataclass
class DiseaseRiskWindow:
    """Disease risk assessment for a time period."""
    period_start: datetime
    period_end: datetime
    disease: str
    risk_level: str  # "low", "moderate", "high", "critical"
    risk_score: float  # 0-1
    leaf_wetness_hours: float
    temp_favorability: float  # 0-1
    recommendation: str
    confidence: float  # 0-1
    data_gaps: List[str]


def calculate_dew_point(temp_c: float, rh_pct: float) -> float:
    """
    Calculate dew point temperature using Magnus formula.

    Args:
        temp_c: Air temperature (°C)
        rh_pct: Relative humidity (%)

    Returns:
        Dew point temperature (°C)
    """
    a = 17.27
    b = 237.7
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(rh_pct / 100.0)
    dew_point = (b * alpha) / (a - alpha)
    return dew_point


def estimate_leaf_wetness_duration(
    weather: WeatherConditions,
    canopy: CanopyState,
    prev_wetness_hours: float = 0.0
) -> LeafWetnessResult:
    """
    Estimate leaf wetness duration from weather and canopy state.

    Leaf wetness occurs when:
    1. Rain > 0.5mm
    2. Dew forms (temp near dew point + high RH + low wind)
    3. Residual from previous wetness event

    Args:
        weather: Current weather conditions
        canopy: Canopy state
        prev_wetness_hours: Carryover wetness from previous period

    Returns:
        LeafWetnessResult with wetness duration and confidence
    """
    drivers = []
    wetness_hours = 0.0
    confidence = 0.85

    # Calculate or use provided dew point
    if weather.dew_point_c is None:
        dew_point = calculate_dew_point(weather.temp_c, weather.rh_pct)
    else:
        dew_point = weather.dew_point_c

    # Factor 1: Rainfall wetness
    if weather.rain_mm > 0.5:
        # Rain intensity affects duration
        if weather.rain_mm > 5.0:
            wetness_hours += 6.0  # Heavy rain
        elif weather.rain_mm > 2.0:
            wetness_hours += 4.0  # Moderate rain
        else:
            wetness_hours += 2.0  # Light rain
        drivers.append("rain")

    # Factor 2: Dew formation
    temp_dew_diff = weather.temp_c - dew_point
    if temp_dew_diff < 2.0 and weather.rh_pct > 85.0 and weather.wind_ms < 2.5:
        # High probability of dew
        dew_hours = 8.0 - (temp_dew_diff * 2.0) - (weather.wind_ms * 1.5)
        dew_hours = max(0.0, min(dew_hours, 12.0))
        wetness_hours += dew_hours
        drivers.append("dew")

    # Factor 3: High humidity with dense canopy
    if weather.rh_pct > 90.0 and canopy.density in ["moderate", "dense"]:
        humidity_hours = (weather.rh_pct - 90.0) * \
            0.3  # Max ~3 hours at 100% RH
        humidity_hours *= (1.2 if canopy.density == "dense" else 1.0)
        wetness_hours += humidity_hours
        if "high_humidity" not in drivers:
            drivers.append("high_humidity")

    # Factor 4: Canopy structure modifiers
    # Dense canopy holds moisture longer
    if canopy.density == "dense" and canopy.lai > 3.0:
        wetness_hours *= 1.2
    elif canopy.density == "sparse":
        wetness_hours *= 0.8

    # Factor 5: Wind drying effect
    if weather.wind_ms > 3.0:
        drying_factor = 1.0 - (weather.wind_ms - 3.0) * \
            0.08  # Up to 40% reduction at 8 m/s
        drying_factor = max(0.6, drying_factor)
        wetness_hours *= drying_factor
        if "wind_drying" not in drivers:
            drivers.append("wind_drying")

    # Factor 6: Carryover from previous wetness
    if prev_wetness_hours > 0:
        decay_rate = 0.5  # 50% decay per hour (simplified)
        carryover = prev_wetness_hours * decay_rate
        wetness_hours += carryover

    # Cap at realistic maximum (24 hours in a day)
    wetness_hours = min(wetness_hours, 24.0)

    # Confidence adjustments
    if weather.dew_point_c is None:
        confidence *= 0.9  # Calculated dew point less certain
    if not drivers:
        confidence *= 0.7  # Low confidence if no clear drivers

    return LeafWetnessResult(
        timestamp=weather.timestamp,
        wetness_hours=round(wetness_hours, 1),
        confidence=round(confidence, 2),
        drivers=drivers
    )


def calculate_rolling_wetness(
    weather_history: List[WeatherConditions],
    canopy: CanopyState,
    window_hours: int = 24
) -> float:
    """
    Calculate cumulative leaf wetness over a rolling window.

    Args:
        weather_history: Hourly or sub-daily weather observations
        canopy: Canopy state
        window_hours: Rolling window size in hours

    Returns:
        Total wetness hours in the window
    """
    total_wetness = 0.0
    prev_wetness = 0.0

    for weather in weather_history[-window_hours:]:
        result = estimate_leaf_wetness_duration(weather, canopy, prev_wetness)
        total_wetness += result.wetness_hours
        prev_wetness = result.wetness_hours

    return min(total_wetness, window_hours)  # Can't exceed window size


# Disease-specific thresholds
DISEASE_MODELS: Dict[str, Dict] = {
    "late_blight_potato": {
        "pathogen": "Phytophthora infestans",
        "optimal_temp_c": (15, 25),
        "min_wetness_hours": 10,
        "critical_wetness_hours": 16,
        "rh_threshold": 90,
        "incubation_days": 5,
    },
    "early_blight_potato": {
        "pathogen": "Alternaria solani",
        "optimal_temp_c": (20, 30),
        "min_wetness_hours": 8,
        "critical_wetness_hours": 12,
        "rh_threshold": 85,
        "incubation_days": 7,
    },
    "gray_leaf_spot_maize": {
        "pathogen": "Cercospora zeae-maydis",
        "optimal_temp_c": (22, 30),
        "min_wetness_hours": 12,
        "critical_wetness_hours": 18,
        "rh_threshold": 90,
        "incubation_days": 10,
    },
    "fusarium_head_blight_wheat": {
        "pathogen": "Fusarium graminearum",
        "optimal_temp_c": (20, 28),
        "min_wetness_hours": 48,  # Needs extended wetness at flowering
        "critical_wetness_hours": 72,
        "rh_threshold": 85,
        "incubation_days": 7,
    },
    "rust_wheat": {
        "pathogen": "Puccinia spp.",
        "optimal_temp_c": (15, 25),
        "min_wetness_hours": 6,
        "critical_wetness_hours": 10,
        "rh_threshold": 95,
        "incubation_days": 7,
    },
    "powdery_mildew_wheat": {
        "pathogen": "Blumeria graminis",
        "optimal_temp_c": (15, 22),
        "min_wetness_hours": 0,  # Can spread without free water (unique)
        "critical_wetness_hours": 0,
        "rh_threshold": 70,  # Lower RH threshold
        "incubation_days": 7,
    },
}


def assess_disease_risk(
    disease_key: str,
    weather_history: List[WeatherConditions],
    canopy: CanopyState,
    crop_stage: str,
    window_hours: int = 72
) -> DiseaseRiskWindow:
    """
    Assess disease risk for a specific pathogen based on weather and canopy.

    Args:
        disease_key: Disease identifier from DISEASE_MODELS
        weather_history: Recent weather observations
        canopy: Current canopy state
        crop_stage: Crop development stage
        window_hours: Assessment window (hours)

    Returns:
        DiseaseRiskWindow with risk assessment
    """
    if disease_key not in DISEASE_MODELS:
        raise ValueError(f"Unknown disease: {disease_key}")

    model = DISEASE_MODELS[disease_key]
    data_gaps = []

    if not weather_history:
        return DiseaseRiskWindow(
            period_start=datetime.now() - timedelta(hours=window_hours),
            period_end=datetime.now(),
            disease=disease_key,
            risk_level="unknown",
            risk_score=0.0,
            leaf_wetness_hours=0.0,
            temp_favorability=0.0,
            recommendation="Insufficient weather data",
            confidence=0.1,
            data_gaps=["no_weather_data"]
        )

    # Calculate leaf wetness
    total_wetness = calculate_rolling_wetness(
        weather_history, canopy, window_hours)

    # Temperature favorability
    avg_temp = sum(
        w.temp_c for w in weather_history[-24:]) / len(weather_history[-24:])
    temp_opt_low, temp_opt_high = model["optimal_temp_c"]

    if temp_opt_low <= avg_temp <= temp_opt_high:
        temp_favorability = 1.0
    elif avg_temp < temp_opt_low:
        temp_favorability = max(0.0, 1.0 - (temp_opt_low - avg_temp) / 10.0)
    else:
        temp_favorability = max(0.0, 1.0 - (avg_temp - temp_opt_high) / 10.0)

    # RH check
    avg_rh = sum(
        w.rh_pct for w in weather_history[-24:]) / len(weather_history[-24:])
    rh_favorability = 1.0 if avg_rh >= model["rh_threshold"] else (
        avg_rh / model["rh_threshold"])

    # Calculate risk score
    crit_wet = model.get("critical_wetness_hours", 0) or 0
    # Some pathogens (e.g., powdery mildew) do not require free water. In such cases,
    # avoid division by zero and let wetness contribute modestly, scaled by RH favorability
    # so overall risk remains moderate/high under favorable RH/temperature but not "critical".
    if crit_wet <= 0:
        wetness_score = 0.4 * rh_favorability
    else:
        wetness_score = min(1.0, total_wetness / crit_wet)
    risk_score = (wetness_score * 0.5 + temp_favorability *
                  0.3 + rh_favorability * 0.2)

    # Risk level classification
    if risk_score >= 0.75:
        risk_level = "critical"
        recommendation = "High infection risk - scout within 24h, prepare fungicide application"
    elif risk_score >= 0.50:
        risk_level = "high"
        recommendation = f"Scout field within 48h - conditions favor {model['pathogen']}"
    elif risk_score >= 0.25:
        risk_level = "moderate"
        recommendation = "Monitor conditions - wetness approaching threshold"
    else:
        risk_level = "low"
        recommendation = "Conditions not favorable for infection"

    # Confidence based on data quality
    confidence = 0.85
    if len(weather_history) < window_hours / 2:
        data_gaps.append("incomplete_weather_history")
        confidence *= 0.7
    if any(w.dew_point_c is None for w in weather_history):
        confidence *= 0.9

    period_start = weather_history[0].timestamp
    period_end = weather_history[-1].timestamp

    return DiseaseRiskWindow(
        period_start=period_start,
        period_end=period_end,
        disease=disease_key,
        risk_level=risk_level,
        risk_score=round(risk_score, 2),
        leaf_wetness_hours=round(total_wetness, 1),
        temp_favorability=round(temp_favorability, 2),
        recommendation=recommendation,
        confidence=round(confidence, 2),
        data_gaps=data_gaps
    )


def get_crop_disease_susceptibility(
    crop: str,
    stage: str
) -> Dict[str, float]:
    """
    Get stage-specific disease susceptibility multipliers.

    Returns:
        Dict of disease_key -> susceptibility_multiplier (0-2.0)
    """
    susceptibility = {}

    if crop.lower() == "potato":
        if stage in ["tuber_initiation", "tuber_bulking"]:
            # Most vulnerable to late blight
            susceptibility["late_blight_potato"] = 1.8
            susceptibility["early_blight_potato"] = 1.3
        else:
            susceptibility["late_blight_potato"] = 1.0
            susceptibility["early_blight_potato"] = 1.0

    elif crop.lower() == "maize":
        if stage in ["V10", "VT", "R1"]:
            # Tasseling/silking vulnerable to gray leaf spot
            susceptibility["gray_leaf_spot_maize"] = 1.6
        else:
            susceptibility["gray_leaf_spot_maize"] = 1.0

    elif crop.lower() == "wheat":
        if stage in ["GS55", "GS65", "GS69"]:
            # Flowering stage - high FHB risk
            susceptibility["fusarium_head_blight_wheat"] = 2.0
            susceptibility["rust_wheat"] = 1.4
        elif stage in ["GS31", "GS39"]:
            # Stem elongation - rust susceptible
            susceptibility["rust_wheat"] = 1.5
            susceptibility["powdery_mildew_wheat"] = 1.3
        else:
            susceptibility["fusarium_head_blight_wheat"] = 0.8
            susceptibility["rust_wheat"] = 1.0
            susceptibility["powdery_mildew_wheat"] = 1.0

    return susceptibility


def generate_disease_windows_for_crop(
    crop: str,
    crop_stage: str,
    weather_history: List[WeatherConditions],
    canopy: CanopyState,
    window_hours: int = 72
) -> List[DiseaseRiskWindow]:
    """
    Generate disease risk assessments for all relevant diseases for a crop.

    Args:
        crop: Crop name
        crop_stage: Current development stage
        weather_history: Weather observations
        canopy: Canopy state
        window_hours: Assessment window

    Returns:
        List of disease risk windows, sorted by risk score (descending)
    """
    susceptibility = get_crop_disease_susceptibility(crop, crop_stage)
    risk_windows = []

    for disease_key, mult in susceptibility.items():
        if disease_key in DISEASE_MODELS:
            risk = assess_disease_risk(
                disease_key, weather_history, canopy, crop_stage, window_hours
            )
            # Adjust risk score by stage susceptibility
            risk.risk_score = min(1.0, risk.risk_score * mult)
            risk_windows.append(risk)

    # Sort by risk score (highest first)
    risk_windows.sort(key=lambda r: r.risk_score, reverse=True)
    return risk_windows
