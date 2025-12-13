"""Trace Storage Service.

Manages storage and retrieval of reasoning traces.
"""

import logging
from typing import List, Optional

from ..contracts.v1.schemas import ReasoningTrace
from ..core.reasoning_trace import get_trace_store, TraceStore

logger = logging.getLogger(__name__)


class TraceService:
    """ReasoningTrace storage and retrieval service."""
    
    def __init__(self) -> None:
        """Initialize trace service."""
        self._store: TraceStore = get_trace_store()
        logger.info("TraceService initialized")
    
    async def store(self, trace: ReasoningTrace) -> str:
        """Store a reasoning trace.
        
        Args:
            trace: Trace to store
            
        Returns:
            Trace ID
        """
        trace_id = self._store.store(trace)
        logger.debug(f"Stored trace {trace_id}")
        return trace_id
    
    async def retrieve(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Retrieve a trace by ID.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            ReasoningTrace if found, None otherwise
        """
        trace = self._store.get(trace_id)
        if trace:
            logger.debug(f"Retrieved trace {trace_id}")
        else:
            logger.debug(f"Trace {trace_id} not found")
        return trace
    
    async def list_by_request(self, request_id: str) -> List[ReasoningTrace]:
        """Get all traces for a request.
        
        Args:
            request_id: Request ID
            
        Returns:
            List of traces for the request
        """
        traces = self._store.get_by_request(request_id)
        logger.debug(f"Found {len(traces)} traces for request {request_id}")
        return traces
    
    async def delete(self, trace_id: str) -> bool:
        """Delete a trace (for GDPR compliance).
        
        Args:
            trace_id: Trace ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        result = self._store.delete(trace_id)
        if result:
            logger.info(f"Deleted trace {trace_id}")
        return result
    
    def get_trace_count(self) -> int:
        """Get total number of stored traces.
        
        Returns:
            Trace count
        """
        return self._store.count()
