"""SQL Server EngineAdapter implementation.

python-tds (`pytds`) is a pure-Python TDS driver -- no ODBC/FreeTDS system
package needed, which matters for `docker compose up` staying dependency-free
(vision.md §3.4). It is synchronous, so calls are offloaded to a thread via
asyncio.to_thread. Phase 1's 1s sampler cadence is acceptable on this seam
for now (same pattern as capability detection); revisit if thread-pool
saturation shows up under multi-instance load.

Capability detection, trivial collector, active-session sampler, and query
stats were validated against live SQL Server 2022 instances
(docs/plans/2026-07-30-phase0-foundation.md,
docs/plans/2026-07-30-phase1-diagnostic-core.md).
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytds

from ..engine_adapter import (
    ActiveSessionRow,
    Engine,
    EngineAdapter,
    EngineCapabilities,
    InstanceConnectionParams,
    QueryPlanRow,
    QueryStatRow,
    TrivialSample,
)

# ADR §3.6 vision: minimal grants for read-only diagnostics on SQL Server.
# Detected via sys.fn_my_permissions, not HAS_PERMS_BY_NAME: on SQL Server
# 2022+, HAS_PERMS_BY_NAME(NULL, 'SERVER', 'VIEW SERVER STATE') can return
# NULL even when the permission is present (confirmed live on 16.0.4165.4),
# which made bool(None) report a false negative in detect-capabilities.
_RELEVANT_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("SERVER", "VIEW SERVER STATE"),
    ("DATABASE", "VIEW DATABASE STATE"),
)

# SQL Server 2022 split VIEW SERVER STATE into granular permissions; either
# the legacy name or the performance slice is enough for our DMV reads.
_SERVER_STATE_EQUIVALENTS: frozenset[str] = frozenset(
    {
        "VIEW SERVER STATE",
        "VIEW SERVER PERFORMANCE STATE",
    }
)

# Statement text slice (same formula as sql-monitor's production queries --
# statement_start/end offsets are in bytes, NVARCHAR is 2 bytes/char).
_ACTIVE_SESSIONS_SQL = """
SELECT
    COALESCE(s.login_name, N'') AS db_user,
    COALESCE(s.program_name, N'') AS application_name,
    COALESCE(s.host_name, N'') AS client_host,
    r.wait_type AS wait_event,
    SUBSTRING(
        st.text,
        (r.statement_start_offset / 2) + 1,
        (
            (CASE r.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE r.statement_end_offset
             END - r.statement_start_offset) / 2
        ) + 1
    ) AS query_text,
    CONVERT(VARCHAR(34), r.query_hash, 1) AS engine_query_key
FROM sys.dm_exec_requests AS r WITH (NOLOCK)
JOIN sys.dm_exec_sessions AS s WITH (NOLOCK)
    ON s.session_id = r.session_id
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) AS st
WHERE r.session_id <> @@SPID
  AND s.is_user_process = 1
"""

_QUERY_STATS_SQL = """
SELECT
    CONVERT(VARCHAR(34), qs.query_hash, 1) AS engine_query_key,
    SUBSTRING(
        st.text,
        (qs.statement_start_offset / 2) + 1,
        (
            (CASE qs.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE qs.statement_end_offset
             END - qs.statement_start_offset) / 2
        ) + 1
    ) AS normalized_text,
    qs.execution_count AS calls,
    qs.total_elapsed_time / 1000.0 AS total_time_ms,
    qs.total_rows AS rows,
    qs.total_logical_reads AS shared_blks_read,
    qs.total_logical_writes AS shared_blks_written
FROM sys.dm_exec_query_stats AS qs WITH (NOLOCK)
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
WHERE qs.execution_count > 0
  AND qs.query_hash IS NOT NULL
  AND (st.dbid IS NULL OR st.dbid = 0 OR st.dbid = DB_ID())
"""

# Batch TOP-N with plan XML in one round-trip (unlike sql-monitor's per-handle
# fetch). Same query_hash may appear more than once with different plan_handles
# -- each distinct plan body is a separate QueryPlanRow for change detection.
_QUERY_PLANS_SQL_TEMPLATE = """
SELECT TOP ({top_n})
    CONVERT(VARCHAR(34), qs.query_hash, 1) AS engine_query_key,
    SUBSTRING(
        st.text,
        (qs.statement_start_offset / 2) + 1,
        (
            (CASE qs.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE qs.statement_end_offset
             END - qs.statement_start_offset) / 2
        ) + 1
    ) AS normalized_text,
    CAST(qp.query_plan AS NVARCHAR(MAX)) AS plan_body
FROM sys.dm_exec_query_stats AS qs WITH (NOLOCK)
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) AS st
CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) AS qp
WHERE qs.execution_count > 0
  AND qs.query_hash IS NOT NULL
  AND qs.plan_handle IS NOT NULL
  AND qp.query_plan IS NOT NULL
  AND (st.dbid IS NULL OR st.dbid = 0 OR st.dbid = DB_ID())
ORDER BY qs.total_elapsed_time DESC
"""


def _connect(params: InstanceConnectionParams) -> pytds.Connection:
    return pytds.connect(
        server=params.host,
        port=params.port,
        database=params.database,
        user=params.username,
        password=params.password,
        timeout=params.connect_timeout_seconds,
        login_timeout=params.connect_timeout_seconds,
        autocommit=True,
    )


def _permission_names(cur: Any, securable_class: str) -> set[str]:
    cur.execute(
        "SELECT permission_name FROM sys.fn_my_permissions(NULL, %s)",
        (securable_class,),
    )
    return {str(row[0]).upper() for row in cur.fetchall()}


def _has_relevant_grant(present: set[str], permission: str) -> bool:
    if permission == "VIEW SERVER STATE":
        return bool(present & _SERVER_STATE_EQUIVALENTS)
    return permission in present


def _fetch_dicts(cur: Any) -> list[dict[str, Any]]:
    columns = [col[0] for col in cur.description]
    return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def _detect_capabilities_sync(params: InstanceConnectionParams) -> EngineCapabilities:
    with _connect(params) as conn, conn.cursor() as cur:
        cur.execute("SELECT CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128))")
        version = str(cur.fetchone()[0])

        cur.execute("SELECT actual_state_desc FROM sys.database_query_store_options")
        row = cur.fetchone()
        query_store_enabled = bool(row) and str(row[0]).upper() != "OFF"
        features = {"query_store": query_store_enabled}

        grants: dict[str, bool] = {}
        for securable_class, permission in _RELEVANT_PERMISSIONS:
            present = _permission_names(cur, securable_class)
            grants[permission] = _has_relevant_grant(present, permission)

    return EngineCapabilities(engine=Engine.SQLSERVER, version=version, features=features, grants=grants)


def _collect_trivial_sample_sync(params: InstanceConnectionParams) -> TrivialSample:
    with _connect(params) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sys.dm_exec_requests WHERE session_id <> @@SPID")
        active_session_count = int(cur.fetchone()[0])

        cur.execute("SELECT SYSUTCDATETIME()")
        server_time: datetime = cur.fetchone()[0]

    return TrivialSample(active_session_count=active_session_count, server_time=server_time)


def _collect_active_sessions_sync(params: InstanceConnectionParams) -> list[ActiveSessionRow]:
    """Snapshot active requests with wait attribution (Phase 1 element 1).

    SQL Server wait types are flat names (``LCK_M_X``), matching migration 068
    seeds -- unlike PostgreSQL's ``Type:Event``. The collector maps a bare
    ``wait_event`` (with ``wait_event_type=None``) to that native name.

    ``wait_type`` NULL means the request is on CPU (same convention as PG's
    NULL wait_event). ``query_hash`` may be NULL for some system requests;
    the collector then falls back to hashing ``query_text``.

    Filtered to ``is_user_process = 1``: without it, ``dm_exec_requests`` is
    dominated by background workers sleeping on benign queues
    (``DISPATCHER_QUEUE_SEMAPHORE``, ``SLEEP_TASK``, …) which are not
    sessions PulseDB diagnoses -- confirmed live on SQL Server 2022 where
    ~90 requests were all system with zero user processes at sample time.
    """
    with _connect(params) as conn, conn.cursor() as cur:
        cur.execute(_ACTIVE_SESSIONS_SQL)
        rows = _fetch_dicts(cur)

    result: list[ActiveSessionRow] = []
    for row in rows:
        engine_query_key = row["engine_query_key"]
        if engine_query_key is not None:
            engine_query_key = str(engine_query_key)
            # CONVERT(..., 1) yields NULL as the string 'NULL' for some drivers
            # when query_hash is NULL -- normalize to a real None.
            if engine_query_key.upper() == "NULL":
                engine_query_key = None

        wait_event = row["wait_event"]
        if wait_event is not None:
            wait_event = str(wait_event)

        query_text = row["query_text"]
        if query_text is not None:
            # dm_exec_sql_text can embed NULs (cursor API); strip before they
            # hit PostgreSQL via normalize_query_text / upsert_query.
            query_text = str(query_text).replace("\x00", "")

        result.append(
            ActiveSessionRow(
                db_user=str(row["db_user"] or ""),
                application_name=str(row["application_name"] or ""),
                client_host=str(row["client_host"] or ""),
                wait_event_type=None,
                wait_event=wait_event,
                query_text=query_text,
                engine_query_key=engine_query_key,
            )
        )
    return result


def _collect_query_stats_sync(params: InstanceConnectionParams) -> list[QueryStatRow]:
    """Cumulative per-query stats from ``sys.dm_exec_query_stats`` (Phase 1 element 2).

    DMV counters are cumulative since plan-cache lifetime (parallel to
    ``pg_stat_statements``); the collector turns them into deltas via
    ``query_stat_cursor``. Query Store is detected as a capability for later
    history-beyond-cache work, but is not the MVP source here -- same
    cumulative→delta shape as PostgreSQL keeps one collector path.

    Filtered to the connected database (``DB_ID()``), matching PostgreSQL's
    ``current_database()`` filter. ``total_elapsed_time`` is microseconds;
    divide by 1000 for ``QueryStatRow.total_time_ms``.
    """
    with _connect(params) as conn, conn.cursor() as cur:
        cur.execute(_QUERY_STATS_SQL)
        rows = _fetch_dicts(cur)

    result: list[QueryStatRow] = []
    for row in rows:
        engine_query_key = str(row["engine_query_key"] or "")
        if not engine_query_key or engine_query_key.upper() == "NULL":
            continue
        normalized_text = row["normalized_text"]
        if normalized_text is None:
            continue
        normalized_text = str(normalized_text).replace("\x00", "")
        if not normalized_text:
            continue
        result.append(
            QueryStatRow(
                engine_query_key=engine_query_key,
                normalized_text=normalized_text,
                calls=int(row["calls"] or 0),
                total_time_ms=float(row["total_time_ms"] or 0.0),
                rows=int(row["rows"] or 0),
                shared_blks_read=int(row["shared_blks_read"] or 0),
                shared_blks_written=int(row["shared_blks_written"] or 0),
            )
        )
    return result


def _collect_query_plans_sync(params: InstanceConnectionParams, *, top_n: int = 20) -> list[QueryPlanRow]:
    """Cached plan XML for top-N queries by total_elapsed_time (Phase 1 element 3).

    One batch query with ``CROSS APPLY dm_exec_query_plan`` -- avoids N
    round-trips per plan_handle (sql-monitor's pattern). VIEW SERVER STATE
    is enough; no extra grants beyond the Phase 0 minimum.
    """
    limit = max(1, int(top_n))
    sql = _QUERY_PLANS_SQL_TEMPLATE.format(top_n=limit)
    with _connect(params) as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = _fetch_dicts(cur)

    result: list[QueryPlanRow] = []
    for row in rows:
        engine_query_key = str(row["engine_query_key"] or "")
        if not engine_query_key or engine_query_key.upper() == "NULL":
            continue
        normalized_text = row["normalized_text"]
        if normalized_text is None:
            continue
        normalized_text = str(normalized_text).replace("\x00", "")
        if not normalized_text:
            continue
        plan_body = row["plan_body"]
        if plan_body is None:
            continue
        plan_body = str(plan_body).replace("\x00", "")
        if not plan_body:
            continue
        result.append(
            QueryPlanRow(
                engine_query_key=engine_query_key,
                normalized_text=normalized_text,
                plan_format="xml",
                plan_body=plan_body,
            )
        )
    return result


class SqlServerEngineAdapter(EngineAdapter):
    engine = Engine.SQLSERVER

    async def detect_capabilities(self, params: InstanceConnectionParams) -> EngineCapabilities:
        return await asyncio.to_thread(_detect_capabilities_sync, params)

    async def collect_trivial_sample(self, params: InstanceConnectionParams) -> TrivialSample:
        return await asyncio.to_thread(_collect_trivial_sample_sync, params)

    async def collect_active_sessions(self, params: InstanceConnectionParams) -> list[ActiveSessionRow]:
        return await asyncio.to_thread(_collect_active_sessions_sync, params)

    async def collect_query_stats(self, params: InstanceConnectionParams) -> list[QueryStatRow]:
        return await asyncio.to_thread(_collect_query_stats_sync, params)

    async def collect_query_plans(self, params: InstanceConnectionParams, *, top_n: int = 20) -> list[QueryPlanRow]:
        return await asyncio.to_thread(_collect_query_plans_sync, params, top_n=top_n)


# Re-exported for tests that need to patch the sync entry points without
# reaching into module-private names.
__all__ = [
    "SqlServerEngineAdapter",
    "_detect_capabilities_sync",
    "_collect_trivial_sample_sync",
    "_collect_active_sessions_sync",
    "_collect_query_stats_sync",
    "_collect_query_plans_sync",
]
