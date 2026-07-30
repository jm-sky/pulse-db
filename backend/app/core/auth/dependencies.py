"""Auth dependencies for FastAPI."""

from fastapi import Depends
from redis.asyncio import Redis

from ..config import settings
from ..redis import get_redis
from .token_blacklist import TokenBlacklistService


async def get_token_blacklist_service(
    redis: Redis = Depends(get_redis),
) -> TokenBlacklistService:
    """FastAPI dependency for token blacklist service.

    Args:
        redis: Redis client from dependency

    Returns:
        TokenBlacklistService instance
    """
    return TokenBlacklistService(redis_client=redis, key_prefix=settings.redis.token_blacklist_prefix)
