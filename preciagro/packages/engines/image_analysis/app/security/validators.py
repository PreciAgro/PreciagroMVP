"""Validation and download helpers for remote image ingestion."""

from __future__ import annotations

import logging
from typing import Iterable, Optional
from urllib.parse import urlparse, parse_qs

import cv2
import numpy as np
import requests

from ..core import settings

LOGGER = logging.getLogger(__name__)


def validate_signed_url(url: str) -> None:
    """Ensure the URL matches allowed host and includes a signature/token parameter."""

    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError("Only http(s) URLs are supported for image ingestion.")

    allowed_hosts = [host.lower() for host in settings.ALLOWED_IMAGE_HOSTS]
    if allowed_hosts and (parsed.hostname or "").lower() not in allowed_hosts:
        raise ValueError("Host not allowed for image ingestion.")

    required_params: Iterable[str] = settings.SIGNED_URL_REQUIRED_PARAMS
    if required_params:
        query_map = parse_qs(parsed.query)
        if not any(param in query_map for param in required_params):
            raise ValueError("Signed URL missing required token parameter.")


def download_image_from_url(url: str) -> np.ndarray:
    """Download an image into an OpenCV matrix."""

    validate_signed_url(url)

    try:
        response = requests.get(url, timeout=settings.DOWNLOAD_TIMEOUT_SECONDS, stream=True)
    except requests.RequestException as exc:
        raise ValueError(f"Failed to download image: {exc}") from exc

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise ValueError(f"Image download failed: {exc}") from exc

    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > settings.MAX_DOWNLOAD_BYTES:
        raise ValueError("Remote image exceeds allowed size.")

    data = response.content
    if len(data) > settings.MAX_DOWNLOAD_BYTES:
        raise ValueError("Remote image exceeds allowed size.")

    np_buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Downloaded image could not be decoded.")

    return image
