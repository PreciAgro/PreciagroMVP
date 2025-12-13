"""Engine-to-engine contracts for the Diagnosis & Recommendation Engine."""

from .v1 import (
    DREInput,
    DREResponse,
    ImageAnalysisSignal,
    ConversationalNLPSignal,
    SensorSignal,
    GeoContextSignal,
    TemporalLogicSignal,
    CropIntelligenceSignal,
    InventorySignal,
    FarmerProfileSignal,
)

__all__ = [
    "DREInput",
    "DREResponse",
    "ImageAnalysisSignal",
    "ConversationalNLPSignal",
    "SensorSignal",
    "GeoContextSignal",
    "TemporalLogicSignal",
    "CropIntelligenceSignal",
    "InventorySignal",
    "FarmerProfileSignal",
]

