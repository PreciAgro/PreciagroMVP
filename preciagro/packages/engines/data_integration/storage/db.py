# storage/db.py  (async simplified)
import json

from sqlalchemy import text

from ..config import settings

# Defer creation of the async engine until it's actually needed. This avoids
# importing DB driver packages (psycopg/asyncpg) at module import time which
# simplifies test runs and environments that don't want to install DB drivers.
DATABASE_URL = settings.DATABASE_URL

_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        # local import so missing DB driver won't fail at import time
        from sqlalchemy.ext.asyncio import create_async_engine

        # Convert DATABASE_URL to use asyncpg driver for async operations
        async_url = DATABASE_URL
        if async_url.startswith("postgresql://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        _engine = create_async_engine(async_url, pool_pre_ping=True)
    return _engine


async def upsert_normalized(item):
    q = text(
        """
    INSERT INTO normalized_items
    (item_id,source_id,collected_at,observed_at,kind,location,tags,payload,raw_ref,content_hash)
    VALUES (:item_id,:source_id,:collected_at,:observed_at,:kind,
            CAST(:location AS JSONB), CAST(:tags AS JSONB), CAST(:payload AS JSONB), :raw_ref, :content_hash)
    ON CONFLICT (source_id, content_hash) DO NOTHING
    """
    )
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            q,
            {
                "item_id": item.item_id,
                "source_id": item.source_id,
                "collected_at": item.collected_at,
                "observed_at": item.observed_at,
                "kind": item.kind,
                "location": item.location.model_dump_json() if item.location else None,
                "tags": json.dumps(item.tags) if item.tags else None,
                "payload": (
                    item.payload.model_dump_json()
                    if hasattr(item.payload, "model_dump_json")
                    else json.dumps(item.payload) if item.payload else None
                ),
                "raw_ref": item.raw_ref,
                "content_hash": item.content_hash,
            },
        )


async def get_items(kind: str | None = None, limit: int = 50):
    """Return a list of normalized items for basic browse/debug API.

    This returns the raw rows as JSON objects; consumers can map to Pydantic
    models as needed.
    """
    where = "WHERE kind = :kind" if kind else ""
    q = text(
        f"SELECT item_id, source_id, collected_at, observed_at, kind, location, tags, payload, content_hash FROM normalized_items {where} ORDER BY collected_at DESC LIMIT :limit"
    )
    engine = _get_engine()
    async with engine.begin() as conn:
        params = {"limit": limit}
        if kind:
            params["kind"] = kind
        cur = await conn.execute(q, params)
        rows = cur.fetchall()
        # sqlalchemy Row -> dict
        return [dict(r._mapping) for r in rows]


async def get_cursor(source_id: str):
    q = text(
        "SELECT source_id, last_observed_at, last_content_hash, updated_at FROM sync_cursors WHERE source_id = :source_id"
    )
    engine = _get_engine()
    async with engine.begin() as conn:
        cur = await conn.execute(q, {"source_id": source_id})
        row = cur.fetchone()
        return dict(row._mapping) if row else None


async def set_cursor(source_id: str, last_observed_at=None, last_content_hash=None):
    q = text(
        """
    INSERT INTO sync_cursors (source_id, last_observed_at, last_content_hash, updated_at)
    VALUES (:source_id, :last_observed_at, :last_content_hash, now())
    ON CONFLICT (source_id) DO UPDATE SET
      last_observed_at = EXCLUDED.last_observed_at,
      last_content_hash = EXCLUDED.last_content_hash,
      updated_at = now();
    """
    )
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            q,
            {
                "source_id": source_id,
                "last_observed_at": last_observed_at,
                "last_content_hash": last_content_hash,
            },
        )


async def ping_db(timeout_seconds: int = 2) -> bool:
    """Quick liveness probe for the DB. Returns True on success, False otherwise."""
    engine = _get_engine()
    try:
        # execute a lightweight query
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
