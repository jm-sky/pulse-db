"""Token blacklist service using Redis.

This service manages revoked JWT tokens to prevent their reuse
after logout or account deletion.
"""

import hashlib
import logging
from datetime import UTC, datetime
from typing import cast

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class TokenBlacklistService:
    """Service for managing blacklisted JWT tokens."""

    def __init__(self, redis_client: Redis, key_prefix: str = "blacklist:token:"):
        """Initialize token blacklist service.

        Args:
            redis_client: Async Redis client
            key_prefix: Prefix for Redis keys (default: "blacklist:token:")
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.jti_prefix = f"{key_prefix}jti:"
        self.user_sessions_prefix = f"{key_prefix}user_sessions:"

    def _get_token_hash(self, token: str) -> str:
        """Generate SHA-256 hash of token for storage.

        Args:
            token: JWT token string

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def _get_redis_key(self, token: str) -> str:
        """Generate Redis key for token.

        Args:
            token: JWT token string

        Returns:
            Redis key string
        """
        token_hash = self._get_token_hash(token)
        return f"{self.key_prefix}{token_hash}"

    async def blacklist_token(self, token: str, expires_at: int, reason: str = "logout") -> None:
        """Add token to blacklist.

        Args:
            token: JWT token to blacklist
            expires_at: Unix timestamp when token expires
            reason: Reason for blacklisting (e.g., "logout", "account_deleted")

        Note:
            Token is stored until its natural expiration (TTL = exp - now).
            After expiration, Redis automatically removes it.
        """
        now = int(datetime.now(UTC).timestamp())
        ttl = expires_at - now

        if ttl <= 0:
            # Token already expired, no need to blacklist
            logger.debug("Token already expired, skipping blacklist")
            return

        key = self._get_redis_key(token)
        value = f"{reason}:{now}"

        await self.redis.setex(key, ttl, value)
        logger.info(f"Token blacklisted: reason={reason}, ttl={ttl}s")

    async def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted.

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted, False otherwise
        """
        key = self._get_redis_key(token)
        exists = await self.redis.exists(key)
        return bool(exists)

    def _get_jti_key(self, jti: str) -> str:
        return f"{self.jti_prefix}{jti}"

    def _get_user_sessions_key(self, user_id: str) -> str:
        return f"{self.user_sessions_prefix}{user_id}"

    async def track_user_session(self, user_id: str, jti: str, expires_at: int) -> None:
        """Register a session JTI for a user until token expiration."""
        now = int(datetime.now(UTC).timestamp())
        ttl = expires_at - now
        if ttl <= 0:
            return

        user_sessions_key = self._get_user_sessions_key(user_id)
        await self.redis.zadd(user_sessions_key, {jti: expires_at})
        await self.redis.expire(user_sessions_key, ttl)

    async def is_jti_blacklisted(self, jti: str) -> bool:
        """Check if JTI has been revoked."""
        exists = await self.redis.exists(self._get_jti_key(jti))
        return bool(exists)

    async def blacklist_jti(self, jti: str, expires_at: int, reason: str = "logout") -> None:
        """Blacklist JTI until its natural expiration."""
        now = int(datetime.now(UTC).timestamp())
        ttl = expires_at - now
        if ttl <= 0:
            return
        await self.redis.setex(self._get_jti_key(jti), ttl, f"{reason}:{now}")

    async def revoke_session(self, user_id: str, jti: str, expires_at: int, reason: str = "logout") -> None:
        """Revoke a specific user session and remove it from active set."""
        await self.blacklist_jti(jti=jti, expires_at=expires_at, reason=reason)
        await self.redis.zrem(self._get_user_sessions_key(user_id), jti)

    async def blacklist_all_user_tokens(self, user_id: str, reason: str = "account_deleted") -> int:
        """Blacklist all tokens for a user.

        Note:
            This is a placeholder. In production, you'd need to:
            1. Store user_id → token mapping in Redis
            2. Or use a different token storage strategy

        Args:
            user_id: User ID
            reason: Reason for blacklisting

        Returns:
            Number of tokens blacklisted
        """
        sessions_key = self._get_user_sessions_key(user_id)
        now = int(datetime.now(UTC).timestamp())
        await self.redis.zremrangebyscore(sessions_key, "-inf", now)

        sessions = cast(
            "list[tuple[bytes | str, float]]",
            await self.redis.zrangebyscore(
                sessions_key,
                min=now,
                max="+inf",
                withscores=True,
            ),
        )
        count = 0
        for jti_raw, exp_score in sessions:
            jti = jti_raw.decode("utf-8") if isinstance(jti_raw, bytes) else str(jti_raw)
            expires_at = int(exp_score)
            await self.blacklist_jti(jti=jti, expires_at=expires_at, reason=reason)
            count += 1

        await self.redis.delete(sessions_key)
        logger.info(f"Revoked {count} sessions for user_id={user_id}")
        return count

    async def get_blacklist_stats(self) -> dict:
        """Get statistics about blacklisted tokens.

        Returns:
            Dict with blacklist statistics
        """
        pattern = f"{self.key_prefix}*"
        cursor = 0
        count = 0

        # Scan Redis keys (non-blocking)
        while True:
            cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
            count += len(keys)

            if cursor == 0:
                break

        return {
            "total_blacklisted": count,
            "key_prefix": self.key_prefix,
        }
