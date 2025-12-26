from __future__ import annotations

from typing import Optional

from .http import BaseServiceClient


class ImageAnalysisClient(BaseServiceClient):
    def classify_stage(self, photo_uri: str, crop: str) -> Optional[dict]:
        payload = {"uri": photo_uri, "crop": crop}
        return self._request("POST", "/image-analysis/stage", json=payload)
