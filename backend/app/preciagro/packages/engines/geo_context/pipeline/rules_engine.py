"""Rules engine for agricultural recommendations."""

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ..contracts.v1.fco import ClimateData, SoilData


class RulesEngine:
    """Applies agricultural rules for recommendations."""

    def __init__(self):
        self.planting_rules = None
        self.spray_rules = None
        self._load_rules()

    def _load_rules(self):
        """Load rules from YAML files."""
        try:
            rules_dir = Path(__file__).parent.parent / "rules"

            planting_file = rules_dir / "planting_rules.yaml"
            if planting_file.exists():
                with open(planting_file, "r") as f:
                    self.planting_rules = yaml.safe_load(f)

            spray_file = rules_dir / "spray_rules.yaml"
            if spray_file.exists():
                with open(spray_file, "r") as f:
                    self.spray_rules = yaml.safe_load(f)

        except Exception as e:
            print(f"Error loading rules: {e}")

    async def get_planting_recommendations(
        self,
        location: Dict[str, float],
        soil: Optional[SoilData],
        climate: Optional[ClimateData],
        crop_types: List[str],
    ) -> List[Dict]:
        """Get planting recommendations based on rules."""
        recommendations = []

        if not self.planting_rules or not crop_types:
            return recommendations

        for crop_type in crop_types:
            crop_rules = self.planting_rules.get("crops", {}).get(crop_type)
            if not crop_rules:
                continue

            # Evaluate soil conditions
            soil_score = self._evaluate_soil_conditions(soil, crop_rules.get("soil", {}))

            # Evaluate climate conditions
            climate_score = self._evaluate_climate_conditions(
                climate, crop_rules.get("climate", {})
            )

            # Overall recommendation
            overall_score = (soil_score + climate_score) / 2

            if overall_score > 0.5:  # Threshold for recommendation
                recommendations.append(
                    {
                        "crop_type": crop_type,
                        "recommendation": "suitable",
                        "confidence": overall_score,
                        "soil_suitability": soil_score,
                        "climate_suitability": climate_score,
                        "notes": self._generate_planting_notes(soil, climate, crop_rules),
                    }
                )

        return recommendations

    async def get_spray_recommendations(
        self,
        location: Dict[str, float],
        climate: Optional[ClimateData],
        crop_types: List[str],
    ) -> List[Dict]:
        """Get spray recommendations based on rules."""
        recommendations = []

        if not self.spray_rules or not climate:
            return recommendations

        spray_conditions = self.spray_rules.get("conditions", {})

        # Check wind speed
        wind_suitable = True
        if climate.wind_speed is not None:
            max_wind = spray_conditions.get("max_wind_speed", 15)  # km/h
            wind_suitable = climate.wind_speed <= max_wind

        # Check temperature
        temp_suitable = True
        if climate.temperature_avg is not None:
            min_temp = spray_conditions.get("min_temperature", 5)
            max_temp = spray_conditions.get("max_temperature", 30)
            temp_suitable = min_temp <= climate.temperature_avg <= max_temp

        # Check humidity
        humidity_suitable = True
        if climate.humidity is not None:
            min_humidity = spray_conditions.get("min_humidity", 40)
            humidity_suitable = climate.humidity >= min_humidity

        # Overall suitability
        if wind_suitable and temp_suitable and humidity_suitable:
            recommendations.append(
                {
                    "recommendation": "favorable_conditions",
                    "confidence": 0.9,
                    "conditions": {
                        "wind_suitable": wind_suitable,
                        "temperature_suitable": temp_suitable,
                        "humidity_suitable": humidity_suitable,
                    },
                    "notes": "Current conditions are favorable for spraying operations",
                }
            )
        else:
            recommendations.append(
                {
                    "recommendation": "unfavorable_conditions",
                    "confidence": 0.8,
                    "conditions": {
                        "wind_suitable": wind_suitable,
                        "temperature_suitable": temp_suitable,
                        "humidity_suitable": humidity_suitable,
                    },
                    "notes": "Current conditions are not ideal for spraying",
                }
            )

        return recommendations

    def _evaluate_soil_conditions(self, soil: Optional[SoilData], soil_rules: Dict) -> float:
        """Evaluate soil conditions against rules."""
        if not soil or not soil_rules:
            return 0.5  # Neutral score

        score = 0.0
        criteria_count = 0

        # Check pH
        if soil.ph is not None and "ph_range" in soil_rules:
            ph_min, ph_max = soil_rules["ph_range"]
            if ph_min <= soil.ph <= ph_max:
                score += 1.0
            else:
                # Partial score based on distance from optimal range
                optimal_ph = (ph_min + ph_max) / 2
                distance = abs(soil.ph - optimal_ph)
                score += max(0, 1 - distance / 2)
            criteria_count += 1

        # Check organic matter
        if soil.organic_matter is not None and "min_organic_matter" in soil_rules:
            min_om = soil_rules["min_organic_matter"]
            score += 1.0 if soil.organic_matter >= min_om else soil.organic_matter / min_om
            criteria_count += 1

        return score / max(criteria_count, 1)

    def _evaluate_climate_conditions(
        self, climate: Optional[ClimateData], climate_rules: Dict
    ) -> float:
        """Evaluate climate conditions against rules."""
        if not climate or not climate_rules:
            return 0.5  # Neutral score

        score = 0.0
        criteria_count = 0

        # Check temperature
        if climate.temperature_avg is not None and "temperature_range" in climate_rules:
            temp_min, temp_max = climate_rules["temperature_range"]
            if temp_min <= climate.temperature_avg <= temp_max:
                score += 1.0
            else:
                # Partial score
                optimal_temp = (temp_min + temp_max) / 2
                distance = abs(climate.temperature_avg - optimal_temp)
                score += max(0, 1 - distance / 10)
            criteria_count += 1

        # Check growing degree days
        if climate.growing_degree_days is not None and "min_gdd" in climate_rules:
            min_gdd = climate_rules["min_gdd"]
            score += 1.0 if climate.growing_degree_days >= min_gdd else 0.5
            criteria_count += 1

        return score / max(criteria_count, 1)

    def _generate_planting_notes(
        self, soil: Optional[SoilData], climate: Optional[ClimateData], rules: Dict
    ) -> str:
        """Generate planting notes based on conditions."""
        notes = []

        if soil and soil.ph is not None:
            if soil.ph < 6.0:
                notes.append("Consider lime application to raise pH")
            elif soil.ph > 8.0:
                notes.append("Soil pH is high, monitor nutrient availability")

        if climate and climate.temperature_avg is not None:
            if climate.temperature_avg < 10:
                notes.append("Temperatures may be too low for optimal growth")
            elif climate.temperature_avg > 30:
                notes.append("High temperatures may stress plants")

        return "; ".join(notes) if notes else "No specific recommendations"
