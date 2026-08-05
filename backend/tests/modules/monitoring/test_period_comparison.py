"""Tests for baseline level 1 period comparison (Phase 1 element 6)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.monitoring.period_comparison import (
    PeriodMetrics,
    QueryComparisonRow,
    WaitPeriodMetrics,
    compare_instance_period_summary,
    compare_instance_query_periods,
    compare_query_period_rows,
    compare_wait_period_rows,
)
from app.modules.monitoring.repository import (
    InstancePeriodAggregate,
    QueryPeriodAggregate,
    WaitPeriodAggregate,
)
from main import app

BASELINE_START = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)
BASELINE_END = datetime(2026, 8, 2, 0, 0, tzinfo=UTC)
CURRENT_START = datetime(2026, 8, 3, 0, 0, tzinfo=UTC)
CURRENT_END = datetime(2026, 8, 4, 0, 0, tzinfo=UTC)


class TestCompareQueryPeriodRows:
    def test_detects_regression_when_avg_time_increases(self) -> None:
        baseline = {"q1": PeriodMetrics(calls=100, total_time_ms=1000.0, rows_returned=100)}
        current = {"q1": PeriodMetrics(calls=100, total_time_ms=2000.0, rows_returned=100)}

        rows = compare_query_period_rows(
            baseline_rows=baseline,
            current_rows=current,
            query_texts={"q1": "SELECT 1"},
            min_baseline_calls=1,
            min_current_calls=1,
        )

        assert len(rows) == 1
        row = rows[0]
        assert row.query_id == "q1"
        assert row.query_text == "SELECT 1"
        assert row.is_regression is True
        assert row.avg_time_ms_delta == pytest.approx(10.0)
        assert row.avg_time_ms_delta_pct == pytest.approx(100.0)

    def test_not_regression_when_avg_time_decreases(self) -> None:
        baseline = {"q1": PeriodMetrics(calls=10, total_time_ms=100.0, rows_returned=10)}
        current = {"q1": PeriodMetrics(calls=10, total_time_ms=50.0, rows_returned=10)}

        rows = compare_query_period_rows(
            baseline_rows=baseline,
            current_rows=current,
            query_texts={},
            min_baseline_calls=1,
            min_current_calls=1,
        )

        assert rows[0].is_regression is False
        assert rows[0].avg_time_ms_delta_pct == pytest.approx(-50.0)

    def test_respects_minimum_call_thresholds(self) -> None:
        baseline = {"q1": PeriodMetrics(calls=1, total_time_ms=10.0, rows_returned=1)}
        current = {"q1": PeriodMetrics(calls=100, total_time_ms=5000.0, rows_returned=100)}

        rows = compare_query_period_rows(
            baseline_rows=baseline,
            current_rows=current,
            query_texts={},
            min_baseline_calls=10,
            min_current_calls=10,
        )

        assert rows[0].is_regression is False

    def test_includes_queries_present_in_only_one_period(self) -> None:
        baseline = {"q1": PeriodMetrics(calls=5, total_time_ms=50.0, rows_returned=5)}
        current = {"q2": PeriodMetrics(calls=5, total_time_ms=50.0, rows_returned=5)}

        rows = compare_query_period_rows(
            baseline_rows=baseline,
            current_rows=current,
            query_texts={},
            min_baseline_calls=1,
            min_current_calls=1,
        )

        assert {row.query_id for row in rows} == {"q1", "q2"}
        by_id = {row.query_id: row for row in rows}
        assert by_id["q1"].current is None
        assert by_id["q2"].baseline is None


class TestCompareWaitPeriodRows:
    def test_computes_wait_deltas(self) -> None:
        baseline = {"lock": WaitPeriodMetrics(wait_class_id="lock", wait_seconds=10.0, sample_count=10, is_other=False)}
        current = {"lock": WaitPeriodMetrics(wait_class_id="lock", wait_seconds=15.0, sample_count=12, is_other=False)}

        rows = compare_wait_period_rows(
            baseline_rows=baseline,
            current_rows=current,
            wait_labels={"lock": "Lock"},
        )

        assert len(rows) == 1
        assert rows[0].wait_class_label == "Lock"
        assert rows[0].wait_seconds_delta == pytest.approx(5.0)
        assert rows[0].wait_seconds_delta_pct == pytest.approx(50.0)
        assert rows[0].sample_count_delta == 2


@pytest.mark.asyncio
async def test_compare_instance_query_periods_filters_regressions_and_limits() -> None:
    session = AsyncMock()
    baseline_rows = [
        QueryPeriodAggregate(query_id="slow", calls=10, total_time_ms=100.0, rows_returned=10),
        QueryPeriodAggregate(query_id="fast", calls=10, total_time_ms=50.0, rows_returned=10),
    ]
    current_rows = [
        QueryPeriodAggregate(query_id="slow", calls=10, total_time_ms=200.0, rows_returned=10),
        QueryPeriodAggregate(query_id="fast", calls=10, total_time_ms=25.0, rows_returned=10),
    ]

    with (
        patch("app.modules.monitoring.period_comparison.repository.instance_exists", AsyncMock(return_value=True)),
        patch(
            "app.modules.monitoring.period_comparison.repository.aggregate_query_stat_period",
            AsyncMock(side_effect=[baseline_rows, current_rows]),
        ),
        patch(
            "app.modules.monitoring.period_comparison.repository.get_query_texts",
            AsyncMock(return_value={"slow": "SELECT slow", "fast": "SELECT fast"}),
        ),
    ):
        result = await compare_instance_query_periods(
            session,
            instance_id="inst-1",
            baseline_start=BASELINE_START,
            baseline_end=BASELINE_END,
            current_start=CURRENT_START,
            current_end=CURRENT_END,
            regressions_only=True,
            limit=10,
        )

    assert result.instance_id == "inst-1"
    assert len(result.queries) == 1
    assert result.queries[0].query_id == "slow"
    assert result.queries[0].is_regression is True


@pytest.mark.asyncio
async def test_compare_instance_period_summary_builds_instance_and_wait_rows() -> None:
    session = AsyncMock()
    baseline_instance = InstancePeriodAggregate(calls=100, total_time_ms=1000.0, rows_returned=100)
    current_instance = InstancePeriodAggregate(calls=100, total_time_ms=1500.0, rows_returned=100)

    with (
        patch("app.modules.monitoring.period_comparison.repository.instance_exists", AsyncMock(return_value=True)),
        patch(
            "app.modules.monitoring.period_comparison.repository.aggregate_instance_query_stat_period",
            AsyncMock(side_effect=[baseline_instance, current_instance]),
        ),
        patch(
            "app.modules.monitoring.period_comparison.repository.aggregate_wait_period",
            AsyncMock(
                side_effect=[
                    [WaitPeriodAggregate(wait_class_id="lock", wait_seconds=5.0, sample_count=5, is_other=False)],
                    [WaitPeriodAggregate(wait_class_id="lock", wait_seconds=8.0, sample_count=6, is_other=False)],
                ]
            ),
        ),
        patch(
            "app.modules.monitoring.period_comparison.repository.get_wait_class_labels",
            AsyncMock(return_value={"lock": "Lock"}),
        ),
    ):
        summary = await compare_instance_period_summary(
            session,
            instance_id="inst-1",
            baseline_start=BASELINE_START,
            baseline_end=BASELINE_END,
            current_start=CURRENT_START,
            current_end=CURRENT_END,
        )

    assert summary.instance_baseline is not None
    assert summary.instance_current is not None
    assert summary.instance_avg_time_ms_delta_pct == pytest.approx(50.0)
    assert len(summary.waits) == 1
    assert summary.waits[0].wait_class_label == "Lock"


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


def test_query_period_comparison_endpoint_returns_openapi_payload(authenticated_client: TestClient) -> None:
    from app.modules.monitoring.period_comparison import PeriodWindow, QueryPeriodComparisonResult

    mock_result = QueryPeriodComparisonResult(
        instance_id="inst-1",
        baseline=PeriodWindow(start=BASELINE_START, end=BASELINE_END),
        current=PeriodWindow(start=CURRENT_START, end=CURRENT_END),
        queries=[
            QueryComparisonRow(
                query_id="q1",
                query_text="SELECT 1",
                baseline=PeriodMetrics(calls=10, total_time_ms=100.0, rows_returned=10),
                current=PeriodMetrics(calls=10, total_time_ms=150.0, rows_returned=10),
                avg_time_ms_delta=5.0,
                avg_time_ms_delta_pct=50.0,
                calls_delta=0,
                total_time_ms_delta=50.0,
                is_regression=True,
            )
        ],
    )

    with patch(
        "app.modules.monitoring.router.pc.compare_instance_query_periods",
        AsyncMock(return_value=mock_result),
    ):
        response = authenticated_client.get(
            "/api/monitoring/instances/inst-1/queries/period-comparison",
            params={
                "baseline_start": BASELINE_START.isoformat(),
                "baseline_end": BASELINE_END.isoformat(),
                "current_start": CURRENT_START.isoformat(),
                "current_end": CURRENT_END.isoformat(),
            },
        )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["instanceId"] == "inst-1"
    assert len(data["queries"]) == 1
    assert data["queries"][0]["isRegression"] is True
    assert data["queries"][0]["avgTimeMsDeltaPct"] == pytest.approx(50.0)


def test_period_comparison_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/monitoring/instances/inst-1/queries/period-comparison",
            params={
                "baseline_start": BASELINE_START.isoformat(),
                "baseline_end": BASELINE_END.isoformat(),
                "current_start": CURRENT_START.isoformat(),
                "current_end": CURRENT_END.isoformat(),
            },
        )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
