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


async def update_instance_connection(
    *,
    instance_id: str,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
) -> None:
    """Update connection params for a registered instance (re-encrypts password)."""
    encrypted_password = encrypt_secret(password)
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
                UPDATE monitored_instance
                SET host = :host,
                    port = :port,
                    database_name = :database_name,
                    username = :username,
                    encrypted_password = :encrypted_password,
                    updated_at = now()
                WHERE id = :id
                """),
            {
                "id": instance_id,
                "host": host,
                "port": port,
                "database_name": database,
                "username": username,
                "encrypted_password": encrypted_password,
            },
        )
        await session.commit()


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


# --- REST read APIs: instance list + waits timeline -------------------------


@dataclass(frozen=True, slots=True)
class InstanceListRow:
    id: str
    name: str
    engine: Engine
    host: str
    port: int
    is_active: bool
    last_sample_at: datetime | None
    last_collector_finished_at: datetime | None
    last_collector_status: str | None
    last_collector_gap_detected: bool | None


@dataclass(frozen=True, slots=True)
class WaitsTimelineRow:
    bucket_start: datetime
    wait_class_id: str | None
    wait_seconds: float
    sample_count: int
    is_other: bool


async def list_instances_with_status(session: AsyncSession) -> list[InstanceListRow]:
    result = await session.execute(
        text("""
            SELECT
                mi.id,
                mi.name,
                mi.engine,
                mi.host,
                mi.port,
                mi.is_active,
                ls.last_sample_at,
                lr.finished_at AS last_collector_finished_at,
                lr.status AS last_collector_status,
                lr.gap_detected AS last_collector_gap_detected
            FROM monitored_instance mi
            LEFT JOIN LATERAL (
                SELECT MAX(sampled_at) AS last_sample_at
                FROM session_sample ss
                WHERE ss.instance_id = mi.id
            ) ls ON TRUE
            LEFT JOIN LATERAL (
                SELECT finished_at, status, gap_detected
                FROM collector_run cr
                WHERE cr.instance_id = mi.id AND cr.kind = 'session_sample'
                ORDER BY cr.started_at DESC
                LIMIT 1
            ) lr ON TRUE
            ORDER BY mi.created_at
            """),
    )
    return [
        InstanceListRow(
            id=row.id,
            name=row.name,
            engine=Engine(row.engine),
            host=row.host,
            port=row.port,
            is_active=row.is_active,
            last_sample_at=row.last_sample_at,
            last_collector_finished_at=row.last_collector_finished_at,
            last_collector_status=row.last_collector_status,
            last_collector_gap_detected=row.last_collector_gap_detected,
        )
        for row in result
    ]


async def fetch_waits_timeline(
    session: AsyncSession,
    *,
    instance_id: str,
    period_start: datetime,
    period_end: datetime,
    granularity: str,
) -> list[WaitsTimelineRow]:
    """Instance-level wait seconds per bucket and wait class from ash rollups."""
    table = "ash_1m" if granularity == "1m" else "ash_1h"
    result = await session.execute(
        text(f"""
            SELECT
                bucket_start,
                wait_class_id,
                SUM(wait_seconds) AS wait_seconds,
                SUM(sample_count)::bigint AS sample_count,
                BOOL_OR(is_other) AS is_other
            FROM "{table}"
            WHERE instance_id = :instance_id
                AND bucket_start >= :period_start
                AND bucket_start < :period_end
            GROUP BY bucket_start, wait_class_id
            ORDER BY bucket_start, wait_class_id NULLS LAST
            """),
        {
            "instance_id": instance_id,
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    return [
        WaitsTimelineRow(
            bucket_start=row.bucket_start,
            wait_class_id=row.wait_class_id,
            wait_seconds=float(row.wait_seconds),
            sample_count=int(row.sample_count),
            is_other=bool(row.is_other),
        )
        for row in result
    ]


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


# --- Phase 1 element 3: execution plans + plan-change detection ------------


def compute_plan_hash(plan_body: str) -> str:
    """Content-addressed identity for `plan_text` (same shape as `norm_hash`)."""
    return hashlib.sha256(plan_body.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class QueryPlanUpsertResult:
    plan_hash: str
    is_new: bool


@dataclass(frozen=True, slots=True)
class QueryPlanListItem:
    plan_hash: str
    plan_format: str
    first_seen: datetime
    last_seen: datetime


@dataclass(frozen=True, slots=True)
class QueryPlanDetail:
    plan_hash: str
    plan_format: str
    plan_body: str
    first_seen: datetime
    last_seen: datetime


@dataclass(frozen=True, slots=True)
class PlanChangeRow:
    query_id: str
    plan_hash: str
    plan_format: str
    first_seen: datetime
    query_text: str | None
    plan_count: int


async def upsert_plan_text(session: AsyncSession, *, plan_format: str, plan_body: str) -> str:
    """Insert `plan_text` by content hash; return `plan_hash`. Idempotent."""
    plan_hash = compute_plan_hash(plan_body)
    await session.execute(
        text("""
            INSERT INTO plan_text (plan_hash, plan_format, plan_body)
            VALUES (:plan_hash, :plan_format, :plan_body)
            ON CONFLICT (plan_hash) DO NOTHING
            """),
        {"plan_hash": plan_hash, "plan_format": plan_format, "plan_body": plan_body},
    )
    return plan_hash


async def upsert_query_plan(session: AsyncSession, *, query_id: str, plan_hash: str) -> QueryPlanUpsertResult:
    """Link query ↔ plan. New `(query_id, plan_hash)` is the plan-change event (ADR §3)."""
    existing = await session.execute(
        text("""
            SELECT 1 FROM query_plan
            WHERE query_id = :query_id AND plan_hash = :plan_hash
            """),
        {"query_id": query_id, "plan_hash": plan_hash},
    )
    is_new = existing.first() is None

    await session.execute(
        text("""
            INSERT INTO query_plan (query_id, plan_hash)
            VALUES (:query_id, :plan_hash)
            ON CONFLICT (query_id, plan_hash)
                DO UPDATE SET last_seen = now()
            """),
        {"query_id": query_id, "plan_hash": plan_hash},
    )
    return QueryPlanUpsertResult(plan_hash=plan_hash, is_new=is_new)


async def list_query_plans(session: AsyncSession, *, query_id: str) -> list[QueryPlanListItem]:
    result = await session.execute(
        text("""
            SELECT qp.plan_hash, pt.plan_format, qp.first_seen, qp.last_seen
            FROM query_plan qp
            JOIN plan_text pt ON pt.plan_hash = qp.plan_hash
            WHERE qp.query_id = :query_id
            ORDER BY qp.first_seen ASC
            """),
        {"query_id": query_id},
    )
    return [
        QueryPlanListItem(
            plan_hash=row.plan_hash,
            plan_format=row.plan_format,
            first_seen=row.first_seen,
            last_seen=row.last_seen,
        )
        for row in result
    ]


async def get_query_plan_detail(
    session: AsyncSession,
    *,
    instance_id: str,
    query_id: str,
    plan_hash: str,
) -> QueryPlanDetail | None:
    result = await session.execute(
        text("""
            SELECT qp.plan_hash, pt.plan_format, pt.plan_body, qp.first_seen, qp.last_seen
            FROM query_plan qp
            JOIN plan_text pt ON pt.plan_hash = qp.plan_hash
            JOIN query q ON q.id = qp.query_id
            WHERE qp.query_id = :query_id
              AND qp.plan_hash = :plan_hash
              AND q.instance_id = :instance_id
            """),
        {"query_id": query_id, "plan_hash": plan_hash, "instance_id": instance_id},
    )
    row = result.first()
    if row is None:
        return None
    return QueryPlanDetail(
        plan_hash=row.plan_hash,
        plan_format=row.plan_format,
        plan_body=row.plan_body,
        first_seen=row.first_seen,
        last_seen=row.last_seen,
    )


async def query_belongs_to_instance(session: AsyncSession, *, instance_id: str, query_id: str) -> bool:
    result = await session.execute(
        text("""
            SELECT 1 FROM query
            WHERE id = :query_id AND instance_id = :instance_id
            """),
        {"query_id": query_id, "instance_id": instance_id},
    )
    return result.first() is not None


async def list_plan_changes(
    session: AsyncSession,
    *,
    instance_id: str,
    since: datetime,
) -> list[PlanChangeRow]:
    """Plans whose `first_seen` is at/after `since` for queries on this instance.

    Includes `plan_count` so callers can tell a first-ever plan from a genuine
    change (count > 1).
    """
    result = await session.execute(
        text("""
            SELECT
                qp.query_id AS query_id,
                qp.plan_hash AS plan_hash,
                pt.plan_format AS plan_format,
                qp.first_seen AS first_seen,
                qt.normalized_text AS query_text,
                (
                    SELECT COUNT(*)::int FROM query_plan qp2 WHERE qp2.query_id = qp.query_id
                ) AS plan_count
            FROM query_plan qp
            JOIN plan_text pt ON pt.plan_hash = qp.plan_hash
            JOIN query q ON q.id = qp.query_id
            JOIN query_text qt ON qt.norm_hash = q.norm_hash
            WHERE q.instance_id = :instance_id
              AND qp.first_seen >= :since
            ORDER BY qp.first_seen DESC
            """),
        {"instance_id": instance_id, "since": since},
    )
    return [
        PlanChangeRow(
            query_id=row.query_id,
            plan_hash=row.plan_hash,
            plan_format=row.plan_format,
            first_seen=row.first_seen,
            query_text=row.query_text,
            plan_count=row.plan_count,
        )
        for row in result
    ]


# --- Phase 1 element 4: blocking + deadlocks --------------------------------


@dataclass(frozen=True, slots=True)
class BlockingEventRecord:
    id: str
    instance_id: str
    detected_at: datetime
    blocking_query_id: str | None
    blocked_query_id: str | None
    blocked_duration_ms: float | None
    details: dict


@dataclass(frozen=True, slots=True)
class DeadlockEventRecord:
    id: str
    instance_id: str
    detected_at: datetime
    victim_query_id: str | None
    details: dict


async def insert_blocking_event(
    session: AsyncSession,
    *,
    instance_id: str,
    detected_at: datetime,
    blocking_query_id: str | None,
    blocked_query_id: str | None,
    blocked_duration_ms: float | None,
    details: dict,
) -> str:
    event_id = generate_id()
    await session.execute(
        text("""
            INSERT INTO blocking_event
                (id, instance_id, detected_at, blocking_query_id, blocked_query_id,
                 blocked_duration_ms, details)
            VALUES
                (:id, :instance_id, :detected_at, :blocking_query_id, :blocked_query_id,
                 :blocked_duration_ms, CAST(:details AS jsonb))
            """),
        {
            "id": event_id,
            "instance_id": instance_id,
            "detected_at": detected_at,
            "blocking_query_id": blocking_query_id,
            "blocked_query_id": blocked_query_id,
            "blocked_duration_ms": blocked_duration_ms,
            "details": json.dumps(details),
        },
    )
    return event_id


async def insert_deadlock_event(
    session: AsyncSession,
    *,
    instance_id: str,
    detected_at: datetime,
    victim_query_id: str | None,
    details: dict,
) -> str:
    event_id = generate_id()
    await session.execute(
        text("""
            INSERT INTO deadlock_event
                (id, instance_id, detected_at, victim_query_id, details)
            VALUES
                (:id, :instance_id, :detected_at, :victim_query_id, CAST(:details AS jsonb))
            """),
        {
            "id": event_id,
            "instance_id": instance_id,
            "detected_at": detected_at,
            "victim_query_id": victim_query_id,
            "details": json.dumps(details),
        },
    )
    return event_id


async def get_deadlock_watermark(session: AsyncSession, *, instance_id: str) -> datetime | None:
    result = await session.execute(
        text("SELECT last_event_at FROM deadlock_cursor WHERE instance_id = :instance_id"),
        {"instance_id": instance_id},
    )
    row = result.first()
    return row.last_event_at if row else None


async def set_deadlock_watermark(session: AsyncSession, *, instance_id: str, last_event_at: datetime) -> None:
    await session.execute(
        text("""
            INSERT INTO deadlock_cursor (instance_id, last_event_at, updated_at)
            VALUES (:instance_id, :last_event_at, now())
            ON CONFLICT (instance_id) DO UPDATE SET
                last_event_at = EXCLUDED.last_event_at,
                updated_at = now()
            """),
        {"instance_id": instance_id, "last_event_at": last_event_at},
    )


async def list_blocking_events(
    session: AsyncSession,
    *,
    instance_id: str,
    since: datetime,
) -> list[BlockingEventRecord]:
    result = await session.execute(
        text("""
            SELECT id, instance_id, detected_at, blocking_query_id, blocked_query_id,
                   blocked_duration_ms, details
            FROM blocking_event
            WHERE instance_id = :instance_id AND detected_at >= :since
            ORDER BY detected_at DESC
            """),
        {"instance_id": instance_id, "since": since},
    )
    return [
        BlockingEventRecord(
            id=row.id,
            instance_id=row.instance_id,
            detected_at=row.detected_at,
            blocking_query_id=row.blocking_query_id,
            blocked_query_id=row.blocked_query_id,
            blocked_duration_ms=row.blocked_duration_ms,
            details=dict(row.details) if row.details else {},
        )
        for row in result
    ]


async def list_deadlock_events(
    session: AsyncSession,
    *,
    instance_id: str,
    since: datetime,
) -> list[DeadlockEventRecord]:
    result = await session.execute(
        text("""
            SELECT id, instance_id, detected_at, victim_query_id, details
            FROM deadlock_event
            WHERE instance_id = :instance_id AND detected_at >= :since
            ORDER BY detected_at DESC
            """),
        {"instance_id": instance_id, "since": since},
    )
    return [
        DeadlockEventRecord(
            id=row.id,
            instance_id=row.instance_id,
            detected_at=row.detected_at,
            victim_query_id=row.victim_query_id,
            details=dict(row.details) if row.details else {},
        )
        for row in result
    ]


async def get_deadlock_event(
    session: AsyncSession,
    *,
    instance_id: str,
    event_id: str,
) -> DeadlockEventRecord | None:
    result = await session.execute(
        text("""
            SELECT id, instance_id, detected_at, victim_query_id, details
            FROM deadlock_event
            WHERE id = :event_id AND instance_id = :instance_id
            """),
        {"event_id": event_id, "instance_id": instance_id},
    )
    row = result.first()
    if row is None:
        return None
    return DeadlockEventRecord(
        id=row.id,
        instance_id=row.instance_id,
        detected_at=row.detected_at,
        victim_query_id=row.victim_query_id,
        details=dict(row.details) if row.details else {},
    )


# --- Phase 1 element 5: index inventory + recommendations --------------------


@dataclass(frozen=True, slots=True)
class IndexSnapshotRecord:
    id: str
    instance_id: str
    database_name: str
    schema_name: str
    table_name: str
    index_name: str
    snapshot_at: datetime
    size_bytes: int | None
    scans: int | None
    is_unused: bool
    bloat_ratio: float | None


@dataclass(frozen=True, slots=True)
class RecommendationRecord:
    id: str
    instance_id: str
    created_at: datetime
    category: str
    query_id: str | None
    evidence: dict
    ddl_suggestion: str | None
    status: str


def compute_recommendation_evidence_key(*, schema_name: str, table_name: str, index_or_columns: str) -> str:
    """Canonical hash for recommendation dedup (instance_id, category, evidence_key)."""
    payload = json.dumps(
        {"schema": schema_name, "table": table_name, "index_or_columns": index_or_columns},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def insert_index_snapshot(
    session: AsyncSession,
    *,
    instance_id: str,
    database_name: str,
    schema_name: str,
    table_name: str,
    index_name: str,
    snapshot_at: datetime,
    size_bytes: int | None,
    scans: int | None,
    is_unused: bool,
    bloat_ratio: float | None,
) -> str:
    snapshot_id = generate_id()
    await session.execute(
        text("""
            INSERT INTO index_snapshot
                (id, instance_id, database_name, schema_name, table_name, index_name,
                 snapshot_at, size_bytes, scans, is_unused, bloat_ratio)
            VALUES
                (:id, :instance_id, :database_name, :schema_name, :table_name, :index_name,
                 :snapshot_at, :size_bytes, :scans, :is_unused, :bloat_ratio)
            """),
        {
            "id": snapshot_id,
            "instance_id": instance_id,
            "database_name": database_name,
            "schema_name": schema_name,
            "table_name": table_name,
            "index_name": index_name,
            "snapshot_at": snapshot_at,
            "size_bytes": size_bytes,
            "scans": scans,
            "is_unused": is_unused,
            "bloat_ratio": bloat_ratio,
        },
    )
    return snapshot_id


async def list_index_snapshots(
    session: AsyncSession,
    *,
    instance_id: str,
    snapshot_at: datetime | None = None,
) -> list[IndexSnapshotRecord]:
    """Latest inventory snapshot for an instance, or a specific snapshot_at."""
    if snapshot_at is None:
        result = await session.execute(
            text("""
                SELECT id, instance_id, database_name, schema_name, table_name, index_name,
                       snapshot_at, size_bytes, scans, is_unused, bloat_ratio
                FROM index_snapshot
                WHERE instance_id = :instance_id
                  AND snapshot_at = (
                      SELECT MAX(snapshot_at) FROM index_snapshot WHERE instance_id = :instance_id
                  )
                ORDER BY schema_name, table_name, index_name
                """),
            {"instance_id": instance_id},
        )
    else:
        result = await session.execute(
            text("""
                SELECT id, instance_id, database_name, schema_name, table_name, index_name,
                       snapshot_at, size_bytes, scans, is_unused, bloat_ratio
                FROM index_snapshot
                WHERE instance_id = :instance_id AND snapshot_at = :snapshot_at
                ORDER BY schema_name, table_name, index_name
                """),
            {"instance_id": instance_id, "snapshot_at": snapshot_at},
        )
    return [
        IndexSnapshotRecord(
            id=row.id,
            instance_id=row.instance_id,
            database_name=row.database_name,
            schema_name=row.schema_name,
            table_name=row.table_name,
            index_name=row.index_name,
            snapshot_at=row.snapshot_at,
            size_bytes=row.size_bytes,
            scans=row.scans,
            is_unused=row.is_unused,
            bloat_ratio=row.bloat_ratio,
        )
        for row in result
    ]


async def upsert_recommendation(
    session: AsyncSession,
    *,
    instance_id: str,
    category: str,
    evidence_key: str,
    evidence: dict,
    ddl_suggestion: str | None,
    query_id: str | None = None,
) -> str:
    """Dedup open recommendations by (instance_id, category, evidence_key).

    If an open row exists, refresh evidence/ddl_suggestion. Otherwise insert.
    Dismissed/applied rows are left alone (a new open rec can be created later).
    """
    evidence_with_key = {**evidence, "evidence_key": evidence_key}
    existing = await session.execute(
        text("""
            SELECT id FROM recommendation
            WHERE instance_id = :instance_id
              AND category = :category
              AND status = 'open'
              AND evidence->>'evidence_key' = :evidence_key
            LIMIT 1
            """),
        {"instance_id": instance_id, "category": category, "evidence_key": evidence_key},
    )
    row = existing.first()
    if row is not None:
        await session.execute(
            text("""
                UPDATE recommendation
                SET evidence = CAST(:evidence AS jsonb),
                    ddl_suggestion = :ddl_suggestion,
                    query_id = COALESCE(:query_id, query_id)
                WHERE id = :id
                """),
            {
                "id": row.id,
                "evidence": json.dumps(evidence_with_key),
                "ddl_suggestion": ddl_suggestion,
                "query_id": query_id,
            },
        )
        return str(row.id)

    rec_id = generate_id()
    await session.execute(
        text("""
            INSERT INTO recommendation
                (id, instance_id, category, query_id, evidence, ddl_suggestion, status)
            VALUES
                (:id, :instance_id, :category, :query_id, CAST(:evidence AS jsonb),
                 :ddl_suggestion, 'open')
            """),
        {
            "id": rec_id,
            "instance_id": instance_id,
            "category": category,
            "query_id": query_id,
            "evidence": json.dumps(evidence_with_key),
            "ddl_suggestion": ddl_suggestion,
        },
    )
    return rec_id


async def list_recommendations(
    session: AsyncSession,
    *,
    instance_id: str,
    category: str | None = None,
    status: str | None = "open",
) -> list[RecommendationRecord]:
    clauses = ["instance_id = :instance_id"]
    params: dict = {"instance_id": instance_id}
    if category is not None:
        clauses.append("category = :category")
        params["category"] = category
    if status is not None:
        clauses.append("status = :status")
        params["status"] = status
    where = " AND ".join(clauses)
    result = await session.execute(
        text(f"""
            SELECT id, instance_id, created_at, category, query_id, evidence, ddl_suggestion, status
            FROM recommendation
            WHERE {where}
            ORDER BY created_at DESC
            """),
        params,
    )
    return [
        RecommendationRecord(
            id=row.id,
            instance_id=row.instance_id,
            created_at=row.created_at,
            category=row.category,
            query_id=row.query_id,
            evidence=dict(row.evidence) if row.evidence else {},
            ddl_suggestion=row.ddl_suggestion,
            status=row.status,
        )
        for row in result
    ]


async def get_recommendation(
    session: AsyncSession,
    *,
    instance_id: str,
    recommendation_id: str,
) -> RecommendationRecord | None:
    result = await session.execute(
        text("""
            SELECT id, instance_id, created_at, category, query_id, evidence, ddl_suggestion, status
            FROM recommendation
            WHERE instance_id = :instance_id AND id = :recommendation_id
            """),
        {"instance_id": instance_id, "recommendation_id": recommendation_id},
    )
    row = result.first()
    if row is None:
        return None
    return RecommendationRecord(
        id=row.id,
        instance_id=row.instance_id,
        created_at=row.created_at,
        category=row.category,
        query_id=row.query_id,
        evidence=dict(row.evidence) if row.evidence else {},
        ddl_suggestion=row.ddl_suggestion,
        status=row.status,
    )
