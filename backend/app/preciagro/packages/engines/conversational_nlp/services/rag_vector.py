"""Vector DB-backed retrieval using Qdrant (in-memory by default)."""

from __future__ import annotations

import logging
from typing import List, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
except Exception:  # noqa: BLE001
    QdrantClient = None  # type: ignore[assignment]
    qmodels = None  # type: ignore[assignment]

from ..models import Citation, IntentResult, ToolsContext
from .embedding import Embedder
from .rag import RAGRetriever

logger = logging.getLogger(__name__)


class VectorDBRetriever:
    """Retrieves passages from Qdrant; falls back to keyword retriever if unavailable."""

    def __init__(
        self,
        enabled: bool,
        top_k: int,
        index_path: Optional[str],
        host: str,
        port: int,
        api_key: str,
        collection: str,
        embedder_model: str | None,
    ) -> None:
        self.enabled = enabled
        self.top_k = top_k
        self.collection = collection
        self.embedder = Embedder(
            model_name=embedder_model,
            n_features=512,
        )
        # Force initialization to set vector size
        self.embedder.embed("init")
        self.keyword_fallback = RAGRetriever(enabled=True, top_k=top_k, index_path=index_path)

        if not enabled or QdrantClient is None or qmodels is None:
            self.client = None
            if enabled:
                logger.warning("Qdrant client unavailable; falling back to keyword retriever.")
            return

        try:
            if host == ":memory:":
                self.client = QdrantClient(":memory:")
            else:
                self.client = QdrantClient(host=host, port=port, api_key=api_key or None)
            self._ensure_collection()
            docs = self.keyword_fallback._load_index(index_path)  # type: ignore[attr-defined]
            self._upsert_docs(docs)
            logger.info("Vector retriever ready with %d docs", len(docs))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector DB retriever unavailable, using keyword fallback: %s", exc)
            self.client = None

    def _ensure_collection(self) -> None:
        """Create collection if it does not exist."""
        assert self.client is not None
        try:
            self.client.get_collection(self.collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(
                    size=self.embedder.vector_size, distance=qmodels.Distance.COSINE
                ),
            )

    def _upsert_docs(self, docs: List[dict]) -> None:
        """Embed and upsert docs into Qdrant."""
        if not self.client:
            return
        points = []
        for idx, doc in enumerate(docs):
            payload = {
                "doc_id": doc.get("id") or f"doc-{idx}",
                "snippet": doc.get("snippet", ""),
                "keywords": doc.get("keywords", []),
            }
            vector = self.embedder.embed(payload["snippet"])
            points.append(
                qmodels.PointStruct(
                    id=idx,
                    vector=vector,
                    payload=payload,
                )
            )
        if points:
            self.client.upsert(collection_name=self.collection, points=points)

    async def retrieve(
        self,
        intent: IntentResult,
        tools_context: ToolsContext,
        user_message: str,
    ) -> List[Citation]:
        """Retrieve citations using vector search or fallback."""
        if not self.enabled:
            return []
        if not self.client:
            return await self.keyword_fallback.retrieve(
                intent=intent,
                tools_context=tools_context,
                user_message=user_message,
            )

        keywords = self.keyword_fallback._collect_keywords(  # type: ignore[attr-defined]
            intent=intent,
            tools_context=tools_context,
            user_message=user_message,
        )
        query_text = " ".join(keywords) or intent.intent
        vector = self.embedder.embed(query_text)
        try:
            results = self.client.search(
                collection_name=self.collection,
                query_vector=vector,
                limit=self.top_k,
            )
            citations: List[Citation] = []
            for point in results:
                payload = point.payload or {}
                citations.append(
                    Citation(
                        source="rag",
                        id=str(payload.get("doc_id", payload.get("id", point.id))),
                        snippet=str(payload.get("snippet", "")),
                    )
                )
            if citations:
                return citations
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vector search failed, falling back to keyword retriever: %s", exc)

        return await self.keyword_fallback.retrieve(
            intent=intent,
            tools_context=tools_context,
            user_message=user_message,
        )
