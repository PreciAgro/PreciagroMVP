"""Ingest RAG docs into Qdrant (local or remote).

Usage:
  python scripts/ingest_rag_vector.py --index docs.json --host :memory:

Docs JSON structure:
[
  {"id": "doc1", "snippet": "text...", "keywords": ["maize", "planting"]}
]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from preciagro.packages.engines.conversational_nlp.services.embedding import Embedder


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_docs(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ingest(
    docs_path: str,
    host: str,
    port: int,
    api_key: str,
    collection: str,
    n_features: int = 512,
    model_name: str | None = None,
) -> None:
    client = QdrantClient(":memory:") if host == ":memory:" else QdrantClient(host=host, port=port, api_key=api_key or None)
    embedder = Embedder(n_features=n_features, model_name=model_name)
    docs = load_docs(docs_path)
    logger.info("Creating collection %s", collection)
    # Prime embedder to get actual dimension (esp. sentence-transformers)
    sample_vec = embedder.embed(docs[0].get("snippet", "") if docs else "")
    vector_dim = len(sample_vec) if sample_vec else embedder.vector_size
    client.recreate_collection(
        collection_name=collection,
        vectors_config=qmodels.VectorParams(size=vector_dim, distance=qmodels.Distance.COSINE),
    )
    points = []
    for idx, doc in enumerate(docs):
        payload = {
            "doc_id": doc.get("id") or f"doc-{idx}",
            "snippet": doc.get("snippet", ""),
            "keywords": doc.get("keywords", []),
        }
        vector = embedder.embed(payload["snippet"])
        points.append(qmodels.PointStruct(id=idx, vector=vector, payload=payload))
    client.upsert(collection_name=collection, points=points)
    logger.info("Ingested %d docs into %s", len(points), collection)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest RAG docs into Qdrant")
    parser.add_argument("--index", required=False, default="preciagro/packages/engines/conversational_nlp/data/rag_seed.json")
    parser.add_argument("--host", default=os.getenv("QDRANT_HOST", ":memory:"))
    parser.add_argument("--port", type=int, default=int(os.getenv("QDRANT_PORT", "6333")))
    parser.add_argument("--api-key", default=os.getenv("QDRANT_API_KEY", ""))
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "conversational_rag"))
    parser.add_argument("--n-features", type=int, default=512)
    parser.add_argument("--embedder-model", default=os.getenv("RAG_EMBEDDER_MODEL", "auto"))
    args = parser.parse_args()
    model_name = None if args.host == ":memory:" and args.embedder_model == "auto" else (None if args.embedder_model == "auto" else args.embedder_model)
    ingest(
        docs_path=args.index,
        host=args.host,
        port=args.port,
        api_key=args.api_key,
        collection=args.collection,
        n_features=args.n_features,
        model_name=model_name,
    )


if __name__ == "__main__":
    main()
