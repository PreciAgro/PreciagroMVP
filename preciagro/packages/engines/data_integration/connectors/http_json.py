# connectors/http_json.py
import httpx
import time
from .base import IngestConnector


class HttpJsonConnector(IngestConnector):
    def __init__(self, name, url, params=None, headers=None):
        self.name, self.url = name, url
        self.params, self.headers = params or {}, headers or {}

    def fetch(self, *, cursor=None):
        with httpx.Client(timeout=20) as c:
            resp = c.get(self.url, params=self.params, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            # If list: return directly; if dict: extract list part.
            items = data if isinstance(
                data, list) else data.get("results", [data])
            for it in items:
                yield it
        time.sleep(0.05)  # tiny throttle
