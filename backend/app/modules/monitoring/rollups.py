"""Rollups (ADR §6, roadmap Phase 0 element 7): `ash_1m`, `ash_1h`, `query_stat_1h`.

Not an optimization -- the condition for baseline comparisons (Phase 1
elements 6-7) and for UI queries that span weeks without scanning raw
`session_sample`/`query_stat_delta`.

Each rollup is a watermark-advancing job, not a view (ADR §6: "Rollup liczony
jest zadaniem przesuwającym watermark... Logika przenosi się 1:1 na
continuous aggregate" if a future Timescale migration happens). A bucket is
only processed once it's fully "closed" -- `close_delay_seconds` (default
120s) after its end, so samples that land a little late don't get silently
dropped from a bucket already rolled up.

`ash_1h` and `query_stat_1h` intentionally roll up from `ash_1m` /
`query_stat_delta` respectively rather than re-scanning raw `session_sample`
-- cheaper, and (for `ash_1h`) it's the standard rollup-of-rollups shape
that keeps this 1:1 with a Timescale continuous-aggregate hierarchy. One
consequence, accepted per ADR §6's "Top-N gubi zapytania z ogona": a
(query, wait_class) pair that never lands in a minute's top 20 is gone by
the time the hourly rollup runs -- it was never in `ash_1m` to re-aggregate.
Raw `session_sample` (7 day retention) is still the fallback for "what was
in the long tail".

Top-N+other (ADR §6): per instance-bucket, keep the heaviest `top_n` rows
(20 by default) and fold everything else into a single `is_other` row. This
is applied at every rollup level (`ash_1m`, `ash_1h`, `query_stat_1h`) -- the
ADR's cardinality argument ("aplikacje generują tysiące zapytań") applies
equally to `query_stat_1h`, which isn't otherwise bounded by anything but
`pg_stat_statements.max`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.database import AsyncSessionLocal

from . import repository
from .repository import AshBucketRow, QueryStatBucketRow

_DEFAULT_CLOSE_DELAY_SECONDS = 120
_DEFAULT_TOP_N = 20
_DEFAULT_MAX_BUCKETS_1M = 120
_DEFAULT_MAX_BUCKETS_1H = 48


def _floor_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)


def _floor_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def _last_closed_minute_bucket(now: datetime, close_delay_seconds: int) -> datetime:
    """Latest 1-minute bucket_start whose bucket [t, t+1m) ended at least close_delay_seconds ago."""
    cutoff = now - timedelta(seconds=close_delay_seconds)
    return _floor_minute(cutoff) - timedelta(minutes=1)


def _last_closed_hour_bucket(now: datetime, close_delay_seconds: int) -> datetime:
    cutoff = now - timedelta(seconds=close_delay_seconds)
    return _floor_hour(cutoff) - timedelta(hours=1)


def _last_hour_with_complete_source(source_watermark: datetime) -> datetime:
    """Latest hour whose minutes are all <= an upstream 1m-grain watermark.

    An hour [h, h+1h) is only safe to roll up once its last constituent
    minute bucket (h + 59m) has itself been processed -- otherwise the
    hourly rollup would be computed from a partial hour and never revisited.
    """
    hour = _floor_hour(source_watermark)
    if source_watermark >= hour + timedelta(hours=1) - timedelta(minutes=1):
        return hour
    return hour - timedelta(hours=1)


def _apply_top_n_and_other_ash(rows: list[AshBucketRow], top_n: int) -> list[tuple[AshBucketRow, bool]]:
    ordered = sorted(rows, key=lambda r: r.wait_seconds, reverse=True)
    top = [(row, False) for row in ordered[:top_n]]
    rest = ordered[top_n:]
    if not rest:
        return top
    other = AshBucketRow(
        query_id=None,
        wait_class_id=None,
        wait_seconds=sum(r.wait_seconds for r in rest),
        sample_count=sum(r.sample_count for r in rest),
    )
    return [*top, (other, True)]


def _apply_top_n_and_other_query_stat(rows: list[QueryStatBucketRow], top_n: int) -> list[tuple[QueryStatBucketRow, bool]]:
    ordered = sorted(rows, key=lambda r: r.total_time_ms, reverse=True)
    top = [(row, False) for row in ordered[:top_n]]
    rest = ordered[top_n:]
    if not rest:
        return top
    other = QueryStatBucketRow(
        query_id=None,
        calls=sum(r.calls for r in rest),
        total_time_ms=sum(r.total_time_ms for r in rest),
        rows_returned=sum(r.rows_returned for r in rest),
        shared_blks_read=sum(r.shared_blks_read for r in rest),
        shared_blks_written=sum(r.shared_blks_written for r in rest),
    )
    return [*top, (other, True)]


@dataclass(frozen=True, slots=True)
class RollupResult:
    kind: str
    buckets_processed: int
    rows_written: int
    last_bucket: datetime | None


async def run_ash_1m_rollup(
    instance_id: str,
    *,
    top_n: int = _DEFAULT_TOP_N,
    close_delay_seconds: int = _DEFAULT_CLOSE_DELAY_SECONDS,
    max_buckets: int = _DEFAULT_MAX_BUCKETS_1M,
    now: datetime | None = None,
) -> RollupResult:
    """Roll closed 1-minute buckets of `session_sample` into `ash_1m`, advancing the watermark."""
    now = now or datetime.now(UTC)
    buckets_processed = 0
    rows_written = 0
    last_processed: datetime | None = None

    async with AsyncSessionLocal() as session:
        watermark = await repository.get_rollup_cursor(session, instance_id=instance_id, kind="ash_1m")
        if watermark is None:
            earliest = await repository.get_earliest_session_sample_at(session, instance_id=instance_id)
            if earliest is None:
                return RollupResult(kind="ash_1m", buckets_processed=0, rows_written=0, last_bucket=None)
            bucket = _floor_minute(earliest)
        else:
            bucket = watermark + timedelta(minutes=1)

        last_closed = _last_closed_minute_bucket(now, close_delay_seconds)

        while bucket <= last_closed and buckets_processed < max_buckets:
            bucket_end = bucket + timedelta(minutes=1)
            raw_rows = await repository.aggregate_session_sample_bucket(session, instance_id=instance_id, bucket_start=bucket, bucket_end=bucket_end)
            for row, is_other in _apply_top_n_and_other_ash(raw_rows, top_n):
                await repository.insert_ash_rollup_row(session, table="ash_1m", instance_id=instance_id, bucket_start=bucket, row=row, is_other=is_other)
                rows_written += 1
            await repository.set_rollup_cursor(session, instance_id=instance_id, kind="ash_1m", watermark=bucket)
            last_processed = bucket
            buckets_processed += 1
            bucket = bucket_end

        await session.commit()

    return RollupResult(kind="ash_1m", buckets_processed=buckets_processed, rows_written=rows_written, last_bucket=last_processed)


async def run_ash_1h_rollup(
    instance_id: str,
    *,
    top_n: int = _DEFAULT_TOP_N,
    close_delay_seconds: int = _DEFAULT_CLOSE_DELAY_SECONDS,
    max_buckets: int = _DEFAULT_MAX_BUCKETS_1H,
    now: datetime | None = None,
) -> RollupResult:
    """Roll closed 1-hour buckets of `ash_1m` into `ash_1h`, advancing the watermark."""
    now = now or datetime.now(UTC)
    buckets_processed = 0
    rows_written = 0
    last_processed: datetime | None = None

    async with AsyncSessionLocal() as session:
        ash_1m_watermark = await repository.get_rollup_cursor(session, instance_id=instance_id, kind="ash_1m")
        if ash_1m_watermark is None:
            return RollupResult(kind="ash_1h", buckets_processed=0, rows_written=0, last_bucket=None)

        watermark = await repository.get_rollup_cursor(session, instance_id=instance_id, kind="ash_1h")
        if watermark is None:
            earliest = await repository.get_earliest_session_sample_at(session, instance_id=instance_id)
            if earliest is None:
                return RollupResult(kind="ash_1h", buckets_processed=0, rows_written=0, last_bucket=None)
            bucket = _floor_hour(earliest)
        else:
            bucket = watermark + timedelta(hours=1)

        last_closed = min(_last_closed_hour_bucket(now, close_delay_seconds), _last_hour_with_complete_source(ash_1m_watermark))

        while bucket <= last_closed and buckets_processed < max_buckets:
            bucket_end = bucket + timedelta(hours=1)
            raw_rows = await repository.aggregate_ash_1m_bucket(session, instance_id=instance_id, bucket_start=bucket, bucket_end=bucket_end)
            for row, is_other in _apply_top_n_and_other_ash(raw_rows, top_n):
                await repository.insert_ash_rollup_row(session, table="ash_1h", instance_id=instance_id, bucket_start=bucket, row=row, is_other=is_other)
                rows_written += 1
            await repository.set_rollup_cursor(session, instance_id=instance_id, kind="ash_1h", watermark=bucket)
            last_processed = bucket
            buckets_processed += 1
            bucket = bucket_end

        await session.commit()

    return RollupResult(kind="ash_1h", buckets_processed=buckets_processed, rows_written=rows_written, last_bucket=last_processed)


async def run_query_stat_1h_rollup(
    instance_id: str,
    *,
    top_n: int = _DEFAULT_TOP_N,
    close_delay_seconds: int = _DEFAULT_CLOSE_DELAY_SECONDS,
    max_buckets: int = _DEFAULT_MAX_BUCKETS_1H,
    now: datetime | None = None,
) -> RollupResult:
    """Roll closed 1-hour buckets of `query_stat_delta` into `query_stat_1h`, advancing the watermark."""
    now = now or datetime.now(UTC)
    buckets_processed = 0
    rows_written = 0
    last_processed: datetime | None = None

    async with AsyncSessionLocal() as session:
        watermark = await repository.get_rollup_cursor(session, instance_id=instance_id, kind="query_stat_1h")
        if watermark is None:
            earliest = await repository.get_earliest_query_stat_delta_at(session, instance_id=instance_id)
            if earliest is None:
                return RollupResult(kind="query_stat_1h", buckets_processed=0, rows_written=0, last_bucket=None)
            bucket = _floor_hour(earliest)
        else:
            bucket = watermark + timedelta(hours=1)

        last_closed = _last_closed_hour_bucket(now, close_delay_seconds)

        while bucket <= last_closed and buckets_processed < max_buckets:
            bucket_end = bucket + timedelta(hours=1)
            raw_rows = await repository.aggregate_query_stat_delta_bucket(session, instance_id=instance_id, bucket_start=bucket, bucket_end=bucket_end)
            for row, is_other in _apply_top_n_and_other_query_stat(raw_rows, top_n):
                await repository.insert_query_stat_1h_row(session, instance_id=instance_id, bucket_start=bucket, row=row, is_other=is_other)
                rows_written += 1
            await repository.set_rollup_cursor(session, instance_id=instance_id, kind="query_stat_1h", watermark=bucket)
            last_processed = bucket
            buckets_processed += 1
            bucket = bucket_end

        await session.commit()

    return RollupResult(kind="query_stat_1h", buckets_processed=buckets_processed, rows_written=rows_written, last_bucket=last_processed)
