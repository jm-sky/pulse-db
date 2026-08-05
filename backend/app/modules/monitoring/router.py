"""FastAPI router for monitoring read APIs."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import CurrentUser

from . import period_comparison as pc
from . import repository
from . import waits_timeline as wt
from .schemas import (
    BlockingEventResponse,
    BlockingEventsResponse,
    DeadlockEventDetailResponse,
    DeadlockEventsResponse,
    DeadlockEventSummaryResponse,
    IndexesResponse,
    IndexSnapshotItemResponse,
    MonitoredInstanceListResponse,
    MonitoredInstanceResponse,
    PeriodComparisonSummaryResponse,
    PeriodMetricsResponse,
    PeriodWindowResponse,
    PlanChangeItemResponse,
    PlanChangesResponse,
    QueryPeriodComparisonItem,
    QueryPeriodComparisonResponse,
    QueryPlanDetailResponse,
    QueryPlanItemResponse,
    QueryPlansListResponse,
    RecommendationDetailResponse,
    RecommendationItemResponse,
    RecommendationsResponse,
    WaitPeriodComparisonItem,
    WaitPeriodMetricsResponse,
    WaitsTimelinePointResponse,
    WaitsTimelineResponse,
    WaitsTimelineSeriesResponse,
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
    "/instances",
    response_model=MonitoredInstanceListResponse,
    summary="List monitored instances",
    description="Registered instances with derived collector health from session sampling.",
)
async def list_instances(
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MonitoredInstanceListResponse:
    result = await wt.list_instance_summaries(db)
    return MonitoredInstanceListResponse(
        instances=[
            MonitoredInstanceResponse(
                id=row.id,
                name=row.name,
                engine=row.engine,
                host=row.host,
                port=row.port,
                isActive=row.is_active,
                collectorStatus=row.collector_status,
                lastSampleAt=row.last_sample_at,
            )
            for row in result.instances
        ],
    )


@router.get(
    "/instances/{instance_id}/waits/timeline",
    response_model=WaitsTimelineResponse,
    summary="Wait time timeline for an instance",
    description=("Stacked-bar source data: per-bucket wait seconds by wait class from " "`ash_1m` (≤24h default) or `ash_1h` rollups."),
)
async def get_instance_waits_timeline(
    instance_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    start: datetime = Query(description="Window start (inclusive)"),
    end: datetime = Query(description="Window end (exclusive)"),
    granularity: Literal["1m", "1h"] | None = Query(
        default=None,
        description="Rollup table; auto-selects 1m for ranges ≤24h when omitted",
    ),
) -> WaitsTimelineResponse:
    result = await wt.get_waits_timeline(
        db,
        instance_id=instance_id,
        start=start,
        end=end,
        granularity=granularity,
    )
    return WaitsTimelineResponse(
        instanceId=result.instance_id,
        granularity=result.granularity,
        start=result.start,
        end=result.end,
        series=[
            WaitsTimelineSeriesResponse(
                waitClassId=series.wait_class_id,
                label=series.label,
                points=[
                    WaitsTimelinePointResponse(
                        bucketStart=point.bucket_start,
                        waitSeconds=point.wait_seconds,
                        sampleCount=point.sample_count,
                    )
                    for point in series.points
                ],
            )
            for series in result.series
        ],
    )


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


@router.get(
    "/instances/{instance_id}/queries/plan-changes",
    response_model=PlanChangesResponse,
    summary="List recent plan-change events",
    description=("Queries that gained a new `query_plan` row (first_seen >= since). " "`isPlanChange` is true when the query already had at least one other plan " "(genuine change vs first-ever capture)."),
)
async def list_plan_changes(
    instance_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    since: datetime = Query(description="Return plans first seen at or after this timestamp"),
) -> PlanChangesResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    rows = await repository.list_plan_changes(db, instance_id=instance_id, since=since)
    return PlanChangesResponse(
        instanceId=instance_id,
        since=since,
        changes=[
            PlanChangeItemResponse(
                queryId=row.query_id,
                planHash=row.plan_hash,
                planFormat=row.plan_format,
                firstSeen=row.first_seen,
                queryText=row.query_text,
                planCount=row.plan_count,
                isPlanChange=row.plan_count > 1,
            )
            for row in rows
        ],
    )


@router.get(
    "/instances/{instance_id}/queries/{query_id}/plans",
    response_model=QueryPlansListResponse,
    summary="List execution plans for a query",
    description=("Stored plans for one query (`plan_text` via `query_plan`). " "`isPlanChange` is true when more than one distinct plan_hash exists."),
)
async def list_plans_for_query(
    instance_id: str,
    query_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QueryPlansListResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")
    if not await repository.query_belongs_to_instance(db, instance_id=instance_id, query_id=query_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Query not found on this instance")

    plans = await repository.list_query_plans(db, query_id=query_id)
    return QueryPlansListResponse(
        instanceId=instance_id,
        queryId=query_id,
        isPlanChange=len(plans) > 1,
        plans=[
            QueryPlanItemResponse(
                planHash=p.plan_hash,
                planFormat=p.plan_format,
                firstSeen=p.first_seen,
                lastSeen=p.last_seen,
            )
            for p in plans
        ],
    )


@router.get(
    "/instances/{instance_id}/queries/{query_id}/plans/{plan_hash}",
    response_model=QueryPlanDetailResponse,
    summary="Export one execution plan body",
    description="Full XML/JSON plan body for export (no built-in visualizer — vision §5).",
)
async def get_plan_detail(
    instance_id: str,
    query_id: str,
    plan_hash: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QueryPlanDetailResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    detail = await repository.get_query_plan_detail(db, instance_id=instance_id, query_id=query_id, plan_hash=plan_hash)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    return QueryPlanDetailResponse(
        instanceId=instance_id,
        queryId=query_id,
        planHash=detail.plan_hash,
        planFormat=detail.plan_format,
        planBody=detail.plan_body,
        firstSeen=detail.first_seen,
        lastSeen=detail.last_seen,
    )


@router.get(
    "/instances/{instance_id}/blocking",
    response_model=BlockingEventsResponse,
    summary="List recent blocking events",
    description="Active lock-chain snapshots written by the blocking collector tick.",
)
async def list_blocking(
    instance_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    since: datetime = Query(description="Return events detected at or after this timestamp"),
) -> BlockingEventsResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    rows = await repository.list_blocking_events(db, instance_id=instance_id, since=since)
    return BlockingEventsResponse(
        instanceId=instance_id,
        since=since,
        events=[
            BlockingEventResponse(
                id=row.id,
                detectedAt=row.detected_at,
                blockingQueryId=row.blocking_query_id,
                blockedQueryId=row.blocked_query_id,
                blockedDurationMs=row.blocked_duration_ms,
                details=row.details,
            )
            for row in rows
        ],
    )


@router.get(
    "/instances/{instance_id}/deadlocks",
    response_model=DeadlockEventsResponse,
    summary="List recent deadlock events",
    description="Deadlocks drained from SQL Server system_health (PostgreSQL: empty in MVP).",
)
async def list_deadlocks(
    instance_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    since: datetime = Query(description="Return events detected at or after this timestamp"),
) -> DeadlockEventsResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    rows = await repository.list_deadlock_events(db, instance_id=instance_id, since=since)
    return DeadlockEventsResponse(
        instanceId=instance_id,
        since=since,
        events=[
            DeadlockEventSummaryResponse(
                id=row.id,
                detectedAt=row.detected_at,
                victimQueryId=row.victim_query_id,
                victimProcessId=row.details.get("victim_process_id") if isinstance(row.details, dict) else None,
                hasXml=bool(row.details.get("xml")) if isinstance(row.details, dict) else False,
            )
            for row in rows
        ],
    )


@router.get(
    "/instances/{instance_id}/deadlocks/{event_id}",
    response_model=DeadlockEventDetailResponse,
    summary="Export one deadlock event (including XML)",
)
async def get_deadlock(
    instance_id: str,
    event_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeadlockEventDetailResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    row = await repository.get_deadlock_event(db, instance_id=instance_id, event_id=event_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deadlock event not found")

    return DeadlockEventDetailResponse(
        id=row.id,
        instanceId=row.instance_id,
        detectedAt=row.detected_at,
        victimQueryId=row.victim_query_id,
        details=row.details,
    )


@router.get(
    "/instances/{instance_id}/indexes",
    response_model=IndexesResponse,
    summary="List latest index inventory snapshot",
    description="Rows from the most recent indexes collector tick (optional exact snapshot_at).",
)
async def list_indexes(
    instance_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    snapshot_at: datetime | None = Query(default=None, description="Exact snapshot timestamp; default = latest"),
) -> IndexesResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    rows = await repository.list_index_snapshots(db, instance_id=instance_id, snapshot_at=snapshot_at)
    return IndexesResponse(
        instanceId=instance_id,
        snapshotAt=rows[0].snapshot_at if rows else snapshot_at,
        indexes=[
            IndexSnapshotItemResponse(
                id=row.id,
                databaseName=row.database_name,
                schemaName=row.schema_name,
                tableName=row.table_name,
                indexName=row.index_name,
                snapshotAt=row.snapshot_at,
                sizeBytes=row.size_bytes,
                scans=row.scans,
                isUnused=row.is_unused,
                bloatRatio=row.bloat_ratio,
            )
            for row in rows
        ],
    )


@router.get(
    "/instances/{instance_id}/recommendations",
    response_model=RecommendationsResponse,
    summary="List index (and other) recommendations",
)
async def list_recommendations(
    instance_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = Query(default=None, description="Filter by category, e.g. unused_index / missing_index"),
    status_filter: str | None = Query(default="open", alias="status", description="Filter by status; omit or null for all"),
) -> RecommendationsResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    rows = await repository.list_recommendations(
        db,
        instance_id=instance_id,
        category=category,
        status=status_filter,
    )
    return RecommendationsResponse(
        instanceId=instance_id,
        recommendations=[
            RecommendationItemResponse(
                id=row.id,
                createdAt=row.created_at,
                category=row.category,
                queryId=row.query_id,
                evidence=row.evidence,
                ddlSuggestion=row.ddl_suggestion,
                status=row.status,
            )
            for row in rows
        ],
    )


@router.get(
    "/instances/{instance_id}/recommendations/{recommendation_id}",
    response_model=RecommendationDetailResponse,
    summary="Get one recommendation",
)
async def get_recommendation(
    instance_id: str,
    recommendation_id: str,
    _: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationDetailResponse:
    if not await repository.instance_exists(db, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    row = await repository.get_recommendation(db, instance_id=instance_id, recommendation_id=recommendation_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found")

    return RecommendationDetailResponse(
        id=row.id,
        instanceId=row.instance_id,
        createdAt=row.created_at,
        category=row.category,
        queryId=row.query_id,
        evidence=row.evidence,
        ddlSuggestion=row.ddl_suggestion,
        status=row.status,
    )
