# connectors/http_json.py
import time

import httpx

from .base import IngestConnector


class HttpJsonConnector(IngestConnector):
    """Simple connector for HTTP JSON endpoints.

    This is useful for REST APIs that return JSON arrays or objects. It is
    intentionally synchronous; if you need high throughput consider an async
    variant that uses `httpx.AsyncClient`.

    TODOs:
    - Add optional pagination handling.
    - Add configurable retry/backoff using `tenacity` or httpx built-in retry.
    """

    def __init__(self, name, url, params=None, headers=None):
        self.name, self.url = name, url
        self.params, self.headers = params or {}, headers or {}

    def fetch(self, *, cursor=None):
        with httpx.Client(timeout=20) as c:
            resp = c.get(self.url, params=self.params, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            # If list: return directly; if dict: extract list part.
            items = data if isinstance(data, list) else data.get("results", [data])
            for it in items:
                yield it
        # Small throttle to avoid hammering endpoints. Replace with smarter
        # backoff/pacing if needed.
        time.sleep(0.05)
