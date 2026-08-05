"""Tests for Phase 1 element 5: index inventory + recommendations."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.monitoring.adapters.postgres_adapter import PostgresEngineAdapter
from app.modules.monitoring.adapters.sqlserver_adapter import (
    SqlServerEngineAdapter,
    _build_missing_index_ddl,
)
from app.modules.monitoring.engine_adapter import (
    Engine,
    IndexInventoryRow,
    InstanceConnectionParams,
    MissingIndexRow,
)
from app.modules.monitoring.repository import (
    IndexSnapshotRecord,
    RecommendationRecord,
    compute_recommendation_evidence_key,
)
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
async def test_postgres_collect_missing_indexes_always_empty() -> None:
    rows = await PostgresEngineAdapter().collect_missing_indexes(PG_PARAMS)
    assert rows == []


@pytest.mark.asyncio
async def test_postgres_collect_index_inventory_maps_unused() -> None:
    conn = AsyncMock()
    conn.fetch = AsyncMock(
        return_value=[
            {
                "database_name": "pulse_db",
                "schema_name": "public",
                "table_name": "orders",
                "index_name": "ix_orders_stale",
                "size_bytes": 8192,
                "scans": 0,
                "is_primary_key": False,
                "is_unique": False,
                "index_definition": "CREATE INDEX ix_orders_stale ON public.orders (id)",
                "key_columns": "id",
            },
            {
                "database_name": "pulse_db",
                "schema_name": "public",
                "table_name": "orders",
                "index_name": "orders_pkey",
                "size_bytes": 16384,
                "scans": 0,
                "is_primary_key": True,
                "is_unique": True,
                "index_definition": "CREATE UNIQUE INDEX orders_pkey ON public.orders (id)",
                "key_columns": "id",
            },
        ]
    )
    conn.close = AsyncMock()

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        rows = await PostgresEngineAdapter().collect_index_inventory(PG_PARAMS)

    assert len(rows) == 2
    assert rows[0].is_unused is True
    assert rows[0].bloat_ratio is None
    assert rows[1].is_unused is False  # PK even with zero scans
    conn.close.assert_awaited_once()


def test_build_missing_index_ddl() -> None:
    ddl = _build_missing_index_ddl(
        schema_name="dbo",
        table_name="Orders",
        equality_columns="[CustomerId]",
        inequality_columns="[CreatedAt]",
        included_columns="[Amount]",
    )
    assert "CREATE NONCLUSTERED INDEX" in ddl
    assert "[dbo].[Orders]" in ddl
    assert "[CustomerId]" in ddl
    assert "[CreatedAt]" in ddl
    assert "INCLUDE ([Amount])" in ddl


@pytest.mark.asyncio
async def test_sqlserver_collect_index_inventory_merges_usage_and_frag() -> None:
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

    def_cols = (
        "database_name",
        "schema_name",
        "table_name",
        "index_name",
        "index_id",
        "type_desc",
        "is_primary_key",
        "is_unique",
        "filter_definition",
        "size_bytes",
        "key_columns",
        "included_columns",
    )
    def_rows = [
        ("app", "dbo", "T", "IX_unused", 2, "NONCLUSTERED", False, False, None, 4096, "a", None),
        ("app", "dbo", "T", "PK_T", 1, "CLUSTERED", True, True, None, 8192, "id", None),
    ]
    usage_cols = ("schema_name", "table_name", "index_name", "user_seeks", "user_scans", "user_lookups", "user_updates")
    usage_rows = [
        ("dbo", "T", "IX_unused", 0, 0, 0, 5),
        ("dbo", "T", "PK_T", 10, 0, 0, 1),
    ]
    frag_cols = ("schema_name", "table_name", "index_name", "avg_fragmentation_pct", "page_count")
    frag_rows = [("dbo", "T", "IX_unused", 25.0, 200)]

    fake_conn = _FakeConn(
        [
            ("all", (def_cols, def_rows)),
            ("all", (usage_cols, usage_rows)),
            ("all", (frag_cols, frag_rows)),
        ]
    )

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        rows = await SqlServerEngineAdapter().collect_index_inventory(SS_PARAMS)

    by_name = {r.index_name: r for r in rows}
    assert by_name["IX_unused"].is_unused is True
    assert by_name["IX_unused"].scans == 0
    assert by_name["IX_unused"].bloat_ratio == 0.25
    assert by_name["PK_T"].is_unused is False
    assert by_name["PK_T"].scans == 10


@pytest.mark.asyncio
async def test_sqlserver_collect_missing_indexes_builds_ddl() -> None:
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

    cols = (
        "database_name",
        "schema_name",
        "table_name",
        "equality_columns",
        "inequality_columns",
        "included_columns",
        "avg_user_impact",
        "user_seeks",
        "user_scans",
    )
    rows = [("app", "dbo", "Orders", "[CustomerId]", None, "[Amount]", 90.5, 100, 2)]
    fake_conn = _FakeConn([("all", (cols, rows))])

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        result = await SqlServerEngineAdapter().collect_missing_indexes(SS_PARAMS)

    assert len(result) == 1
    assert result[0].avg_user_impact == 90.5
    assert "CREATE NONCLUSTERED INDEX" in result[0].ddl_suggestion
    assert "[CustomerId]" in result[0].ddl_suggestion


@pytest.mark.asyncio
async def test_run_indexes_collection_writes_snapshot_and_recommendations() -> None:
    from app.modules.monitoring.collector import run_indexes_collection

    params = InstanceConnectionParams(
        host="h",
        port=5432,
        database="db",
        username="u",
        password="p",
        engine=Engine.POSTGRESQL,
    )
    inventory = [
        IndexInventoryRow(
            database_name="db",
            schema_name="public",
            table_name="t",
            index_name="ix_stale",
            size_bytes=100,
            scans=0,
            is_unused=True,
            bloat_ratio=None,
            is_primary_key=False,
            is_unique=False,
            details={},
        )
    ]
    adapter = AsyncMock()
    adapter.collect_index_inventory = AsyncMock(return_value=inventory)
    adapter.collect_missing_indexes = AsyncMock(return_value=[])

    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    upserts: list[dict] = []

    async def _upsert(*_args: object, **kwargs: object) -> str:
        upserts.append(dict(kwargs))
        return "rec-1"

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", return_value=session_cm),
        patch("app.modules.monitoring.collector.repository.get_connection_params", AsyncMock(return_value=params)),
        patch("app.modules.monitoring.collector.repository.get_last_collector_run", AsyncMock(return_value=(None, None))),
        patch("app.modules.monitoring.collector._adapter_for", MagicMock(return_value=adapter)),
        patch("app.modules.monitoring.collector.repository.insert_index_snapshot", AsyncMock(return_value="snap-1")),
        patch("app.modules.monitoring.collector.repository.upsert_recommendation", AsyncMock(side_effect=_upsert)),
        patch("app.modules.monitoring.collector.repository.insert_collector_run", AsyncMock(return_value="run-1")),
    ):
        result = await run_indexes_collection("inst-1")

    assert result.status == "ok"
    assert result.indexes_written == 1
    assert result.recommendations_upserted == 1
    assert upserts[0]["category"] == "unused_index"
    assert "DROP INDEX" in (upserts[0]["ddl_suggestion"] or "")


@pytest.mark.asyncio
async def test_run_indexes_collection_upserts_missing_from_ss() -> None:
    from app.modules.monitoring.collector import run_indexes_collection

    params = InstanceConnectionParams(
        host="h",
        port=1433,
        database="db",
        username="u",
        password="p",
        engine=Engine.SQLSERVER,
    )
    missing = [
        MissingIndexRow(
            database_name="db",
            schema_name="dbo",
            table_name="T",
            equality_columns="[a]",
            inequality_columns=None,
            included_columns=None,
            user_seeks=10,
            user_scans=0,
            avg_user_impact=50.0,
            ddl_suggestion="CREATE NONCLUSTERED INDEX [IX_T_a] ON [dbo].[T] ([a]);",
            evidence={"user_seeks": 10},
        )
    ]
    adapter = AsyncMock()
    adapter.collect_index_inventory = AsyncMock(return_value=[])
    adapter.collect_missing_indexes = AsyncMock(return_value=missing)

    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    upserts: list[dict] = []

    async def _upsert(*_args: object, **kwargs: object) -> str:
        upserts.append(dict(kwargs))
        return "rec-2"

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", return_value=session_cm),
        patch("app.modules.monitoring.collector.repository.get_connection_params", AsyncMock(return_value=params)),
        patch("app.modules.monitoring.collector.repository.get_last_collector_run", AsyncMock(return_value=(None, None))),
        patch("app.modules.monitoring.collector._adapter_for", MagicMock(return_value=adapter)),
        patch("app.modules.monitoring.collector.repository.insert_index_snapshot", AsyncMock()),
        patch("app.modules.monitoring.collector.repository.upsert_recommendation", AsyncMock(side_effect=_upsert)),
        patch("app.modules.monitoring.collector.repository.insert_collector_run", AsyncMock(return_value="run-2")),
    ):
        result = await run_indexes_collection("inst-1")

    assert result.status == "ok"
    assert result.recommendations_upserted == 1
    assert upserts[0]["category"] == "missing_index"


def test_evidence_key_stable() -> None:
    a = compute_recommendation_evidence_key(schema_name="dbo", table_name="T", index_or_columns="ix_a")
    b = compute_recommendation_evidence_key(schema_name="dbo", table_name="T", index_or_columns="ix_a")
    c = compute_recommendation_evidence_key(schema_name="dbo", table_name="T", index_or_columns="ix_b")
    assert a == b
    assert a != c


def test_scheduler_includes_indexes_tick() -> None:
    from app.modules.monitoring.scheduler import _ticks_for_engine

    by_name = {spec.name: spec for spec in _ticks_for_engine(Engine.POSTGRESQL)}
    assert by_name["indexes"].interval_seconds == 86400.0


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


def test_indexes_and_recommendations_api(authenticated_client: TestClient) -> None:
    snap_at = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
    indexes = [
        IndexSnapshotRecord(
            id="i1",
            instance_id="inst-1",
            database_name="db",
            schema_name="public",
            table_name="t",
            index_name="ix_a",
            snapshot_at=snap_at,
            size_bytes=100,
            scans=0,
            is_unused=True,
            bloat_ratio=None,
        )
    ]
    recs = [
        RecommendationRecord(
            id="r1",
            instance_id="inst-1",
            created_at=snap_at,
            category="unused_index",
            query_id=None,
            evidence={"index_name": "ix_a", "evidence_key": "abc"},
            ddl_suggestion='DROP INDEX IF EXISTS "public"."ix_a";',
            status="open",
        )
    ]

    with (
        patch("app.modules.monitoring.router.repository.instance_exists", AsyncMock(return_value=True)),
        patch("app.modules.monitoring.router.repository.list_index_snapshots", AsyncMock(return_value=indexes)),
        patch("app.modules.monitoring.router.repository.list_recommendations", AsyncMock(return_value=recs)),
        patch("app.modules.monitoring.router.repository.get_recommendation", AsyncMock(return_value=recs[0])),
    ):
        ir = authenticated_client.get("/api/monitoring/instances/inst-1/indexes")
        assert ir.status_code == status.HTTP_200_OK
        body = ir.json()
        assert len(body["indexes"]) == 1
        assert body["indexes"][0]["isUnused"] is True

        rr = authenticated_client.get("/api/monitoring/instances/inst-1/recommendations")
        assert rr.status_code == status.HTTP_200_OK
        assert rr.json()["recommendations"][0]["category"] == "unused_index"

        detail = authenticated_client.get("/api/monitoring/instances/inst-1/recommendations/r1")
        assert detail.status_code == status.HTTP_200_OK
        assert "DROP INDEX" in detail.json()["ddlSuggestion"]
