from functools import lru_cache
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings

INDEX_QUEUE_KEY = "queue:documents:index"


@lru_cache
def get_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


async def enqueue_document_indexing(document_id: str) -> None:
    await get_redis().lpush(INDEX_QUEUE_KEY, document_id)


async def dequeue_document_indexing(timeout_seconds: int = 5) -> Optional[str]:
    result = await get_redis().brpop(INDEX_QUEUE_KEY, timeout=timeout_seconds)
    if result is None:
        return None
    _, document_id = result
    return document_id
