
# bus/publisher.py
# Connect to Redis using the URL from environment variable (default: localhost)
import os
import json
import uuid
import datetime
import redis
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def publish_ingest_created(item):
    """
    Publishes an event to Redis Stream when a new normalized ingest item is created.
    The event contains a unique ID, type, timestamp, and the item payload.
    """
    event = {
        "event_id": str(uuid.uuid4()),  # Unique event identifier
        "event_type": "ingest.normalized.created",  # Event type for consumers
        "occurred_at": datetime.datetime.utcnow().isoformat(),  # UTC timestamp
        "item": item.model_dump()  # Serialized item (Pydantic model)
    }
    # Add the event to the Redis Stream for downstream consumers
    r.xadd("bus:ingest.normalized.created", {"payload": json.dumps(event)})
