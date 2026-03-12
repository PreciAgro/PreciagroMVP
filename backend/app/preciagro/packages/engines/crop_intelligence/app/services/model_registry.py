from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import joblib


logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).resolve().parents[3] / "config" / "models.json"
ARTIFACT_ROOT = Path(__file__).resolve().parents[3]


class ModelManager:
    """Lightweight loader over the static JSON registry + on-disk artifacts."""

    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self.registry_path = registry_path
        self._registry = self._load_registry()

    @lru_cache(maxsize=32)
    def metadata(self, name: str) -> Optional[Dict[str, Any]]:
        for entry in self._registry.get("models", []):
            if entry["name"] == name:
                return entry
        return None

    def resolve_artifact(self, name: str) -> Optional[Path]:
        meta = self.metadata(name)
        if not meta:
            return None
        rel_path = meta.get("artifacts", {}).get("model_file")
        if not rel_path:
            return None
        return (ARTIFACT_ROOT / rel_path).resolve()

    @lru_cache(maxsize=8)
    def load_joblib(self, name: str):
        artifact = self.resolve_artifact(name)
        if not artifact or not artifact.exists():
            logger.warning("Artifact for model %s not found at %s", name, artifact)
            return None
        try:
            return joblib.load(artifact)
        except Exception:  # pragma: no cover - dependent on external files
            logger.exception("Failed to load model artifact %s", artifact)
            return None

    def _load_registry(self) -> Dict[str, Any]:
        if not self.registry_path.exists():  # pragma: no cover - env guard
            logger.warning("Model registry file missing: %s", self.registry_path)
            return {}
        with self.registry_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


model_manager = ModelManager()
