"""FastAPI router for monitoring read APIs (Phase 1 element 6)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import CurrentUser

from . import period_comparison as pc
from .schemas import (
    PeriodComparisonSummaryResponse,
    PeriodMetricsResponse,
    PeriodWindowResponse,
    QueryPeriodComparisonItem,
    QueryPeriodComparisonResponse,
    WaitPeriodComparisonItem,
    WaitPeriodMetricsResponse,
)

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


def _period_metrics(metrics: pc.PeriodMetrics | None) -> PeriodMetricsResponse | None:
    if metrics is None:
        return None
    return PeriodMetricsResponse(
        calls=metrics.calls,
        totalTimeMs=metrics.total_time_ms,
        rowsReturned=metrics.rows_returned,
        avgTimeMs=metrics.avg_time_ms,
    )


def _wait_metrics(metrics: pc.WaitPeriodMetrics | None) -> WaitPeriodMetricsResponse | None:
    if metrics is None:
        return None
    return WaitPeriodMetricsResponse(
        waitClassId=metrics.wait_class_id,
        waitSeconds=metrics.wait_seconds,
        sampleCount=metrics.sample_count,
        isOther=metrics.is_other,
    )


def _period_window(window: pc.PeriodWindow) -> PeriodWindowResponse:
    return PeriodWindowResponse(start=window.start, end=window.end)


@router.get(
    "/instances/{instance_id}/queries/period-comparison",
    response_model=QueryPeriodComparisonResponse,
    summary="Compare query stats between two periods",
    description=("Baseline level 1: compare `query_stat_1h` rollups for each query between " "a baseline window and a current window. Returns per-query deltas and " "flags regressions where average time increased."),
)
async def compare_query_periods(
    instance_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    baseline_start: datetime = Query(description="Baseline window start (inclusive)"),
    baseline_end: datetime = Query(description="Baseline window end (exclusive)"),
    current_start: datetime = Query(description="Current window start (inclusive)"),
    current_end: datetime = Query(description="Current window end (exclusive)"),
    min_baseline_calls: int = Query(default=1, ge=0, description="Minimum calls in baseline to flag regression"),
    min_current_calls: int = Query(default=1, ge=0, description="Minimum calls in current window to flag regression"),
    regressions_only: bool = Query(default=False, description="Return only queries flagged as regressions"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum rows returned after sorting by regression severity"),
) -> QueryPeriodComparisonResponse:
    result = await pc.compare_instance_query_periods(
        db,
        instance_id=instance_id,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
        current_start=current_start,
        current_end=current_end,
        min_baseline_calls=min_baseline_calls,
        min_current_calls=min_current_calls,
        regressions_only=regressions_only,
        limit=limit,
    )
    return QueryPeriodComparisonResponse(
        instanceId=result.instance_id,
        baseline=_period_window(result.baseline),
        current=_period_window(result.current),
        queries=[
            QueryPeriodComparisonItem(
                queryId=row.query_id,
                queryText=row.query_text,
                baseline=_period_metrics(row.baseline),
                current=_period_metrics(row.current),
                avgTimeMsDelta=row.avg_time_ms_delta,
                avgTimeMsDeltaPct=row.avg_time_ms_delta_pct,
                callsDelta=row.calls_delta,
                totalTimeMsDelta=row.total_time_ms_delta,
                isRegression=row.is_regression,
            )
            for row in result.queries
        ],
    )


@router.get(
    "/instances/{instance_id}/period-comparison/summary",
    response_model=PeriodComparisonSummaryResponse,
    summary="Compare instance totals and wait classes between two periods",
    description=("Baseline level 1: instance-wide query totals from `query_stat_1h` plus " "wait-class breakdown from `ash_1h` for baseline vs current windows."),
)
async def compare_period_summary(
    instance_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    baseline_start: datetime = Query(description="Baseline window start (inclusive)"),
    baseline_end: datetime = Query(description="Baseline window end (exclusive)"),
    current_start: datetime = Query(description="Current window start (inclusive)"),
    current_end: datetime = Query(description="Current window end (exclusive)"),
) -> PeriodComparisonSummaryResponse:
    result = await pc.compare_instance_period_summary(
        db,
        instance_id=instance_id,
        baseline_start=baseline_start,
        baseline_end=baseline_end,
        current_start=current_start,
        current_end=current_end,
    )
    return PeriodComparisonSummaryResponse(
        instanceId=result.instance_id,
        baseline=_period_window(result.baseline),
        current=_period_window(result.current),
        instanceBaseline=_period_metrics(result.instance_baseline),
        instanceCurrent=_period_metrics(result.instance_current),
        instanceAvgTimeMsDelta=result.instance_avg_time_ms_delta,
        instanceAvgTimeMsDeltaPct=result.instance_avg_time_ms_delta_pct,
        waits=[
            WaitPeriodComparisonItem(
                waitClassId=row.wait_class_id,
                waitClassLabel=row.wait_class_label,
                baseline=_wait_metrics(row.baseline),
                current=_wait_metrics(row.current),
                waitSecondsDelta=row.wait_seconds_delta,
                waitSecondsDeltaPct=row.wait_seconds_delta_pct,
                sampleCountDelta=row.sample_count_delta,
            )
            for row in result.waits
        ],
    )
