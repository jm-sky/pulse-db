"""Tests for rollups (ash_1m, ash_1h, query_stat_1h): bucket boundary math,
top-N+other truncation, and the watermark-advancing job flow (mocked
repository/session -- real-Postgres coverage is manual, same pattern as
test_collector.py/test_partitions.py, since raw-DDL tables can't run under
this suite's SQLite test database)."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.monitoring.repository import AshBucketRow, QueryStatBucketRow
from app.modules.monitoring.rollups import (
    _apply_top_n_and_other_ash,
    _apply_top_n_and_other_query_stat,
    _last_closed_hour_bucket,
    _last_closed_minute_bucket,
    _last_hour_with_complete_source,
    run_ash_1h_rollup,
    run_ash_1m_rollup,
    run_query_stat_1h_rollup,
)


class TestBucketBoundaries:
    def test_last_closed_minute_bucket_respects_close_delay(self) -> None:
        now = datetime(2026, 7, 31, 12, 5, 30, tzinfo=UTC)

        last_closed = _last_closed_minute_bucket(now, close_delay_seconds=120)

        # cutoff = 12:03:30 -> floor to 12:03:00 -> last *closed* bucket is 12:02:00
        assert last_closed == datetime(2026, 7, 31, 12, 2, 0, tzinfo=UTC)

    def test_last_closed_hour_bucket_respects_close_delay(self) -> None:
        now = datetime(2026, 7, 31, 12, 5, 0, tzinfo=UTC)

        last_closed = _last_closed_hour_bucket(now, close_delay_seconds=120)

        assert last_closed == datetime(2026, 7, 31, 11, 0, 0, tzinfo=UTC)

    def test_last_hour_with_complete_source_when_watermark_is_final_minute(self) -> None:
        watermark = datetime(2026, 7, 31, 12, 59, 0, tzinfo=UTC)

        assert _last_hour_with_complete_source(watermark) == datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)

    def test_last_hour_with_complete_source_when_hour_still_partial(self) -> None:
        watermark = datetime(2026, 7, 31, 12, 30, 0, tzinfo=UTC)

        assert _last_hour_with_complete_source(watermark) == datetime(2026, 7, 31, 11, 0, 0, tzinfo=UTC)


class TestTopNAndOther:
    def test_ash_rows_at_or_under_top_n_pass_through_unchanged(self) -> None:
        rows = [AshBucketRow(query_id="q1", wait_class_id="lock", wait_seconds=5.0, sample_count=5)]

        result = _apply_top_n_and_other_ash(rows, top_n=20)

        assert result == [(rows[0], False)]

    def test_ash_overflow_folds_into_single_other_row(self) -> None:
        rows = [AshBucketRow(query_id=f"q{i}", wait_class_id="lock", wait_seconds=float(10 - i), sample_count=1) for i in range(25)]

        result = _apply_top_n_and_other_ash(rows, top_n=20)

        assert len(result) == 21
        kept, other = result[:20], result[20]
        assert all(not is_other for _row, is_other in kept)
        assert [row.query_id for row, _ in kept] == [f"q{i}" for i in range(20)]
        other_row, is_other = other
        assert is_other is True
        assert other_row.query_id is None
        assert other_row.wait_class_id is None
        assert other_row.sample_count == 5
        assert other_row.wait_seconds == pytest.approx(sum(10 - i for i in range(20, 25)))

    def test_query_stat_overflow_ranked_by_total_time_ms(self) -> None:
        rows = [QueryStatBucketRow(query_id=f"q{i}", calls=1, total_time_ms=float(30 - i), rows_returned=1, shared_blks_read=0, shared_blks_written=0) for i in range(3)]

        result = _apply_top_n_and_other_query_stat(rows, top_n=2)

        assert len(result) == 3
        assert [row.query_id for row, is_other in result[:2]] == ["q0", "q1"]
        other_row, is_other = result[2]
        assert is_other is True
        assert other_row.query_id is None
        assert other_row.calls == 1
        assert other_row.total_time_ms == pytest.approx(28.0)


def _mock_session_factory(mock_session: AsyncMock):
    @asynccontextmanager
    async def fake_session_factory():
        yield mock_session

    return fake_session_factory


@pytest.mark.asyncio
async def test_run_ash_1m_rollup_no_data_yet_is_a_noop() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.rollups.AsyncSessionLocal", _mock_session_factory(mock_session)),
        patch("app.modules.monitoring.rollups.repository") as mock_repo,
    ):
        mock_repo.get_rollup_cursor = AsyncMock(return_value=None)
        mock_repo.get_earliest_session_sample_at = AsyncMock(return_value=None)

        result = await run_ash_1m_rollup("instance-1")

    assert result.buckets_processed == 0
    assert result.rows_written == 0
    assert result.last_bucket is None
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_ash_1m_rollup_processes_closed_buckets_and_advances_watermark() -> None:
    mock_session = AsyncMock()
    now = datetime(2026, 7, 31, 12, 5, 0, tzinfo=UTC)

    with (
        patch("app.modules.monitoring.rollups.AsyncSessionLocal", _mock_session_factory(mock_session)),
        patch("app.modules.monitoring.rollups.repository") as mock_repo,
    ):
        mock_repo.get_rollup_cursor = AsyncMock(return_value=datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC))
        mock_repo.aggregate_session_sample_bucket = AsyncMock(
            return_value=[
                AshBucketRow(query_id="q1", wait_class_id="lock", wait_seconds=3.0, sample_count=3),
            ]
        )
        mock_repo.insert_ash_rollup_row = AsyncMock()
        mock_repo.set_rollup_cursor = AsyncMock()

        result = await run_ash_1m_rollup("instance-1", now=now, close_delay_seconds=120)

    # watermark 12:00 -> next bucket 12:01; last closed bucket at 12:05 cutoff = 12:02
    assert result.buckets_processed == 2
    assert result.rows_written == 2
    assert result.last_bucket == datetime(2026, 7, 31, 12, 2, 0, tzinfo=UTC)
    assert mock_repo.set_rollup_cursor.await_count == 2
    mock_repo.set_rollup_cursor.assert_awaited_with(mock_session, instance_id="instance-1", kind="ash_1m", watermark=datetime(2026, 7, 31, 12, 2, 0, tzinfo=UTC))
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_ash_1m_rollup_empty_bucket_still_advances_watermark_without_writing_rows() -> None:
    mock_session = AsyncMock()
    now = datetime(2026, 7, 31, 12, 4, 0, tzinfo=UTC)

    with (
        patch("app.modules.monitoring.rollups.AsyncSessionLocal", _mock_session_factory(mock_session)),
        patch("app.modules.monitoring.rollups.repository") as mock_repo,
    ):
        mock_repo.get_rollup_cursor = AsyncMock(return_value=datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC))
        mock_repo.aggregate_session_sample_bucket = AsyncMock(return_value=[])
        mock_repo.insert_ash_rollup_row = AsyncMock()
        mock_repo.set_rollup_cursor = AsyncMock()

        result = await run_ash_1m_rollup("instance-1", now=now, close_delay_seconds=120)

    assert result.buckets_processed == 1
    assert result.rows_written == 0
    mock_repo.insert_ash_rollup_row.assert_not_awaited()
    mock_repo.set_rollup_cursor.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_ash_1m_rollup_respects_max_buckets_batch_limit() -> None:
    mock_session = AsyncMock()
    now = datetime(2026, 7, 31, 13, 0, 0, tzinfo=UTC)

    with (
        patch("app.modules.monitoring.rollups.AsyncSessionLocal", _mock_session_factory(mock_session)),
        patch("app.modules.monitoring.rollups.repository") as mock_repo,
    ):
        mock_repo.get_rollup_cursor = AsyncMock(return_value=datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC))
        mock_repo.aggregate_session_sample_bucket = AsyncMock(return_value=[])
        mock_repo.insert_ash_rollup_row = AsyncMock()
        mock_repo.set_rollup_cursor = AsyncMock()

        result = await run_ash_1m_rollup("instance-1", now=now, close_delay_seconds=120, max_buckets=5)

    assert result.buckets_processed == 5
    assert result.last_bucket == datetime(2026, 7, 31, 12, 5, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_run_ash_1h_rollup_waits_for_ash_1m_watermark_to_cover_the_hour() -> None:
    mock_session = AsyncMock()
    now = datetime(2026, 7, 31, 14, 0, 0, tzinfo=UTC)

    with (
        patch("app.modules.monitoring.rollups.AsyncSessionLocal", _mock_session_factory(mock_session)),
        patch("app.modules.monitoring.rollups.repository") as mock_repo,
    ):

        async def fake_get_rollup_cursor(_session, *, instance_id, kind):
            if kind == "ash_1m":
                return datetime(2026, 7, 31, 12, 30, 0, tzinfo=UTC)  # hour 12 still partial
            return None  # no ash_1h watermark yet

        mock_repo.get_rollup_cursor = AsyncMock(side_effect=fake_get_rollup_cursor)
        mock_repo.get_earliest_session_sample_at = AsyncMock(return_value=datetime(2026, 7, 31, 10, 0, 0, tzinfo=UTC))
        mock_repo.aggregate_ash_1m_bucket = AsyncMock(return_value=[])
        mock_repo.insert_ash_rollup_row = AsyncMock()
        mock_repo.set_rollup_cursor = AsyncMock()

        result = await run_ash_1h_rollup("instance-1", now=now)

    # source watermark caps at hour 11 (12 is still partial) -- only hours 10, 11 processed
    assert result.buckets_processed == 2
    assert result.last_bucket == datetime(2026, 7, 31, 11, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_run_ash_1h_rollup_noop_when_ash_1m_has_never_run() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.rollups.AsyncSessionLocal", _mock_session_factory(mock_session)),
        patch("app.modules.monitoring.rollups.repository") as mock_repo,
    ):
        mock_repo.get_rollup_cursor = AsyncMock(return_value=None)

        result = await run_ash_1h_rollup("instance-1")

    assert result.buckets_processed == 0
    mock_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_query_stat_1h_rollup_processes_closed_hour_buckets() -> None:
    mock_session = AsyncMock()
    now = datetime(2026, 7, 31, 14, 0, 0, tzinfo=UTC)

    with (
        patch("app.modules.monitoring.rollups.AsyncSessionLocal", _mock_session_factory(mock_session)),
        patch("app.modules.monitoring.rollups.repository") as mock_repo,
    ):
        mock_repo.get_rollup_cursor = AsyncMock(return_value=datetime(2026, 7, 31, 11, 0, 0, tzinfo=UTC))
        mock_repo.aggregate_query_stat_delta_bucket = AsyncMock(return_value=[QueryStatBucketRow(query_id="q1", calls=10, total_time_ms=100.0, rows_returned=5, shared_blks_read=0, shared_blks_written=0)])
        mock_repo.insert_query_stat_1h_row = AsyncMock()
        mock_repo.set_rollup_cursor = AsyncMock()

        result = await run_query_stat_1h_rollup("instance-1", now=now, close_delay_seconds=120)

    # watermark 11:00 -> next bucket 12:00; now=14:00 with 120s delay closes through 12:00
    assert result.buckets_processed == 1
    assert result.last_bucket == datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)
    mock_repo.insert_query_stat_1h_row.assert_awaited()


@pytest.mark.asyncio
async def test_run_query_stat_1h_rollup_noop_without_data() -> None:
    mock_session = AsyncMock()

    with (
        patch("app.modules.monitoring.rollups.AsyncSessionLocal", _mock_session_factory(mock_session)),
        patch("app.modules.monitoring.rollups.repository") as mock_repo,
    ):
        mock_repo.get_rollup_cursor = AsyncMock(return_value=None)
        mock_repo.get_earliest_query_stat_delta_at = AsyncMock(return_value=None)

        result = await run_query_stat_1h_rollup("instance-1")

    assert result.buckets_processed == 0
    mock_session.commit.assert_not_awaited()
