# storage/db.py  (async simplified)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/preciagro")
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)


async def upsert_normalized(item):
    q = text("""
    INSERT INTO normalized_items
    (item_id,source_id,collected_at,observed_at,kind,location,tags,payload,raw_ref,content_hash)
    VALUES (:item_id,:source_id,:collected_at,:observed_at,:kind,
            CAST(:location AS JSONB), :tags, CAST(:payload AS JSONB), :raw_ref, :content_hash)
    ON CONFLICT (source_id, content_hash) DO NOTHING
    """)
    async with engine.begin() as conn:
        await conn.execute(q, {
            "item_id": item.item_id,
            "source_id": item.source_id,
            "collected_at": item.collected_at,
            "observed_at": item.observed_at,
            "kind": item.kind,
            "location": item.location.model_dump_json() if item.location else None,
            "tags": item.tags,
            "payload": item.payload,
            "raw_ref": item.raw_ref,
            "content_hash": item.content_hash
        })
