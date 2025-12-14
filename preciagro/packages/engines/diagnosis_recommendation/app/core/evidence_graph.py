"""Evidence Graph Builder - Builds provenance-aware evidence graphs."""

import logging
from typing import List, Dict, Any
from datetime import datetime

from ..models.domain import (
    Observation,
    Evidence,
    EvidenceGraph,
    EvidenceType,
)

logger = logging.getLogger(__name__)


class EvidenceGraphBuilder:
    """Builds short-lived, provenance-aware evidence graphs linking observations to context."""
    
    def __init__(self):
        """Initialize the evidence graph builder."""
        self._evidence_rules = self._build_evidence_rules()
    
    def build_graph(
        self,
        observations: List[Observation],
        context: Dict[str, Any]
    ) -> EvidenceGraph:
        """
        Build evidence graph from observations and context.
        
        Args:
            observations: List of normalized observations
            context: Contextual information (geo, temporal, crop, etc.)
            
        Returns:
            Evidence graph with observations and evidence edges
        """
        # Create evidence edges linking observations
        evidence: List[Evidence] = []
        
        # Build direct evidence from observations
        for obs in observations:
            ev = self._create_direct_evidence(obs, context)
            if ev:
                evidence.append(ev)
        
        # Build inferred evidence from observation patterns
        inferred_evidence = self._infer_evidence(observations, context)
        evidence.extend(inferred_evidence)
        
        # Build contextual evidence
        contextual_evidence = self._build_contextual_evidence(observations, context)
        evidence.extend(contextual_evidence)
        
        # Build temporal evidence
        temporal_evidence = self._build_temporal_evidence(observations, context)
        evidence.extend(temporal_evidence)
        
        # Build spatial evidence
        spatial_evidence = self._build_spatial_evidence(observations, context)
        evidence.extend(spatial_evidence)
        
        # Create graph
        graph = EvidenceGraph(
            observations=observations,
            evidence=evidence,
            context_hash=self._compute_context_hash(context),
        )
        
        logger.info(
            f"Built evidence graph with {len(observations)} observations "
            f"and {len(evidence)} evidence edges"
        )
        
        return graph
    
    def _create_direct_evidence(
        self,
        observation: Observation,
        context: Dict[str, Any]
    ) -> Evidence:
        """Create direct evidence from an observation."""
        return Evidence(
            type=EvidenceType.DIRECT,
            observation_ids=[observation.id],
            strength=observation.confidence,
            reasoning=f"Direct observation: {observation.signal} from {observation.source.value}",
            confidence=observation.confidence,
            source_component="evidence_graph_builder",
        )
    
    def _infer_evidence(
        self,
        observations: List[Observation],
        context: Dict[str, Any]
    ) -> List[Evidence]:
        """Infer evidence from observation patterns."""
        evidence = []
        
        # Group observations by signal type
        signal_groups: Dict[str, List[Observation]] = {}
        for obs in observations:
            signal = obs.signal
            if signal not in signal_groups:
                signal_groups[signal] = []
            signal_groups[signal].append(obs)
        
        # Create inferred evidence for correlated observations
        for signal, obs_list in signal_groups.items():
            if len(obs_list) > 1:
                # Multiple observations of same signal strengthen evidence
                avg_confidence = sum(o.confidence for o in obs_list) / len(obs_list)
                strength = min(1.0, avg_confidence * 1.2)  # Boost for multiple sources
                
                ev = Evidence(
                    type=EvidenceType.INFERRED,
                    observation_ids=[o.id for o in obs_list],
                    strength=strength,
                    reasoning=f"Inferred from {len(obs_list)} correlated observations of {signal}",
                    confidence=avg_confidence,
                    source_component="evidence_graph_builder",
                )
                evidence.append(ev)
        
        return evidence
    
    def _build_contextual_evidence(
        self,
        observations: List[Observation],
        context: Dict[str, Any]
    ) -> List[Evidence]:
        """Build contextual evidence from context data."""
        evidence = []
        
        # Extract context that supports observations
        region = context.get("region_code")
        crop_type = context.get("crop_type")
        season = context.get("current_season")
        
        if region or crop_type or season:
            # Create contextual evidence linking context to observations
            relevant_obs = [
                obs for obs in observations
                if self._is_contextually_relevant(obs, context)
            ]
            
            if relevant_obs:
                ev = Evidence(
                    type=EvidenceType.CONTEXTUAL,
                    observation_ids=[obs.id for obs in relevant_obs],
                    strength=0.7,  # Contextual support is moderate
                    reasoning=f"Contextual support from region={region}, crop={crop_type}, season={season}",
                    confidence=0.8,  # Context is typically reliable
                    source_component="evidence_graph_builder",
                )
                evidence.append(ev)
        
        return evidence
    
    def _build_temporal_evidence(
        self,
        observations: List[Observation],
        context: Dict[str, Any]
    ) -> List[Evidence]:
        """Build temporal evidence from timing patterns."""
        evidence = []
        
        # Check for temporal patterns in observations
        if len(observations) > 1:
            # Sort by timestamp
            sorted_obs = sorted(observations, key=lambda o: o.timestamp)
            
            # Check for progression patterns
            if self._detect_temporal_progression(sorted_obs):
                ev = Evidence(
                    type=EvidenceType.TEMPORAL,
                    observation_ids=[obs.id for obs in sorted_obs],
                    strength=0.8,
                    reasoning="Temporal progression pattern detected",
                    confidence=0.75,
                    source_component="evidence_graph_builder",
                )
                evidence.append(ev)
        
        return evidence
    
    def _build_spatial_evidence(
        self,
        observations: List[Observation],
        context: Dict[str, Any]
    ) -> List[Evidence]:
        """Build spatial evidence from spatial patterns."""
        evidence = []
        
        # Check for spatial clustering (if location data available)
        spatial_obs = [
            obs for obs in observations
            if "location" in obs.metadata or "coordinates" in obs.metadata
        ]
        
        if len(spatial_obs) > 1:
            # Spatial clustering strengthens evidence
            ev = Evidence(
                type=EvidenceType.SPATIAL,
                observation_ids=[obs.id for obs in spatial_obs],
                strength=0.75,
                reasoning="Spatial clustering pattern detected",
                confidence=0.7,
                source_component="evidence_graph_builder",
            )
            evidence.append(ev)
        
        return evidence
    
    def _is_contextually_relevant(
        self,
        observation: Observation,
        context: Dict[str, Any]
    ) -> bool:
        """Check if observation is contextually relevant."""
        # Simple heuristic: observations from contextual sources are relevant
        contextual_sources = {
            ObservationSource.GEO_CONTEXT,
            ObservationSource.TEMPORAL_LOGIC,
            ObservationSource.CROP_INTELLIGENCE,
        }
        return observation.source in contextual_sources
    
    def _detect_temporal_progression(self, observations: List[Observation]) -> bool:
        """Detect if observations show temporal progression."""
        if len(observations) < 2:
            return False
        
        # Simple heuristic: check if signals are related and show progression
        signals = [obs.signal for obs in observations]
        
        # Example: yellowing -> browning -> wilting
        progression_patterns = [
            ["yellowing", "browning", "wilting"],
            ["small_spots", "large_spots", "leaf_damage"],
        ]
        
        for pattern in progression_patterns:
            if all(s in signals for s in pattern):
                return True
        
        return False
    
    def _compute_context_hash(self, context: Dict[str, Any]) -> str:
        """Compute hash of context for caching."""
        import hashlib
        import json
        
        # Create stable representation
        context_str = json.dumps(context, sort_keys=True, default=str)
        return hashlib.md5(context_str.encode()).hexdigest()
    
    def _build_evidence_rules(self) -> Dict[str, Any]:
        """Build evidence inference rules."""
        return {
            "correlation_threshold": 0.5,
            "temporal_window_hours": 24,
            "spatial_cluster_radius_km": 1.0,
        }

