"""Waits timeline read model for the main Waits chart (ash rollups)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import repository

Granularity = Literal["1m", "1h"]

_STALE_SESSION_SAMPLE_SECONDS = 120.0


@dataclass(frozen=True, slots=True)
class WaitsTimelinePoint:
    bucket_start: datetime
    wait_seconds: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class WaitsTimelineSeries:
    wait_class_id: str | None
    label: str
    points: list[WaitsTimelinePoint]


@dataclass(frozen=True, slots=True)
class WaitsTimelineResult:
    instance_id: str
    granularity: Granularity
    start: datetime
    end: datetime
    series: list[WaitsTimelineSeries]


@dataclass(frozen=True, slots=True)
class InstanceSummary:
    id: str
    name: str
    engine: str
    host: str
    port: int
    is_active: bool
    collector_status: str
    last_sample_at: datetime | None


@dataclass(frozen=True, slots=True)
class InstanceListResult:
    instances: list[InstanceSummary]


def _derive_collector_status(
    *,
    last_sample_at: datetime | None,
    last_finished_at: datetime | None,
    last_status: str | None,
    gap_detected: bool | None,
    now: datetime,
) -> str:
    if last_finished_at is None and last_sample_at is None:
        return "unknown"
    if last_status == "error" or gap_detected:
        return "degraded"
    reference = last_sample_at or last_finished_at
    if reference is not None:
        age = (now - reference).total_seconds()
        if age > _STALE_SESSION_SAMPLE_SECONDS:
            return "degraded"
    return "ok"


def _validate_window(start: datetime, end: datetime) -> None:
    if start >= end:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start must be before end")


def _choose_granularity(start: datetime, end: datetime, requested: Granularity | None) -> Granularity:
    if requested is not None:
        return requested
    span_hours = (end - start).total_seconds() / 3600.0
    return "1m" if span_hours <= 24 else "1h"


async def list_instance_summaries(session: AsyncSession) -> InstanceListResult:
    from datetime import UTC

    rows = await repository.list_instances_with_status(session)
    now = datetime.now(UTC)
    instances = [
        InstanceSummary(
            id=row.id,
            name=row.name,
            engine=row.engine.value,
            host=row.host,
            port=row.port,
            is_active=row.is_active,
            collector_status=_derive_collector_status(
                last_sample_at=row.last_sample_at,
                last_finished_at=row.last_collector_finished_at,
                last_status=row.last_collector_status,
                gap_detected=row.last_collector_gap_detected,
                now=now,
            ),
            last_sample_at=row.last_sample_at,
        )
        for row in rows
    ]
    return InstanceListResult(instances=instances)


async def get_waits_timeline(
    session: AsyncSession,
    *,
    instance_id: str,
    start: datetime,
    end: datetime,
    granularity: Granularity | None = None,
) -> WaitsTimelineResult:
    _validate_window(start, end)
    if not await repository.instance_exists(session, instance_id=instance_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitored instance not found")

    resolved_granularity = _choose_granularity(start, end, granularity)
    max_span = timedelta(days=7) if resolved_granularity == "1m" else timedelta(days=90)
    if end - start > max_span:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Time range exceeds maximum for granularity {resolved_granularity}",
        )

    rows = await repository.fetch_waits_timeline(
        session,
        instance_id=instance_id,
        period_start=start,
        period_end=end,
        granularity=resolved_granularity,
    )
    wait_labels = await repository.get_wait_class_labels(session)

    series_keys: dict[str | None, list[WaitsTimelinePoint]] = {}

    for row in rows:
        key = row.wait_class_id
        label = "Other" if row.is_other or key is None else wait_labels.get(key, key or "Other")
        series_keys.setdefault(key, []).append(
            WaitsTimelinePoint(
                bucket_start=row.bucket_start,
                wait_seconds=row.wait_seconds,
                sample_count=row.sample_count,
            ),
        )

    series: list[WaitsTimelineSeries] = []
    for wait_class_id, points in sorted(series_keys.items(), key=lambda item: (item[0] is None, item[0] or "")):
        label = "Other"
        if wait_class_id is not None:
            label = wait_labels.get(wait_class_id, wait_class_id)
        elif points:
            label = "Other"
        series.append(
            WaitsTimelineSeries(
                wait_class_id=wait_class_id,
                label=label,
                points=sorted(points, key=lambda p: p.bucket_start),
            ),
        )

    return WaitsTimelineResult(
        instance_id=instance_id,
        granularity=resolved_granularity,
        start=start,
        end=end,
        series=series,
    )
