"""Adapter interfaces for future ML model integration."""

from .base import BaseAdapter
from .cv_adapter import CVAdapter
from .nlp_adapter import NLPAdapter
from .llm_adapter import LLMAdapter
from .rl_adapter import RLAdapter
from .graph_adapter import GraphAdapter

__all__ = [
    "BaseAdapter",
    "CVAdapter",
    "NLPAdapter",
    "LLMAdapter",
    "RLAdapter",
    "GraphAdapter",
]

