"""Tests for Phase 1 element 4: blocking + deadlocks."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.monitoring.adapters.postgres_adapter import PostgresEngineAdapter
from app.modules.monitoring.adapters.sqlserver_adapter import SqlServerEngineAdapter
from app.modules.monitoring.engine_adapter import BlockingRow, DeadlockRow, Engine, InstanceConnectionParams
from app.modules.monitoring.repository import BlockingEventRecord, DeadlockEventRecord
from main import app

PG_PARAMS = InstanceConnectionParams(
    host="localhost",
    port=5432,
    database="pulse_db",
    username="backend",
    password="changeme",
    engine=Engine.POSTGRESQL,
)

SS_PARAMS = InstanceConnectionParams(
    host="mssql.example",
    port=1433,
    database="pulse_db",
    username="backend",
    password="changeme",
    engine=Engine.SQLSERVER,
)


@pytest.mark.asyncio
async def test_postgres_collect_deadlocks_always_empty() -> None:
    rows = await PostgresEngineAdapter().collect_deadlocks(PG_PARAMS, since=None)
    assert rows == []


@pytest.mark.asyncio
async def test_postgres_collect_blocking_maps_lock_chain() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "blocked_pid": 10,
                "blocking_pid": 20,
                "wait_event_type": "Lock",
                "wait_event": "transactionid",
                "locktype": "transactionid",
                "blocked_duration_ms": 1500.0,
                "blocked_user": "app",
                "blocking_user": "app",
                "blocked_application": "a",
                "blocking_application": "b",
                "blocked_client_host": "1.1.1.1",
                "blocking_client_host": "2.2.2.2",
                "blocked_query_text": "UPDATE t SET x=1",
                "blocking_query_text": "SELECT * FROM t FOR UPDATE",
                "blocked_engine_query_key": "1",
                "blocking_engine_query_key": "2",
            }
        ]
    )
    conn.close = AsyncMock()

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        rows = await PostgresEngineAdapter().collect_blocking(PG_PARAMS)

    assert len(rows) == 1
    assert rows[0].blocked_duration_ms == 1500.0
    assert rows[0].details["blocked_pid"] == 10
    assert rows[0].blocked_engine_query_key == "1"
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_sqlserver_collect_blocking_maps_rows() -> None:
    class _FakeCursor:
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

        def fetchall(self) -> object:
            assert self._pending is not None and self._pending[0] == "all"
            return self._pending[1]

    class _FakeConn:
        def __init__(self, script: list[tuple[str, object]]) -> None:
            self._cursor = _FakeCursor(script)

        def __enter__(self) -> "_FakeConn":
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def cursor(self) -> _FakeCursor:
            return self._cursor

    columns = (
        "blocked_session_id",
        "blocking_session_id",
        "wait_type",
        "wait_time_ms",
        "blocked_user",
        "blocking_user",
        "blocked_application",
        "blocking_application",
        "blocked_client_host",
        "blocking_client_host",
        "blocked_query_text",
        "blocking_query_text",
        "blocked_engine_query_key",
        "blocking_engine_query_key",
    )
    rows = [
        (52, 51, "LCK_M_X", 2000, "u", "u", "a", "b", "h1", "h2", "UPDATE t", "SELECT 1", "0xAA", "0xBB"),
    ]
    fake_conn = _FakeConn([("all", (columns, rows))])

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        result = await SqlServerEngineAdapter().collect_blocking(SS_PARAMS)

    assert len(result) == 1
    assert result[0].blocked_duration_ms == 2000.0
    assert result[0].details["blocked_session_id"] == 52
    assert result[0].blocked_engine_query_key == "0xAA"


@pytest.mark.asyncio
async def test_run_deadlocks_collection_advances_watermark() -> None:
    from app.modules.monitoring.collector import run_deadlocks_collection

    params = InstanceConnectionParams(
        host="h",
        port=1433,
        database="db",
        username="u",
        password="p",
        engine=Engine.SQLSERVER,
    )
    occurred = datetime(2026, 8, 5, 12, 0, 0, tzinfo=UTC)
    adapter = AsyncMock()
    adapter.collect_deadlocks = AsyncMock(
        return_value=[
            DeadlockRow(occurred_at=occurred, victim_engine_query_key=None, details={"xml": "<deadlock/>"}),
        ]
    )

    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", return_value=session_cm),
        patch("app.modules.monitoring.collector.repository.get_connection_params", AsyncMock(return_value=params)),
        patch("app.modules.monitoring.collector.repository.get_last_collector_run", AsyncMock(return_value=(None, None))),
        patch("app.modules.monitoring.collector.repository.get_deadlock_watermark", AsyncMock(return_value=None)),
        patch("app.modules.monitoring.collector.repository.get_latest_clock_offset_ms", AsyncMock(return_value=None)),
        patch("app.modules.monitoring.collector._adapter_for", return_value=adapter),
        patch("app.modules.monitoring.collector.repository.insert_deadlock_event", AsyncMock(return_value="e1")),
        patch("app.modules.monitoring.collector.repository.set_deadlock_watermark", AsyncMock()) as set_wm,
        patch("app.modules.monitoring.collector.repository.insert_collector_run", AsyncMock(return_value="run-1")),
    ):
        result = await run_deadlocks_collection("inst-1")

    assert result.status == "ok"
    assert result.events_written == 1
    set_wm.assert_awaited_once()
    assert set_wm.await_args.kwargs["last_event_at"] == occurred


@pytest.mark.asyncio
async def test_run_blocking_collection_writes_events() -> None:
    from app.modules.monitoring.collector import run_blocking_collection

    params = InstanceConnectionParams(
        host="h",
        port=5432,
        database="db",
        username="u",
        password="p",
        engine=Engine.POSTGRESQL,
    )
    adapter = AsyncMock()
    adapter.collect_blocking = AsyncMock(
        return_value=[
            BlockingRow(
                blocked_engine_query_key="1",
                blocking_engine_query_key="2",
                blocked_query_text="UPDATE t",
                blocking_query_text="SELECT 1",
                blocked_duration_ms=100.0,
                details={"blocked_pid": 1},
            )
        ]
    )

    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", return_value=session_cm),
        patch("app.modules.monitoring.collector.repository.get_connection_params", AsyncMock(return_value=params)),
        patch("app.modules.monitoring.collector.repository.get_last_collector_run", AsyncMock(return_value=(None, None))),
        patch("app.modules.monitoring.collector._adapter_for", return_value=adapter),
        patch("app.modules.monitoring.collector.repository.upsert_query", AsyncMock(side_effect=["qb", "qk"])),
        patch("app.modules.monitoring.collector.repository.insert_blocking_event", AsyncMock(return_value="e1")),
        patch("app.modules.monitoring.collector.repository.insert_collector_run", AsyncMock(return_value="run-1")),
    ):
        result = await run_blocking_collection("inst-1")

    assert result.status == "ok"
    assert result.events_written == 1


def test_scheduler_includes_blocking_and_deadlocks_ticks() -> None:
    from app.modules.monitoring.scheduler import _ticks_for_engine

    by_name = {spec.name: spec for spec in _ticks_for_engine(Engine.POSTGRESQL)}
    assert by_name["blocking"].interval_seconds == 30.0
    assert by_name["deadlocks"].interval_seconds == 60.0


@pytest.fixture
def authenticated_client() -> TestClient:
    user = User(
        id="user-1",
        email="dba@example.com",
        name="DBA",
        hashedPassword="hashed",
        isActive=True,
        isEmailVerified=True,
        createdAt=datetime.now(UTC),
    )
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_blocking_and_deadlocks_api(authenticated_client: TestClient) -> None:
    detected = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
    blocking = [
        BlockingEventRecord(
            id="b1",
            instance_id="inst-1",
            detected_at=detected,
            blocking_query_id="q2",
            blocked_query_id="q1",
            blocked_duration_ms=500.0,
            details={"blocked_pid": 10},
        )
    ]
    deadlocks = [
        DeadlockEventRecord(
            id="d1",
            instance_id="inst-1",
            detected_at=detected,
            victim_query_id=None,
            details={"xml": "<deadlock/>", "victim_process_id": "process1"},
        )
    ]

    with (
        patch("app.modules.monitoring.router.repository.instance_exists", AsyncMock(return_value=True)),
        patch("app.modules.monitoring.router.repository.list_blocking_events", AsyncMock(return_value=blocking)),
        patch("app.modules.monitoring.router.repository.list_deadlock_events", AsyncMock(return_value=deadlocks)),
        patch("app.modules.monitoring.router.repository.get_deadlock_event", AsyncMock(return_value=deadlocks[0])),
    ):
        br = authenticated_client.get(
            "/api/monitoring/instances/inst-1/blocking",
            params={"since": "2026-08-05T00:00:00Z"},
        )
        assert br.status_code == status.HTTP_200_OK
        assert len(br.json()["events"]) == 1

        dr = authenticated_client.get(
            "/api/monitoring/instances/inst-1/deadlocks",
            params={"since": "2026-08-05T00:00:00Z"},
        )
        assert dr.status_code == status.HTTP_200_OK
        assert dr.json()["events"][0]["hasXml"] is True

        detail = authenticated_client.get("/api/monitoring/instances/inst-1/deadlocks/d1")
        assert detail.status_code == status.HTTP_200_OK
        assert detail.json()["details"]["xml"] == "<deadlock/>"
