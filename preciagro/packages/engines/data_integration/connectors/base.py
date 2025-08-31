# connectors/base.py
from abc import ABC, abstractmethod
from typing import Iterable, Dict, Any


class IngestConnector(ABC):
    """Abstract base for all connectors.

    Implementations should provide a `fetch` method that yields raw
    dictionary objects. The connector should be lightweight and not perform
    normalization itself — that responsibility belongs to the pipeline
    normalizers (see `pipeline/normalize_*`).

    Future work / TODOs:
    - Add an async version of this interface if connectors need to perform
        high-throughput async HTTP calls.
    - Standardize the cursor format so incremental syncs can be implemented
        consistently across connectors.
    """

    name: str

    @abstractmethod
    def fetch(self, *, cursor: Dict[str, Any] | None) -> Iterable[Dict[str, Any]]:
        """Yield raw dicts. Cursor lets you do incremental sync later."""
