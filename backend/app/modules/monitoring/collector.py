"""Collector runtime: run an EngineAdapter against a registered instance,
measure its own overhead, and record explicit gaps.

Roadmap Phase 0 item 8: "harmonogram, idempotencja, jawne oznaczanie luk,
pomiar wlasnego narzutu" -- this module is the "trywialny kolektor" from
item 5/exit criteria: it writes one instance_metric fact plus a
collector_run row per invocation. The 1s ASH sampler is Phase 1; this proves
the adapter -> repository -> fact-table path end to end.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.database import AsyncSessionLocal

from . import repository
from .adapters import PostgresEngineAdapter, SqlServerEngineAdapter
from .engine_adapter import Engine, EngineAdapter, EngineCapabilities

_ADAPTERS: dict[Engine, EngineAdapter] = {
    Engine.POSTGRESQL: PostgresEngineAdapter(),
    Engine.SQLSERVER: SqlServerEngineAdapter(),
}

# A run started more than this many multiples of the expected interval late
# is considered a collection gap, not just scheduling jitter.
_GAP_THRESHOLD_FACTOR = 2.0


def _adapter_for(engine: Engine) -> EngineAdapter:
    return _ADAPTERS[engine]


def _detect_gap(*, started_at: datetime, last_finished_at: datetime | None, interval_ms: int) -> tuple[bool, float | None]:
    """Explicit gap flagging (ADR/roadmap Phase 0 item 8): a run starting more
    than _GAP_THRESHOLD_FACTOR intervals after the previous one finished
    means one or more ticks were missed, not just scheduling jitter."""
    if last_finished_at is None:
        return False, None
    expected_next = last_finished_at.timestamp() + interval_ms / 1000
    actual_gap = started_at.timestamp() - expected_next
    if actual_gap > (interval_ms / 1000) * (_GAP_THRESHOLD_FACTOR - 1):
        return True, actual_gap
    return False, None


@dataclass(frozen=True, slots=True)
class CollectionResult:
    run_id: str
    status: str
    overhead_ms: float
    active_session_count: int | None
    clock_offset_ms: float | None
    gap_detected: bool
    gap_seconds: float | None
    error_message: str | None


async def detect_and_store_capabilities(instance_id: str) -> EngineCapabilities:
    """Connect once, detect engine capabilities, persist them on monitored_instance."""
    async with AsyncSessionLocal() as session:
        params = await repository.get_connection_params(session, instance_id)
        capabilities = await _adapter_for(params.engine).detect_capabilities(params)
        await repository.update_capabilities(session, instance_id, capabilities)
        await session.commit()
    return capabilities


async def run_trivial_collection(instance_id: str, *, interval_ms: int = 60_000) -> CollectionResult:
    """One collector tick: sample, measure overhead/clock offset, detect gaps, persist."""
    async with AsyncSessionLocal() as session:
        params = await repository.get_connection_params(session, instance_id)
        last_finished_at, _last_interval_ms = await repository.get_last_collector_run(session, instance_id)

        started_at = datetime.now(UTC)
        gap_detected, gap_seconds = _detect_gap(started_at=started_at, last_finished_at=last_finished_at, interval_ms=interval_ms)

        clock_start = time.perf_counter()
        status = "ok"
        error_message: str | None = None
        active_session_count: int | None = None
        clock_offset_ms: float | None = None

        try:
            sample = await _adapter_for(params.engine).collect_trivial_sample(params)
            active_session_count = sample.active_session_count
            server_time = sample.server_time
            if server_time.tzinfo is None:
                server_time = server_time.replace(tzinfo=UTC)
            clock_offset_ms = (server_time - started_at).total_seconds() * 1000
        except Exception as exc:  # collector must never crash the scheduler on a bad instance
            status = "error"
            error_message = str(exc)

        overhead_ms = (time.perf_counter() - clock_start) * 1000
        finished_at = datetime.now(UTC)

        if status == "ok" and active_session_count is not None:
            await repository.insert_instance_metric(
                session,
                instance_id=instance_id,
                sampled_at=finished_at,
                metric_id="active_sessions",
                value=float(active_session_count),
            )

        run_id = await repository.insert_collector_run(
            session,
            instance_id=instance_id,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            interval_ms=interval_ms,
            overhead_ms=overhead_ms,
            clock_offset_ms=clock_offset_ms,
            gap_detected=gap_detected,
            gap_seconds=gap_seconds,
            error_message=error_message,
        )
        await session.commit()

    return CollectionResult(
        run_id=run_id,
        status=status,
        overhead_ms=overhead_ms,
        active_session_count=active_session_count,
        clock_offset_ms=clock_offset_ms,
        gap_detected=gap_detected,
        gap_seconds=gap_seconds,
        error_message=error_message,
    )
