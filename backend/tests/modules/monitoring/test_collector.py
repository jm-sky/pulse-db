"""Tests for the collector runtime: gap detection and the trivial-collection flow."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.monitoring.adapters import PostgresEngineAdapter, SqlServerEngineAdapter
from app.modules.monitoring.adapters.postgres_adapter import WaitSamplingHistoryBatch, WaitSamplingHistoryRow
from app.modules.monitoring.collector import (
    _detect_gap,
    run_query_stats_collection,
    run_session_sample_collection,
    run_trivial_collection,
    run_wait_sampling_history_collection,
)
from app.modules.monitoring.engine_adapter import (
    ActiveSessionRow,
    Engine,
    InstanceConnectionParams,
    QueryStatRow,
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


def _fake_session_factory(mock_session):
    @asynccontextmanager
    async def factory():
        yield mock_session

    return factory


@pytest.mark.asyncio
async def test_run_session_sample_collection_resolves_query_and_wait_state() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_last_collector_run = AsyncMock(return_value=(None, None))
        mock_repo.insert_collector_run = AsyncMock(return_value="run-ash-1")
        mock_repo.find_query_id_by_engine_key = AsyncMock(return_value="query-1")
        mock_repo.upsert_query = AsyncMock(return_value="query-new")
        mock_repo.upsert_session_attr = AsyncMock(return_value="attr-1")
        mock_repo.ensure_wait_event = AsyncMock(return_value=False)
        mock_repo.insert_session_sample = AsyncMock()
        mock_repo.normalize_query_text = MagicMock(side_effect=lambda t: t.strip())
        mock_repo.compute_norm_hash = MagicMock(return_value="synthetic-hash")

        mock_adapter = AsyncMock()
        mock_adapter.collect_active_sessions = AsyncMock(
            return_value=[
                ActiveSessionRow(
                    db_user="app",
                    application_name="billing-service",
                    client_host="10.0.0.5",
                    wait_event_type="Lock",
                    wait_event="relation",
                    query_text="SELECT * FROM accounts WHERE id = $1",
                    engine_query_key="123",
                ),
                ActiveSessionRow(
                    db_user="app",
                    application_name="billing-service",
                    client_host="10.0.0.5",
                    wait_event_type=None,
                    wait_event=None,
                    query_text="UPDATE accounts SET balance = 0",
                    engine_query_key=None,
                ),
            ]
        )
        mock_adapter_for.return_value = mock_adapter

        result = await run_session_sample_collection("instance-1", interval_ms=1_000)

    assert result.status == "ok"
    assert result.session_count == 2
    assert mock_repo.insert_session_sample.await_count == 2

    first_call = mock_repo.insert_session_sample.await_args_list[0].kwargs
    assert first_call["query_id"] == "query-1"
    assert first_call["wait_event_native_name"] == "Lock:relation"
    assert first_call["is_idle"] is False

    second_call = mock_repo.insert_session_sample.await_args_list[1].kwargs
    assert second_call["query_id"] == "query-new"  # no native key -> synthesized
    assert second_call["wait_event_native_name"] is None  # on CPU

    assert mock_repo.insert_collector_run.await_args.kwargs["kind"] == "session_sample"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_session_sample_collection_maps_flat_sqlserver_wait_names() -> None:
    """SQL Server wait types are flat (migration 068); type:event is PostgreSQL-only."""
    mock_session = AsyncMock()
    sqlserver_params = InstanceConnectionParams(
        host="mssql.example",
        port=1433,
        database="pulse_db",
        username="backend",
        password="changeme",
        engine=Engine.SQLSERVER,
    )

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=sqlserver_params)
        mock_repo.get_last_collector_run = AsyncMock(return_value=(None, None))
        mock_repo.insert_collector_run = AsyncMock(return_value="run-ash-mssql")
        mock_repo.find_query_id_by_engine_key = AsyncMock(return_value="query-1")
        mock_repo.upsert_session_attr = AsyncMock(return_value="attr-1")
        mock_repo.ensure_wait_event = AsyncMock(return_value=False)
        mock_repo.insert_session_sample = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.collect_active_sessions = AsyncMock(
            return_value=[
                ActiveSessionRow(
                    db_user="app",
                    application_name="portal",
                    client_host="10.0.0.5",
                    wait_event_type=None,
                    wait_event="LCK_M_X",
                    query_text="UPDATE t SET x = 1",
                    engine_query_key="0xABC",
                ),
            ]
        )
        mock_adapter_for.return_value = mock_adapter

        result = await run_session_sample_collection("instance-mssql", interval_ms=1_000)

    assert result.status == "ok"
    assert mock_repo.insert_session_sample.await_args.kwargs["wait_event_native_name"] == "LCK_M_X"
    mock_repo.ensure_wait_event.assert_awaited_once()
    assert mock_repo.ensure_wait_event.await_args.kwargs["native_name"] == "LCK_M_X"


@pytest.mark.asyncio
async def test_run_session_sample_collection_records_error_without_raising() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_last_collector_run = AsyncMock(return_value=(None, None))
        mock_repo.insert_collector_run = AsyncMock(return_value="run-ash-2")

        mock_adapter = AsyncMock()
        mock_adapter.collect_active_sessions = AsyncMock(side_effect=ConnectionError("instance unreachable"))
        mock_adapter_for.return_value = mock_adapter

        result = await run_session_sample_collection("instance-1")

    assert result.status == "error"
    assert result.error_message == "instance unreachable"
    assert result.session_count is None
    assert mock_repo.insert_collector_run.await_args.kwargs["status"] == "error"


@pytest.mark.asyncio
async def test_run_query_stats_collection_writes_delta_against_cursor() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_last_collector_run = AsyncMock(return_value=(None, None))
        mock_repo.insert_collector_run = AsyncMock(return_value="run-qs-1")
        mock_repo.upsert_query = AsyncMock(return_value="query-1")
        mock_repo.normalize_query_text = MagicMock(side_effect=lambda t: t.strip())

        cursor = MagicMock(last_calls=10, last_total_time_ms=100.0, last_rows=10, last_shared_blks_read=1, last_shared_blks_written=0)
        mock_repo.get_query_stat_cursor = AsyncMock(return_value=cursor)
        mock_repo.upsert_query_stat_cursor = AsyncMock()
        mock_repo.insert_query_stat_delta = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.collect_query_stats = AsyncMock(
            return_value=[
                QueryStatRow(
                    engine_query_key="42",
                    normalized_text="SELECT * FROM accounts WHERE id = $1",
                    calls=15,
                    total_time_ms=150.0,
                    rows=15,
                    shared_blks_read=2,
                    shared_blks_written=0,
                )
            ]
        )
        mock_adapter_for.return_value = mock_adapter

        result = await run_query_stats_collection("instance-1", interval_ms=60_000)

    assert result.status == "ok"
    assert result.queries_seen == 1
    assert result.deltas_written == 1
    mock_repo.insert_query_stat_delta.assert_awaited_once()
    delta_kwargs = mock_repo.insert_query_stat_delta.await_args.kwargs
    assert delta_kwargs["calls"] == 5
    assert delta_kwargs["total_time_ms"] == 50.0
    mock_repo.upsert_query_stat_cursor.assert_awaited_once()
    assert mock_repo.insert_collector_run.await_args.kwargs["kind"] == "query_stats"


@pytest.mark.asyncio
async def test_run_query_stats_collection_skips_delta_on_first_sighting() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_last_collector_run = AsyncMock(return_value=(None, None))
        mock_repo.insert_collector_run = AsyncMock(return_value="run-qs-2")
        mock_repo.upsert_query = AsyncMock(return_value="query-1")
        mock_repo.normalize_query_text = MagicMock(side_effect=lambda t: t.strip())
        mock_repo.get_query_stat_cursor = AsyncMock(return_value=None)
        mock_repo.upsert_query_stat_cursor = AsyncMock()
        mock_repo.insert_query_stat_delta = AsyncMock()

        mock_adapter = AsyncMock()
        mock_adapter.collect_query_stats = AsyncMock(
            return_value=[
                QueryStatRow(
                    engine_query_key="42",
                    normalized_text="SELECT 1",
                    calls=1,
                    total_time_ms=1.0,
                    rows=1,
                    shared_blks_read=0,
                    shared_blks_written=0,
                )
            ]
        )
        mock_adapter_for.return_value = mock_adapter

        result = await run_query_stats_collection("instance-1")

    assert result.status == "ok"
    assert result.queries_seen == 1
    assert result.deltas_written == 0
    mock_repo.insert_query_stat_delta.assert_not_awaited()
    mock_repo.upsert_query_stat_cursor.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_wait_sampling_history_collection_writes_samples_with_extension_period() -> None:
    mock_session = AsyncMock()
    watermark = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
    sample_ts = datetime(2026, 7, 30, 12, 0, 1, tzinfo=UTC)

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_wait_sampling_watermark = AsyncMock(return_value=watermark)
        mock_repo.get_latest_clock_offset_ms = AsyncMock(return_value=25.0)
        mock_repo.set_wait_sampling_watermark = AsyncMock()
        mock_repo.insert_collector_run = AsyncMock(return_value="run-wsh-1")
        mock_repo.find_query_id_by_engine_key = AsyncMock(return_value="query-1")
        mock_repo.upsert_query = AsyncMock(return_value="query-new")
        mock_repo.upsert_session_attr = AsyncMock(return_value="attr-1")
        mock_repo.ensure_wait_event = AsyncMock(return_value=False)
        mock_repo.insert_session_sample = AsyncMock()
        mock_repo.normalize_query_text = MagicMock(side_effect=lambda t: t.strip())
        mock_repo.compute_norm_hash = MagicMock(return_value="synthetic-hash")

        mock_adapter = AsyncMock(spec=PostgresEngineAdapter)
        mock_adapter.collect_wait_sampling_history = AsyncMock(
            return_value=WaitSamplingHistoryBatch(
                rows=[
                    WaitSamplingHistoryRow(
                        pid=5690,
                        sampled_at=sample_ts,
                        wait_event_type="Lock",
                        wait_event="transactionid",
                        engine_query_key="42",
                        db_user="app",
                        application_name="billing-service",
                        client_host="10.0.0.5",
                        query_text="UPDATE accounts SET balance = 0",
                    )
                ],
                history_period_ms=10,
                ring_buffer_min_ts=watermark,
            )
        )
        mock_adapter_for.return_value = mock_adapter

        result = await run_wait_sampling_history_collection("instance-1")

    assert result.status == "ok"
    assert result.samples_written == 1
    assert result.distinct_sessions == 1
    assert result.history_period_ms == 10
    assert result.gap_detected is False
    assert "pg_wait_sampling active" in result.note

    mock_repo.insert_session_sample.assert_awaited_once()
    sample_kwargs = mock_repo.insert_session_sample.await_args.kwargs
    assert sample_kwargs["interval_ms"] == 10
    assert sample_kwargs["sampled_at"] == sample_ts - timedelta(milliseconds=25.0)  # clock-offset corrected
    assert sample_kwargs["query_id"] == "query-1"

    mock_repo.set_wait_sampling_watermark.assert_awaited_once_with(mock_session, instance_id="instance-1", last_ts=sample_ts)
    assert mock_repo.insert_collector_run.await_args.kwargs["kind"] == "wait_sampling_history"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_wait_sampling_history_collection_notes_when_extension_missing() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_wait_sampling_watermark = AsyncMock(return_value=None)
        mock_repo.get_latest_clock_offset_ms = AsyncMock(return_value=None)
        mock_repo.insert_collector_run = AsyncMock(return_value="run-wsh-2")

        mock_adapter = AsyncMock(spec=PostgresEngineAdapter)
        mock_adapter.collect_wait_sampling_history = AsyncMock(return_value=WaitSamplingHistoryBatch(rows=[], history_period_ms=None, ring_buffer_min_ts=None))
        mock_adapter_for.return_value = mock_adapter

        result = await run_wait_sampling_history_collection("instance-1")

    assert result.status == "ok"
    assert result.samples_written == 0
    assert result.history_period_ms is None
    assert "not installed" in result.note


@pytest.mark.asyncio
async def test_run_wait_sampling_history_collection_detects_ring_buffer_overrun() -> None:
    mock_session = AsyncMock()
    watermark = datetime(2026, 7, 30, 12, 0, 0, tzinfo=UTC)
    ring_min_ts = watermark + timedelta(seconds=30)  # ring buffer already rolled past our watermark

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        mock_repo.get_connection_params = AsyncMock(return_value=PARAMS)
        mock_repo.get_wait_sampling_watermark = AsyncMock(return_value=watermark)
        mock_repo.get_latest_clock_offset_ms = AsyncMock(return_value=None)
        mock_repo.insert_collector_run = AsyncMock(return_value="run-wsh-3")

        mock_adapter = AsyncMock(spec=PostgresEngineAdapter)
        mock_adapter.collect_wait_sampling_history = AsyncMock(return_value=WaitSamplingHistoryBatch(rows=[], history_period_ms=10, ring_buffer_min_ts=ring_min_ts))
        mock_adapter_for.return_value = mock_adapter

        result = await run_wait_sampling_history_collection("instance-1")

    assert result.gap_detected is True
    assert result.gap_seconds == pytest.approx(30.0)
    assert mock_repo.insert_collector_run.await_args.kwargs["gap_detected"] is True


@pytest.mark.asyncio
async def test_run_wait_sampling_history_collection_rejects_non_postgres_engine() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.collector.AsyncSessionLocal", _fake_session_factory(mock_session)),
        patch("app.modules.monitoring.collector.repository") as mock_repo,
        patch("app.modules.monitoring.collector._adapter_for") as mock_adapter_for,
    ):
        sqlserver_params = InstanceConnectionParams(host="mssql.example", port=1433, database="pulse_db", username="backend", password="changeme", engine=Engine.SQLSERVER)
        mock_repo.get_connection_params = AsyncMock(return_value=sqlserver_params)
        mock_adapter_for.return_value = AsyncMock(spec=SqlServerEngineAdapter)

        with pytest.raises(NotImplementedError):
            await run_wait_sampling_history_collection("instance-1")
