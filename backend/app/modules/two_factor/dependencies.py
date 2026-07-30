"""Two-factor authentication dependencies."""

from fastapi import Depends
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis

from .challenge_store import WebAuthnChallengeStore


async def get_webauthn_challenge_store(
    redis: Redis = Depends(get_redis),
) -> WebAuthnChallengeStore:
    """FastAPI dependency for WebAuthn challenge store.

    Args:
        redis: Redis client from dependency

    Returns:
        WebAuthnChallengeStore instance
    """
    return WebAuthnChallengeStore(
        redis_client=redis,
        key_prefix=settings.redis.webauthn_challenge_prefix,
        default_ttl=settings.redis.webauthn_challenge_ttl,
    )
