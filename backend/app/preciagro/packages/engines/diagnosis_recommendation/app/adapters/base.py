"""Base adapter interface for ML model integration."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAdapter(ABC):
    """Base interface for all ML model adapters."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize adapter with configuration."""
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)

    @abstractmethod
    def is_available(self) -> bool:
        """Check if adapter is available and ready."""
        pass

    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results."""
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data format."""
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """Get adapter metadata."""
        return {
            "adapter_type": self.__class__.__name__,
            "enabled": self.enabled,
            "available": self.is_available() if self.enabled else False,
        }
