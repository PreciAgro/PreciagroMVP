"""Reasoning Graph Engine - Validates LLM output for contradictions and safety."""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ReasoningNode:
    """Node in the reasoning graph."""
    
    id: str
    type: str  # "fact", "inference", "action", "constraint"
    content: str
    confidence: float
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningGraph:
    """Reasoning graph structure."""
    
    nodes: List[ReasoningNode] = field(default_factory=list)
    edges: List[tuple[str, str, str]] = field(default_factory=list)  # (from, to, relation)
    violations: List[str] = field(default_factory=list)
    
    def add_node(self, node: ReasoningNode) -> None:
        """Add a node to the graph."""
        self.nodes.append(node)
    
    def add_edge(self, from_id: str, to_id: str, relation: str) -> None:
        """Add an edge to the graph."""
        self.edges.append((from_id, to_id, relation))
    
    def validate(self) -> bool:
        """Validate the graph for contradictions and violations."""
        self.violations = []
        
        # Check for contradictions
        self._check_contradictions()
        
        # Check for illegal actions
        self._check_illegal_actions()
        
        # Check for unsafe sequences
        self._check_unsafe_sequences()
        
        return len(self.violations) == 0
    
    def _check_contradictions(self) -> None:
        """Check for contradictory statements."""
        facts = [n for n in self.nodes if n.type == "fact"]
        
        # Simple contradiction detection (can be enhanced)
        fact_contents = {}
        for fact in facts:
            key = fact.content.lower().strip()
            if key in fact_contents:
                self.violations.append(f"Contradiction detected: {fact.content} vs {fact_contents[key].content}")
            fact_contents[key] = fact
    
    def _check_illegal_actions(self) -> None:
        """Check for illegal actions."""
        actions = [n for n in self.nodes if n.type == "action"]
        
        illegal_keywords = ["banned", "prohibited", "illegal", "restricted"]
        for action in actions:
            content_lower = action.content.lower()
            for keyword in illegal_keywords:
                if keyword in content_lower:
                    self.violations.append(f"Illegal action detected: {action.content}")
                    break
    
    def _check_unsafe_sequences(self) -> None:
        """Check for unsafe action sequences."""
        actions = [n for n in self.nodes if n.type == "action"]
        
        # Check for dangerous sequences (e.g., pesticide immediately after fertilizer)
        unsafe_patterns = [
            ("pesticide", "fertilizer"),
            ("herbicide", "planting"),
        ]
        
        action_contents = [a.content.lower() for a in actions]
        for pattern in unsafe_patterns:
            if pattern[0] in " ".join(action_contents) and pattern[1] in " ".join(action_contents):
                self.violations.append(f"Unsafe sequence detected: {pattern[0]} followed by {pattern[1]}")


class ReasoningGraphEngine:
    """Engine for validating and constructing reasoning graphs."""
    
    def __init__(self, strict_mode: bool = True):
        """Initialize RGE.
        
        Args:
            strict_mode: If True, reject graphs with violations
        """
        self.strict_mode = strict_mode
        logger.info(f"ReasoningGraphEngine initialized (strict_mode={strict_mode})")
    
    def validate_output(
        self,
        llm_output: Dict[str, Any],
        request_context: Optional[Dict[str, Any]] = None
    ) -> ReasoningGraph:
        """Validate LLM output and construct reasoning graph.
        
        Args:
            llm_output: Raw LLM output dictionary
            request_context: Original request context
            
        Returns:
            Validated reasoning graph
        """
        graph = ReasoningGraph()
        
        # Extract nodes from LLM output
        self._extract_nodes(llm_output, graph)
        
        # Build edges based on dependencies
        self._build_edges(graph)
        
        # Validate graph
        is_valid = graph.validate()
        
        if not is_valid and self.strict_mode:
            logger.warning(f"Reasoning graph validation failed: {graph.violations}")
            # In strict mode, we might want to reject or modify the output
            # For now, we log warnings but still return the graph
        
        return graph
    
    def _extract_nodes(self, output: Dict[str, Any], graph: ReasoningGraph) -> None:
        """Extract reasoning nodes from LLM output."""
        # Extract facts
        if "evidence" in output:
            for i, evidence in enumerate(output["evidence"]):
                node = ReasoningNode(
                    id=f"fact_{i}",
                    type="fact",
                    content=str(evidence),
                    confidence=0.8,
                    metadata={"source": "llm_output"}
                )
                graph.add_node(node)
        
        # Extract actions
        if "actions" in output:
            for i, action in enumerate(output.get("actions", [])):
                action_text = action.get("action", str(action)) if isinstance(action, dict) else str(action)
                node = ReasoningNode(
                    id=f"action_{i}",
                    type="action",
                    content=action_text,
                    confidence=action.get("confidence", 0.7) if isinstance(action, dict) else 0.7,
                    metadata={"source": "llm_output", "action_data": action}
                )
                graph.add_node(node)
        
        # Extract inferences
        if "rationales" in output:
            for i, rationale in enumerate(output.get("rationales", [])):
                node = ReasoningNode(
                    id=f"inference_{i}",
                    type="inference",
                    content=str(rationale),
                    confidence=0.75,
                    metadata={"source": "llm_output"}
                )
                graph.add_node(node)
    
    def _build_edges(self, graph: ReasoningGraph) -> None:
        """Build edges between nodes based on dependencies."""
        # Simple edge building: connect facts to inferences, inferences to actions
        facts = [n for n in graph.nodes if n.type == "fact"]
        inferences = [n for n in graph.nodes if n.type == "inference"]
        actions = [n for n in graph.nodes if n.type == "action"]
        
        # Connect facts to inferences
        for inference in inferences:
            for fact in facts:
                graph.add_edge(fact.id, inference.id, "supports")
        
        # Connect inferences to actions
        for action in actions:
            for inference in inferences:
                graph.add_edge(inference.id, action.id, "justifies")





