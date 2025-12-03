"""Central logging configuration producing JSON logs."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

class JSONLogFormatter(logging.Formatter):
    """Formatter that serializes log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "time": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
        }
        if isinstance(record.msg, dict):
            base.update(record.msg)
        else:
            base["message"] = record.getMessage()
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=True)


def configure_logging(debug: bool = False, service_name: str = "unknown") -> None:
    """Configure root logger once for the API process."""
    root = logging.getLogger()
    # If already configured, we might want to update level or just return.
    # For now, let's just return to avoid duplicate handlers.
    if getattr(configure_logging, "_configured", False):
        return

    level = logging.DEBUG if debug else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())
    root.handlers = [handler]
    root.setLevel(level)
    
    # Set some noisy libraries to WARNING
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    configure_logging._configured = True
