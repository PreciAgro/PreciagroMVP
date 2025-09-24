"""Agricultural calendar composer - MVP with YAML rule loading."""
import os
import yaml
from typing import Dict, List, Optional
from datetime import datetime, date
from ..contracts.v1.fco import Calendars, CalendarWindow


class CalendarComposer:
    """Composes agricultural calendar from YAML rules - MVP stub."""

    def __init__(self):
        self.rules_path = os.path.join(os.path.dirname(__file__), "../rules/")
        self._rules_cache: Dict = {}

    async def compose(
        self,
        location: Dict[str, float],
        crop_type: str,
        climate_data: Dict
    ) -> Optional[Calendars]:
        """Compose calendar data for location and crop."""
        try:
            lat, lon = location["lat"], location["lon"]

            # Load crop rules from YAML
            crop_rules = await self._load_crop_rules(crop_type)
            if not crop_rules:
                return None

            # Determine climate zone
            climate_zone = self._determine_climate_zone(lat, lon, climate_data)

            # Get zone-specific rules
            zone_rules = crop_rules.get("zones", {}).get(climate_zone, {})

            # Generate calendar components
            planting_windows = self._generate_planting_windows(
                zone_rules, climate_data)
            irrigation_schedule = self._generate_irrigation_schedule(
                zone_rules, climate_data)
            no_spray_windows = self._generate_no_spray_windows(zone_rules)

            return Calendars(
                planting_windows=planting_windows,
                irrigation_baseline=irrigation_schedule,
                no_spray_windows=no_spray_windows
            )

        except Exception as e:
            print(f"Error composing calendar: {e}")
            return None

    async def _load_crop_rules(self, crop_type: str) -> Optional[Dict]:
        """Load crop rules from YAML file."""
        if crop_type in self._rules_cache:
            return self._rules_cache[crop_type]

        rules_file = os.path.join(
            self.rules_path, f"{crop_type.lower()}_rules.yaml")

        if not os.path.exists(rules_file):
            # Return default rules for MVP
            default_rules = self._get_default_rules(crop_type)
            self._rules_cache[crop_type] = default_rules
            return default_rules

        try:
            with open(rules_file, 'r') as f:
                rules = yaml.safe_load(f)
                self._rules_cache[crop_type] = rules
                return rules
        except Exception as e:
            print(f"Error loading rules for {crop_type}: {e}")
            return None

    def _determine_climate_zone(self, lat: float, lon: float, climate_data: Dict) -> str:
        """Determine climate zone based on location and climate data."""
        # Simple zone mapping for MVP
        if 49.0 <= lat <= 55.0 and 14.0 <= lon <= 24.5:
            return "temperate_continental"
        elif -22.5 <= lat <= -15.5 and 25.0 <= lon <= 33.5:
            return "tropical_savanna"
        else:
            return "temperate"

    def _generate_planting_windows(self, zone_rules: Dict, climate_data: Dict) -> List[CalendarWindow]:
        """Generate planting windows based on rules and climate."""
        windows = []
        planting_rules = zone_rules.get("planting", {})

        for window_name, window_rules in planting_rules.items():
            # Simple date calculation for MVP
            optimal_start = self._calculate_date(
                window_rules.get("optimal_start", "03-15"))
            optimal_end = self._calculate_date(
                window_rules.get("optimal_end", "04-30"))
            extended_end = self._calculate_date(
                window_rules.get("extended_end", "05-15"))

            windows.append(CalendarWindow(
                crop=window_name,
                activity="planting",
                window_start=optimal_start,
                window_end=optimal_end,
                notes=f"Extended end: {extended_end}, Confidence: {window_rules.get('confidence', 0.8)}"
            ))

        return windows

    def _generate_irrigation_schedule(self, zone_rules: Dict, climate_data: Dict) -> List[CalendarWindow]:
        """Generate irrigation schedule based on rules and ET0."""
        irrigation_rules = zone_rules.get("irrigation", {})
        if not irrigation_rules:
            return None

        # Use ET0 from climate data if available
        et0_weekly = climate_data.get(
            "et0_weekly_mm", 25.0)  # Default fallback

        weekly_mm = et0_weekly * irrigation_rules.get("et0_multiplier", 0.8)

        return [CalendarWindow(
            crop="irrigation",
            activity="irrigation",
            notes=f"Weekly baseline: {weekly_mm:.1f}mm, Method: {irrigation_rules.get('preferred_method', 'drip')}, Kc: {irrigation_rules.get('initial_kc', 0.6)}"
        )]

    def _generate_no_spray_windows(self, zone_rules: Dict) -> List[CalendarWindow]:
        """Generate no-spray windows from rules."""
        no_spray_rules = zone_rules.get("no_spray", [])
        windows = []

        for rule in no_spray_rules:
            windows.append(CalendarWindow(
                crop="no_spray",
                activity="restriction",
                window_start=self._calculate_date(rule.get("start", "06-01")),
                window_end=self._calculate_date(rule.get("end", "08-31")),
                notes=f"Reason: {rule.get('reason', 'environmental')}, Restrictions: {rule.get('restrictions', [])}"
            ))

        return windows

    def _calculate_date(self, date_str: str) -> date:
        """Convert MM-DD string to date object for current year."""
        try:
            month, day = map(int, date_str.split("-"))
            return date(datetime.now().year, month, day)
        except:
            return date.today()

    def _get_default_rules(self, crop_type: str) -> Dict:
        """Return default rules for a crop type - MVP stub."""
        if crop_type.lower() in ["corn", "maize"]:
            return {
                "zones": {
                    "temperate_continental": {
                        "planting": {
                            "primary": {
                                "optimal_start": "04-15",
                                "optimal_end": "05-15",
                                "extended_end": "06-01",
                                "confidence": 0.85
                            }
                        },
                        "irrigation": {
                            "et0_multiplier": 0.8,
                            "initial_kc": 0.5,
                            "efficiency": 0.75,
                            "preferred_method": "sprinkler"
                        },
                        "no_spray": [
                            {
                                "reason": "pollinator_protection",
                                "start": "06-01",
                                "end": "07-15",
                                "restrictions": ["neonicotinoids", "herbicides_flowering"]
                            }
                        ]
                    }
                }
            }
        else:
            # Generic crop rules
            return {
                "zones": {
                    "temperate": {
                        "planting": {
                            "spring": {
                                "optimal_start": "03-15",
                                "optimal_end": "04-30",
                                "extended_end": "05-15",
                                "confidence": 0.7
                            }
                        },
                        "irrigation": {
                            "et0_multiplier": 0.75,
                            "initial_kc": 0.6,
                            "efficiency": 0.7,
                            "preferred_method": "drip"
                        },
                        "no_spray": []
                    }
                }
            }
