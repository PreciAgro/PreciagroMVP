from __future__ import annotations
from typing import List
from ..models.schemas import ActionOut


class DecisionRanker:
    """Ranks and filters action recommendations by impact score."""

    def rank(self, field_id: str, candidates: List[ActionOut]) -> List[ActionOut]:
        """Rank action candidates by impact score and return top 3.

        Args:
            field_id: Field identifier
            candidates: List of candidate actions

        Returns:
            list: Top 3 ranked actions
        """
        return sorted(candidates, key=lambda a: a.impact_score, reverse=True)[:3]


ranker = DecisionRanker()
