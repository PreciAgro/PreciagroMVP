"""Input Harmonization Layer - Normalizes incoming signals into unified observations."""

import logging
from typing import List, Optional
from datetime import datetime

from ..models.domain import Observation, ObservationSource, ObservationType
from ..contracts.v1.schemas import DREInput

logger = logging.getLogger(__name__)


class InputHarmonizationLayer:
    """Normalizes incoming structured signals from upstream engines into unified observations."""
    
    def __init__(self):
        """Initialize the harmonization layer."""
        self._signal_mappings = self._build_signal_mappings()
    
    def harmonize(self, input_data: DREInput) -> List[Observation]:
        """
        Harmonize all input signals into unified observations.
        
        Args:
            input_data: Raw input from upstream engines
            
        Returns:
            List of normalized observations
        """
        observations: List[Observation] = []
        
        # Harmonize image analysis signals
        if input_data.image_analysis:
            for signal in input_data.image_analysis:
                obs = self._harmonize_image_analysis(signal, input_data)
                if obs:
                    observations.extend(obs)
        
        # Harmonize conversational NLP signals
        if input_data.conversational_nlp:
            obs = self._harmonize_conversational_nlp(input_data.conversational_nlp, input_data)
            if obs:
                observations.extend(obs)
        
        # Harmonize sensor signals
        if input_data.sensors:
            for signal in input_data.sensors:
                obs = self._harmonize_sensor(signal, input_data)
                if obs:
                    observations.append(obs)
        
        # Harmonize geo context signals
        if input_data.geo_context:
            obs = self._harmonize_geo_context(input_data.geo_context, input_data)
            if obs:
                observations.extend(obs)
        
        # Harmonize temporal logic signals
        if input_data.temporal_logic:
            obs = self._harmonize_temporal_logic(input_data.temporal_logic, input_data)
            if obs:
                observations.extend(obs)
        
        # Harmonize crop intelligence signals
        if input_data.crop_intelligence:
            obs = self._harmonize_crop_intelligence(input_data.crop_intelligence, input_data)
            if obs:
                observations.extend(obs)
        
        # Harmonize inventory signals
        if input_data.inventory:
            obs = self._harmonize_inventory(input_data.inventory, input_data)
            if obs:
                observations.extend(obs)
        
        # Harmonize farmer profile signals
        if input_data.farmer_profile:
            obs = self._harmonize_farmer_profile(input_data.farmer_profile, input_data)
            if obs:
                observations.extend(obs)
        
        logger.info(f"Harmonized {len(observations)} observations from input signals")
        return observations
    
    def _harmonize_image_analysis(
        self, signal, input_data: DREInput
    ) -> List[Observation]:
        """Harmonize image analysis signals."""
        observations = []
        
        for label, confidence in signal.confidence_scores.items():
            # Normalize label to standard signal name
            normalized_signal = self._normalize_visual_signal(label)
            
            obs = Observation(
                source=ObservationSource.IMAGE_ANALYSIS,
                type=ObservationType.VISUAL_SIGNAL,
                signal=normalized_signal,
                confidence=confidence,
                metadata={
                    "image_id": signal.image_id,
                    "original_label": label,
                    "visual_features": signal.visual_features,
                    **signal.metadata,
                },
                source_request_id=input_data.request_id,
            )
            observations.append(obs)
        
        return observations
    
    def _harmonize_conversational_nlp(
        self, signal, input_data: DREInput
    ) -> List[Observation]:
        """Harmonize conversational NLP signals."""
        observations = []
        
        # Extract symptoms as observations
        for symptom in signal.symptoms:
            normalized_symptom = self._normalize_symptom(symptom)
            obs = Observation(
                source=ObservationSource.CONVERSATIONAL_NLP,
                type=ObservationType.SYMPTOM,
                signal=normalized_symptom,
                confidence=signal.confidence,
                metadata={
                    "intent": signal.intent,
                    "entities": signal.entities,
                    "original_symptom": symptom,
                    **signal.metadata,
                },
                source_request_id=input_data.request_id,
            )
            observations.append(obs)
        
        return observations
    
    def _harmonize_sensor(self, signal, input_data: DREInput) -> Observation:
        """Harmonize sensor signals."""
        normalized_signal = self._normalize_sensor_signal(signal.sensor_type)
        
        return Observation(
            source=ObservationSource.SENSOR,
            type=ObservationType.ENVIRONMENTAL,
            signal=normalized_signal,
            confidence=0.9,  # Sensors typically have high confidence
            value=signal.value,
            unit=signal.unit,
            metadata={
                "sensor_id": signal.sensor_id,
                "sensor_type": signal.sensor_type,
                "timestamp": signal.timestamp.isoformat(),
                **signal.metadata,
            },
            source_request_id=input_data.request_id,
        )
    
    def _harmonize_geo_context(
        self, signal, input_data: DREInput
    ) -> List[Observation]:
        """Harmonize geo context signals."""
        observations = []
        
        # Extract soil observations
        if signal.soil_data:
            for key, value in signal.soil_data.items():
                if isinstance(value, (int, float)):
                    normalized_key = self._normalize_soil_property(key)
                    obs = Observation(
                        source=ObservationSource.GEO_CONTEXT,
                        type=ObservationType.CONTEXTUAL,
                        signal=normalized_key,
                        confidence=signal.confidence,
                        value=float(value),
                        metadata={
                            "region_code": signal.region_code,
                            "property": key,
                            **signal.metadata,
                        },
                        source_request_id=input_data.request_id,
                    )
                    observations.append(obs)
        
        return observations
    
    def _harmonize_temporal_logic(
        self, signal, input_data: DREInput
    ) -> List[Observation]:
        """Harmonize temporal logic signals."""
        observations = []
        
        if signal.growth_stage:
            obs = Observation(
                source=ObservationSource.TEMPORAL_LOGIC,
                type=ObservationType.TEMPORAL,
                signal="growth_stage",
                confidence=signal.confidence,
                metadata={
                    "growth_stage": signal.growth_stage,
                    "current_season": signal.current_season,
                    "timing_windows": signal.timing_windows,
                    **signal.metadata,
                },
                source_request_id=input_data.request_id,
            )
            observations.append(obs)
        
        return observations
    
    def _harmonize_crop_intelligence(
        self, signal, input_data: DREInput
    ) -> List[Observation]:
        """Harmonize crop intelligence signals."""
        observations = []
        
        # Extract health status
        if signal.health_status:
            obs = Observation(
                source=ObservationSource.CROP_INTELLIGENCE,
                type=ObservationType.CONTEXTUAL,
                signal="health_status",
                confidence=signal.confidence,
                metadata={
                    "health_status": signal.health_status,
                    "crop_type": signal.crop_type,
                    "variety": signal.variety,
                    "growth_stage": signal.growth_stage,
                    **signal.metadata,
                },
                source_request_id=input_data.request_id,
            )
            observations.append(obs)
        
        # Extract risks as observations
        for risk in signal.risks:
            risk_type = risk.get("type", "unknown_risk")
            normalized_risk = self._normalize_risk_signal(risk_type)
            obs = Observation(
                source=ObservationSource.CROP_INTELLIGENCE,
                type=ObservationType.ENVIRONMENTAL,
                signal=normalized_risk,
                confidence=risk.get("confidence", signal.confidence),
                metadata={
                    "risk": risk,
                    "crop_type": signal.crop_type,
                    **signal.metadata,
                },
                source_request_id=input_data.request_id,
            )
            observations.append(obs)
        
        return observations
    
    def _harmonize_inventory(
        self, signal, input_data: DREInput
    ) -> List[Observation]:
        """Harmonize inventory signals."""
        observations = []
        
        # Extract available inputs as observations
        for input_name, input_data_dict in signal.available_inputs.items():
            obs = Observation(
                source=ObservationSource.INVENTORY,
                type=ObservationType.INVENTORY,
                signal=f"available_{input_name}",
                confidence=1.0,  # Inventory is factual
                value=input_data_dict.get("quantity", 0.0),
                metadata={
                    "input_name": input_name,
                    "input_data": input_data_dict,
                    **signal.metadata,
                },
                source_request_id=input_data.request_id,
            )
            observations.append(obs)
        
        return observations
    
    def _harmonize_farmer_profile(
        self, signal, input_data: DREInput
    ) -> List[Observation]:
        """Harmonize farmer profile signals."""
        observations = []
        
        # Extract constraints as observations
        for constraint_key, constraint_value in signal.constraints.items():
            obs = Observation(
                source=ObservationSource.FARMER_PROFILE,
                type=ObservationType.CONTEXTUAL,
                signal=f"farmer_constraint_{constraint_key}",
                confidence=1.0,  # Farmer constraints are factual
                metadata={
                    "constraint_key": constraint_key,
                    "constraint_value": constraint_value,
                    "budget_class": signal.budget_class,
                    **signal.metadata,
                },
                source_request_id=input_data.request_id,
            )
            observations.append(obs)
        
        return observations
    
    def _build_signal_mappings(self) -> dict:
        """Build mappings for signal normalization."""
        return {
            # Visual signals
            "leaf_spot": "leaf_spot",
            "yellowing": "yellowing",
            "wilting": "wilting",
            "blight": "blight",
            "rust": "rust",
            "mildew": "mildew",
            # Symptoms
            "yellow leaves": "yellowing",
            "brown spots": "leaf_spot",
            # Sensor types
            "soil_moisture": "soil_moisture",
            "temperature": "temperature",
            "humidity": "humidity",
            # Soil properties
            "ph": "soil_ph",
            "organic_matter": "soil_organic_matter",
            "nitrogen": "soil_nitrogen",
        }
    
    def _normalize_visual_signal(self, label: str) -> str:
        """Normalize visual signal label to standard name."""
        label_lower = label.lower()
        return self._signal_mappings.get(label_lower, label_lower.replace(" ", "_"))
    
    def _normalize_symptom(self, symptom: str) -> str:
        """Normalize symptom description to standard signal."""
        symptom_lower = symptom.lower()
        return self._signal_mappings.get(symptom_lower, symptom_lower.replace(" ", "_"))
    
    def _normalize_sensor_signal(self, sensor_type: str) -> str:
        """Normalize sensor type to standard signal."""
        return self._signal_mappings.get(sensor_type.lower(), sensor_type.lower())
    
    def _normalize_soil_property(self, property_name: str) -> str:
        """Normalize soil property name to standard signal."""
        return self._signal_mappings.get(property_name.lower(), f"soil_{property_name.lower()}")
    
    def _normalize_risk_signal(self, risk_type: str) -> str:
        """Normalize risk type to standard signal."""
        return f"risk_{risk_type.lower().replace(' ', '_')}"

