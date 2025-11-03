"""Lightweight helpers for the data_integration package.

This file currently contains small stubs used for local development and
smoke-testing. It is intentionally simple so other parts of the system can
import the package without requiring network or DB access.

TODOs:
- Replace the stubs below with real integration helpers or remove this file
    once the package is fully wired into the application startup.
"""


def latest_weather(region: str) -> dict:
    """Return a tiny fake weather summary used by demos and tests.

    This is a stub. Real implementations should live in connectors/ and be
    exercised by the pipeline normalizers.
    """
    return {
        "tmax_c": 29.0 if region.startswith("zim") else 24.0,
        "rain_mm": 1.2 if region.startswith("pl") else 0.0,
    }
