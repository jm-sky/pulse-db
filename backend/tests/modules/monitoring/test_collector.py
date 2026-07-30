"""Tests for the collector runtime: gap detection and the trivial-collection flow."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.monitoring.collector import _detect_gap, run_trivial_collection
from app.modules.monitoring.engine_adapter import (
    Engine,
    InstanceConnectionParams,
    TrivialSample,
)


class TestDetectGap:
    def test_no_previous_run_means_no_gap(self) -> None:
        gap_detected, gap_seconds = _detect_gap(started_at=datetime.now(UTC), last_finished_at=None, interval_ms=60_000)

        assert gap_detected is False
        assert gap_seconds is None

    def test_run_within_expected_cadence_is_not_a_gap(self) -> None:
        last_finished_at = datetime.now(UTC) - timedelta(seconds=60)

        gap_detected, gap_seconds = _detect_gap(started_at=datetime.now(UTC), last_finished_at=last_finished_at, interval_ms=60_000)

        assert gap_detected is False
        assert gap_seconds is None

    def test_run_more_than_threshold_late_is_a_gap(self) -> None:
        last_finished_at = datetime.now(UTC) - timedelta(seconds=200)

        gap_detected, gap_seconds = _detect_gap(started_at=datetime.now(UTC), last_finished_at=last_finished_at, interval_ms=60_000)

        assert gap_detected is True
        assert gap_seconds == pytest.approx(140, abs=1)


PARAMS = InstanceConnectionParams(host="localhost", port=5432, database="pulse_db", username="backend", password="changeme", engine=Engine.POSTGRESQL)


@pytest.mark.asyncio
async def test_run_trivial_collection_writes_metric_and_ok_run() -> None:
    mock_session = AsyncMock()

    @asynccontextmanager
    async def fake_session_factory():
        yield mock_session

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", fake_session_factory),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_last_collector_run = AsyncMock(return_value=(None, None))
        mock_repo.insert_instance_metric = AsyncMock()
        mock_repo.insert_collector_run = AsyncMock(return_value="run-1")

        mock_adapter = AsyncMock()
        mock_adapter.collect_trivial_sample = AsyncMock(return_value=TrivialSample(active_session_count=5, server_time=datetime.now(UTC)))
        mock_adapter_for.return_value = mock_adapter

        result = await run_trivial_collection("instance-1", interval_ms=30_000)

    assert result.status == "ok"
    assert result.active_session_count == 5
    assert result.gap_detected is False
    mock_repo.insert_instance_metric.assert_awaited_once()
    assert mock_repo.insert_instance_metric.await_args.kwargs["metric_id"] == "active_sessions"
    assert mock_repo.insert_instance_metric.await_args.kwargs["value"] == 5.0
    mock_repo.insert_collector_run.assert_awaited_once()
    assert mock_repo.insert_collector_run.await_args.kwargs["status"] == "ok"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_trivial_collection_records_error_without_raising() -> None:
    mock_session = AsyncMock()

    @asynccontextmanager
    async def fake_session_factory():
        yield mock_session

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", fake_session_factory),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_last_collector_run = AsyncMock(return_value=(None, None))
        mock_repo.insert_instance_metric = AsyncMock()
        mock_repo.insert_collector_run = AsyncMock(return_value="run-2")

        mock_adapter = AsyncMock()
        mock_adapter.collect_trivial_sample = AsyncMock(side_effect=ConnectionError("instance unreachable"))
        mock_adapter_for.return_value = mock_adapter

        result = await run_trivial_collection("instance-1", interval_ms=30_000)

    assert result.status == "error"
    assert result.error_message == "instance unreachable"
    assert result.active_session_count is None
    mock_repo.insert_instance_metric.assert_not_awaited()
    assert mock_repo.insert_collector_run.await_args.kwargs["status"] == "error"


@pytest.mark.asyncio
async def test_run_trivial_collection_flags_gap_when_previous_run_is_overdue() -> None:
    mock_session = AsyncMock()

    @asynccontextmanager
    async def fake_session_factory():
        yield mock_session

    stale_finished_at = datetime.now(UTC) - timedelta(seconds=200)

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", fake_session_factory),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_last_collector_run = AsyncMock(return_value=(stale_finished_at, 60_000))
        mock_repo.insert_instance_metric = AsyncMock()
        mock_repo.insert_collector_run = AsyncMock(return_value="run-3")

        mock_adapter = AsyncMock()
        mock_adapter.collect_trivial_sample = AsyncMock(return_value=TrivialSample(active_session_count=0, server_time=datetime.now(UTC)))
        mock_adapter_for.return_value = mock_adapter

        result = await run_trivial_collection("instance-1", interval_ms=60_000)

    assert result.gap_detected is True
    assert result.gap_seconds is not None
    assert mock_repo.insert_collector_run.await_args.kwargs["gap_detected"] is True
