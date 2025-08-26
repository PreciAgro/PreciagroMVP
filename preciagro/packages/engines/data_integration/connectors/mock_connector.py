"""A simple mocked connector used for testing/demo as a second data source.

It implements the same interface as other connectors: `.fetch(cursor=..., lat=..., lon=..., scope=...)`
which yields raw dicts expected by normalizers.
"""
from typing import Iterable
import time


class MockConnector:
    def __init__(self, name: str = "mock.source"):
        self.name = name

    def fetch(self, *, cursor=None, lat=None, lon=None, scope=None, units=None) -> Iterable[dict]:
        # yield a single synthetic record
        ts = int(time.time())
        yield {"dt": ts, "temp": 25.0, "humidity": 40, "weather": [{"description": "mocked"}], "lat": lat or 0.0, "lon": lon or 0.0}
