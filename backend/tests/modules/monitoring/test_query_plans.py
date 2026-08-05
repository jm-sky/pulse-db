"""Tests for Phase 1 element 3: execution plans + plan-change detection."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.monitoring.adapters.postgres_adapter import (
    PostgresEngineAdapter,
    _is_explainable,
)
from app.modules.monitoring.adapters.sqlserver_adapter import SqlServerEngineAdapter
from app.modules.monitoring.engine_adapter import Engine, InstanceConnectionParams, QueryPlanRow
from app.modules.monitoring.repository import (
    PlanChangeRow,
    QueryPlanDetail,
    QueryPlanListItem,
    QueryPlanUpsertResult,
    compute_plan_hash,
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


class TestPlanHash:
    def test_stable_for_same_body(self) -> None:
        assert compute_plan_hash('[{"Plan":1}]') == compute_plan_hash('[{"Plan":1}]')

    def test_differs_when_body_changes(self) -> None:
        assert compute_plan_hash("<ShowPlanXML/>") != compute_plan_hash("<ShowPlanXML version='2'/>")


class TestIsExplainable:
    def test_accepts_simple_select(self) -> None:
        assert _is_explainable("SELECT 1") is True

    def test_rejects_multi_statement(self) -> None:
        assert _is_explainable("SELECT 1; SELECT 2") is False

    def test_rejects_nested_explain(self) -> None:
        assert _is_explainable("EXPLAIN SELECT 1") is False

    def test_allows_trailing_semicolon(self) -> None:
        assert _is_explainable("SELECT 1;") is True


@pytest.mark.asyncio
async def test_postgres_collect_query_plans_skips_explain_errors() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1)
    conn.close = AsyncMock()

    async def fetch_side_effect(sql, *args):
        if isinstance(sql, str) and sql.startswith("EXPLAIN"):
            if "secret" in sql:
                raise PermissionError("permission denied")
            return [({"Plan": {"Node Type": "Result"}},)]
        return [
            {"engine_query_key": "1", "normalized_text": "SELECT 1"},
            {"engine_query_key": "2", "normalized_text": "SELECT * FROM secret"},
        ]

    conn.fetch = AsyncMock(side_effect=fetch_side_effect)

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        plans = await PostgresEngineAdapter().collect_query_plans(PG_PARAMS, top_n=20)

    assert len(plans) == 1
    assert plans[0].engine_query_key == "1"
    assert plans[0].plan_format == "json"
    assert "Plan" in plans[0].plan_body
    conn.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_postgres_collect_query_plans_empty_without_extension() -> None:
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)
    conn.close = AsyncMock()

    with patch("app.modules.monitoring.adapters.postgres_adapter.asyncpg.connect", AsyncMock(return_value=conn)):
        plans = await PostgresEngineAdapter().collect_query_plans(PG_PARAMS)

    assert plans == []
    conn.fetch.assert_not_called()


@pytest.mark.asyncio
async def test_sqlserver_collect_query_plans_maps_xml_rows() -> None:
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

        def fetchone(self) -> object:
            assert self._pending is not None and self._pending[0] == "one"
            return self._pending[1]

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

    columns = ("engine_query_key", "normalized_text", "plan_body")
    rows = [
        ("0xDEAD", "SELECT 1", "<ShowPlanXML>a</ShowPlanXML>"),
        ("NULL", "skip", "<x/>"),
        ("0xBEEF", "SELECT 2", None),
    ]
    fake_conn = _FakeConn([("all", (columns, rows))])

    with patch("app.modules.monitoring.adapters.sqlserver_adapter.pytds.connect", MagicMock(return_value=fake_conn)):
        plans = await SqlServerEngineAdapter().collect_query_plans(SS_PARAMS, top_n=20)

    assert len(plans) == 1
    assert plans[0].engine_query_key == "0xDEAD"
    assert plans[0].plan_format == "xml"
    assert plans[0].plan_body == "<ShowPlanXML>a</ShowPlanXML>"


@pytest.mark.asyncio
async def test_run_query_plans_collection_counts_new_plans() -> None:
    from app.modules.monitoring.collector import run_query_plans_collection

    params = InstanceConnectionParams(
        host="h",
        port=5432,
        database="db",
        username="u",
        password="p",
        engine=Engine.POSTGRESQL,
    )
    plan_rows = [
        QueryPlanRow(
            engine_query_key="42",
            normalized_text="SELECT 1",
            plan_format="json",
            plan_body='[{"Plan":1}]',
        ),
        QueryPlanRow(
            engine_query_key="42",
            normalized_text="SELECT 1",
            plan_format="json",
            plan_body='[{"Plan":2}]',
        ),
    ]

    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)

    adapter = AsyncMock()
    adapter.collect_query_plans = AsyncMock(return_value=plan_rows)

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", return_value=session_cm),
        patch("app.modules.monitoring.collector.repository.get_connection_params", AsyncMock(return_value=params)),
        patch(
            "app.modules.monitoring.collector.repository.get_last_collector_run",
            AsyncMock(return_value=(None, None)),
        ),
        patch("app.modules.monitoring.collector._adapter_for", return_value=adapter),
        patch("app.modules.monitoring.collector.repository.upsert_query", AsyncMock(return_value="q1")),
        patch(
            "app.modules.monitoring.collector.repository.upsert_plan_text",
            AsyncMock(side_effect=["hash1", "hash2"]),
        ),
        patch(
            "app.modules.monitoring.collector.repository.upsert_query_plan",
            AsyncMock(
                side_effect=[
                    QueryPlanUpsertResult(plan_hash="hash1", is_new=True),
                    QueryPlanUpsertResult(plan_hash="hash2", is_new=True),
                ]
            ),
        ),
        patch("app.modules.monitoring.collector.repository.insert_collector_run", AsyncMock(return_value="run-1")),
    ):
        result = await run_query_plans_collection("inst-1")

    assert result.status == "ok"
    assert result.plans_seen == 2
    assert result.plans_new == 2
    assert result.run_id == "run-1"


def test_scheduler_includes_query_plans_tick() -> None:
    from app.modules.monitoring.scheduler import _ticks_for_engine

    names = {spec.name for spec in _ticks_for_engine(Engine.POSTGRESQL)}
    assert "query_plans" in names
    by_name = {spec.name: spec for spec in _ticks_for_engine(Engine.SQLSERVER)}
    assert by_name["query_plans"].interval_seconds == 600.0


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


def test_plans_api_list_and_changes(authenticated_client: TestClient) -> None:
    first_seen = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)
    plans = [
        QueryPlanListItem(plan_hash="h1", plan_format="json", first_seen=first_seen, last_seen=first_seen),
        QueryPlanListItem(
            plan_hash="h2",
            plan_format="json",
            first_seen=datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
            last_seen=datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
        ),
    ]
    changes = [
        PlanChangeRow(
            query_id="q1",
            plan_hash="h2",
            plan_format="json",
            first_seen=datetime(2026, 8, 5, 11, 0, tzinfo=UTC),
            query_text="SELECT 1",
            plan_count=2,
        )
    ]
    detail = QueryPlanDetail(
        plan_hash="h1",
        plan_format="json",
        plan_body='[{"Plan":1}]',
        first_seen=first_seen,
        last_seen=first_seen,
    )

    with (
        patch("app.modules.monitoring.router.repository.instance_exists", AsyncMock(return_value=True)),
        patch("app.modules.monitoring.router.repository.query_belongs_to_instance", AsyncMock(return_value=True)),
        patch("app.modules.monitoring.router.repository.list_query_plans", AsyncMock(return_value=plans)),
        patch("app.modules.monitoring.router.repository.list_plan_changes", AsyncMock(return_value=changes)),
        patch("app.modules.monitoring.router.repository.get_query_plan_detail", AsyncMock(return_value=detail)),
    ):
        list_resp = authenticated_client.get("/api/monitoring/instances/inst-1/queries/q1/plans")
        assert list_resp.status_code == status.HTTP_200_OK
        body = list_resp.json()
        assert body["isPlanChange"] is True
        assert len(body["plans"]) == 2

        changes_resp = authenticated_client.get(
            "/api/monitoring/instances/inst-1/queries/plan-changes",
            params={"since": "2026-08-05T00:00:00Z"},
        )
        assert changes_resp.status_code == status.HTTP_200_OK
        assert changes_resp.json()["changes"][0]["isPlanChange"] is True

        detail_resp = authenticated_client.get("/api/monitoring/instances/inst-1/queries/q1/plans/h1")
        assert detail_resp.status_code == status.HTTP_200_OK
        assert detail_resp.json()["planBody"] == '[{"Plan":1}]'
