"""Text embedder for RAG/vector store."""

from __future__ import annotations

import logging
from typing import List, Optional

from sklearn.feature_extraction.text import HashingVectorizer

logger = logging.getLogger(__name__)


class Embedder:
    """Sentence-transformers embedder with hashing fallback (no downloads)."""

    def __init__(self, n_features: int = 512, model_name: str | None = None) -> None:
        self.n_features = n_features
        self.model_name = model_name
        self._st_model: Optional[object] = None
        self.vectorizer: Optional[HashingVectorizer] = None
        self.vector_size: int = n_features
        self._init_models()

    def _init_models(self) -> None:
        """Try to load sentence-transformer; fallback to hashing."""
        if self.model_name:
            try:
                from sentence_transformers import SentenceTransformer

                self._st_model = SentenceTransformer(self.model_name)
                logger.info("Loaded sentence-transformer model: %s", self.model_name)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Sentence-transformer unavailable (%s); using hashing fallback", exc)

        self.vectorizer = HashingVectorizer(
            n_features=self.n_features, alternate_sign=False, norm="l2"
        )

    def embed(self, text: str) -> List[float]:
        """Return dense embedding vector."""
        if self._st_model:
            # type: ignore[operator]
            vec = self._st_model.encode([text or ""], normalize_embeddings=True)[0]
            self.vector_size = len(vec)
            return vec.tolist()
        if not self.vectorizer:
            self.vectorizer = HashingVectorizer(
                n_features=self.n_features, alternate_sign=False, norm="l2"
            )
        vec = self.vectorizer.transform([text or ""])
        arr = vec.toarray()[0]
        self.vector_size = len(arr)
        return arr.tolist()
