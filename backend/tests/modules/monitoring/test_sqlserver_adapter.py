"""Tests for SqlServerEngineAdapter, mocking pytds (no real instance needed).

Not exercised against a live SQL Server -- see
docs/plans/2026-07-30-phase0-foundation.md for that follow-up. These tests
pin down the query/parsing logic against the documented DMV/HAS_PERMS_BY_NAME
shapes so a future live-instance check has something to compare against.
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
    def __init__(self, fetchone_values: list) -> None:
        self._values = iter(fetchone_values)

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def execute(self, *_args: object, **_kwargs: object) -> None:
        pass

    def fetchone(self) -> tuple:
        return next(self._values)


class _FakeConnection:
    def __init__(self, fetchone_values: list) -> None:
        self._cursor = _FakeCursor(fetchone_values)

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self._cursor


@pytest.mark.asyncio
async def test_detect_capabilities_reports_query_store_and_grants() -> None:
    fake_conn = _FakeConnection(
        fetchone_values=[
            ("16.0.1000.6",),  # ProductVersion
            ("READ_WRITE",),  # query store actual_state_desc
            (True,),  # VIEW SERVER STATE
            (True,),  # VIEW DATABASE STATE
        ]
    )

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        capabilities = await SqlServerEngineAdapter().detect_capabilities(PARAMS)

    assert capabilities.engine is Engine.SQLSERVER
    assert capabilities.version == "16.0.1000.6"
    assert capabilities.features == {"query_store": True}
    assert capabilities.grants == {"VIEW SERVER STATE": True, "VIEW DATABASE STATE": True}


@pytest.mark.asyncio
async def test_detect_capabilities_query_store_off() -> None:
    fake_conn = _FakeConnection(fetchone_values=[("16.0.1000.6",), ("OFF",), (False,), (False,)])

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        capabilities = await SqlServerEngineAdapter().detect_capabilities(PARAMS)

    assert capabilities.features == {"query_store": False}


@pytest.mark.asyncio
async def test_collect_trivial_sample_returns_active_requests_and_server_time() -> None:
    server_time = datetime(2026, 7, 30, 12, 0, 0)
    fake_conn = _FakeConnection(fetchone_values=[(2,), (server_time,)])

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        sample = await SqlServerEngineAdapter().collect_trivial_sample(PARAMS)

    assert sample.active_session_count == 2
    assert sample.server_time == server_time


@pytest.mark.asyncio
async def test_collect_active_sessions_raises_not_implemented() -> None:
    """Phase 1 element 1, SQL Server slice: explicitly deferred, not silently empty."""
    with pytest.raises(NotImplementedError):
        await SqlServerEngineAdapter().collect_active_sessions(PARAMS)


@pytest.mark.asyncio
async def test_collect_query_stats_raises_not_implemented() -> None:
    """Phase 1 element 2, SQL Server slice: explicitly deferred, not silently empty."""
    with pytest.raises(NotImplementedError):
        await SqlServerEngineAdapter().collect_query_stats(PARAMS)
