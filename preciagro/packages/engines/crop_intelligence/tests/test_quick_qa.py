"""
Quick QA Tests for CIE MVP - Fuzz testing and boundary conditions.
Validates robustness before pilot launch.
"""

import pytest
from datetime import date, datetime, timedelta
from app.core.water_physics import (
    calculate_et0_fao56,
    get_crop_kc,
    run_soil_water_bucket,
    WeatherDay,
    SoilBucket,
    get_water_stress_level,
)
from app.core.disease_physics import (
    estimate_leaf_wetness_duration,
    assess_disease_risk,
    WeatherConditions,
    CanopyState,
)
from app.core.confidence import (
    calculate_state_confidence,
    calculate_model_confidence,
    calculate_data_quality_confidence,
    build_confidence_breakdown,
)


class TestWaterPhysicsFuzz:
    """Fuzz tests for water calculation module."""

    def test_et0_handles_missing_radiation(self):
        """ET₀ calculation should work with estimated radiation."""
        et0, conf = calculate_et0_fao56(
            tmax_c=30,
            tmin_c=18,
            rh_mean=70,
            wind_ms=2.5,
            latitude=-18.0,
            elevation_m=1500,
            day_of_year=350,
            radiation_mjm2=None,  # Missing - will estimate
        )
        assert et0 > 0
        assert conf < 1.0  # Reduced confidence
        assert conf >= 0.7

    def test_et0_handles_zero_wind(self):
        """ET₀ should default wind to 2.0 m/s when missing."""
        et0, conf = calculate_et0_fao56(
            tmax_c=28,
            tmin_c=16,
            rh_mean=65,
            wind_ms=0.0,
            latitude=-18.0,
            elevation_m=1500,
            day_of_year=1,
        )
        assert et0 > 0
        assert conf < 1.0

    def test_et0_extreme_temperatures(self):
        """ET₀ should handle extreme (but valid) temperatures."""
        # Hot
        et0_hot, _ = calculate_et0_fao56(
            tmax_c=45,
            tmin_c=30,
            rh_mean=20,
            wind_ms=5.0,
            latitude=0,
            elevation_m=100,
            day_of_year=180,
        )
        assert et0_hot > 8.0  # Very high ET

        # Cold
        et0_cold, _ = calculate_et0_fao56(
            tmax_c=5,
            tmin_c=-2,
            rh_mean=80,
            wind_ms=1.0,
            latitude=52,
            elevation_m=200,
            day_of_year=30,
        )
        assert et0_cold >= 0  # Should not be negative

    def test_kc_unknown_crop(self):
        """Unknown crop should return conservative Kc."""
        kc, stage, conf = get_crop_kc(
            crop="unknown_xyz", planting_date=date(2025, 11, 1), current_date=date(2025, 12, 15)
        )
        assert kc == 1.0
        assert stage == "unknown"
        assert conf == 0.5

    def test_water_stress_sensitive_stage(self):
        """Water stress should trigger critical alert during sensitive stages."""
        stress, urgency, rec = get_water_stress_level(
            current_soil_mm=35, whc_mm=140, crop_stage="mid-season"  # Water-sensitive
        )
        assert stress == "severe"
        assert urgency > 0.9
        assert "24h" in rec.lower()

    def test_soil_bucket_handles_no_rain(self):
        """Soil bucket should deplete without rain."""
        weather = [
            WeatherDay(
                date=date(2025, 12, i), tmax_c=32, tmin_c=20, rh_mean=60, wind_ms=3.0, rain_mm=0.0
            )
            for i in range(1, 8)
        ]
        bucket = SoilBucket(whc_mm=140, current_mm=100)

        results = run_soil_water_bucket(
            weather_history=weather,
            soil_bucket=bucket,
            crop="maize",
            planting_date=date(2025, 11, 10),
            latitude=-18.0,
        )

        # Soil moisture should decline
        assert results[-1].soil_mm < results[0].soil_mm
        assert results[-1].deficit_mm > results[0].deficit_mm


class TestDiseasePhysicsFuzz:
    """Fuzz tests for disease risk module."""

    def test_leaf_wetness_no_drivers(self):
        """Leaf wetness should be minimal with no rain/dew."""
        weather = WeatherConditions(
            timestamp=datetime.now(), temp_c=25, rh_pct=50, wind_ms=5.0, rain_mm=0.0
        )
        canopy = CanopyState(stage="V6", lai=2.5, height_cm=60, density="moderate")

        result = estimate_leaf_wetness_duration(weather, canopy)
        assert result.wetness_hours < 2.0
        assert result.confidence < 0.9

    def test_leaf_wetness_rain_event(self):
        """Heavy rain should produce significant wetness hours."""
        weather = WeatherConditions(
            timestamp=datetime.now(), temp_c=22, rh_pct=95, wind_ms=1.0, rain_mm=15.0
        )
        canopy = CanopyState(stage="R1", lai=5.0, height_cm=200, density="dense")

        result = estimate_leaf_wetness_duration(weather, canopy)
        assert result.wetness_hours >= 6.0
        assert "rain" in result.drivers

    def test_disease_risk_insufficient_data(self):
        """Disease assessment should handle empty weather history."""
        risk = assess_disease_risk(
            disease_key="late_blight_potato",
            weather_history=[],
            canopy=CanopyState(stage="tuber_bulking", lai=4.0, height_cm=50, density="dense"),
            crop_stage="tuber_bulking",
        )
        assert risk.risk_level == "unknown"
        assert risk.confidence < 0.2
        assert "no_weather_data" in risk.data_gaps

    def test_disease_risk_favorable_conditions(self):
        """Favorable conditions should trigger high risk."""
        # Simulate 72 hours of late blight-favorable weather
        weather_history = [
            WeatherConditions(
                timestamp=datetime.now() - timedelta(hours=72 - i),
                temp_c=20,
                rh_pct=95,
                wind_ms=1.5,
                rain_mm=2.0 if i % 24 == 0 else 0,
            )
            for i in range(72)
        ]
        canopy = CanopyState(stage="tuber_bulking", lai=4.5, height_cm=50, density="dense")

        risk = assess_disease_risk(
            disease_key="late_blight_potato",
            weather_history=weather_history,
            canopy=canopy,
            crop_stage="tuber_bulking",
        )
        assert risk.risk_level in ["high", "critical"]
        assert risk.risk_score > 0.60


class TestConfidencePlumbing:
    """Tests for confidence/uncertainty tracking."""

    def test_state_confidence_no_photo(self):
        """Missing photos should heavily penalize confidence."""
        conf, gaps = calculate_state_confidence(
            last_photo_date=None,
            current_date=date(2025, 12, 15),
            vi_history_days=14,
            ndvi_quality="good",
        )
        assert conf < 0.6
        assert any(g.category == "photo" and g.severity == "critical" for g in gaps)

    def test_state_confidence_stale_photo(self):
        """Old photos should moderately reduce confidence."""
        conf, gaps = calculate_state_confidence(
            last_photo_date=date(2025, 11, 1),
            current_date=date(2025, 12, 15),  # 44 days old
            vi_history_days=14,
            ndvi_quality="good",
        )
        assert conf < 0.85
        assert any(g.category == "photo" for g in gaps)

    def test_model_confidence_poor_validation(self):
        """Low validation metric should reduce confidence."""
        conf, explanation = calculate_model_confidence(
            model_type="yield",
            training_samples=300,
            validation_metric=0.55,  # Poor R²
            regional_match=True,
            crop_match=True,
        )
        assert conf < 0.75
        assert "validation" in explanation.lower()

    def test_data_quality_weather_gaps(self):
        """Weather gaps should reduce confidence."""
        conf, gaps = calculate_data_quality_confidence(
            weather_gaps_days=12,  # 12 missing days
            weather_last_update=datetime.now() - timedelta(hours=6),
            soil_data_source="soilgrids",
            action_log_completeness=0.80,
        )
        assert conf < 0.80
        assert any(g.category == "weather" for g in gaps)

    def test_confidence_breakdown_aggregation(self):
        """Overall confidence should be geometric mean of components."""
        breakdown = build_confidence_breakdown(
            state_conf=0.80,
            state_gaps=[],
            model_conf=0.75,
            model_explanation="Test model",
            data_quality=0.85,
            data_gaps=[],
        )
        # Formula: 0.8^0.4 × 0.75^0.3 × 0.85^0.3 ≈ 0.80
        assert 0.78 <= breakdown.overall <= 0.82


class TestBudgetConstraints:
    """Tests for budget-based action filtering (to be implemented)."""

    def test_low_budget_limits_actions(self):
        """Low budget should filter expensive multi-split N applications."""
        # TODO: Implement ranker integration
        pytest.skip("Budget ranker not yet implemented")

    def test_high_budget_allows_fungicide(self):
        """High budget should allow multiple fungicide applications."""
        pytest.skip("Budget ranker not yet implemented")


class TestEdgeCases:
    """Edge case validations."""

    def test_flat_ndvi_doesnt_crash(self):
        """Flat NDVI time-series should not cause errors."""
        # Simulate 30 days of identical NDVI (cloud cover, etc.)
        flat_ndvi = [0.35] * 30
        # Should handle gracefully (stage detector should use GDD fallback)
        pytest.skip("Stage detector integration test pending")

    def test_rainy_season_start_triggers_actions(self):
        """First rains should trigger N timing recommendations."""
        pytest.skip("Integration test - requires full action pipeline")

    def test_high_rh_no_leaf_wetness_still_disease_risk(self):
        """Powdery mildew should be detected even without leaf wetness."""
        weather_history = [
            WeatherConditions(
                timestamp=datetime.now() - timedelta(hours=72 - i),
                temp_c=18,
                rh_pct=75,
                wind_ms=2.0,
                rain_mm=0,
            )
            for i in range(72)
        ]
        canopy = CanopyState(stage="GS31", lai=3.0, height_cm=40, density="moderate")

        risk = assess_disease_risk(
            disease_key="powdery_mildew_wheat",
            weather_history=weather_history,
            canopy=canopy,
            crop_stage="GS31",
        )
        # Powdery mildew has lower RH threshold (70%) and no wetness requirement
        assert risk.risk_level in ["moderate", "high"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
