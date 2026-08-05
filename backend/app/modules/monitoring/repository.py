"""Raw-SQL repository for the monitoring domain.

The domain schema is raw DDL (migrations/068, migrations/069), not
SQLAlchemy metadata (see backend/migrations/README.md), so reads/writes here
go through `text()` rather than the ORM.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.core.database import AsyncSessionLocal

from .crypto import decrypt_secret, encrypt_secret
from .engine_adapter import Engine, EngineCapabilities, InstanceConnectionParams

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_query_text(raw_text: str) -> str:
    """Collapse whitespace so semantically-identical query text hashes the same.

    Deliberately *not* a literal-stripping normalizer (ADR §10 risk: "nie
    piszemy własnej [normalizacji] od zera" -- the engine already does that
    via pg_stat_statements/Query Store). This only smooths formatting noise
    on top of text that's ideally already engine-normalized; it's also used
    as the interim fallback when a session's query hasn't appeared in
    pg_stat_statements yet (query still running, first execution).

    Strips NUL bytes: SQL Server cursor/`sp_cursor` text from
    ``dm_exec_sql_text`` can embed ``\\x00``, which PostgreSQL rejects as
    invalid UTF-8 (confirmed live on BSM-SQL13).
    """
    cleaned = raw_text.replace("\x00", "")
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def compute_norm_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class MonitoredInstanceRecord:
    id: str
    name: str
    engine: Engine
    host: str
    port: int
    database_name: str
    username: str
    timezone: str
    capabilities: dict
    is_active: bool


async def register_instance(
    *,
    name: str,
    engine: Engine,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    timezone: str = "UTC",
) -> str:
    """Register a monitored instance. Password is encrypted before it ever hits the DB."""
    instance_id = generate_id()
    encrypted_password = encrypt_secret(password)
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                INSERT INTO monitored_instance
                    (id, name, engine, host, port, database_name, username, encrypted_password, timezone)
                VALUES
                    (:id, :name, :engine, :host, :port, :database_name, :username, :encrypted_password, :timezone)
                """),
            {
                "id": instance_id,
                "name": name,
                "engine": engine.value,
                "host": host,
                "port": port,
                "database_name": database,
                "username": username,
                "encrypted_password": encrypted_password,
                "timezone": timezone,
            },
        )
        await session.commit()
    return instance_id


async def list_instances() -> list[MonitoredInstanceRecord]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
                SELECT id, name, engine, host, port, database_name, username, timezone, capabilities, is_active
                FROM monitored_instance
                ORDER BY created_at
                """))
        return [
            MonitoredInstanceRecord(
                id=row.id,
                name=row.name,
                engine=Engine(row.engine),
                host=row.host,
                port=row.port,
                database_name=row.database_name,
                username=row.username,
                timezone=row.timezone,
                capabilities=row.capabilities or {},
                is_active=row.is_active,
            )
            for row in result
        ]


async def get_connection_params(session: AsyncSession, instance_id: str) -> InstanceConnectionParams:
    """Load an instance row and decrypt its password for a live connection.

    Callers own the session's lifetime (kept separate from register/list so
    the collector can reuse one session across several repository calls).
    """
    result = await session.execute(
        text("""
            SELECT engine, host, port, database_name, username, encrypted_password
            FROM monitored_instance
            WHERE id = :id
            """),
        {"id": instance_id},
    )
    row = result.one()
    return InstanceConnectionParams(
        host=row.host,
        port=row.port,
        database=row.database_name,
        username=row.username,
        password=decrypt_secret(row.encrypted_password),
        engine=Engine(row.engine),
    )


async def update_capabilities(session: AsyncSession, instance_id: str, capabilities: EngineCapabilities) -> None:
    await session.execute(
        text("""
            UPDATE monitored_instance
            SET capabilities = CAST(:capabilities AS jsonb), last_seen_at = now(), updated_at = now()
            WHERE id = :id
            """),
        {"id": instance_id, "capabilities": json.dumps(capabilities.to_jsonb())},
    )


async def get_last_collector_run(session: AsyncSession, instance_id: str, kind: str = "trivial") -> tuple[datetime | None, int | None]:
    """Return (finished_at, interval_ms) of the most recent run of this kind, or (None, None).

    `kind` matters (migration 070): a 1s-cadence session sampler and a 60s
    trivial/query-stats tick must each compare against their own last run,
    not each other's, or gap detection misfires.
    """
    result = await session.execute(
        text("""
            SELECT finished_at, interval_ms
            FROM collector_run
            WHERE instance_id = :instance_id AND kind = :kind AND finished_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 1
            """),
        {"instance_id": instance_id, "kind": kind},
    )
    row = result.first()
    if row is None:
        return None, None
    return row.finished_at, row.interval_ms


async def insert_collector_run(
    session: AsyncSession,
    *,
    instance_id: str,
    kind: str,
    started_at: datetime,
    finished_at: datetime | None,
    status: str,
    interval_ms: int,
    overhead_ms: float | None,
    clock_offset_ms: float | None,
    gap_detected: bool,
    gap_seconds: float | None,
    error_message: str | None,
) -> str:
    run_id = generate_id()
    await session.execute(
        text("""
            INSERT INTO collector_run
                (id, instance_id, kind, started_at, finished_at, status, interval_ms, overhead_ms,
                 clock_offset_ms, gap_detected, gap_seconds, error_message)
            VALUES
                (:id, :instance_id, :kind, :started_at, :finished_at, :status, :interval_ms, :overhead_ms,
                 :clock_offset_ms, :gap_detected, :gap_seconds, :error_message)
            """),
        {
            "id": run_id,
            "instance_id": instance_id,
            "kind": kind,
            "started_at": started_at,
            "finished_at": finished_at,
            "status": status,
            "interval_ms": interval_ms,
            "overhead_ms": overhead_ms,
            "clock_offset_ms": clock_offset_ms,
            "gap_detected": gap_detected,
            "gap_seconds": gap_seconds,
            "error_message": error_message,
        },
    )
    return run_id


async def insert_instance_metric(session: AsyncSession, *, instance_id: str, sampled_at: datetime, metric_id: str, value: float) -> None:
    await session.execute(
        text("""
            INSERT INTO instance_metric (id, instance_id, sampled_at, metric_id, value)
            VALUES (:id, :instance_id, :sampled_at, :metric_id, :value)
            """),
        {"id": generate_id(), "instance_id": instance_id, "sampled_at": sampled_at, "metric_id": metric_id, "value": value},
    )


# --- Phase 1 element 1/2: query identity, sessions, query stats ------------


async def upsert_query(session: AsyncSession, *, instance_id: str, engine: Engine, engine_query_key: str, normalized_text: str) -> str:
    """Upsert `query_text` (by content hash) + `query` (by native identity), return `query.id`.

    Two-step upsert mirrors ADR §5's two-level identity: `query_text.norm_hash`
    is content-addressed and shared across instances/engines when the text
    matches; `query.engine_query_key` is per-instance native identity that
    can change (version upgrade, stats reset) without breaking the link to
    history, because it's `norm_hash` that ties old and new rows together.
    """
    norm_hash = compute_norm_hash(normalized_text)
    await session.execute(
        text("""
            INSERT INTO query_text (norm_hash, normalized_text)
            VALUES (:norm_hash, :normalized_text)
            ON CONFLICT (norm_hash) DO NOTHING
            """),
        {"norm_hash": norm_hash, "normalized_text": normalized_text},
    )

    result = await session.execute(
        text("""
            INSERT INTO query (id, instance_id, engine, engine_query_key, norm_hash)
            VALUES (:id, :instance_id, :engine, :engine_query_key, :norm_hash)
            ON CONFLICT (instance_id, engine_query_key)
                DO UPDATE SET last_seen = now(), norm_hash = EXCLUDED.norm_hash
            RETURNING id
            """),
        {
            "id": generate_id(),
            "instance_id": instance_id,
            "engine": engine.value,
            "engine_query_key": engine_query_key,
            "norm_hash": norm_hash,
        },
    )
    return str(result.scalar_one())


async def find_query_id_by_engine_key(session: AsyncSession, *, instance_id: str, engine_query_key: str) -> str | None:
    result = await session.execute(
        text("SELECT id FROM query WHERE instance_id = :instance_id AND engine_query_key = :engine_query_key"),
        {"instance_id": instance_id, "engine_query_key": engine_query_key},
    )
    row = result.first()
    return row.id if row else None


async def ensure_wait_event(session: AsyncSession, *, engine: Engine, native_name: str) -> bool:
    """Return `is_idle` for (engine, native_name), auto-registering unknown natives as `other`.

    ADR §5: "Nieznany wait natywny wpada do Other z zachowaną nazwą i nie
    psuje zbierania" -- an engine/PG-version wait name we haven't seeded
    (migration 068) must never block a sample from being written.
    """
    result = await session.execute(
        text("SELECT is_idle FROM wait_event WHERE engine = :engine AND native_name = :native_name"),
        {"engine": engine.value, "native_name": native_name},
    )
    row = result.first()
    if row is not None:
        return bool(row.is_idle)

    await session.execute(
        text("""
            INSERT INTO wait_event (engine, native_name, wait_class_id, is_idle)
            VALUES (:engine, :native_name, 'other', FALSE)
            ON CONFLICT (engine, native_name) DO NOTHING
            """),
        {"engine": engine.value, "native_name": native_name},
    )
    return False


async def upsert_session_attr(session: AsyncSession, *, instance_id: str, db_user: str, program: str, client_host: str) -> str:
    result = await session.execute(
        text("""
            INSERT INTO session_attr (id, instance_id, db_user, program, client_host)
            VALUES (:id, :instance_id, :db_user, :program, :client_host)
            ON CONFLICT (instance_id, db_user, program, client_host)
                DO UPDATE SET db_user = EXCLUDED.db_user
            RETURNING id
            """),
        {
            "id": generate_id(),
            "instance_id": instance_id,
            "db_user": db_user,
            "program": program,
            "client_host": client_host,
        },
    )
    return str(result.scalar_one())


async def insert_session_sample(
    session: AsyncSession,
    *,
    instance_id: str,
    sampled_at: datetime,
    interval_ms: int,
    query_id: str | None,
    wait_event_engine: str | None,
    wait_event_native_name: str | None,
    session_attr_id: str,
    is_idle: bool,
) -> None:
    await session.execute(
        text("""
            INSERT INTO session_sample
                (id, instance_id, sampled_at, interval_ms, query_id, wait_event_engine,
                 wait_event_native_name, session_attr_id, is_idle)
            VALUES
                (:id, :instance_id, :sampled_at, :interval_ms, :query_id, :wait_event_engine,
                 :wait_event_native_name, :session_attr_id, :is_idle)
            """),
        {
            "id": generate_id(),
            "instance_id": instance_id,
            "sampled_at": sampled_at,
            "interval_ms": interval_ms,
            "query_id": query_id,
            "wait_event_engine": wait_event_engine,
            "wait_event_native_name": wait_event_native_name,
            "session_attr_id": session_attr_id,
            "is_idle": is_idle,
        },
    )


@dataclass(frozen=True, slots=True)
class QueryStatCursor:
    last_calls: int
    last_total_time_ms: float
    last_rows: int
    last_shared_blks_read: int
    last_shared_blks_written: int


async def get_query_stat_cursor(session: AsyncSession, *, instance_id: str, engine_query_key: str) -> QueryStatCursor | None:
    result = await session.execute(
        text("""
            SELECT last_calls, last_total_time_ms, last_rows, last_shared_blks_read, last_shared_blks_written
            FROM query_stat_cursor
            WHERE instance_id = :instance_id AND engine_query_key = :engine_query_key
            """),
        {"instance_id": instance_id, "engine_query_key": engine_query_key},
    )
    row = result.first()
    if row is None:
        return None
    return QueryStatCursor(
        last_calls=row.last_calls,
        last_total_time_ms=row.last_total_time_ms,
        last_rows=row.last_rows,
        last_shared_blks_read=row.last_shared_blks_read,
        last_shared_blks_written=row.last_shared_blks_written,
    )


async def upsert_query_stat_cursor(
    session: AsyncSession,
    *,
    instance_id: str,
    engine_query_key: str,
    calls: int,
    total_time_ms: float,
    rows: int,
    shared_blks_read: int,
    shared_blks_written: int,
) -> None:
    await session.execute(
        text("""
            INSERT INTO query_stat_cursor
                (instance_id, engine_query_key, last_calls, last_total_time_ms, last_rows,
                 last_shared_blks_read, last_shared_blks_written, updated_at)
            VALUES
                (:instance_id, :engine_query_key, :calls, :total_time_ms, :rows,
                 :shared_blks_read, :shared_blks_written, now())
            ON CONFLICT (instance_id, engine_query_key) DO UPDATE SET
                last_calls = EXCLUDED.last_calls,
                last_total_time_ms = EXCLUDED.last_total_time_ms,
                last_rows = EXCLUDED.last_rows,
                last_shared_blks_read = EXCLUDED.last_shared_blks_read,
                last_shared_blks_written = EXCLUDED.last_shared_blks_written,
                updated_at = now()
            """),
        {
            "instance_id": instance_id,
            "engine_query_key": engine_query_key,
            "calls": calls,
            "total_time_ms": total_time_ms,
            "rows": rows,
            "shared_blks_read": shared_blks_read,
            "shared_blks_written": shared_blks_written,
        },
    )


async def insert_query_stat_delta(
    session: AsyncSession,
    *,
    instance_id: str,
    query_id: str,
    bucket_start: datetime,
    calls: int,
    total_time_ms: float,
    rows_returned: int,
    shared_blks_read: int,
    shared_blks_written: int,
) -> None:
    await session.execute(
        text("""
            INSERT INTO query_stat_delta
                (id, instance_id, query_id, bucket_start, calls, total_time_ms, rows_returned,
                 shared_blks_read, shared_blks_written)
            VALUES
                (:id, :instance_id, :query_id, :bucket_start, :calls, :total_time_ms, :rows_returned,
                 :shared_blks_read, :shared_blks_written)
            """),
        {
            "id": generate_id(),
            "instance_id": instance_id,
            "query_id": query_id,
            "bucket_start": bucket_start,
            "calls": calls,
            "total_time_ms": total_time_ms,
            "rows_returned": rows_returned,
            "shared_blks_read": shared_blks_read,
            "shared_blks_written": shared_blks_written,
        },
    )


# --- Phase 1 element 1, richer source: pg_wait_sampling_history -----------


async def get_wait_sampling_watermark(session: AsyncSession, *, instance_id: str) -> datetime | None:
    result = await session.execute(
        text("SELECT last_ts FROM wait_sampling_cursor WHERE instance_id = :instance_id"),
        {"instance_id": instance_id},
    )
    row = result.first()
    return row.last_ts if row else None


async def set_wait_sampling_watermark(session: AsyncSession, *, instance_id: str, last_ts: datetime) -> None:
    await session.execute(
        text("""
            INSERT INTO wait_sampling_cursor (instance_id, last_ts, updated_at)
            VALUES (:instance_id, :last_ts, now())
            ON CONFLICT (instance_id) DO UPDATE SET last_ts = EXCLUDED.last_ts, updated_at = now()
            """),
        {"instance_id": instance_id, "last_ts": last_ts},
    )


# --- Phase 0 element 7: rollups (ash_1m, ash_1h, query_stat_1h) -----------


@dataclass(frozen=True, slots=True)
class AshBucketRow:
    query_id: str | None
    wait_class_id: str | None
    wait_seconds: float
    sample_count: int


@dataclass(frozen=True, slots=True)
class QueryStatBucketRow:
    query_id: str | None
    calls: int
    total_time_ms: float
    rows_returned: int
    shared_blks_read: int
    shared_blks_written: int


async def get_rollup_cursor(session: AsyncSession, *, instance_id: str, kind: str) -> datetime | None:
    result = await session.execute(
        text("SELECT watermark FROM rollup_cursor WHERE instance_id = :instance_id AND kind = :kind"),
        {"instance_id": instance_id, "kind": kind},
    )
    row = result.first()
    return row.watermark if row else None


async def set_rollup_cursor(session: AsyncSession, *, instance_id: str, kind: str, watermark: datetime) -> None:
    await session.execute(
        text("""
            INSERT INTO rollup_cursor (instance_id, kind, watermark, updated_at)
            VALUES (:instance_id, :kind, :watermark, now())
            ON CONFLICT (instance_id, kind) DO UPDATE SET watermark = EXCLUDED.watermark, updated_at = now()
            """),
        {"instance_id": instance_id, "kind": kind, "watermark": watermark},
    )


async def get_earliest_session_sample_at(session: AsyncSession, *, instance_id: str) -> datetime | None:
    result = await session.execute(
        text("SELECT MIN(sampled_at) AS earliest FROM session_sample WHERE instance_id = :instance_id"),
        {"instance_id": instance_id},
    )
    return result.scalar_one_or_none()


async def get_earliest_query_stat_delta_at(session: AsyncSession, *, instance_id: str) -> datetime | None:
    result = await session.execute(
        text("SELECT MIN(bucket_start) AS earliest FROM query_stat_delta WHERE instance_id = :instance_id"),
        {"instance_id": instance_id},
    )
    return result.scalar_one_or_none()


async def aggregate_session_sample_bucket(session: AsyncSession, *, instance_id: str, bucket_start: datetime, bucket_end: datetime) -> list[AshBucketRow]:
    """Wait attribution for one raw bucket, grouped by (query, wait class).

    Excludes idle rows by default (ADR §5's correctness rule: idle time is
    never counted as waiting). Rows with no native wait event and
    `is_idle = FALSE` are sessions actually running on CPU -- classified as
    the `cpu` wait class even though there's no `wait_event` row for them.
    """
    result = await session.execute(
        text("""
            SELECT
                ss.query_id AS query_id,
                COALESCE(we.wait_class_id, 'cpu') AS wait_class_id,
                SUM(ss.interval_ms) / 1000.0 AS wait_seconds,
                COUNT(*) AS sample_count
            FROM session_sample ss
            LEFT JOIN wait_event we
                ON we.engine = ss.wait_event_engine AND we.native_name = ss.wait_event_native_name
            WHERE ss.instance_id = :instance_id
                AND ss.sampled_at >= :bucket_start
                AND ss.sampled_at < :bucket_end
                AND ss.is_idle = FALSE
            GROUP BY ss.query_id, COALESCE(we.wait_class_id, 'cpu')
            """),
        {"instance_id": instance_id, "bucket_start": bucket_start, "bucket_end": bucket_end},
    )
    return [AshBucketRow(query_id=row.query_id, wait_class_id=row.wait_class_id, wait_seconds=row.wait_seconds, sample_count=row.sample_count) for row in result]


async def aggregate_ash_1m_bucket(session: AsyncSession, *, instance_id: str, bucket_start: datetime, bucket_end: datetime) -> list[AshBucketRow]:
    """Rollup-of-rollup for `ash_1h`: re-group `ash_1m` rows covering one hour.

    Cheaper than re-scanning raw `session_sample` for the hour, and keeps the
    hourly top-N a genuine re-ranking rather than a second, independent
    truncation -- prior `is_other` rows (query_id/wait_class_id both NULL)
    naturally merge into one combined "other" contribution via GROUP BY,
    which then competes fairly for the hour's own top N.
    """
    result = await session.execute(
        text("""
            SELECT query_id, wait_class_id, SUM(wait_seconds) AS wait_seconds, SUM(sample_count) AS sample_count
            FROM ash_1m
            WHERE instance_id = :instance_id
                AND bucket_start >= :bucket_start
                AND bucket_start < :bucket_end
            GROUP BY query_id, wait_class_id
            """),
        {"instance_id": instance_id, "bucket_start": bucket_start, "bucket_end": bucket_end},
    )
    return [AshBucketRow(query_id=row.query_id, wait_class_id=row.wait_class_id, wait_seconds=row.wait_seconds, sample_count=row.sample_count) for row in result]


async def insert_ash_rollup_row(session: AsyncSession, *, table: str, instance_id: str, bucket_start: datetime, row: AshBucketRow, is_other: bool) -> None:
    """`table` is always one of the two internal constants ('ash_1m'/'ash_1h'), never user input."""
    await session.execute(
        text(f"""
            INSERT INTO "{table}" (id, instance_id, bucket_start, query_id, wait_class_id, wait_seconds, sample_count, is_other)
            VALUES (:id, :instance_id, :bucket_start, :query_id, :wait_class_id, :wait_seconds, :sample_count, :is_other)
            """),
        {
            "id": generate_id(),
            "instance_id": instance_id,
            "bucket_start": bucket_start,
            "query_id": row.query_id,
            "wait_class_id": row.wait_class_id,
            "wait_seconds": row.wait_seconds,
            "sample_count": row.sample_count,
            "is_other": is_other,
        },
    )


async def aggregate_query_stat_delta_bucket(session: AsyncSession, *, instance_id: str, bucket_start: datetime, bucket_end: datetime) -> list[QueryStatBucketRow]:
    result = await session.execute(
        text("""
            SELECT
                query_id,
                SUM(calls) AS calls,
                SUM(total_time_ms) AS total_time_ms,
                SUM(rows_returned) AS rows_returned,
                SUM(shared_blks_read) AS shared_blks_read,
                SUM(shared_blks_written) AS shared_blks_written
            FROM query_stat_delta
            WHERE instance_id = :instance_id
                AND bucket_start >= :bucket_start
                AND bucket_start < :bucket_end
            GROUP BY query_id
            """),
        {"instance_id": instance_id, "bucket_start": bucket_start, "bucket_end": bucket_end},
    )
    return [
        QueryStatBucketRow(
            query_id=row.query_id,
            calls=row.calls,
            total_time_ms=row.total_time_ms,
            rows_returned=row.rows_returned,
            shared_blks_read=row.shared_blks_read,
            shared_blks_written=row.shared_blks_written,
        )
        for row in result
    ]


async def insert_query_stat_1h_row(session: AsyncSession, *, instance_id: str, bucket_start: datetime, row: QueryStatBucketRow, is_other: bool) -> None:
    await session.execute(
        text("""
            INSERT INTO query_stat_1h
                (id, instance_id, bucket_start, query_id, calls, total_time_ms, rows_returned, shared_blks_read, shared_blks_written, is_other)
            VALUES
                (:id, :instance_id, :bucket_start, :query_id, :calls, :total_time_ms, :rows_returned, :shared_blks_read, :shared_blks_written, :is_other)
            """),
        {
            "id": generate_id(),
            "instance_id": instance_id,
            "bucket_start": bucket_start,
            "query_id": row.query_id,
            "calls": row.calls,
            "total_time_ms": row.total_time_ms,
            "rows_returned": row.rows_returned,
            "shared_blks_read": row.shared_blks_read,
            "shared_blks_written": row.shared_blks_written,
            "is_other": is_other,
        },
    )


# --- Phase 1 element 6: period comparison (baseline level 1) ----------------


@dataclass(frozen=True, slots=True)
class QueryPeriodAggregate:
    query_id: str
    calls: int
    total_time_ms: float
    rows_returned: int


@dataclass(frozen=True, slots=True)
class InstancePeriodAggregate:
    calls: int
    total_time_ms: float
    rows_returned: int


@dataclass(frozen=True, slots=True)
class WaitPeriodAggregate:
    wait_class_id: str | None
    wait_seconds: float
    sample_count: int
    is_other: bool


async def instance_exists(session: AsyncSession, *, instance_id: str) -> bool:
    result = await session.execute(
        text("SELECT 1 FROM monitored_instance WHERE id = :instance_id"),
        {"instance_id": instance_id},
    )
    return result.first() is not None


async def aggregate_query_stat_period(
    session: AsyncSession,
    *,
    instance_id: str,
    period_start: datetime,
    period_end: datetime,
) -> list[QueryPeriodAggregate]:
    """Sum `query_stat_1h` per query for a half-open window [start, end).

    Excludes the top-N overflow bucket (`is_other`) so comparisons stay at
    per-query grain; queries outside top-N in a given hour simply have no
    row for that hour (ADR §6 accepted trade-off).
    """
    result = await session.execute(
        text("""
            SELECT
                qs.query_id AS query_id,
                SUM(qs.calls)::bigint AS calls,
                SUM(qs.total_time_ms) AS total_time_ms,
                SUM(qs.rows_returned)::bigint AS rows_returned
            FROM query_stat_1h qs
            WHERE qs.instance_id = :instance_id
                AND qs.bucket_start >= :period_start
                AND qs.bucket_start < :period_end
                AND qs.is_other = FALSE
                AND qs.query_id IS NOT NULL
            GROUP BY qs.query_id
            """),
        {"instance_id": instance_id, "period_start": period_start, "period_end": period_end},
    )
    return [
        QueryPeriodAggregate(
            query_id=row.query_id,
            calls=int(row.calls),
            total_time_ms=float(row.total_time_ms),
            rows_returned=int(row.rows_returned),
        )
        for row in result
    ]


async def aggregate_instance_query_stat_period(
    session: AsyncSession,
    *,
    instance_id: str,
    period_start: datetime,
    period_end: datetime,
) -> InstancePeriodAggregate | None:
    """Instance-wide totals from `query_stat_1h`, including the overflow bucket."""
    result = await session.execute(
        text("""
            SELECT
                SUM(calls)::bigint AS calls,
                SUM(total_time_ms) AS total_time_ms,
                SUM(rows_returned)::bigint AS rows_returned
            FROM query_stat_1h
            WHERE instance_id = :instance_id
                AND bucket_start >= :period_start
                AND bucket_start < :period_end
            """),
        {"instance_id": instance_id, "period_start": period_start, "period_end": period_end},
    )
    row = result.first()
    if row is None or row.calls is None:
        return None
    return InstancePeriodAggregate(
        calls=int(row.calls),
        total_time_ms=float(row.total_time_ms),
        rows_returned=int(row.rows_returned),
    )


async def aggregate_wait_period(
    session: AsyncSession,
    *,
    instance_id: str,
    period_start: datetime,
    period_end: datetime,
) -> list[WaitPeriodAggregate]:
    """Sum `ash_1h` per wait class for a half-open window [start, end)."""
    result = await session.execute(
        text("""
            SELECT
                wait_class_id,
                SUM(wait_seconds) AS wait_seconds,
                SUM(sample_count)::bigint AS sample_count,
                BOOL_OR(is_other) AS is_other
            FROM ash_1h
            WHERE instance_id = :instance_id
                AND bucket_start >= :period_start
                AND bucket_start < :period_end
            GROUP BY wait_class_id
            """),
        {"instance_id": instance_id, "period_start": period_start, "period_end": period_end},
    )
    return [
        WaitPeriodAggregate(
            wait_class_id=row.wait_class_id,
            wait_seconds=float(row.wait_seconds),
            sample_count=int(row.sample_count),
            is_other=bool(row.is_other),
        )
        for row in result
    ]


async def get_query_texts(session: AsyncSession, *, query_ids: list[str]) -> dict[str, str]:
    if not query_ids:
        return {}
    result = await session.execute(
        text("""
            SELECT q.id AS query_id, qt.normalized_text
            FROM query q
            JOIN query_text qt ON qt.norm_hash = q.norm_hash
            WHERE q.id IN :query_ids
            """).bindparams(bindparam("query_ids", expanding=True)),
        {"query_ids": query_ids},
    )
    return {row.query_id: row.normalized_text for row in result}


async def get_wait_class_labels(session: AsyncSession) -> dict[str, str]:
    result = await session.execute(text("SELECT id, label FROM wait_class"))
    return {row.id: row.label for row in result}


async def get_latest_clock_offset_ms(session: AsyncSession, *, instance_id: str) -> float | None:
    """Most recent measured `clock_offset_ms` for this instance (any collector_run kind).

    Used to translate monitored-instance-clock timestamps (e.g.
    `pg_wait_sampling_history.ts`) back to PulseDB's authoritative clock
    (ADR §9: "Zegarem autorytatywnym jest zegar PulseDB, nie monitorowanej
    bazy" -- but engine-origin timestamps are still translatable after the
    fact once the offset is known).
    """
    result = await session.execute(
        text("""
            SELECT clock_offset_ms
            FROM collector_run
            WHERE instance_id = :instance_id AND clock_offset_ms IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 1
            """),
        {"instance_id": instance_id},
    )
    row = result.first()
    return row.clock_offset_ms if row else None
