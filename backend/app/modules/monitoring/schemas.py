"""Pydantic schemas for monitoring API (Phase 1 element 6: period comparison)."""

from datetime import datetime

from pydantic import BaseModel


class PeriodWindowResponse(BaseModel):
    start: datetime
    end: datetime


class PeriodMetricsResponse(BaseModel):
    calls: int
    totalTimeMs: float
    rowsReturned: int
    avgTimeMs: float | None = None


class QueryPeriodComparisonItem(BaseModel):
    queryId: str
    queryText: str | None = None
    baseline: PeriodMetricsResponse | None = None
    current: PeriodMetricsResponse | None = None
    avgTimeMsDelta: float | None = None
    avgTimeMsDeltaPct: float | None = None
    callsDelta: int | None = None
    totalTimeMsDelta: float | None = None
    isRegression: bool


class QueryPeriodComparisonResponse(BaseModel):
    instanceId: str
    baseline: PeriodWindowResponse
    current: PeriodWindowResponse
    queries: list[QueryPeriodComparisonItem]


class WaitPeriodMetricsResponse(BaseModel):
    waitClassId: str | None = None
    waitSeconds: float
    sampleCount: int
    isOther: bool


class WaitPeriodComparisonItem(BaseModel):
    waitClassId: str | None = None
    waitClassLabel: str | None = None
    baseline: WaitPeriodMetricsResponse | None = None
    current: WaitPeriodMetricsResponse | None = None
    waitSecondsDelta: float | None = None
    waitSecondsDeltaPct: float | None = None
    sampleCountDelta: int | None = None


class PeriodComparisonSummaryResponse(BaseModel):
    instanceId: str
    baseline: PeriodWindowResponse
    current: PeriodWindowResponse
    instanceBaseline: PeriodMetricsResponse | None = None
    instanceCurrent: PeriodMetricsResponse | None = None
    instanceAvgTimeMsDelta: float | None = None
    instanceAvgTimeMsDeltaPct: float | None = None
    waits: list[WaitPeriodComparisonItem]


class MonitoredInstanceResponse(BaseModel):
    id: str
    name: str
    engine: str
    host: str
    port: int
    isActive: bool
    collectorStatus: str
    lastSampleAt: datetime | None = None


class MonitoredInstanceListResponse(BaseModel):
    instances: list[MonitoredInstanceResponse]


class WaitsTimelinePointResponse(BaseModel):
    bucketStart: datetime
    waitSeconds: float
    sampleCount: int


class WaitsTimelineSeriesResponse(BaseModel):
    waitClassId: str | None = None
    label: str
    points: list[WaitsTimelinePointResponse]


class WaitsTimelineResponse(BaseModel):
    instanceId: str
    granularity: str
    start: datetime
    end: datetime
    series: list[WaitsTimelineSeriesResponse]
