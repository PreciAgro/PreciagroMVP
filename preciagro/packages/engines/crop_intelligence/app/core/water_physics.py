"""
FAO-56 Penman-Monteith ET₀ and ETc calculation with soil water bucket model.
Replaces placeholder water logic with physics-based computation.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class WeatherDay:
    """Daily weather data for ET₀ calculation."""

    date: date
    tmax_c: float  # Max temperature °C
    tmin_c: float  # Min temperature °C
    rh_mean: float  # Mean relative humidity %
    wind_ms: float  # Wind speed at 2m height (m/s)
    rain_mm: float  # Daily rainfall mm
    radiation_mjm2: Optional[float] = None  # Solar radiation MJ/m²/day


@dataclass
class CropCoefficients:
    """Crop-specific Kc curves and parameters."""

    crop: str
    kc_ini: float  # Initial stage Kc
    kc_mid: float  # Mid-season Kc
    kc_end: float  # End-season Kc
    stage_lengths_days: List[int]  # [initial, dev, mid, late]


@dataclass
class SoilBucket:
    """Soil water bucket state."""

    whc_mm: float  # Water holding capacity (mm)
    current_mm: float  # Current water content (mm)
    uncertainty_pct: float = 15.0  # Uncertainty in WHC estimation


@dataclass
class WaterBalance:
    """Daily water balance output."""

    date: date
    et0_mm: float  # Reference ET
    etc_mm: float  # Crop ET
    kc: float  # Crop coefficient
    rain_mm: float
    irrigation_mm: float
    soil_mm: float  # Soil water content
    deficit_mm: float  # Water deficit
    confidence: float  # 0-1, based on data quality


# FAO-56 Crop Kc schedules (Zimbabwe/Poland typical)
CROP_KC_DATABASE: Dict[str, CropCoefficients] = {
    "maize": CropCoefficients(
        crop="maize",
        kc_ini=0.30,
        kc_mid=1.20,
        kc_end=0.60,
        stage_lengths_days=[25, 35, 40, 30],  # ~130 days total
    ),
    "wheat": CropCoefficients(
        crop="wheat",
        kc_ini=0.30,
        kc_mid=1.15,
        kc_end=0.40,
        stage_lengths_days=[20, 30, 50, 30],  # ~130 days
    ),
    "potato": CropCoefficients(
        crop="potato",
        kc_ini=0.50,
        kc_mid=1.15,
        kc_end=0.75,
        stage_lengths_days=[25, 30, 45, 25],  # ~125 days
    ),
    "tobacco": CropCoefficients(
        crop="tobacco",
        kc_ini=0.35,
        kc_mid=1.10,
        kc_end=0.90,
        stage_lengths_days=[30, 40, 40, 20],  # ~130 days
    ),
}


def calculate_et0_fao56(
    tmax_c: float,
    tmin_c: float,
    rh_mean: float,
    wind_ms: float,
    latitude: float,
    elevation_m: float,
    day_of_year: int,
    radiation_mjm2: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate reference evapotranspiration (ET₀) using FAO-56 Penman-Monteith.

    Returns:
        (et0_mm, confidence): ET₀ in mm/day and confidence score (0-1)
    """
    # Mean temperature
    tmean = (tmax_c + tmin_c) / 2.0

    # Atmospheric pressure (kPa) from elevation
    p = 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26

    # Psychrometric constant (kPa/°C)
    gamma = 0.000665 * p

    # Saturation vapor pressure (kPa)
    es_tmax = 0.6108 * math.exp((17.27 * tmax_c) / (tmax_c + 237.3))
    es_tmin = 0.6108 * math.exp((17.27 * tmin_c) / (tmin_c + 237.3))
    es = (es_tmax + es_tmin) / 2.0

    # Actual vapor pressure (kPa)
    ea = es * (rh_mean / 100.0)

    # Slope of vapor pressure curve (kPa/°C)
    delta = (4098.0 * es) / ((tmean + 237.3) ** 2)

    # Solar radiation (estimate if not provided)
    confidence = 1.0
    if radiation_mjm2 is None:
        # Hargreaves estimate (reduces confidence)
        ra = _extraterrestrial_radiation(latitude, day_of_year)
        radiation_mjm2 = 0.16 * math.sqrt(tmax_c - tmin_c) * ra
        confidence = 0.75  # Reduced confidence with estimated radiation

    # Net radiation (simplified, assuming Rs/Rso ≈ 0.7, albedo=0.23)
    rn = 0.77 * radiation_mjm2 - 0.0864 * (
        4.903e-9
        * ((tmax_c + 273.16) ** 4 + (tmin_c + 273.16) ** 4)
        / 2.0
        * (0.34 - 0.14 * math.sqrt(ea))
    )

    # Wind adjustment (if wind is missing, use default 2 m/s)
    if wind_ms <= 0:
        wind_ms = 2.0
        confidence *= 0.9

    # FAO-56 Penman-Monteith equation
    numerator = 0.408 * delta * rn + gamma * (900.0 / (tmean + 273.0)) * wind_ms * (es - ea)
    denominator = delta + gamma * (1.0 + 0.34 * wind_ms)

    et0 = numerator / denominator
    et0 = max(0.0, et0)  # ET₀ cannot be negative

    return et0, confidence


def _extraterrestrial_radiation(latitude: float, day_of_year: int) -> float:
    """Calculate extraterrestrial radiation Ra (MJ/m²/day) for solar estimation."""
    lat_rad = latitude * math.pi / 180.0
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
    delta = 0.409 * math.sin(2.0 * math.pi * day_of_year / 365.0 - 1.39)
    ws = math.acos(-math.tan(lat_rad) * math.tan(delta))
    ra = (
        (24.0 * 60.0 / math.pi)
        * 0.0820
        * dr
        * (
            ws * math.sin(lat_rad) * math.sin(delta)
            + math.cos(lat_rad) * math.cos(delta) * math.sin(ws)
        )
    )
    return max(0.0, ra)


def get_crop_kc(
    crop: str, planting_date: date, current_date: date, stage_override: Optional[str] = None
) -> Tuple[float, str, float]:
    """
    Get crop coefficient (Kc) for a given crop and date.

    Returns:
        (kc, stage_name, confidence): Kc value, stage name, and confidence
    """
    crop_lower = crop.lower()
    if crop_lower not in CROP_KC_DATABASE:
        # Unknown crop - return conservative mid-season Kc
        return 1.0, "unknown", 0.5

    kc_data = CROP_KC_DATABASE[crop_lower]
    days_since_planting = (current_date - planting_date).days

    # Stage boundaries
    stage_ends = [sum(kc_data.stage_lengths_days[: i + 1]) for i in range(4)]

    confidence = 1.0

    if days_since_planting < 0:
        return kc_data.kc_ini, "pre-plant", 0.3
    elif days_since_planting < stage_ends[0]:
        # Initial stage
        return kc_data.kc_ini, "initial", confidence
    elif days_since_planting < stage_ends[1]:
        # Development stage - linear interpolation
        days_into_stage = days_since_planting - stage_ends[0]
        stage_length = kc_data.stage_lengths_days[1]
        kc = kc_data.kc_ini + (kc_data.kc_mid - kc_data.kc_ini) * (days_into_stage / stage_length)
        return kc, "development", confidence
    elif days_since_planting < stage_ends[2]:
        # Mid-season stage
        return kc_data.kc_mid, "mid-season", confidence
    elif days_since_planting < stage_ends[3]:
        # Late season - linear interpolation
        days_into_stage = days_since_planting - stage_ends[2]
        stage_length = kc_data.stage_lengths_days[3]
        kc = kc_data.kc_mid - (kc_data.kc_mid - kc_data.kc_end) * (days_into_stage / stage_length)
        return kc, "late-season", confidence
    else:
        # Post-harvest
        return kc_data.kc_end, "post-harvest", 0.7


def run_soil_water_bucket(
    weather_history: List[WeatherDay],
    soil_bucket: SoilBucket,
    crop: str,
    planting_date: date,
    irrigation_history: Optional[List[Tuple[date, float]]] = None,
    latitude: float = -18.0,
    elevation_m: float = 1500.0,
) -> List[WaterBalance]:
    """
    Run soil water bucket model with FAO-56 ETc calculation.

    Args:
        weather_history: Daily weather data
        soil_bucket: Initial soil state (WHC, current water)
        crop: Crop name
        planting_date: Date of planting
        irrigation_history: List of (date, mm) irrigation events
        latitude: Field latitude (for ET₀)
        elevation_m: Field elevation (for ET₀)

    Returns:
        List of daily water balance records
    """
    irrigation_dict = {}
    if irrigation_history:
        irrigation_dict = {d: mm for d, mm in irrigation_history}

    results = []
    current_soil_mm = soil_bucket.current_mm

    for weather in weather_history:
        # Calculate ET₀
        et0, et0_conf = calculate_et0_fao56(
            tmax_c=weather.tmax_c,
            tmin_c=weather.tmin_c,
            rh_mean=weather.rh_mean,
            wind_ms=weather.wind_ms,
            latitude=latitude,
            elevation_m=elevation_m,
            day_of_year=weather.date.timetuple().tm_yday,
            radiation_mjm2=weather.radiation_mjm2,
        )

        # Get crop Kc
        kc, stage, kc_conf = get_crop_kc(crop, planting_date, weather.date)

        # Calculate ETc
        etc = et0 * kc

        # Get irrigation
        irrigation_mm = irrigation_dict.get(weather.date, 0.0)

        # Update soil bucket
        current_soil_mm += weather.rain_mm + irrigation_mm - etc
        current_soil_mm = max(0.0, min(current_soil_mm, soil_bucket.whc_mm))

        # Calculate deficit
        deficit_mm = soil_bucket.whc_mm - current_soil_mm

        # Overall confidence (product of component confidences)
        confidence = et0_conf * kc_conf * (1.0 - soil_bucket.uncertainty_pct / 100.0)

        results.append(
            WaterBalance(
                date=weather.date,
                et0_mm=round(et0, 2),
                etc_mm=round(etc, 2),
                kc=round(kc, 3),
                rain_mm=weather.rain_mm,
                irrigation_mm=irrigation_mm,
                soil_mm=round(current_soil_mm, 1),
                deficit_mm=round(deficit_mm, 1),
                confidence=round(confidence, 2),
            )
        )

    return results


def get_water_stress_level(
    current_soil_mm: float, whc_mm: float, crop_stage: str
) -> Tuple[str, float, str]:
    """
    Determine water stress level and irrigation recommendation.

    Returns:
        (stress_level, urgency_score, recommendation)
    """
    pct_available = (current_soil_mm / whc_mm) * 100.0

    # Critical thresholds vary by stage
    if crop_stage in ["development", "mid-season"]:
        # Water-sensitive stages
        if pct_available < 30:
            return (
                "severe",
                0.95,
                "Irrigate within 24h - critical water deficit during sensitive stage",
            )
        elif pct_available < 50:
            return "moderate", 0.70, "Plan irrigation within 3-5 days - soil moisture dropping"
        elif pct_available < 70:
            return "mild", 0.40, "Monitor closely - adequate but declining"
        else:
            return "none", 0.0, "Soil moisture adequate"
    else:
        # Less sensitive stages (initial, late-season)
        if pct_available < 25:
            return "severe", 0.85, "Irrigate soon - soil moisture very low"
        elif pct_available < 40:
            return "moderate", 0.60, "Consider irrigation within 5-7 days"
        elif pct_available < 60:
            return "mild", 0.30, "Soil moisture acceptable"
        else:
            return "none", 0.0, "Soil moisture adequate"


def estimate_irrigation_need(
    water_balance: List[WaterBalance], forecast_rain_mm: float, days_ahead: int = 7
) -> Tuple[float, str, float]:
    """
    Estimate irrigation amount needed based on recent deficit and forecast.

    Returns:
        (mm_needed, timing_advice, confidence)
    """
    if not water_balance:
        return 0.0, "Insufficient data", 0.1

    latest = water_balance[-1]
    recent_avg_etc = sum(wb.etc_mm for wb in water_balance[-7:]) / min(7, len(water_balance))

    # Projected deficit over next `days_ahead`
    projected_etc = recent_avg_etc * days_ahead
    projected_deficit = latest.deficit_mm + projected_etc - forecast_rain_mm

    if projected_deficit > 30:
        mm_needed = projected_deficit * 0.8  # 80% replacement
        timing = f"Apply {round(mm_needed)} mm before next ETc surge"
        confidence = latest.confidence * 0.85  # Forecast uncertainty
    elif projected_deficit > 15:
        mm_needed = projected_deficit * 0.6
        timing = f"Light irrigation (~{round(mm_needed)} mm) if rain doesn't arrive"
        confidence = latest.confidence * 0.75
    else:
        mm_needed = 0.0
        timing = "No irrigation needed - sufficient moisture expected"
        confidence = latest.confidence * 0.9

    return mm_needed, timing, confidence
