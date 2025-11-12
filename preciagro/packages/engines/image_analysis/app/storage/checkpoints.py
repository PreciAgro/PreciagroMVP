"""Utilities for downloading and caching model checkpoints."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

import requests

from ..core import settings

LOGGER = logging.getLogger(__name__)


class CheckpointManager:
    """Resolves checkpoint URIs to local files, downloading when needed."""

    def __init__(self) -> None:
        self.cache_dir = Path(settings.CHECKPOINT_CACHE_DIR).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def resolve(self, weights_path: Optional[str], weights_uri: Optional[str]) -> Path:
        """Return a local filesystem path for the provided weights definition."""

        if not weights_path:
            if not weights_uri:
                msg = "Segmentation weights_path or weights_uri must be provided"
                raise ValueError(msg)
            weights_path = self._cache_from_uri(weights_uri)
            return Path(weights_path)

        normalized = self._normalize_path(weights_path)
        if normalized.exists():
            return normalized

        if not weights_uri:
            msg = f"Checkpoint not found locally ({normalized}) and no weights_uri provided"
            raise FileNotFoundError(msg)

        LOGGER.info("Downloading SAM2 checkpoint from %s", weights_uri)
        self._download(weights_uri, normalized)
        return normalized

    def _normalize_path(self, weights_path: str) -> Path:
        if weights_path.startswith("cache://"):
            relative = weights_path.replace("cache://", "", 1)
            return self.cache_dir / relative
        return Path(weights_path).resolve()

    def _cache_from_uri(self, uri: str) -> str:
        filename = hashlib.sha256(uri.encode()).hexdigest()[:12] + ".pt"
        target = self.cache_dir / filename
        if not target.exists():
            self._download(uri, target)
        return str(target)

    def _download(self, uri: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(uri, stream=True, timeout=60) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
