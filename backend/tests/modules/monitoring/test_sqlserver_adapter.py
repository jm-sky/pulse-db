"""Tests for SqlServerEngineAdapter, mocking pytds (no real instance needed).

Pins query/parsing logic against the documented DMV / fn_my_permissions
shapes. Live-instance validation: docs/plans/2026-07-30-phase0-foundation.md
and docs/plans/2026-07-30-phase1-diagnostic-core.md.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.modules.monitoring.adapters.sqlserver_adapter import SqlServerEngineAdapter
from app.modules.monitoring.engine_adapter import Engine, InstanceConnectionParams

PARAMS = InstanceConnectionParams(
    host="mssql.example",
    port=1433,
    database="pulse_db",
    username="backend",
    password="changeme",
    engine=Engine.SQLSERVER,
)


class _FakeCursor:
    """Scripted cursor: each execute() advances to the next (kind, payload).

    kind is ``"one"`` (fetchone) or ``"all"`` (fetchall).
    """

    def __init__(self, script: list[tuple[str, object]]) -> None:
        self._script = iter(script)
        self._pending: tuple[str, object] | None = None
        self.description: list[tuple[str]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def execute(self, *_args: object, **_kwargs: object) -> None:
        self._pending = next(self._script)
        kind, payload = self._pending
        if kind == "all" and isinstance(payload, tuple) and len(payload) == 2:
            self.description = [(name,) for name in payload[0]]
            self._pending = ("all", payload[1])

    def fetchone(self) -> object:
        assert self._pending is not None and self._pending[0] == "one"
        return self._pending[1]

    def fetchall(self) -> object:
        assert self._pending is not None and self._pending[0] == "all"
        return self._pending[1]


class _FakeConnection:
    def __init__(self, script: list[tuple[str, object]]) -> None:
        self._cursor = _FakeCursor(script)

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self._cursor


def _capabilities_script(
    *,
    version: str = "16.0.1000.6",
    query_store_state: str = "READ_WRITE",
    system_health_count: int = 1,
    server_perms: list[tuple[str, ...]] | None = None,
    database_perms: list[tuple[str, ...]] | None = None,
) -> list[tuple[str, object]]:
    return [
        ("one", (version,)),
        ("one", (query_store_state,)),
        ("one", (system_health_count,)),
        ("all", server_perms if server_perms is not None else [("VIEW SERVER STATE",)]),
        ("all", database_perms if database_perms is not None else [("VIEW DATABASE STATE",)]),
    ]


@pytest.mark.asyncio
async def test_detect_capabilities_reports_query_store_and_grants() -> None:
    fake_conn = _FakeConnection(_capabilities_script())

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        capabilities = await SqlServerEngineAdapter().detect_capabilities(PARAMS)

    assert capabilities.engine is Engine.SQLSERVER
    assert capabilities.version == "16.0.1000.6"
    assert capabilities.features == {"query_store": True, "deadlock_history": True}
    assert capabilities.grants == {"VIEW SERVER STATE": True, "VIEW DATABASE STATE": True}


@pytest.mark.asyncio
async def test_detect_capabilities_query_store_off() -> None:
    fake_conn = _FakeConnection(_capabilities_script(query_store_state="OFF", system_health_count=0, server_perms=[], database_perms=[]))

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        capabilities = await SqlServerEngineAdapter().detect_capabilities(PARAMS)

    assert capabilities.features == {"query_store": False, "deadlock_history": False}
    assert capabilities.grants == {"VIEW SERVER STATE": False, "VIEW DATABASE STATE": False}


@pytest.mark.asyncio
async def test_detect_capabilities_accepts_sql2022_performance_state() -> None:
    """Granular SQL Server 2022 grant counts as VIEW SERVER STATE for our DMVs."""
    fake_conn = _FakeConnection(
        _capabilities_script(
            server_perms=[("VIEW SERVER PERFORMANCE STATE",)],
            database_perms=[("VIEW DATABASE STATE",)],
        )
    )

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        capabilities = await SqlServerEngineAdapter().detect_capabilities(PARAMS)

    assert capabilities.grants == {"VIEW SERVER STATE": True, "VIEW DATABASE STATE": True}


@pytest.mark.asyncio
async def test_collect_trivial_sample_returns_active_requests_and_server_time() -> None:
    server_time = datetime(2026, 7, 30, 12, 0, 0)
    fake_conn = _FakeConnection([("one", (2,)), ("one", (server_time,))])

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        sample = await SqlServerEngineAdapter().collect_trivial_sample(PARAMS)

    assert sample.active_session_count == 2
    assert sample.server_time == server_time


@pytest.mark.asyncio
async def test_collect_active_sessions_maps_flat_wait_and_query_hash() -> None:
    columns = (
        "db_user",
        "application_name",
        "client_host",
        "wait_event",
        "query_text",
        "engine_query_key",
    )
    rows = [
        ("app_user", "App", "10.0.0.1", "LCK_M_X", "UPDATE t SET x=1", "0xABC"),
        ("app_user", "App", "10.0.0.1", None, "SELECT 1", None),
    ]
    fake_conn = _FakeConnection([("all", (columns, rows))])

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        sessions = await SqlServerEngineAdapter().collect_active_sessions(PARAMS)

    assert len(sessions) == 2
    assert sessions[0].wait_event_type is None
    assert sessions[0].wait_event == "LCK_M_X"
    assert sessions[0].engine_query_key == "0xABC"
    assert sessions[0].query_text == "UPDATE t SET x=1"
    assert sessions[1].wait_event is None
    assert sessions[1].engine_query_key is None


@pytest.mark.asyncio
async def test_collect_query_stats_maps_dmv_counters() -> None:
    columns = (
        "engine_query_key",
        "normalized_text",
        "calls",
        "total_time_ms",
        "rows",
        "shared_blks_read",
        "shared_blks_written",
    )
    rows = [
        ("0xDEAD", "SELECT 1", 10, 12.5, 3, 100, 2),
        ("NULL", "should skip", 1, 1.0, 0, 0, 0),
    ]
    fake_conn = _FakeConnection([("all", (columns, rows))])

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        stats = await SqlServerEngineAdapter().collect_query_stats(PARAMS)

    assert len(stats) == 1
    assert stats[0].engine_query_key == "0xDEAD"
    assert stats[0].normalized_text == "SELECT 1"
    assert stats[0].calls == 10
    assert stats[0].total_time_ms == 12.5
    assert stats[0].rows == 3
    assert stats[0].shared_blks_read == 100
    assert stats[0].shared_blks_written == 2
