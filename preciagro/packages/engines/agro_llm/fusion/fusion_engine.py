"""Multi-modal Fusion Engine - Combines image, soil, weather data."""

import logging
from typing import Dict, Any, List, Optional

from ..contracts.v1.schemas import FarmerRequest, ImageFeature

logger = logging.getLogger(__name__)


class MultiModalFusionEngine:
    """Engine for fusing multi-modal inputs into unified context."""
    
    def __init__(self):
        """Initialize fusion engine."""
        logger.info("MultiModalFusionEngine initialized")
    
    def fuse(
        self,
        request: FarmerRequest,
        image_embeddings: Optional[List[List[float]]] = None,
        rag_context: Optional[Dict[str, Any]] = None,
        kg_context: Optional[Dict[str, Any]] = None,
        local_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fuse all inputs into unified context.
        
        Args:
            request: Original farmer request
            image_embeddings: Image embeddings from image analysis
            rag_context: RAG retrieval context
            kg_context: Knowledge graph context
            local_context: Local intelligence context
            
        Returns:
            Unified context dictionary
        """
        context = {
            "text": request.text,
            "geo": {
                "lat": request.geo.lat,
                "lon": request.geo.lon,
                "region_code": request.geo.region_code
            },
            "language": request.language,
            "modalities": {}
        }
        
        # Add image features
        if request.image_features:
            context["modalities"]["images"] = {
                "count": len(request.image_features),
                "features": [
                    {
                        "id": feat.id,
                        "embedding_dim": len(feat.embedding) if feat.embedding else 0,
                        "labels": feat.labels
                    }
                    for feat in request.image_features
                ]
            }
        
        # Add image embeddings if provided separately
        if image_embeddings:
            context["modalities"]["image_embeddings"] = {
                "count": len(image_embeddings),
                "dimension": len(image_embeddings[0]) if image_embeddings else 0
            }
        
        # Add soil data
        if request.soil:
            context["modalities"]["soil"] = {
                "pH": request.soil.pH,
                "moisture": request.soil.moisture,
                "organic_matter": request.soil.organic_matter,
                "nitrogen": request.soil.nitrogen,
                "phosphorus": request.soil.phosphorus,
                "potassium": request.soil.potassium
            }
        
        # Add weather data
        if request.weather:
            context["modalities"]["weather"] = {
                "temp": request.weather.temp,
                "humidity": request.weather.humidity,
                "rainfall": request.weather.rainfall,
                "wind_speed": request.weather.wind_speed,
                "forecast_days": request.weather.forecast_days
            }
        
        # Add crop data
        if request.crop:
            context["modalities"]["crop"] = {
                "type": request.crop.type,
                "variety": request.crop.variety,
                "growth_stage": request.crop.growth_stage,
                "planting_date": request.crop.planting_date
            }
        
        # Add RAG context
        if rag_context:
            context["rag"] = rag_context
        
        # Add KG context
        if kg_context:
            context["knowledge_graph"] = kg_context
        
        # Add local context
        if local_context:
            context["local"] = local_context
        
        # Add session context
        if request.session_context:
            context["session"] = [
                {
                    "message_id": ctx.message_id,
                    "intent": ctx.intent,
                    "entities": ctx.entities
                }
                for ctx in request.session_context
            ]
        
        logger.debug(f"Fused context with {len(context.get('modalities', {}))} modalities")
        
        return context





