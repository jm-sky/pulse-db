"""Redis client configuration and dependency injection."""

import logging
from collections.abc import AsyncGenerator

import redis.asyncio as redis
from redis.asyncio import Redis

from .config import settings

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    """Get Redis client instance (singleton).

    Returns:
        Redis client instance
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = await redis.from_url(
            settings.redis.url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10,
        )
        logger.info("Redis client initialized")

    return _redis_client


async def close_redis_client() -> None:
    """Close Redis client connection."""
    global _redis_client

    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis client closed")


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency for Redis client.

    Yields:
        Redis client instance
    """
    client = await get_redis_client()
    try:
        yield client
    finally:
        # Connection pool handles cleanup
        pass
