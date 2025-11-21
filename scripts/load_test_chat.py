"""Lightweight load test for /chat/message using asyncio."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, List

import httpx


CHAT_URL = os.getenv("CHAT_URL", "http://localhost:8103/chat/message")
CONCURRENCY = int(os.getenv("LOAD_TEST_CONCURRENCY", "10"))
REQUESTS = int(os.getenv("LOAD_TEST_REQUESTS", "50"))


def payload(i: int) -> dict[str, Any]:
    return {
        "message_id": f"msg-{i}",
        "session_id": f"session-{i%5}",
        "channel": "load_test",
        "user": {"id": f"user-{i%3}", "farm_ids": ["farm-1"], "role": "farmer"},
        "locale": "en-US",
        "text": "When should I plant maize in Murewa this year?",
        "metadata": {"location": "Murewa"},
    }


async def worker(client: httpx.AsyncClient, idxs: List[int], results: List[float]) -> None:
    for i in idxs:
        start = time.perf_counter()
        resp = await client.post(CHAT_URL, json=payload(i), timeout=15.0)
        elapsed = (time.perf_counter() - start) * 1000
        results.append(elapsed)
        if resp.status_code != 200:
            print(f"Request {i} failed: {resp.status_code} {resp.text}")


async def main() -> None:
    results: List[float] = []
    idxs = list(range(REQUESTS))
    batches = [idxs[i::CONCURRENCY] for i in range(CONCURRENCY)]
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(worker(client, batch, results) for batch in batches))
    print(f"Completed {len(results)} requests; p50={percentile(results,50):.1f}ms p95={percentile(results,95):.1f}ms")


def percentile(data: List[float], p: int) -> float:
    if not data:
        return 0.0
    data = sorted(data)
    k = int(len(data) * p / 100)
    k = min(k, len(data) - 1)
    return data[k]


if __name__ == "__main__":
    asyncio.run(main())
