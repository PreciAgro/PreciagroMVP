"""Agro LLM Engine - Core agricultural language model."""

from typing import Dict, Any, Optional

from .pipeline import AgroLLMPipeline
from .contracts.v1.schemas import FarmerRequest, AgroLLMResponse
from .config import ConfigLoader, AgroLLMConfig

# Global pipeline instance (lazy initialization)
_pipeline: Optional[AgroLLMPipeline] = None


def get_pipeline(config: Optional[AgroLLMConfig] = None) -> AgroLLMPipeline:
    """Get or create pipeline instance.
    
    Args:
        config: Optional configuration (if None, loads from default)
        
    Returns:
        AgroLLMPipeline instance
    """
    global _pipeline
    if _pipeline is None:
        if config is None:
            config_loader = ConfigLoader()
            config = config_loader.load()
        _pipeline = AgroLLMPipeline(config=config)
    return _pipeline


async def run(data: Dict[str, Any]) -> Dict[str, Any]:
    """Run agro LLM engine (legacy interface).
    
    Args:
        data: Input data containing prompts, context, etc.
        
    Returns:
        Dictionary with LLM responses and generated content.
    """
    pipeline = get_pipeline()
    try:
        response = await pipeline.process_request(data)
        return response.model_dump()
    except Exception as e:
        return {
            'engine': 'agro_llm',
            'status': 'error',
            'error': str(e),
            'message': 'Error processing request'
        }


def status() -> Dict[str, Any]:
    """Get engine status.
    
    Returns:
        Dictionary with engine state information.
    """
    pipeline = get_pipeline()
    return {
        'engine': 'agro_llm',
        'state': 'active' if pipeline is not None else 'idle',
        'version': '1.0.0',
        'implemented': True,
        'config': {
            'model_mode': pipeline.config.model_provider.mode if pipeline else None,
            'features': {
                'rag': pipeline.config.feature_flags.enable_rag if pipeline else False,
                'kg': pipeline.config.feature_flags.enable_kg if pipeline else False,
                'local': pipeline.config.feature_flags.use_local if pipeline else False
            }
        } if pipeline else {}
    }


__all__ = [
    "AgroLLMPipeline",
    "FarmerRequest",
    "AgroLLMResponse",
    "ConfigLoader",
    "AgroLLMConfig",
    "get_pipeline",
    "run",
    "status",
]
