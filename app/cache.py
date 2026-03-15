import redis.asyncio as redis

from app.config import REDIS_URL

redis_client: redis.Redis | None = None


async def init_redis() -> None:
    global redis_client
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)


async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


async def cache_get(key: str) -> str | None:
    if redis_client is None:
        return None
    return await redis_client.get(key)


async def cache_set(key: str, value: str, ttl: int = 3600) -> None:
    if redis_client is None:
        return
    await redis_client.set(key, value, ex=ttl)


async def cache_delete(key: str) -> None:
    if redis_client is None:
        return
    await redis_client.delete(key)


def link_cache_key(short_code: str) -> str:
    return f"link:{short_code}"


def stats_cache_key(short_code: str) -> str:
    return f"stats:{short_code}"
