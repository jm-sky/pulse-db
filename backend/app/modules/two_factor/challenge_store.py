"""WebAuthn challenge storage using Redis.

Stores WebAuthn registration and authentication challenges server-side
to prevent tampering and ensure one-time use.
"""

import base64
import json
import logging
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class WebAuthnChallengeStore:
    """Service for storing WebAuthn challenges in Redis."""

    def __init__(
        self,
        redis_client: Redis,
        key_prefix: str = "webauthn:challenge:",
        default_ttl: int = 300,
    ):
        """Initialize challenge store.

        Args:
            redis_client: Async Redis client
            key_prefix: Prefix for Redis keys
            default_ttl: Default TTL in seconds (default: 5 minutes)
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

    def _get_redis_key(self, challenge_token: str) -> str:
        """Generate Redis key for challenge token."""
        return f"{self.key_prefix}{challenge_token}"

    async def store_challenge(
        self,
        challenge_token: str,
        user_id: str,
        challenge: bytes,
        challenge_type: str = "registration",
        ttl: int | None = None,
    ) -> None:
        """Store WebAuthn challenge in Redis.

        Args:
            challenge_token: Unique token identifying this challenge
            user_id: User ID associated with challenge
            challenge: Raw challenge bytes
            challenge_type: Type of challenge ("registration" or "authentication")
            ttl: Time-to-live in seconds (default: 5 minutes)

        Note:
            Challenge is automatically deleted after TTL or on retrieval (one-time use).
        """
        if ttl is None:
            ttl = self.default_ttl

        key = self._get_redis_key(challenge_token)
        data = {
            "user_id": user_id,
            "challenge": base64.b64encode(challenge).decode(),
            "challenge_type": challenge_type,
            "created_at": datetime.now(UTC).isoformat(),
        }

        await self.redis.setex(key, ttl, json.dumps(data))
        logger.info(f"Challenge stored: token={challenge_token[:8]}..., type={challenge_type}, ttl={ttl}s")

    async def get_challenge(self, challenge_token: str) -> dict[str, Any] | None:
        """Get challenge data (without deleting).

        Args:
            challenge_token: Challenge token

        Returns:
            Challenge data dict or None if not found/expired
        """
        key = self._get_redis_key(challenge_token)
        data = await self.redis.get(key)

        if not data:
            logger.warning(f"Challenge not found: token={challenge_token[:8]}...")
            return None

        result: dict[str, Any] = json.loads(data)
        return result

    async def get_and_delete_challenge(self, challenge_token: str) -> dict[str, Any] | None:
        """Get challenge data and delete it (one-time use).

        Args:
            challenge_token: Challenge token

        Returns:
            Challenge data dict or None if not found/expired

        Note:
            This ensures challenge can only be used once (prevents replay attacks).
        """
        key = self._get_redis_key(challenge_token)

        # Use pipeline for atomic get+delete
        async with self.redis.pipeline(transaction=True) as pipe:
            await pipe.get(key)
            await pipe.delete(key)
            result = await pipe.execute()

        data = result[0]
        if not data:
            logger.warning(f"Challenge not found: token={challenge_token[:8]}...")
            return None

        logger.info(f"Challenge consumed: token={challenge_token[:8]}...")
        parsed: dict[str, Any] = json.loads(data)
        return parsed

    async def delete_challenge(self, challenge_token: str) -> bool:
        """Delete challenge.

        Args:
            challenge_token: Challenge token

        Returns:
            True if challenge was deleted, False if not found
        """
        key = self._get_redis_key(challenge_token)
        deleted = await self.redis.delete(key)
        return bool(deleted)

    async def get_stats(self) -> dict:
        """Get statistics about stored challenges.

        Returns:
            Dict with challenge statistics
        """
        pattern = f"{self.key_prefix}*"
        cursor = 0
        count = 0

        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            count += len(keys)

            if cursor == 0:
                break

        return {
            "total_challenges": count,
            "key_prefix": self.key_prefix,
        }
