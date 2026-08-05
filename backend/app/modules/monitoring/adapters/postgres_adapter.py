"""PostgreSQL EngineAdapter implementation.

Uses asyncpg directly (not the app's own SQLAlchemy engine) because these
connections go out to arbitrary monitored instances, not to PulseDB's own
repository database.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime

import asyncpg

from ..engine_adapter import (
    ActiveSessionRow,
    BlockingRow,
    DeadlockRow,
    Engine,
    EngineAdapter,
    EngineCapabilities,
    IndexInventoryRow,
    InstanceConnectionParams,
    MissingIndexRow,
    QueryPlanRow,
    QueryStatRow,
    TrivialSample,
)

logger = logging.getLogger(__name__)

# Multi-statement text is unsafe to feed to EXPLAIN as a single command.
_MULTI_STATEMENT_RE = re.compile(r";\s*\S")

# Extensions relevant to capability detection (ADR §1, §4 vision, roadmap Phase 0a spike).
_RELEVANT_EXTENSIONS = ("pg_stat_statements", "pg_wait_sampling", "hypopg")

# Minimum grants a collector account needs; §3.6 vision -- pg_monitor is the
# documented minimal grant for read-only diagnostics.
_RELEVANT_ROLES = ("pg_monitor",)

# Tag every monitoring connection so pg_stat_activity can distinguish PulseDB
# sampler traffic from application workloads (and from other PulseDB ticks).
_MONITOR_APPLICATION_NAME = "pulse_db_monitor"

_PG_BLOCKING_SQL = """
SELECT DISTINCT ON (blocked.pid, blocking.pid)
    blocked.pid AS blocked_pid,
    blocking.pid AS blocking_pid,
    blocked.wait_event_type,
    blocked.wait_event,
    bl.locktype,
    EXTRACT(EPOCH FROM (now() - blocked.state_change)) * 1000 AS blocked_duration_ms,
    COALESCE(blocked.usename, '') AS blocked_user,
    COALESCE(blocking.usename, '') AS blocking_user,
    COALESCE(blocked.application_name, '') AS blocked_application,
    COALESCE(blocking.application_name, '') AS blocking_application,
    COALESCE(host(blocked.client_addr), '') AS blocked_client_host,
    COALESCE(host(blocking.client_addr), '') AS blocking_client_host,
    blocked.query AS blocked_query_text,
    blocking.query AS blocking_query_text,
    NULLIF(blocked.query_id, 0)::text AS blocked_engine_query_key,
    NULLIF(blocking.query_id, 0)::text AS blocking_engine_query_key
FROM pg_locks bl
JOIN pg_stat_activity blocked ON blocked.pid = bl.pid
JOIN pg_locks bk
    ON bk.locktype = bl.locktype
    AND bk.database IS NOT DISTINCT FROM bl.database
    AND bk.relation IS NOT DISTINCT FROM bl.relation
    AND bk.page IS NOT DISTINCT FROM bl.page
    AND bk.tuple IS NOT DISTINCT FROM bl.tuple
    AND bk.virtualxid IS NOT DISTINCT FROM bl.virtualxid
    AND bk.transactionid IS NOT DISTINCT FROM bl.transactionid
    AND bk.classid IS NOT DISTINCT FROM bl.classid
    AND bk.objid IS NOT DISTINCT FROM bl.objid
    AND bk.objsubid IS NOT DISTINCT FROM bl.objsubid
    AND bk.pid <> bl.pid
JOIN pg_stat_activity blocking ON blocking.pid = bk.pid
WHERE NOT bl.granted
  AND bk.granted
  AND blocked.pid <> pg_backend_pid()
  AND blocking.pid <> pg_backend_pid()
ORDER BY blocked.pid, blocking.pid, blocked_duration_ms DESC NULLS LAST
"""

_PG_BLOCKING_SQL_NO_QUERY_ID = """
SELECT DISTINCT ON (blocked.pid, blocking.pid)
    blocked.pid AS blocked_pid,
    blocking.pid AS blocking_pid,
    blocked.wait_event_type,
    blocked.wait_event,
    bl.locktype,
    EXTRACT(EPOCH FROM (now() - blocked.state_change)) * 1000 AS blocked_duration_ms,
    COALESCE(blocked.usename, '') AS blocked_user,
    COALESCE(blocking.usename, '') AS blocking_user,
    COALESCE(blocked.application_name, '') AS blocked_application,
    COALESCE(blocking.application_name, '') AS blocking_application,
    COALESCE(host(blocked.client_addr), '') AS blocked_client_host,
    COALESCE(host(blocking.client_addr), '') AS blocking_client_host,
    blocked.query AS blocked_query_text,
    blocking.query AS blocking_query_text,
    NULL::text AS blocked_engine_query_key,
    NULL::text AS blocking_engine_query_key
FROM pg_locks bl
JOIN pg_stat_activity blocked ON blocked.pid = bl.pid
JOIN pg_locks bk
    ON bk.locktype = bl.locktype
    AND bk.database IS NOT DISTINCT FROM bl.database
    AND bk.relation IS NOT DISTINCT FROM bl.relation
    AND bk.page IS NOT DISTINCT FROM bl.page
    AND bk.tuple IS NOT DISTINCT FROM bl.tuple
    AND bk.virtualxid IS NOT DISTINCT FROM bl.virtualxid
    AND bk.transactionid IS NOT DISTINCT FROM bl.transactionid
    AND bk.classid IS NOT DISTINCT FROM bl.classid
    AND bk.objid IS NOT DISTINCT FROM bl.objid
    AND bk.objsubid IS NOT DISTINCT FROM bl.objsubid
    AND bk.pid <> bl.pid
JOIN pg_stat_activity blocking ON blocking.pid = bk.pid
WHERE NOT bl.granted
  AND bk.granted
  AND blocked.pid <> pg_backend_pid()
  AND blocking.pid <> pg_backend_pid()
ORDER BY blocked.pid, blocking.pid, blocked_duration_ms DESC NULLS LAST
"""

_PG_INDEX_INVENTORY_SQL = """
SELECT
    current_database() AS database_name,
    psi.schemaname AS schema_name,
    psi.relname AS table_name,
    psi.indexrelname AS index_name,
    pg_relation_size(psi.indexrelid) AS size_bytes,
    psi.idx_scan AS scans,
    i.indisprimary AS is_primary_key,
    i.indisunique AS is_unique,
    pg_get_indexdef(psi.indexrelid) AS index_definition,
    (
        SELECT string_agg(a.attname, ', ' ORDER BY x.ordinality)
        FROM unnest(i.indkey) WITH ORDINALITY AS x(attnum, ordinality)
        JOIN pg_attribute a
          ON a.attrelid = i.indrelid AND a.attnum = x.attnum
    ) AS key_columns
FROM pg_stat_user_indexes psi
JOIN pg_index i ON i.indexrelid = psi.indexrelid
ORDER BY psi.schemaname, psi.relname, psi.indexrelname
"""


@dataclass(frozen=True, slots=True)
class WaitSamplingHistoryRow:
    """One `pg_wait_sampling_history` sample, enriched with current session context.

    This is the "richer source" from roadmap Faza 1 element 1 ("pg_wait_sampling
    opcjonalnie gdy obecne"): the extension's own background worker samples
    every backend at `history_period_ms` (10ms default) independent of our
    poll cadence, so it captures waits our poll would miss between ticks.
    Session context (db_user/application_name/client_host/query_text) is
    resolved by joining the *current* `pg_stat_activity` by pid at read
    time -- best effort, since the pid may have been reused by a different
    session since the historical sample was taken (documented limitation,
    not silently assumed correct).
    """

    pid: int
    sampled_at: datetime  # instance-clock timestamp; caller corrects for clock_offset_ms (ADR §9)
    wait_event_type: str | None
    wait_event: str | None
    engine_query_key: str | None
    db_user: str
    application_name: str
    client_host: str
    query_text: str | None


@dataclass(frozen=True, slots=True)
class WaitSamplingHistoryBatch:
    rows: list[WaitSamplingHistoryRow]
    history_period_ms: int | None  # None when pg_wait_sampling isn't installed
    ring_buffer_min_ts: datetime | None  # oldest ts still in the ring buffer, for gap detection


class PostgresEngineAdapter(EngineAdapter):
    engine = Engine.POSTGRESQL

    async def _connect(self, params: InstanceConnectionParams) -> asyncpg.Connection:
        return await asyncpg.connect(
            host=params.host,
            port=params.port,
            database=params.database,
            user=params.username,
            password=params.password,
            timeout=params.connect_timeout_seconds,
            server_settings={"application_name": _MONITOR_APPLICATION_NAME},
        )

    async def detect_capabilities(self, params: InstanceConnectionParams) -> EngineCapabilities:
        conn = await self._connect(params)
        try:
            version: str = await conn.fetchval("SHOW server_version")

            installed = {row["extname"] for row in await conn.fetch("SELECT extname FROM pg_extension WHERE extname = ANY($1::text[])", list(_RELEVANT_EXTENSIONS))}
            features = {ext: ext in installed for ext in _RELEVANT_EXTENSIONS}
            # No zero-overhead deadlock ring buffer on PostgreSQL (Phase 1
            # element 4) -- history requires log parse, out of MVP scope.
            features["deadlock_history"] = False
            # Missing-index DMV is SQL Server only (Phase 1 element 5).
            features["missing_index_dmv"] = False

            grants = {role: bool(await conn.fetchval("SELECT pg_has_role(current_user, $1, 'MEMBER')", role)) for role in _RELEVANT_ROLES}
            # Superuser bypasses role checks and already has everything pg_monitor grants.
            grants["superuser"] = bool(await conn.fetchval("SELECT usesuper FROM pg_user WHERE usename = current_user"))

            return EngineCapabilities(
                engine=self.engine,
                version=version,
                features=features,
                grants=grants,
            )
        finally:
            await conn.close()

    async def collect_trivial_sample(self, params: InstanceConnectionParams) -> TrivialSample:
        conn = await self._connect(params)
        try:
            active_session_count: int = await conn.fetchval("SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND pid <> pg_backend_pid()")
            server_time = await conn.fetchval("SELECT now()")
            return TrivialSample(active_session_count=active_session_count, server_time=server_time)
        finally:
            await conn.close()

    async def collect_active_sessions(self, params: InstanceConnectionParams) -> list[ActiveSessionRow]:
        conn = await self._connect(params)
        try:
            # query_id (native query identity) needs PG14+ with compute_query_id
            # on or pg_stat_statements loaded -- column may not exist on older
            # servers or with the feature off, so fall back gracefully rather
            # than erroring the whole sample (ADR §5 identity is best-effort,
            # not a hard requirement for sampling to work at all).
            try:
                rows = await conn.fetch("""
                    SELECT
                        COALESCE(usename, '') AS db_user,
                        COALESCE(application_name, '') AS application_name,
                        COALESCE(host(client_addr), '') AS client_host,
                        wait_event_type,
                        wait_event,
                        query,
                        query_id::text AS engine_query_key
                    FROM pg_stat_activity
                    WHERE state = 'active' AND pid <> pg_backend_pid()
                    """)
            except asyncpg.exceptions.UndefinedColumnError:
                rows = await conn.fetch("""
                    SELECT
                        COALESCE(usename, '') AS db_user,
                        COALESCE(application_name, '') AS application_name,
                        COALESCE(host(client_addr), '') AS client_host,
                        wait_event_type,
                        wait_event,
                        query,
                        NULL AS engine_query_key
                    FROM pg_stat_activity
                    WHERE state = 'active' AND pid <> pg_backend_pid()
                    """)

            return [
                ActiveSessionRow(
                    db_user=row["db_user"],
                    application_name=row["application_name"],
                    client_host=row["client_host"],
                    wait_event_type=row["wait_event_type"],
                    wait_event=row["wait_event"],
                    query_text=row["query"],
                    engine_query_key=row["engine_query_key"],
                )
                for row in rows
            ]
        finally:
            await conn.close()

    async def collect_query_stats(self, params: InstanceConnectionParams) -> list[QueryStatRow]:
        conn = await self._connect(params)
        try:
            installed = await conn.fetchval("SELECT count(*) FROM pg_extension WHERE extname = 'pg_stat_statements'")
            if not installed:
                return []

            rows = await conn.fetch("""
                SELECT
                    s.queryid::text AS engine_query_key,
                    s.query AS normalized_text,
                    s.calls,
                    s.total_exec_time AS total_time_ms,
                    s.rows,
                    s.shared_blks_read,
                    s.shared_blks_written
                FROM pg_stat_statements s
                JOIN pg_database d ON d.oid = s.dbid
                WHERE d.datname = current_database() AND s.queryid IS NOT NULL
                """)
            return [
                QueryStatRow(
                    engine_query_key=row["engine_query_key"],
                    normalized_text=row["normalized_text"],
                    calls=row["calls"],
                    total_time_ms=row["total_time_ms"],
                    rows=row["rows"],
                    shared_blks_read=row["shared_blks_read"],
                    shared_blks_written=row["shared_blks_written"],
                )
                for row in rows
            ]
        finally:
            await conn.close()

    async def collect_query_plans(self, params: InstanceConnectionParams, *, top_n: int = 20) -> list[QueryPlanRow]:
        """Estimated plans via ``EXPLAIN (FORMAT JSON)`` for top-N by total_exec_time.

        Never ``EXPLAIN ANALYZE`` (would execute the statement). Per-query
        permission/syntax failures are skipped -- the monitor account often
        lacks SELECT on application schemas (see docs/grants.md); that must
        not abort the whole tick.
        """
        conn = await self._connect(params)
        try:
            installed = await conn.fetchval("SELECT count(*) FROM pg_extension WHERE extname = 'pg_stat_statements'")
            if not installed:
                return []

            limit = max(1, int(top_n))
            candidates = await conn.fetch(
                """
                SELECT
                    s.queryid::text AS engine_query_key,
                    s.query AS normalized_text
                FROM pg_stat_statements s
                JOIN pg_database d ON d.oid = s.dbid
                WHERE d.datname = current_database()
                  AND s.queryid IS NOT NULL
                  AND s.query IS NOT NULL
                  AND s.query <> '<insufficient privilege>'
                ORDER BY s.total_exec_time DESC
                LIMIT $1
                """,
                limit,
            )

            results: list[QueryPlanRow] = []
            for row in candidates:
                query_text = row["normalized_text"]
                if not query_text or not _is_explainable(query_text):
                    continue
                plan_body = await _explain_json(conn, query_text)
                if plan_body is None:
                    continue
                results.append(
                    QueryPlanRow(
                        engine_query_key=row["engine_query_key"],
                        normalized_text=query_text,
                        plan_format="json",
                        plan_body=plan_body,
                    )
                )
            return results
        finally:
            await conn.close()

    async def collect_blocking(self, params: InstanceConnectionParams) -> list[BlockingRow]:
        """Active lock chains via ``pg_locks`` × ``pg_stat_activity``."""
        conn = await self._connect(params)
        try:
            try:
                rows = await conn.fetch(_PG_BLOCKING_SQL)
            except asyncpg.exceptions.UndefinedColumnError:
                # Pre-PG14 without query_id column
                rows = await conn.fetch(_PG_BLOCKING_SQL_NO_QUERY_ID)

            results: list[BlockingRow] = []
            for row in rows:
                results.append(
                    BlockingRow(
                        blocked_engine_query_key=row["blocked_engine_query_key"],
                        blocking_engine_query_key=row["blocking_engine_query_key"],
                        blocked_query_text=row["blocked_query_text"],
                        blocking_query_text=row["blocking_query_text"],
                        blocked_duration_ms=float(row["blocked_duration_ms"]) if row["blocked_duration_ms"] is not None else None,
                        details={
                            "blocked_pid": row["blocked_pid"],
                            "blocking_pid": row["blocking_pid"],
                            "wait_event_type": row["wait_event_type"],
                            "wait_event": row["wait_event"],
                            "locktype": row["locktype"],
                            "blocked_user": row["blocked_user"],
                            "blocking_user": row["blocking_user"],
                            "blocked_application": row["blocked_application"],
                            "blocking_application": row["blocking_application"],
                            "blocked_client_host": row["blocked_client_host"],
                            "blocking_client_host": row["blocking_client_host"],
                        },
                    )
                )
            return results
        finally:
            await conn.close()

    async def collect_deadlocks(self, params: InstanceConnectionParams, *, since: datetime | None) -> list[DeadlockRow]:
        """PostgreSQL MVP: no deadlock history source (see capabilities.deadlock_history)."""
        _ = params, since
        return []

    async def collect_index_inventory(self, params: InstanceConnectionParams) -> list[IndexInventoryRow]:
        """pg_stat_user_indexes + pg_class size; unused = idx_scan=0 and not PK/unique."""
        conn = await self._connect(params)
        try:
            rows = await conn.fetch(_PG_INDEX_INVENTORY_SQL)
            results: list[IndexInventoryRow] = []
            for row in rows:
                scans = int(row["scans"]) if row["scans"] is not None else 0
                is_pk = bool(row["is_primary_key"])
                is_unique = bool(row["is_unique"])
                is_unused = scans == 0 and not is_pk and not is_unique
                results.append(
                    IndexInventoryRow(
                        database_name=row["database_name"],
                        schema_name=row["schema_name"],
                        table_name=row["table_name"],
                        index_name=row["index_name"],
                        size_bytes=int(row["size_bytes"]) if row["size_bytes"] is not None else None,
                        scans=scans,
                        is_unused=is_unused,
                        bloat_ratio=None,
                        is_primary_key=is_pk,
                        is_unique=is_unique,
                        details={
                            "key_columns": row["key_columns"],
                            "index_definition": row["index_definition"],
                        },
                    )
                )
            return results
        finally:
            await conn.close()

    async def collect_missing_indexes(self, params: InstanceConnectionParams) -> list[MissingIndexRow]:
        """PostgreSQL MVP: no missing-index DMV (see capabilities.missing_index_dmv)."""
        _ = params
        return []

    async def collect_wait_sampling_history(self, params: InstanceConnectionParams, *, since: datetime | None) -> WaitSamplingHistoryBatch:
        """Pull `pg_wait_sampling_history` rows newer than `since` (Faza 1 element 1, richer source).

        Filtered to `backend_type = 'client backend'` -- unfiltered, the
        ring buffer is dominated by background workers (autovacuum,
        checkpointer, walwriter, ...) sampled at the same 10ms period,
        which are not sessions PulseDB diagnoses. Measured locally: an
        otherwise-idle instance produces ~600 history rows/4s from just
        background workers -- explicit opt-in and this filter both exist
        because of that measurement, not a guess (docs/plans/2026-07-30-phase1-diagnostic-core.md).
        """
        conn = await self._connect(params)
        try:
            installed = await conn.fetchval("SELECT count(*) FROM pg_extension WHERE extname = 'pg_wait_sampling'")
            if not installed:
                return WaitSamplingHistoryBatch(rows=[], history_period_ms=None, ring_buffer_min_ts=None)

            history_period_ms = await conn.fetchval("SELECT current_setting('pg_wait_sampling.history_period')::int")
            ring_buffer_min_ts = await conn.fetchval("SELECT min(ts) FROM pg_wait_sampling_history")

            rows = await conn.fetch(
                """
                SELECT
                    h.pid,
                    h.ts,
                    h.event_type,
                    h.event,
                    NULLIF(h.queryid, 0)::text AS engine_query_key,
                    COALESCE(a.usename, '') AS db_user,
                    COALESCE(a.application_name, '') AS application_name,
                    COALESCE(host(a.client_addr), '') AS client_host,
                    a.query AS query_text
                FROM pg_wait_sampling_history h
                JOIN pg_stat_activity a ON a.pid = h.pid AND a.backend_type = 'client backend'
                WHERE h.pid <> pg_backend_pid() AND ($1::timestamptz IS NULL OR h.ts > $1)
                ORDER BY h.ts
                """,
                since,
            )
            return WaitSamplingHistoryBatch(
                rows=[
                    WaitSamplingHistoryRow(
                        pid=row["pid"],
                        sampled_at=row["ts"],
                        wait_event_type=row["event_type"],
                        wait_event=row["event"],
                        engine_query_key=row["engine_query_key"],
                        db_user=row["db_user"],
                        application_name=row["application_name"],
                        client_host=row["client_host"],
                        query_text=row["query_text"],
                    )
                    for row in rows
                ],
                history_period_ms=history_period_ms,
                ring_buffer_min_ts=ring_buffer_min_ts,
            )
        finally:
            await conn.close()


def _is_explainable(query_text: str) -> bool:
    """Reject text we will not feed to EXPLAIN as a single command."""
    stripped = query_text.strip()
    if not stripped:
        return False
    if stripped.upper().startswith("EXPLAIN"):
        return False
    if _MULTI_STATEMENT_RE.search(stripped):
        return False
    return True


async def _explain_json(conn: asyncpg.Connection, query_text: str) -> str | None:
    """Run ``EXPLAIN (FORMAT JSON)``; return canonical JSON text or None on failure.

    The statement text comes from ``pg_stat_statements`` on the same instance
    (not an API client). Still skip on any error -- permission denied is the
    common case when the monitor role lacks SELECT on app tables.
    """
    try:
        # EXPLAIN does not accept the subject as a bind parameter; the text is
        # already filtered by `_is_explainable`.
        rows = await conn.fetch(f"EXPLAIN (FORMAT JSON) {query_text}")
    except Exception as exc:  # noqa: BLE001 -- skip this query, keep the tick
        logger.debug("EXPLAIN skipped: %s", exc)
        return None
    if not rows:
        return None
    # asyncpg returns the JSON plan as a string or already-decoded list/dict.
    raw = rows[0][0]
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, separators=(",", ":"), ensure_ascii=False)
