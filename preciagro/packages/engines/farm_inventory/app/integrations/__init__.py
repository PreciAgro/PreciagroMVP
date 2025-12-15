"""Integration clients for other PreciAgro engines."""

from .crop_intelligence import CropIntelligenceClient
from .temporal_logic import TemporalLogicClient
from .diagnosis_recommendation import DiagnosisRecommendationClient

__all__ = [
    "CropIntelligenceClient",
    "TemporalLogicClient",
    "DiagnosisRecommendationClient",
]
