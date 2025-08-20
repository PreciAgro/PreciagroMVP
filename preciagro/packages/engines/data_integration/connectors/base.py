# connectors/base.py
from abc import ABC, abstractmethod
from typing import Iterable, Dict, Any


class IngestConnector(ABC):
    name: str

    @abstractmethod
    def fetch(self, *, cursor: Dict[str, Any] | None) -> Iterable[Dict[str, Any]]:
        """Yield raw dicts. Cursor lets you do incremental sync later."""
