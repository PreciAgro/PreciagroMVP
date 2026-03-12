from __future__ import annotations

import pytest

from preciagro.packages.engines.image_analysis.app.core.config import settings
from preciagro.packages.engines.image_analysis.app.security.validators import validate_signed_url


def test_validate_signed_url_allows_listed_host(monkeypatch: pytest.MonkeyPatch) -> None:
    original_hosts = settings.ALLOWED_IMAGE_HOSTS.copy()
    original_params = settings.SIGNED_URL_REQUIRED_PARAMS.copy()
    try:
        settings.ALLOWED_IMAGE_HOSTS = ["signed.example.com"]
        settings.SIGNED_URL_REQUIRED_PARAMS = ["signature"]
        validate_signed_url("https://signed.example.com/path.png?signature=abc")
    finally:
        settings.ALLOWED_IMAGE_HOSTS = original_hosts
        settings.SIGNED_URL_REQUIRED_PARAMS = original_params


def test_validate_signed_url_rejects_missing_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    original_params = settings.SIGNED_URL_REQUIRED_PARAMS.copy()
    try:
        settings.SIGNED_URL_REQUIRED_PARAMS = ["token"]
        with pytest.raises(ValueError):
            validate_signed_url("https://signed.example.com/path.png")
    finally:
        settings.SIGNED_URL_REQUIRED_PARAMS = original_params
