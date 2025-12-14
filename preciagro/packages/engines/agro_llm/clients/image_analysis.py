"""Image Analysis Client Interface."""

import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ImageAnalysisClient(ABC):
    """Client interface for Image Analysis Engine."""
    
    def __init__(self, endpoint: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize image analysis client.
        
        Args:
            endpoint: Image analysis service endpoint
            api_key: API key if required
        """
        self.endpoint = endpoint
        self.api_key = api_key
        logger.info(f"ImageAnalysisClient initialized (endpoint={endpoint})")
    
    @abstractmethod
    async def analyze_image(
        self,
        image_id: str,
        crop_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze image for diseases, pests, etc.
        
        Args:
            image_id: Image identifier
            crop_type: Optional crop type hint
            
        Returns:
            Analysis results dictionary
        """
        pass
    
    async def analyze_images(
        self,
        image_ids: List[str],
        crop_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Analyze multiple images.
        
        Args:
            image_ids: List of image identifiers
            crop_type: Optional crop type hint
            
        Returns:
            List of analysis results
        """
        results = []
        for image_id in image_ids:
            try:
                result = await self.analyze_image(image_id, crop_type)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing image {image_id}: {e}")
                results.append({"error": str(e), "image_id": image_id})
        return results


class StubImageAnalysisClient(ImageAnalysisClient):
    """Stub implementation of Image Analysis Client."""
    
    async def analyze_image(
        self,
        image_id: str,
        crop_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Stub implementation."""
        logger.warning(f"Stub ImageAnalysisClient.analyze_image called for {image_id}")
        return {
            "image_id": image_id,
            "crop": crop_type or "unknown",
            "disease": None,
            "health_score": 0.8,
            "status": "stub"
        }
    
    async def analyze_images(
        self,
        image_ids: List[str],
        crop_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Stub implementation for multiple images."""
        return await super().analyze_images(image_ids, crop_type)

