"""Tests for waits timeline and instance list APIs."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.monitoring.engine_adapter import Engine
from app.modules.monitoring.repository import InstanceListRow, WaitsTimelineRow
from app.modules.monitoring.waits_timeline import (
    WaitsTimelinePoint,
    WaitsTimelineResult,
    WaitsTimelineSeries,
    _derive_collector_status,
    get_waits_timeline,
    list_instance_summaries,
)
from main import app

START = datetime(2026, 8, 5, 9, 0, tzinfo=UTC)
END = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


class TestDeriveCollectorStatus:
    def test_unknown_when_no_data(self) -> None:
        now = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)
        assert _derive_collector_status(
            last_sample_at=None,
            last_finished_at=None,
            last_status=None,
            gap_detected=None,
            now=now,
        ) == "unknown"

    def test_degraded_on_gap(self) -> None:
        now = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)
        assert _derive_collector_status(
            last_sample_at=now,
            last_finished_at=now,
            last_status="ok",
            gap_detected=True,
            now=now,
        ) == "degraded"

    def test_ok_when_recent_sample(self) -> None:
        now = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)
        assert _derive_collector_status(
            last_sample_at=now,
            last_finished_at=now,
            last_status="ok",
            gap_detected=False,
            now=now,
        ) == "ok"


@pytest.mark.asyncio
async def test_list_instance_summaries_maps_rows() -> None:
    session = AsyncMock()
    recent = datetime.now(UTC)
    rows = [
        InstanceListRow(
            id="inst-1",
            name="pg-local",
            engine=Engine.POSTGRESQL,
            host="localhost",
            port=5432,
            is_active=True,
            last_sample_at=recent,
            last_collector_finished_at=recent,
            last_collector_status="ok",
            last_collector_gap_detected=False,
        ),
    ]
    with patch("app.modules.monitoring.waits_timeline.repository.list_instances_with_status", AsyncMock(return_value=rows)):
        result = await list_instance_summaries(session)
    assert len(result.instances) == 1
    assert result.instances[0].id == "inst-1"
    assert result.instances[0].collector_status == "ok"


@pytest.mark.asyncio
async def test_get_waits_timeline_groups_series() -> None:
    session = AsyncMock()
    timeline_rows = [
        WaitsTimelineRow(
            bucket_start=START,
            wait_class_id="cpu",
            wait_seconds=1.0,
            sample_count=60,
            is_other=False,
        ),
        WaitsTimelineRow(
            bucket_start=START,
            wait_class_id="lock",
            wait_seconds=2.0,
            sample_count=30,
            is_other=False,
        ),
    ]
    with (
        patch("app.modules.monitoring.waits_timeline.repository.instance_exists", AsyncMock(return_value=True)),
        patch(
            "app.modules.monitoring.waits_timeline.repository.fetch_waits_timeline",
            AsyncMock(return_value=timeline_rows),
        ),
        patch(
            "app.modules.monitoring.waits_timeline.repository.get_wait_class_labels",
            AsyncMock(return_value={"cpu": "CPU", "lock": "Lock"}),
        ),
    ):
        result = await get_waits_timeline(session, instance_id="inst-1", start=START, end=END, granularity="1m")
    assert result.instance_id == "inst-1"
    assert result.granularity == "1m"
    assert len(result.series) == 2
    labels = {series.label for series in result.series}
    assert labels == {"CPU", "Lock"}


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


def test_list_instances_endpoint(authenticated_client: TestClient) -> None:
    from app.modules.monitoring.waits_timeline import InstanceListResult, InstanceSummary

    mock_result = InstanceListResult(
        instances=[
            InstanceSummary(
                id="inst-1",
                name="pg-local",
                engine="postgresql",
                host="localhost",
                port=5432,
                is_active=True,
                collector_status="ok",
                last_sample_at=START,
            ),
        ],
    )
    with patch("app.modules.monitoring.router.wt.list_instance_summaries", AsyncMock(return_value=mock_result)):
        response = authenticated_client.get("/api/monitoring/instances")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["instances"]) == 1
    assert data["instances"][0]["name"] == "pg-local"


def test_waits_timeline_endpoint(authenticated_client: TestClient) -> None:
    mock_result = WaitsTimelineResult(
        instance_id="inst-1",
        granularity="1m",
        start=START,
        end=END,
        series=[
            WaitsTimelineSeries(
                wait_class_id="cpu",
                label="CPU",
                points=[WaitsTimelinePoint(bucket_start=START, wait_seconds=1.5, sample_count=60)],
            ),
        ],
    )
    with patch("app.modules.monitoring.router.wt.get_waits_timeline", AsyncMock(return_value=mock_result)):
        response = authenticated_client.get(
            "/api/monitoring/instances/inst-1/waits/timeline",
            params={"start": START.isoformat(), "end": END.isoformat()},
        )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["instanceId"] == "inst-1"
    assert data["series"][0]["label"] == "CPU"
    assert data["series"][0]["points"][0]["waitSeconds"] == pytest.approx(1.5)
