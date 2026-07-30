"""Server-side storage for the OAuth CSRF `state` parameter.

`OAuthService.generate_state()` (app/core/oauth.py) only produces the random
value — until now nothing persisted it server-side, so `/oauth/callback` had
no way to verify `state` itself; only the frontend compared its copy. This
store lets the issuing endpoint persist `state` (short TTL, single-use,
bound to the provider it was issued for) so the callback can verify and
consume it before exchanging the authorization code.
"""

import json
import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class OAuthStateStore:
    """Redis-backed single-use store for OAuth CSRF state tokens."""

    def __init__(
        self,
        redis_client: Redis,
        key_prefix: str = "oauth:state:",
        default_ttl: int = 600,
    ):
        """
        Initialize the state store.

        Args:
            redis_client: Async Redis client
            key_prefix: Prefix for Redis keys
            default_ttl: Default TTL in seconds (default: 10 minutes)
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl

    def _key(self, state: str) -> str:
        return f"{self.key_prefix}{state}"

    async def store_state(self, state: str, provider: str, ttl: int | None = None) -> None:
        """
        Persist an issued state, bound to the provider it was issued for.

        Args:
            state: The CSRF state value returned to the client
            provider: OAuth provider the state was issued for
            ttl: Time-to-live in seconds (default: 10 minutes)
        """
        await self.redis.setex(
            self._key(state),
            ttl or self.default_ttl,
            json.dumps({"provider": provider}),
        )

    async def consume_state(self, state: str, provider: str) -> bool:
        """
        Verify a state was issued for this provider, and delete it (single-use).

        Args:
            state: State value received from the client at the callback
            provider: Provider the callback is for

        Returns:
            True if the state was found, unexpired, and matches the provider.
            False otherwise (missing, expired, reused, or provider mismatch).
        """
        key = self._key(state)

        # Atomic get+delete so a state can never be verified twice (replay).
        async with self.redis.pipeline(transaction=True) as pipe:
            await pipe.get(key)
            await pipe.delete(key)
            result = await pipe.execute()

        raw = result[0]
        if not raw:
            logger.warning("OAuth state not found or already used")
            return False

        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            return False

        return bool(data.get("provider") == provider)


async def get_oauth_state_store() -> OAuthStateStore:
    """Build an OAuthStateStore backed by the shared Redis client."""
    from app.core.redis import get_redis_client

    redis_client = await get_redis_client()
    return OAuthStateStore(redis_client)
