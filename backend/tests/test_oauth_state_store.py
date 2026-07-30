"""Unit tests for OAuthStateStore (issue 037: OAuth CSRF `state` was never
verified server-side — only compared on the frontend). Covers the three
verification points from the issue: normal login succeeds, a replayed state
is rejected, and a state the server never issued is rejected.
"""

import pytest

from app.core.oauth_state_store import OAuthStateStore


class FakePipeline:
    """Minimal stand-in for redis.asyncio's pipeline: queues ops, executes in order."""

    def __init__(self, store: dict[str, str]):
        self._store = store
        self._ops: list[tuple[str, str]] = []

    async def __aenter__(self) -> "FakePipeline":
        return self

    async def __aexit__(self, *_args: object) -> bool:
        return False

    async def get(self, key: str) -> None:
        self._ops.append(("get", key))

    async def delete(self, key: str) -> None:
        self._ops.append(("delete", key))

    async def execute(self) -> list[object]:
        results: list[object] = []
        for op, key in self._ops:
            if op == "get":
                results.append(self._store.get(key))
            else:
                results.append(1 if self._store.pop(key, None) is not None else 0)
        return results


class FakeRedis:
    """Minimal in-memory stand-in for redis.asyncio.Redis (setex/get/delete/pipeline)."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self._store[key] = value

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0

    def pipeline(self, transaction: bool = True) -> FakePipeline:
        return FakePipeline(self._store)


@pytest.fixture
def state_store() -> OAuthStateStore:
    return OAuthStateStore(redis_client=FakeRedis())  # type: ignore[arg-type]


class TestOAuthStateStore:
    @pytest.mark.asyncio
    async def test_normal_login_state_is_valid(self, state_store: OAuthStateStore) -> None:
        await state_store.store_state("state-abc", "google")

        assert await state_store.consume_state("state-abc", "google") is True

    @pytest.mark.asyncio
    async def test_replayed_state_is_rejected(self, state_store: OAuthStateStore) -> None:
        await state_store.store_state("state-abc", "google")

        assert await state_store.consume_state("state-abc", "google") is True
        # Second attempt with the same state must fail (single-use).
        assert await state_store.consume_state("state-abc", "google") is False

    @pytest.mark.asyncio
    async def test_never_issued_state_is_rejected(self, state_store: OAuthStateStore) -> None:
        assert await state_store.consume_state("never-issued", "google") is False

    @pytest.mark.asyncio
    async def test_state_issued_for_different_provider_is_rejected(self, state_store: OAuthStateStore) -> None:
        await state_store.store_state("state-abc", "google")

        assert await state_store.consume_state("state-abc", "github") is False
