"""Tests for PostgresEngineAdapter, mocking asyncpg (no real instance needed)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.monitoring.adapters.postgres_adapter import PostgresEngineAdapter
from app.modules.monitoring.engine_adapter import Engine, InstanceConnectionParams

PARAMS = InstanceConnectionParams(
    host="localhost",
    port=5432,
    database="pulse_db",
    username="backend",
    password="changeme",
    engine=Engine.POSTGRESQL,
)


def _mock_connection(*, fetchval_values: list, fetch_rows: list[dict]) -> AsyncMock:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(side_effect=fetchval_values)
    conn.fetch = AsyncMock(return_value=fetch_rows)
    conn.close = AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_detect_capabilities_reports_installed_extensions_and_grants() -> None:
    conn = _mock_connection(
        fetchval_values=["17.0", True, True],  # server_version, pg_monitor grant, superuser
        fetch_rows=[{"extname": "pg_stat_statements"}],
    )

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        capabilities = await PostgresEngineAdapter().detect_capabilities(PARAMS)

    assert capabilities.engine is Engine.POSTGRESQL
    assert capabilities.version == "17.0"
    assert capabilities.features == {"pg_stat_statements": True, "pg_wait_sampling": False, "hypopg": False}
    assert capabilities.grants == {"pg_monitor": True, "superuser": True}
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_collect_trivial_sample_returns_active_sessions_and_server_time() -> None:
    server_time = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
    conn = _mock_connection(fetchval_values=[3, server_time], fetch_rows=[])

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        sample = await PostgresEngineAdapter().collect_trivial_sample(PARAMS)

    assert sample.active_session_count == 3
    assert sample.server_time == server_time
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_connection_is_closed_even_when_query_fails() -> None:
    conn = _mock_connection(fetchval_values=[], fetch_rows=[])
    conn.fetchval = AsyncMock(side_effect=RuntimeError("boom"))

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        with pytest.raises(RuntimeError):
            await PostgresEngineAdapter().detect_capabilities(PARAMS)

    conn.close.assert_awaited_once()
