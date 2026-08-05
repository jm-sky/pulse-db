"""Collector runtime: run an EngineAdapter against a registered instance,
measure its own overhead, and record explicit gaps.

Roadmap Phase 0 item 8: "harmonogram, idempotencja, jawne oznaczanie luk,
pomiar wlasnego narzutu" -- this module is the "trywialny kolektor" from
item 5/exit criteria: it writes one instance_metric fact plus a
collector_run row per invocation.

Phase 1 elements 1/2 (docs/plans/2026-07-30-phase1-diagnostic-core.md) add
two more tick functions alongside `run_trivial_collection`:
`run_session_sample_collection` (1s-cadence ASH sample -> `session_sample`)
and `run_query_stats_collection` (60s-cadence pg_stat_statements delta ->
`query_stat_delta`). Each is one invocation, same as the trivial tick --
looping them on their respective cadences is a scheduler's job (still
manual via CLI/cron for now, per roadmap Phase 0 item 8's deferral).

`run_wait_sampling_history_collection` is a fourth, explicitly opt-in tick:
the "richer source" from roadmap element 1 ("pg_wait_sampling opcjonalnie
gdy obecne, z komunikatem o różnicy jakości"). PostgreSQL only, and not
folded into `run_session_sample_collection`'s default path -- see its
docstring for why (volume, not just an easy quality upgrade).

`run_query_plans_collection` is Phase 1 element 3 (docs/plans/2026-08-05-query-plans.md):
top-N execution plans into `plan_text`/`query_plan` on a 10-minute cadence.

`run_blocking_collection` / `run_deadlocks_collection` are Phase 1 element 4
(docs/plans/2026-08-05-blocking-deadlocks.md): active lock chains and
SQL Server system_health deadlock history.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

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


def _wait_event_native_name(wait_event_type: str | None, wait_event: str | None) -> str | None:
    """Map adapter wait fields to `wait_event.native_name`.

    PostgreSQL uses hierarchical ``Type:Event`` (migration 068 seeds).
    SQL Server uses flat wait-type names (``LCK_M_X``) -- adapters leave
    ``wait_event_type`` as None and put the type in ``wait_event``.
    """
    if wait_event_type and wait_event:
        return f"{wait_event_type}:{wait_event}"
    if wait_event:
        return wait_event
    return None


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


@dataclass(frozen=True, slots=True)
class SessionSampleResult:
    run_id: str
    status: str
    overhead_ms: float
    session_count: int | None
    gap_detected: bool
    gap_seconds: float | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class QueryStatsResult:
    run_id: str
    status: str
    overhead_ms: float
    queries_seen: int | None
    deltas_written: int | None
    gap_detected: bool
    gap_seconds: float | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class WaitSamplingHistoryResult:
    run_id: str
    status: str
    overhead_ms: float
    samples_written: int | None
    distinct_sessions: int | None
    history_period_ms: int | None
    gap_detected: bool
    gap_seconds: float | None
    error_message: str | None
    note: str | None


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
        last_finished_at, _last_interval_ms = await repository.get_last_collector_run(session, instance_id, kind="trivial")

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
            await session.rollback()

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
            kind="trivial",
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


async def run_session_sample_collection(instance_id: str, *, interval_ms: int = 1_000) -> SessionSampleResult:
    """One ASH tick (Phase 1 element 1): snapshot active sessions with wait attribution.

    Resolves query identity for each session (native key -> known `query`
    row -> interim fallback upsert if unseen) and wait-event classification
    (auto-registering unknown natives as `other`, ADR §5) before writing
    `session_sample` rows. No `clock_offset_ms` here -- the trivial tick
    already measures it; repeating that query on every 1s sample would be
    pure overhead for a number that doesn't change tick to tick.
    """
    async with AsyncSessionLocal() as session:
        params = await repository.get_connection_params(session, instance_id)
        last_finished_at, _last_interval_ms = await repository.get_last_collector_run(session, instance_id, kind="session_sample")

        started_at = datetime.now(UTC)
        gap_detected, gap_seconds = _detect_gap(started_at=started_at, last_finished_at=last_finished_at, interval_ms=interval_ms)

        clock_start = time.perf_counter()
        status = "ok"
        error_message: str | None = None
        session_count: int | None = None

        try:
            active_sessions = await _adapter_for(params.engine).collect_active_sessions(params)
            sampled_at = datetime.now(UTC)
            session_count = 0

            for row in active_sessions:
                query_id: str | None = None
                if row.engine_query_key:
                    query_id = await repository.find_query_id_by_engine_key(session, instance_id=instance_id, engine_query_key=row.engine_query_key)
                    if query_id is None and row.query_text:
                        # Query hasn't shown up via query-stats collection yet
                        # (still running / first execution) -- interim upsert
                        # using our own normalization (ADR §10 risk).
                        normalized = repository.normalize_query_text(row.query_text)
                        query_id = await repository.upsert_query(session, instance_id=instance_id, engine=params.engine, engine_query_key=row.engine_query_key, normalized_text=normalized)
                elif row.query_text:
                    # No native identity at all -- synthesize one from our own
                    # hash so the session is still attributable to *a* query.
                    normalized = repository.normalize_query_text(row.query_text)
                    query_id = await repository.upsert_query(session, instance_id=instance_id, engine=params.engine, engine_query_key=repository.compute_norm_hash(normalized), normalized_text=normalized)

                session_attr_id = await repository.upsert_session_attr(
                    session,
                    instance_id=instance_id,
                    db_user=row.db_user,
                    program=row.application_name,
                    client_host=row.client_host,
                )

                wait_event_engine: str | None = None
                wait_event_native_name: str | None = None
                is_idle = False
                wait_event_native_name = _wait_event_native_name(row.wait_event_type, row.wait_event)
                if wait_event_native_name is not None:
                    wait_event_engine = params.engine.value
                    is_idle = await repository.ensure_wait_event(session, engine=params.engine, native_name=wait_event_native_name)

                await repository.insert_session_sample(
                    session,
                    instance_id=instance_id,
                    sampled_at=sampled_at,
                    interval_ms=interval_ms,
                    query_id=query_id,
                    wait_event_engine=wait_event_engine,
                    wait_event_native_name=wait_event_native_name,
                    session_attr_id=session_attr_id,
                    is_idle=is_idle,
                )
                session_count += 1
        except Exception as exc:  # collector must never crash the scheduler on a bad instance
            status = "error"
            error_message = str(exc)
            await session.rollback()

        overhead_ms = (time.perf_counter() - clock_start) * 1000
        finished_at = datetime.now(UTC)

        run_id = await repository.insert_collector_run(
            session,
            instance_id=instance_id,
            kind="session_sample",
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            interval_ms=interval_ms,
            overhead_ms=overhead_ms,
            clock_offset_ms=None,
            gap_detected=gap_detected,
            gap_seconds=gap_seconds,
            error_message=error_message,
        )
        await session.commit()

    return SessionSampleResult(
        run_id=run_id,
        status=status,
        overhead_ms=overhead_ms,
        session_count=session_count,
        gap_detected=gap_detected,
        gap_seconds=gap_seconds,
        error_message=error_message,
    )


async def run_query_stats_collection(instance_id: str, *, interval_ms: int = 60_000) -> QueryStatsResult:
    """One query-stats tick (Phase 1 element 2): pg_stat_statements cumulative -> delta.

    pg_stat_statements/Query Store only expose running totals since the last
    reset; `query_stat_delta` stores per-bucket deltas (ADR §3). Each query's
    previous cumulative reading lives in `query_stat_cursor` (migration 070)
    so the delta is `current - previous`, clamped to >= 0 to survive a stats
    reset without going negative. First sighting of a query establishes the
    cursor baseline without writing a (meaningless) delta row.
    """
    async with AsyncSessionLocal() as session:
        params = await repository.get_connection_params(session, instance_id)
        last_finished_at, _last_interval_ms = await repository.get_last_collector_run(session, instance_id, kind="query_stats")

        started_at = datetime.now(UTC)
        gap_detected, gap_seconds = _detect_gap(started_at=started_at, last_finished_at=last_finished_at, interval_ms=interval_ms)
        bucket_start = started_at.replace(second=0, microsecond=0)

        clock_start = time.perf_counter()
        status = "ok"
        error_message: str | None = None
        queries_seen: int | None = None
        deltas_written: int | None = None

        try:
            stat_rows = await _adapter_for(params.engine).collect_query_stats(params)
            queries_seen = 0
            deltas_written = 0

            for row in stat_rows:
                queries_seen += 1
                normalized = repository.normalize_query_text(row.normalized_text)
                query_id = await repository.upsert_query(session, instance_id=instance_id, engine=params.engine, engine_query_key=row.engine_query_key, normalized_text=normalized)

                cursor = await repository.get_query_stat_cursor(session, instance_id=instance_id, engine_query_key=row.engine_query_key)
                if cursor is not None:
                    delta_calls = max(0, row.calls - cursor.last_calls)
                    if delta_calls > 0:
                        await repository.insert_query_stat_delta(
                            session,
                            instance_id=instance_id,
                            query_id=query_id,
                            bucket_start=bucket_start,
                            calls=delta_calls,
                            total_time_ms=max(0.0, row.total_time_ms - cursor.last_total_time_ms),
                            rows_returned=max(0, row.rows - cursor.last_rows),
                            shared_blks_read=max(0, row.shared_blks_read - cursor.last_shared_blks_read),
                            shared_blks_written=max(0, row.shared_blks_written - cursor.last_shared_blks_written),
                        )
                        deltas_written += 1

                await repository.upsert_query_stat_cursor(
                    session,
                    instance_id=instance_id,
                    engine_query_key=row.engine_query_key,
                    calls=row.calls,
                    total_time_ms=row.total_time_ms,
                    rows=row.rows,
                    shared_blks_read=row.shared_blks_read,
                    shared_blks_written=row.shared_blks_written,
                )
        except Exception as exc:  # collector must never crash the scheduler on a bad instance
            status = "error"
            error_message = str(exc)
            await session.rollback()

        overhead_ms = (time.perf_counter() - clock_start) * 1000
        finished_at = datetime.now(UTC)

        run_id = await repository.insert_collector_run(
            session,
            instance_id=instance_id,
            kind="query_stats",
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            interval_ms=interval_ms,
            overhead_ms=overhead_ms,
            clock_offset_ms=None,
            gap_detected=gap_detected,
            gap_seconds=gap_seconds,
            error_message=error_message,
        )
        await session.commit()

    return QueryStatsResult(
        run_id=run_id,
        status=status,
        overhead_ms=overhead_ms,
        queries_seen=queries_seen,
        deltas_written=deltas_written,
        gap_detected=gap_detected,
        gap_seconds=gap_seconds,
        error_message=error_message,
    )


async def run_wait_sampling_history_collection(instance_id: str) -> WaitSamplingHistoryResult:
    """Explicit opt-in richer-source tick (Faza 1 element 1): drain `pg_wait_sampling_history`
    since the last watermark into `session_sample`, instead of one `pg_stat_activity` point
    sample per poll.

    Why this is its own function/CLI command rather than a mode of
    `run_session_sample_collection`: measured locally, the extension's
    default 10ms period means a session active for the full ~1s between
    two poll-based ticks yields *one* poll-based `session_sample` row but
    *~100* history-based rows for that same second -- materially higher
    storage than the ADR's stated `session_sample` volume budget (§10 risk
    table). Folding it into the default path would silently multiply
    storage the moment `pg_wait_sampling` happens to be installed. Opt-in
    plus `note` on the result (surfaced by the CLI) is the "z komunikatem o
    różnicy jakości" the roadmap calls for.

    `interval_ms` on written rows is the extension's actual measured
    period (`pg_wait_sampling.history_period`), not a poll interval --
    ADR §4's correctness rule ("interval_ms jest kolumną... nie stałą")
    applies here more literally than anywhere else in the collector.

    Timestamps come from the monitored instance's clock; corrected with
    the most recently measured `clock_offset_ms` (ADR §9) before storage.
    The watermark itself stays in the instance's clock domain (compared
    against the raw `pg_wait_sampling_history.ts` column next run), only
    the stored `sampled_at` is translated.
    """
    async with AsyncSessionLocal() as session:
        params = await repository.get_connection_params(session, instance_id)
        adapter = _adapter_for(params.engine)
        if not isinstance(adapter, PostgresEngineAdapter):
            raise NotImplementedError("run_wait_sampling_history_collection: PostgreSQL only -- pg_wait_sampling has no SQL Server equivalent")

        watermark = await repository.get_wait_sampling_watermark(session, instance_id=instance_id)

        started_at = datetime.now(UTC)
        clock_start = time.perf_counter()
        status = "ok"
        error_message: str | None = None
        samples_written: int | None = None
        distinct_sessions: int | None = None
        history_period_ms: int | None = None
        note: str | None = None
        gap_detected = False
        gap_seconds: float | None = None

        try:
            clock_offset_ms = await repository.get_latest_clock_offset_ms(session, instance_id=instance_id)
            batch = await adapter.collect_wait_sampling_history(params, since=watermark)
            history_period_ms = batch.history_period_ms

            if history_period_ms is None:
                note = "pg_wait_sampling not installed on this instance -- see docs/grants.md"
            else:
                note = (
                    f"pg_wait_sampling active ({history_period_ms}ms native period): expect substantially "
                    "more session_sample rows per active session than the poll-based sampler while this "
                    "source is used -- verify retention/storage budget (ADR data model §7, §10) before "
                    "running this continuously"
                )

            # Ring buffer is fixed-size (pg_wait_sampling.history_size rows);
            # if it wrapped past our watermark before this tick ran, older
            # samples were lost -- an explicit gap, not silence.
            if watermark is not None and batch.ring_buffer_min_ts is not None and batch.ring_buffer_min_ts > watermark:
                gap_detected = True
                gap_seconds = (batch.ring_buffer_min_ts - watermark).total_seconds()

            offset_delta = timedelta(milliseconds=clock_offset_ms) if clock_offset_ms is not None else timedelta(0)
            seen_pids: set[int] = set()
            latest_ts = watermark

            for row in batch.rows:
                seen_pids.add(row.pid)
                if latest_ts is None or row.sampled_at > latest_ts:
                    latest_ts = row.sampled_at

                query_id: str | None = None
                if row.engine_query_key:
                    query_id = await repository.find_query_id_by_engine_key(session, instance_id=instance_id, engine_query_key=row.engine_query_key)
                    if query_id is None and row.query_text:
                        normalized = repository.normalize_query_text(row.query_text)
                        query_id = await repository.upsert_query(session, instance_id=instance_id, engine=params.engine, engine_query_key=row.engine_query_key, normalized_text=normalized)
                elif row.query_text:
                    normalized = repository.normalize_query_text(row.query_text)
                    query_id = await repository.upsert_query(session, instance_id=instance_id, engine=params.engine, engine_query_key=repository.compute_norm_hash(normalized), normalized_text=normalized)

                session_attr_id = await repository.upsert_session_attr(
                    session,
                    instance_id=instance_id,
                    db_user=row.db_user,
                    program=row.application_name,
                    client_host=row.client_host,
                )

                wait_event_engine: str | None = None
                wait_event_native_name: str | None = None
                is_idle = False
                wait_event_native_name = _wait_event_native_name(row.wait_event_type, row.wait_event)
                if wait_event_native_name is not None:
                    wait_event_engine = params.engine.value
                    is_idle = await repository.ensure_wait_event(session, engine=params.engine, native_name=wait_event_native_name)

                await repository.insert_session_sample(
                    session,
                    instance_id=instance_id,
                    sampled_at=row.sampled_at - offset_delta,
                    interval_ms=history_period_ms or 10,
                    query_id=query_id,
                    wait_event_engine=wait_event_engine,
                    wait_event_native_name=wait_event_native_name,
                    session_attr_id=session_attr_id,
                    is_idle=is_idle,
                )

            samples_written = len(batch.rows)
            distinct_sessions = len(seen_pids)

            if latest_ts is not None and latest_ts != watermark:
                await repository.set_wait_sampling_watermark(session, instance_id=instance_id, last_ts=latest_ts)
        except Exception as exc:  # collector must never crash the scheduler on a bad instance
            status = "error"
            error_message = str(exc)
            await session.rollback()

        overhead_ms = (time.perf_counter() - clock_start) * 1000
        finished_at = datetime.now(UTC)

        run_id = await repository.insert_collector_run(
            session,
            instance_id=instance_id,
            kind="wait_sampling_history",
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            interval_ms=history_period_ms or 0,
            overhead_ms=overhead_ms,
            clock_offset_ms=None,
            gap_detected=gap_detected,
            gap_seconds=gap_seconds,
            error_message=error_message,
        )
        await session.commit()

    return WaitSamplingHistoryResult(
        run_id=run_id,
        status=status,
        overhead_ms=overhead_ms,
        samples_written=samples_written,
        distinct_sessions=distinct_sessions,
        history_period_ms=history_period_ms,
        gap_detected=gap_detected,
        gap_seconds=gap_seconds,
        error_message=error_message,
        note=note,
    )


@dataclass(frozen=True, slots=True)
class QueryPlansResult:
    run_id: str
    status: str
    overhead_ms: float
    plans_seen: int | None
    plans_new: int | None
    gap_detected: bool
    gap_seconds: float | None
    error_message: str | None


async def run_query_plans_collection(
    instance_id: str,
    *,
    interval_ms: int = 600_000,
    top_n: int = 20,
) -> QueryPlansResult:
    """One query-plans tick (Phase 1 element 3): top-N plans -> plan_text / query_plan.

    A new `(query_id, plan_hash)` row is the plan-change event itself (ADR §3).
    Re-seeing the same plan only bumps `last_seen`. Cadence is intentionally
    coarser than query_stats (10 min default) -- plans are large and EXPLAIN /
    dm_exec_query_plan is heavier than counter reads.
    """
    async with AsyncSessionLocal() as session:
        params = await repository.get_connection_params(session, instance_id)
        last_finished_at, _last_interval_ms = await repository.get_last_collector_run(session, instance_id, kind="query_plans")

        started_at = datetime.now(UTC)
        gap_detected, gap_seconds = _detect_gap(started_at=started_at, last_finished_at=last_finished_at, interval_ms=interval_ms)

        clock_start = time.perf_counter()
        status = "ok"
        error_message: str | None = None
        plans_seen: int | None = None
        plans_new: int | None = None

        try:
            plan_rows = await _adapter_for(params.engine).collect_query_plans(params, top_n=top_n)
            plans_seen = 0
            plans_new = 0

            for row in plan_rows:
                plans_seen += 1
                normalized = repository.normalize_query_text(row.normalized_text)
                query_id = await repository.upsert_query(
                    session,
                    instance_id=instance_id,
                    engine=params.engine,
                    engine_query_key=row.engine_query_key,
                    normalized_text=normalized,
                )
                plan_hash = await repository.upsert_plan_text(session, plan_format=row.plan_format, plan_body=row.plan_body)
                upsert = await repository.upsert_query_plan(session, query_id=query_id, plan_hash=plan_hash)
                if upsert.is_new:
                    plans_new += 1
        except Exception as exc:  # collector must never crash the scheduler on a bad instance
            status = "error"
            error_message = str(exc)
            await session.rollback()

        overhead_ms = (time.perf_counter() - clock_start) * 1000
        finished_at = datetime.now(UTC)

        run_id = await repository.insert_collector_run(
            session,
            instance_id=instance_id,
            kind="query_plans",
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            interval_ms=interval_ms,
            overhead_ms=overhead_ms,
            clock_offset_ms=None,
            gap_detected=gap_detected,
            gap_seconds=gap_seconds,
            error_message=error_message,
        )
        await session.commit()

    return QueryPlansResult(
        run_id=run_id,
        status=status,
        overhead_ms=overhead_ms,
        plans_seen=plans_seen,
        plans_new=plans_new,
        gap_detected=gap_detected,
        gap_seconds=gap_seconds,
        error_message=error_message,
    )


def _resolve_query_id_best_effort(
    *,
    engine_query_key: str | None,
    query_text: str | None,
) -> tuple[str | None, str | None]:
    """Return (engine_query_key_for_upsert, normalized_text) or (None, None)."""
    if engine_query_key and query_text:
        return engine_query_key, repository.normalize_query_text(query_text)
    if engine_query_key and not query_text:
        return engine_query_key, f"-- pulse_db:no_text:{engine_query_key}"
    if query_text and not engine_query_key:
        normalized = repository.normalize_query_text(query_text)
        return repository.compute_norm_hash(normalized), normalized
    return None, None


@dataclass(frozen=True, slots=True)
class BlockingCollectionResult:
    run_id: str
    status: str
    overhead_ms: float
    events_written: int | None
    gap_detected: bool
    gap_seconds: float | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class DeadlocksCollectionResult:
    run_id: str
    status: str
    overhead_ms: float
    events_written: int | None
    gap_detected: bool
    gap_seconds: float | None
    error_message: str | None


async def run_blocking_collection(instance_id: str, *, interval_ms: int = 30_000) -> BlockingCollectionResult:
    """One blocking tick (Phase 1 element 4): active lock chains -> blocking_event."""
    async with AsyncSessionLocal() as session:
        params = await repository.get_connection_params(session, instance_id)
        last_finished_at, _ = await repository.get_last_collector_run(session, instance_id, kind="blocking")

        started_at = datetime.now(UTC)
        gap_detected, gap_seconds = _detect_gap(started_at=started_at, last_finished_at=last_finished_at, interval_ms=interval_ms)

        clock_start = time.perf_counter()
        status = "ok"
        error_message: str | None = None
        events_written: int | None = None

        try:
            rows = await _adapter_for(params.engine).collect_blocking(params)
            events_written = 0
            for row in rows:
                blocked_key, blocked_text = _resolve_query_id_best_effort(
                    engine_query_key=row.blocked_engine_query_key,
                    query_text=row.blocked_query_text,
                )
                blocking_key, blocking_text = _resolve_query_id_best_effort(
                    engine_query_key=row.blocking_engine_query_key,
                    query_text=row.blocking_query_text,
                )
                blocked_query_id = None
                blocking_query_id = None
                if blocked_key and blocked_text:
                    blocked_query_id = await repository.upsert_query(
                        session,
                        instance_id=instance_id,
                        engine=params.engine,
                        engine_query_key=blocked_key,
                        normalized_text=blocked_text,
                    )
                if blocking_key and blocking_text:
                    blocking_query_id = await repository.upsert_query(
                        session,
                        instance_id=instance_id,
                        engine=params.engine,
                        engine_query_key=blocking_key,
                        normalized_text=blocking_text,
                    )
                await repository.insert_blocking_event(
                    session,
                    instance_id=instance_id,
                    detected_at=started_at,
                    blocking_query_id=blocking_query_id,
                    blocked_query_id=blocked_query_id,
                    blocked_duration_ms=row.blocked_duration_ms,
                    details=row.details,
                )
                events_written += 1
        except Exception as exc:
            status = "error"
            error_message = str(exc)
            await session.rollback()

        overhead_ms = (time.perf_counter() - clock_start) * 1000
        finished_at = datetime.now(UTC)

        run_id = await repository.insert_collector_run(
            session,
            instance_id=instance_id,
            kind="blocking",
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            interval_ms=interval_ms,
            overhead_ms=overhead_ms,
            clock_offset_ms=None,
            gap_detected=gap_detected,
            gap_seconds=gap_seconds,
            error_message=error_message,
        )
        await session.commit()

    return BlockingCollectionResult(
        run_id=run_id,
        status=status,
        overhead_ms=overhead_ms,
        events_written=events_written,
        gap_detected=gap_detected,
        gap_seconds=gap_seconds,
        error_message=error_message,
    )


async def run_deadlocks_collection(instance_id: str, *, interval_ms: int = 60_000) -> DeadlocksCollectionResult:
    """One deadlocks tick (Phase 1 element 4): system_health drain -> deadlock_event."""
    async with AsyncSessionLocal() as session:
        params = await repository.get_connection_params(session, instance_id)
        last_finished_at, _ = await repository.get_last_collector_run(session, instance_id, kind="deadlocks")
        watermark = await repository.get_deadlock_watermark(session, instance_id=instance_id)

        started_at = datetime.now(UTC)
        gap_detected, gap_seconds = _detect_gap(started_at=started_at, last_finished_at=last_finished_at, interval_ms=interval_ms)

        clock_start = time.perf_counter()
        status = "ok"
        error_message: str | None = None
        events_written: int | None = None

        try:
            clock_offset_ms = await repository.get_latest_clock_offset_ms(session, instance_id=instance_id)
            rows = await _adapter_for(params.engine).collect_deadlocks(params, since=watermark)
            events_written = 0
            max_occurred: datetime | None = watermark

            for row in rows:
                detected_at = row.occurred_at
                if clock_offset_ms is not None:
                    detected_at = row.occurred_at + timedelta(milliseconds=clock_offset_ms)
                if detected_at.tzinfo is None:
                    detected_at = detected_at.replace(tzinfo=UTC)

                victim_query_id = None
                victim_key, victim_text = _resolve_query_id_best_effort(
                    engine_query_key=row.victim_engine_query_key,
                    query_text=None,
                )
                if victim_key and victim_text:
                    victim_query_id = await repository.upsert_query(
                        session,
                        instance_id=instance_id,
                        engine=params.engine,
                        engine_query_key=victim_key,
                        normalized_text=victim_text,
                    )

                await repository.insert_deadlock_event(
                    session,
                    instance_id=instance_id,
                    detected_at=detected_at,
                    victim_query_id=victim_query_id,
                    details=row.details,
                )
                events_written += 1
                if max_occurred is None or row.occurred_at > max_occurred:
                    max_occurred = row.occurred_at

            if max_occurred is not None and (watermark is None or max_occurred > watermark):
                await repository.set_deadlock_watermark(session, instance_id=instance_id, last_event_at=max_occurred)
        except Exception as exc:
            status = "error"
            error_message = str(exc)
            await session.rollback()

        overhead_ms = (time.perf_counter() - clock_start) * 1000
        finished_at = datetime.now(UTC)

        run_id = await repository.insert_collector_run(
            session,
            instance_id=instance_id,
            kind="deadlocks",
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            interval_ms=interval_ms,
            overhead_ms=overhead_ms,
            clock_offset_ms=None,
            gap_detected=gap_detected,
            gap_seconds=gap_seconds,
            error_message=error_message,
        )
        await session.commit()

    return DeadlocksCollectionResult(
        run_id=run_id,
        status=status,
        overhead_ms=overhead_ms,
        events_written=events_written,
        gap_detected=gap_detected,
        gap_seconds=gap_seconds,
        error_message=error_message,
    )
