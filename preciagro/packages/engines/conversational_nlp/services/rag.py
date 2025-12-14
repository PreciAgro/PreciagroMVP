"""Simple retrieval layer for RAG integration with optional on-disk index."""

from __future__ import annotations

import json
import logging
import os
from typing import List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer

from ..models import Citation, IntentResult, ToolsContext

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Retrieves contextual passages; loads an optional JSON index or falls back to seed docs."""

    def __init__(self, enabled: bool, top_k: int = 3, index_path: str | None = None) -> None:
        self.enabled = enabled
        self.top_k = top_k
        self._docs = self._load_index(index_path) if index_path else self._seed_docs()
        self._vectorizer, self._doc_matrix = self._build_index(self._docs)

    async def retrieve(
        self,
        intent: IntentResult,
        tools_context: ToolsContext,
        user_message: str,
    ) -> List[Citation]:
        """Return citations if RAG is enabled."""
        if not self.enabled:
            return []

        keywords = self._collect_keywords(intent, tools_context, user_message)
        ranked = self._rank_docs(keywords)

        results = []
        for doc in ranked[: self.top_k]:
            results.append(
                Citation(
                    source="rag",
                    id=doc["id"],
                    snippet=doc["snippet"],
                )
            )
        return results

    @staticmethod
    def _collect_keywords(
        intent: IntentResult,
        tools_context: ToolsContext,
        user_message: str,
    ) -> List[str]:
        """Derive keywords from intent/entities plus user text and tool context."""
        kws = [intent.intent]
        ent = intent.entities
        for value in [
            ent.crop,
            ent.location,
            ent.field_name,
            ent.season_or_date,
            ent.problem_type,
        ]:
            if value:
                kws.extend(str(value).lower().split())
        if user_message:
            kws.extend(user_message.lower().split())
        region = tools_context.geo_context.get("region")
        if region:
            kws.extend(str(region).lower().split())
        return [kw for kw in kws if kw]

    def _rank_docs(self, query_keywords: List[str]) -> List[dict[str, str | List[str]]]:
        """Rank docs using TF-IDF similarity fallbacking to keyword overlap."""
        if not self._vectorizer or self._doc_matrix is None:
            return sorted(
                self._docs,
                key=lambda doc: self._score(doc["keywords"], query_keywords),
                reverse=True,
            )

        query_text = " ".join(query_keywords)
        if not query_text.strip():
            return self._docs

        query_vec = self._vectorizer.transform([query_text])
        scores = (self._doc_matrix * query_vec.T).toarray().ravel()
        scored = [(score, idx) for idx, score in enumerate(scores)]
        scored.sort(reverse=True, key=lambda x: x[0])
        return [self._docs[idx] for score, idx in scored if score > 0] or self._docs

    @staticmethod
    def _score(doc_keywords: List[str], query_keywords: List[str]) -> int:
        """Simple overlap score."""
        return sum(1 for kw in query_keywords if kw in doc_keywords)

    @staticmethod
    def _build_index(docs: List[dict[str, str | List[str]]]) -> Tuple[TfidfVectorizer | None, any]:
        """Build TF-IDF index over snippets."""
        if not docs:
            return None, None
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            texts = [str(doc["snippet"]) for doc in docs]
            matrix = vectorizer.fit_transform(texts)
            return vectorizer, matrix
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to build RAG TF-IDF index: %s", exc)
            return None, None

    @staticmethod
    def _load_index(index_path: str) -> List[dict[str, str | List[str]]]:
        """Load documents from a JSON/JSONL file."""
        if not index_path or not os.path.exists(index_path):
            logger.warning("RAG index not found at %s; using seed docs", index_path)
            return RAGRetriever._seed_docs()
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            docs = []
            for item in data:
                if not all(k in item for k in ("id", "snippet", "keywords")):
                    continue
                docs.append(
                    {
                        "id": str(item["id"]),
                        "keywords": [kw.lower() for kw in item.get("keywords", [])],
                        "snippet": str(item["snippet"]),
                    }
                )
            if not docs:
                logger.warning("RAG index empty at %s; using seed docs", index_path)
                return RAGRetriever._seed_docs()
            logger.info("Loaded %d RAG docs from %s", len(docs), index_path)
            return docs
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load RAG index: %s; using seed docs", exc)
            return RAGRetriever._seed_docs()

    @staticmethod
    def _seed_docs() -> List[dict[str, str | List[str]]]:
        """Seed minimal documents to exercise retrieval flow."""
        return [
            {
                "id": "zim_maize_window",
                "keywords": ["plan_planting", "maize", "zimbabwe", "plant", "window"],
                "snippet": "For central Zimbabwe, plant maize between mid-November and early December when soil moisture is adequate.",
            },
            {
                "id": "pesticide_label_safety",
                "keywords": ["diagnose_disease", "spray", "safety", "wind"],
                "snippet": "Always follow pesticide labels and local regulations; avoid spraying during high wind or temperature inversions.",
            },
            {
                "id": "inventory_best_practice",
                "keywords": ["inventory_status", "stock", "inputs"],
                "snippet": "Track seed and fertilizer stock weekly; reorder when below two-week buffer.",
            },
        ]
