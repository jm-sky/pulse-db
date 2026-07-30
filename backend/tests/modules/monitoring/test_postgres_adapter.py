"""Tests for PostgresEngineAdapter, mocking asyncpg (no real instance needed)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import asyncpg
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


@pytest.mark.asyncio
async def test_collect_active_sessions_maps_wait_state_and_query_key() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "db_user": "app",
                "application_name": "billing-service",
                "client_host": "10.0.0.5",
                "wait_event_type": "Lock",
                "wait_event": "relation",
                "query": "SELECT * FROM accounts WHERE id = $1",
                "engine_query_key": "123456789",
            },
            {
                "db_user": "app",
                "application_name": "billing-service",
                "client_host": "10.0.0.5",
                "wait_event_type": None,
                "wait_event": None,
                "query": "UPDATE accounts SET balance = balance - 1 WHERE id = $1",
                "engine_query_key": "987654321",
            },
        ]
    )
    conn.close = AsyncMock()

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        sessions = await PostgresEngineAdapter().collect_active_sessions(PARAMS)

    assert len(sessions) == 2
    assert sessions[0].wait_event_type == "Lock"
    assert sessions[0].wait_event == "relation"
    assert sessions[0].engine_query_key == "123456789"
    # On-CPU session: no wait event at all, not classified as idle.
    assert sessions[1].wait_event_type is None
    assert sessions[1].wait_event is None
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_collect_active_sessions_falls_back_when_query_id_column_missing() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(
        side_effect=[
            asyncpg.exceptions.UndefinedColumnError('column "query_id" does not exist'),
            [
                {
                    "db_user": "app",
                    "application_name": "",
                    "client_host": "",
                    "wait_event_type": None,
                    "wait_event": None,
                    "query": "SELECT 1",
                    "engine_query_key": None,
                }
            ],
        ]
    )
    conn.close = AsyncMock()

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        sessions = await PostgresEngineAdapter().collect_active_sessions(PARAMS)

    assert len(sessions) == 1
    assert sessions[0].engine_query_key is None
    assert conn.fetch.await_count == 2


@pytest.mark.asyncio
async def test_collect_query_stats_returns_empty_when_extension_not_installed() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)
    conn.close = AsyncMock()

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        stats = await PostgresEngineAdapter().collect_query_stats(PARAMS)

    assert stats == []
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_collect_query_stats_maps_cumulative_counters() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1)
    conn.fetch = AsyncMock(
        return_value=[
            {
                "engine_query_key": "42",
                "normalized_text": "SELECT * FROM accounts WHERE id = $1",
                "calls": 100,
                "total_time_ms": 543.2,
                "rows": 100,
                "shared_blks_read": 10,
                "shared_blks_written": 0,
            }
        ]
    )
    conn.close = AsyncMock()

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        stats = await PostgresEngineAdapter().collect_query_stats(PARAMS)

    assert len(stats) == 1
    assert stats[0].engine_query_key == "42"
    assert stats[0].calls == 100
    assert stats[0].total_time_ms == 543.2
