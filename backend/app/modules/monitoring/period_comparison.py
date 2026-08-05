"""Baseline level 1: compare two time windows over rollup tables (ADR §6, vision §5).

Reads `query_stat_1h` for query duration/calls and `ash_1h` for wait attribution.
Pure comparison logic lives here; SQL aggregation is in `repository`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import repository


@dataclass(frozen=True, slots=True)
class PeriodMetrics:
    calls: int
    total_time_ms: float
    rows_returned: int

    @property
    def avg_time_ms(self) -> float | None:
        if self.calls <= 0:
            return None
        return self.total_time_ms / self.calls


@dataclass(frozen=True, slots=True)
class WaitPeriodMetrics:
    wait_class_id: str | None
    wait_seconds: float
    sample_count: int
    is_other: bool


@dataclass(frozen=True, slots=True)
class QueryComparisonRow:
    query_id: str
    query_text: str | None
    baseline: PeriodMetrics | None
    current: PeriodMetrics | None
    avg_time_ms_delta: float | None
    avg_time_ms_delta_pct: float | None
    calls_delta: int | None
    total_time_ms_delta: float | None
    is_regression: bool


@dataclass(frozen=True, slots=True)
class WaitComparisonRow:
    wait_class_id: str | None
    wait_class_label: str | None
    baseline: WaitPeriodMetrics | None
    current: WaitPeriodMetrics | None
    wait_seconds_delta: float | None
    wait_seconds_delta_pct: float | None
    sample_count_delta: int | None


@dataclass(frozen=True, slots=True)
class PeriodComparisonSummary:
    instance_id: str
    baseline: PeriodWindow
    current: PeriodWindow
    instance_baseline: PeriodMetrics | None
    instance_current: PeriodMetrics | None
    instance_avg_time_ms_delta: float | None
    instance_avg_time_ms_delta_pct: float | None
    waits: list[WaitComparisonRow]


@dataclass(frozen=True, slots=True)
class PeriodWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class QueryPeriodComparisonResult:
    instance_id: str
    baseline: PeriodWindow
    current: PeriodWindow
    queries: list[QueryComparisonRow]


def _delta(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None:
        return None
    return current - baseline


def _delta_pct(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None or baseline == 0:
        return None
    return ((current - baseline) / baseline) * 100.0


def _metrics_from_repo(row: repository.QueryPeriodAggregate | repository.InstancePeriodAggregate) -> PeriodMetrics:
    return PeriodMetrics(calls=row.calls, total_time_ms=row.total_time_ms, rows_returned=row.rows_returned)


def _wait_metrics_from_repo(row: repository.WaitPeriodAggregate) -> WaitPeriodMetrics:
    return WaitPeriodMetrics(
        wait_class_id=row.wait_class_id,
        wait_seconds=row.wait_seconds,
        sample_count=row.sample_count,
        is_other=row.is_other,
    )


def compare_query_period_rows(
    *,
    baseline_rows: dict[str, PeriodMetrics],
    current_rows: dict[str, PeriodMetrics],
    query_texts: dict[str, str],
    min_baseline_calls: int,
    min_current_calls: int,
) -> list[QueryComparisonRow]:
    """Merge baseline/current aggregates and compute regression deltas."""
    query_ids = sorted(set(baseline_rows) | set(current_rows))
    results: list[QueryComparisonRow] = []

    for query_id in query_ids:
        baseline = baseline_rows.get(query_id)
        current = current_rows.get(query_id)
        baseline_avg = baseline.avg_time_ms if baseline else None
        current_avg = current.avg_time_ms if current else None
        avg_delta = _delta(current_avg, baseline_avg)
        avg_delta_pct = _delta_pct(current_avg, baseline_avg)
        calls_delta = None if baseline is None or current is None else current.calls - baseline.calls
        total_time_delta = None if baseline is None or current is None else current.total_time_ms - baseline.total_time_ms

        has_baseline = baseline is not None and baseline.calls >= min_baseline_calls
        has_current = current is not None and current.calls >= min_current_calls
        is_regression = has_baseline and has_current and baseline_avg is not None and current_avg is not None and current_avg > baseline_avg

        results.append(
            QueryComparisonRow(
                query_id=query_id,
                query_text=query_texts.get(query_id),
                baseline=baseline,
                current=current,
                avg_time_ms_delta=avg_delta,
                avg_time_ms_delta_pct=avg_delta_pct,
                calls_delta=calls_delta,
                total_time_ms_delta=total_time_delta,
                is_regression=is_regression,
            )
        )

    return results


def compare_wait_period_rows(
    *,
    baseline_rows: dict[str | None, WaitPeriodMetrics],
    current_rows: dict[str | None, WaitPeriodMetrics],
    wait_labels: dict[str, str],
) -> list[WaitComparisonRow]:
    wait_keys = sorted(set(baseline_rows) | set(current_rows), key=lambda key: (key is None, key or ""))
    results: list[WaitComparisonRow] = []

    for wait_class_id in wait_keys:
        baseline = baseline_rows.get(wait_class_id)
        current = current_rows.get(wait_class_id)
        baseline_seconds = baseline.wait_seconds if baseline else None
        current_seconds = current.wait_seconds if current else None
        sample_delta = None
        if baseline is not None and current is not None:
            sample_delta = current.sample_count - baseline.sample_count

        results.append(
            WaitComparisonRow(
                wait_class_id=wait_class_id,
                wait_class_label=wait_labels.get(wait_class_id) if wait_class_id else "other",
                baseline=baseline,
                current=current,
                wait_seconds_delta=_delta(current_seconds, baseline_seconds),
                wait_seconds_delta_pct=_delta_pct(current_seconds, baseline_seconds),
                sample_count_delta=sample_delta,
            )
        )

    return results


def _validate_period_window(start: datetime, end: datetime, *, label: str) -> None:
    if start >= end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label}: start must be before end",
        )


async def _ensure_instance(session: AsyncSession, instance_id: str) -> None:
    if not await repository.instance_exists(session, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")


async def compare_instance_query_periods(
    session: AsyncSession,
    *,
    instance_id: str,
    baseline_start: datetime,
    baseline_end: datetime,
    current_start: datetime,
    current_end: datetime,
    min_baseline_calls: int = 1,
    min_current_calls: int = 1,
    regressions_only: bool = False,
    limit: int = 100,
) -> QueryPeriodComparisonResult:
    """Compare per-query stats between two windows using `query_stat_1h`."""
    _validate_period_window(baseline_start, baseline_end, label="baseline")
    _validate_period_window(current_start, current_end, label="current")
    await _ensure_instance(session, instance_id)

    baseline_agg = await repository.aggregate_query_stat_period(
        session,
        instance_id=instance_id,
        period_start=baseline_start,
        period_end=baseline_end,
    )
    current_agg = await repository.aggregate_query_stat_period(
        session,
        instance_id=instance_id,
        period_start=current_start,
        period_end=current_end,
    )

    baseline_rows = {row.query_id: _metrics_from_repo(row) for row in baseline_agg}
    current_rows = {row.query_id: _metrics_from_repo(row) for row in current_agg}
    query_ids = list(set(baseline_rows) | set(current_rows))
    query_texts = await repository.get_query_texts(session, query_ids=query_ids)

    rows = compare_query_period_rows(
        baseline_rows=baseline_rows,
        current_rows=current_rows,
        query_texts=query_texts,
        min_baseline_calls=min_baseline_calls,
        min_current_calls=min_current_calls,
    )

    if regressions_only:
        rows = [row for row in rows if row.is_regression]

    rows.sort(
        key=lambda row: (
            row.avg_time_ms_delta_pct is None,
            -(row.avg_time_ms_delta_pct or 0.0),
            -(row.avg_time_ms_delta or 0.0),
        ),
    )
    if limit > 0:
        rows = rows[:limit]

    return QueryPeriodComparisonResult(
        instance_id=instance_id,
        baseline=PeriodWindow(start=baseline_start, end=baseline_end),
        current=PeriodWindow(start=current_start, end=current_end),
        queries=rows,
    )


async def compare_instance_period_summary(
    session: AsyncSession,
    *,
    instance_id: str,
    baseline_start: datetime,
    baseline_end: datetime,
    current_start: datetime,
    current_end: datetime,
) -> PeriodComparisonSummary:
    """Instance-level totals and wait-class breakdown from rollups."""
    _validate_period_window(baseline_start, baseline_end, label="baseline")
    _validate_period_window(current_start, current_end, label="current")
    await _ensure_instance(session, instance_id)

    baseline_instance = await repository.aggregate_instance_query_stat_period(
        session,
        instance_id=instance_id,
        period_start=baseline_start,
        period_end=baseline_end,
    )
    current_instance = await repository.aggregate_instance_query_stat_period(
        session,
        instance_id=instance_id,
        period_start=current_start,
        period_end=current_end,
    )

    instance_baseline = _metrics_from_repo(baseline_instance) if baseline_instance else None
    instance_current = _metrics_from_repo(current_instance) if current_instance else None
    baseline_avg = instance_baseline.avg_time_ms if instance_baseline else None
    current_avg = instance_current.avg_time_ms if instance_current else None

    baseline_waits = await repository.aggregate_wait_period(
        session,
        instance_id=instance_id,
        period_start=baseline_start,
        period_end=baseline_end,
    )
    current_waits = await repository.aggregate_wait_period(
        session,
        instance_id=instance_id,
        period_start=current_start,
        period_end=current_end,
    )
    wait_labels = await repository.get_wait_class_labels(session)

    baseline_wait_rows = {row.wait_class_id: _wait_metrics_from_repo(row) for row in baseline_waits}
    current_wait_rows = {row.wait_class_id: _wait_metrics_from_repo(row) for row in current_waits}

    return PeriodComparisonSummary(
        instance_id=instance_id,
        baseline=PeriodWindow(start=baseline_start, end=baseline_end),
        current=PeriodWindow(start=current_start, end=current_end),
        instance_baseline=instance_baseline,
        instance_current=instance_current,
        instance_avg_time_ms_delta=_delta(current_avg, baseline_avg),
        instance_avg_time_ms_delta_pct=_delta_pct(current_avg, baseline_avg),
        waits=compare_wait_period_rows(
            baseline_rows=baseline_wait_rows,
            current_rows=current_wait_rows,
            wait_labels=wait_labels,
        ),
    )
