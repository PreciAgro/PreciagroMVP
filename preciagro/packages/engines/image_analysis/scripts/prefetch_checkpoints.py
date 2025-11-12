"""Utility script to prefetch SAM2 checkpoints."""

from __future__ import annotations

from preciagro.packages.engines.image_analysis.app.core.registry import get_model_registry
from preciagro.packages.engines.image_analysis.app.storage.checkpoints import CheckpointManager


def main() -> None:
    manager = CheckpointManager()
    registry = get_model_registry()
    for crop, config in registry.crops.items():
        seg = config.segmentation
        if seg.enabled:
            manager.resolve(seg.weights_path, seg.weights_uri)
            print(f"[prefetch] ensured segmentation weights for crop={crop}")  # noqa: T201
        counting = config.counting
        if counting.enabled:
            manager.resolve(counting.weights_path, counting.weights_uri)
            print(f"[prefetch] ensured counting weights for crop={crop}")  # noqa: T201


if __name__ == "__main__":
    main()
