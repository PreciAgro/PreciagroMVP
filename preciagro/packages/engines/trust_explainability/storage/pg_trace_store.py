"""PostgreSQL and SQLite Trace Storage.

Production-ready persistent storage for reasoning traces.
"""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from ..contracts.v1.schemas import ReasoningTrace

logger = logging.getLogger(__name__)


class TraceStoreBase(ABC):
    """Abstract base class for trace storage."""
    
    @abstractmethod
    async def store(self, trace: ReasoningTrace) -> str:
        """Store a trace and return its ID."""
        pass
    
    @abstractmethod
    async def retrieve(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Retrieve a trace by ID."""
        pass
    
    @abstractmethod
    async def search(
        self,
        filters: Dict[str, Any],
        limit: int = 100
    ) -> List[ReasoningTrace]:
        """Search traces with filters."""
        pass
    
    @abstractmethod
    async def delete(self, trace_id: str) -> bool:
        """Delete a trace (GDPR compliance)."""
        pass


class SQLiteTraceStore(TraceStoreBase):
    """SQLite-backed trace storage.
    
    Good for development and single-node deployments.
    """
    
    def __init__(self, db_path: str = "traces.db") -> None:
        """Initialize SQLite trace store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = db_path
        self._init_db()
        logger.info(f"SQLiteTraceStore initialized at {db_path}")
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reasoning_traces (
                    trace_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    decision_type TEXT,
                    confidence REAL,
                    safety_status TEXT,
                    signature TEXT,
                    trace_data TEXT NOT NULL,
                    UNIQUE(trace_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_request_id 
                ON reasoning_traces(request_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON reasoning_traces(created_at)
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def store(self, trace: ReasoningTrace) -> str:
        """Store a trace."""
        trace_data = trace.model_dump_json()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO reasoning_traces
                (trace_id, request_id, created_at, decision_type, 
                 confidence, safety_status, signature, trace_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trace.trace_id,
                trace.request_id,
                trace.created_at.isoformat(),
                trace.decision_type,
                trace.confidence.overall_confidence if trace.confidence else None,
                trace.safety_check.status.value if trace.safety_check else None,
                None,  # Signature added separately
                trace_data
            ))
            conn.commit()
        
        logger.debug(f"Stored trace {trace.trace_id}")
        return trace.trace_id
    
    async def retrieve(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Retrieve a trace by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT trace_data FROM reasoning_traces WHERE trace_id = ?",
                (trace_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return ReasoningTrace.model_validate_json(row["trace_data"])
            return None
    
    async def search(
        self,
        filters: Dict[str, Any],
        limit: int = 100
    ) -> List[ReasoningTrace]:
        """Search traces with filters."""
        conditions = []
        params = []
        
        if "request_id" in filters:
            conditions.append("request_id = ?")
            params.append(filters["request_id"])
        
        if "decision_type" in filters:
            conditions.append("decision_type = ?")
            params.append(filters["decision_type"])
        
        if "min_confidence" in filters:
            conditions.append("confidence >= ?")
            params.append(filters["min_confidence"])
        
        if "safety_status" in filters:
            conditions.append("safety_status = ?")
            params.append(filters["safety_status"])
        
        if "from_date" in filters:
            conditions.append("created_at >= ?")
            params.append(filters["from_date"])
        
        if "to_date" in filters:
            conditions.append("created_at <= ?")
            params.append(filters["to_date"])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                f"""
                SELECT trace_data FROM reasoning_traces 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params
            )
            
            traces = []
            for row in cursor.fetchall():
                trace = ReasoningTrace.model_validate_json(row["trace_data"])
                traces.append(trace)
            
            return traces
    
    async def delete(self, trace_id: str) -> bool:
        """Delete a trace."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM reasoning_traces WHERE trace_id = ?",
                (trace_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
        
        if deleted:
            logger.info(f"Deleted trace {trace_id}")
        return deleted
    
    async def count(self) -> int:
        """Get total trace count."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM reasoning_traces")
            return cursor.fetchone()[0]
    
    async def update_signature(
        self,
        trace_id: str,
        signature: str
    ) -> bool:
        """Update trace signature."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE reasoning_traces SET signature = ? WHERE trace_id = ?",
                (signature, trace_id)
            )
            conn.commit()
            return cursor.rowcount > 0


class PostgresTraceStore(TraceStoreBase):
    """PostgreSQL-backed trace storage.
    
    For production multi-node deployments.
    Requires asyncpg or psycopg3.
    """
    
    def __init__(
        self,
        connection_string: str,
        pool_size: int = 10
    ) -> None:
        """Initialize PostgreSQL trace store.
        
        Args:
            connection_string: PostgreSQL connection string
            pool_size: Connection pool size
        """
        self._connection_string = connection_string
        self._pool_size = pool_size
        self._pool = None
        logger.info("PostgresTraceStore configured")
    
    async def _get_pool(self):
        """Get or create connection pool."""
        if self._pool is None:
            try:
                import asyncpg
                self._pool = await asyncpg.create_pool(
                    self._connection_string,
                    min_size=2,
                    max_size=self._pool_size
                )
                await self._init_schema()
            except ImportError:
                raise ImportError("asyncpg required for PostgresTraceStore")
        return self._pool
    
    async def _init_schema(self) -> None:
        """Initialize database schema."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reasoning_traces (
                    trace_id UUID PRIMARY KEY,
                    request_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    decision_type VARCHAR(100),
                    confidence REAL,
                    safety_status VARCHAR(50),
                    signature VARCHAR(512),
                    signature_algorithm VARCHAR(50),
                    trace_data JSONB NOT NULL
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_traces_request_id 
                ON reasoning_traces(request_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_traces_created_at
                ON reasoning_traces(created_at)
            """)
    
    async def store(self, trace: ReasoningTrace) -> str:
        """Store a trace."""
        pool = await self._get_pool()
        trace_data = trace.model_dump(mode="json")
        
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO reasoning_traces
                (trace_id, request_id, created_at, decision_type,
                 confidence, safety_status, trace_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (trace_id) DO UPDATE SET
                    trace_data = EXCLUDED.trace_data
            """,
                trace.trace_id,
                trace.request_id,
                trace.created_at,
                trace.decision_type,
                trace.confidence.overall_confidence if trace.confidence else None,
                trace.safety_check.status.value if trace.safety_check else None,
                json.dumps(trace_data)
            )
        
        logger.debug(f"Stored trace {trace.trace_id}")
        return trace.trace_id
    
    async def retrieve(self, trace_id: str) -> Optional[ReasoningTrace]:
        """Retrieve a trace by ID."""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT trace_data FROM reasoning_traces WHERE trace_id = $1",
                trace_id
            )
            
            if row:
                return ReasoningTrace.model_validate(row["trace_data"])
            return None
    
    async def search(
        self,
        filters: Dict[str, Any],
        limit: int = 100
    ) -> List[ReasoningTrace]:
        """Search traces with filters."""
        pool = await self._get_pool()
        
        conditions = []
        params = []
        param_idx = 1
        
        if "request_id" in filters:
            conditions.append(f"request_id = ${param_idx}")
            params.append(filters["request_id"])
            param_idx += 1
        
        if "decision_type" in filters:
            conditions.append(f"decision_type = ${param_idx}")
            params.append(filters["decision_type"])
            param_idx += 1
        
        if "min_confidence" in filters:
            conditions.append(f"confidence >= ${param_idx}")
            params.append(filters["min_confidence"])
            param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        params.append(limit)
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT trace_data FROM reasoning_traces
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx}
                """,
                *params
            )
            
            return [
                ReasoningTrace.model_validate(row["trace_data"])
                for row in rows
            ]
    
    async def delete(self, trace_id: str) -> bool:
        """Delete a trace."""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM reasoning_traces WHERE trace_id = $1",
                trace_id
            )
            deleted = result == "DELETE 1"
        
        if deleted:
            logger.info(f"Deleted trace {trace_id}")
        return deleted
    
    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
