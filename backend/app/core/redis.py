from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from app.core.config import settings


def make_redis_client() -> aioredis.Redis:
    return aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )


async def get_redis() -> AsyncIterator[aioredis.Redis]:
    client = make_redis_client()
    try:
        yield client
    finally:
        await client.aclose()
