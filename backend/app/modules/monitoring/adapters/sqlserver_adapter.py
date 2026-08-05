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

# Active blocking chains: one row per blocked request (sql-monitor SQL_BLOCKING shape).
_BLOCKING_SQL = """
SELECT
    r.session_id AS blocked_session_id,
    r.blocking_session_id AS blocking_session_id,
    r.wait_type AS wait_type,
    r.wait_time AS wait_time_ms,
    COALESCE(bs.login_name, N'') AS blocked_user,
    COALESCE(ks.login_name, N'') AS blocking_user,
    COALESCE(bs.program_name, N'') AS blocked_application,
    COALESCE(ks.program_name, N'') AS blocking_application,
    COALESCE(bs.host_name, N'') AS blocked_client_host,
    COALESCE(ks.host_name, N'') AS blocking_client_host,
    SUBSTRING(
        bst.text,
        (r.statement_start_offset / 2) + 1,
        (
            (CASE r.statement_end_offset
                WHEN -1 THEN DATALENGTH(bst.text)
                ELSE r.statement_end_offset
             END - r.statement_start_offset) / 2
        ) + 1
    ) AS blocked_query_text,
    kst.text AS blocking_query_text,
    CONVERT(VARCHAR(34), r.query_hash, 1) AS blocked_engine_query_key,
    CONVERT(VARCHAR(34), kr.query_hash, 1) AS blocking_engine_query_key
FROM sys.dm_exec_requests AS r WITH (NOLOCK)
JOIN sys.dm_exec_sessions AS bs WITH (NOLOCK) ON bs.session_id = r.session_id
LEFT JOIN sys.dm_exec_sessions AS ks WITH (NOLOCK) ON ks.session_id = r.blocking_session_id
LEFT JOIN sys.dm_exec_requests AS kr WITH (NOLOCK) ON kr.session_id = r.blocking_session_id
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) AS bst
OUTER APPLY sys.dm_exec_sql_text(COALESCE(kr.sql_handle, ks.most_recent_sql_handle)) AS kst
WHERE r.blocking_session_id > 0
  AND r.session_id <> @@SPID
  AND bs.is_user_process = 1
ORDER BY r.wait_time DESC
"""

# Deadlocks from system_health XE ring buffer (zero overhead -- session always on).
_DEADLOCKS_SQL = """
SELECT
    xdr.value('@timestamp', 'datetime2') AS event_time,
    CONVERT(nvarchar(max),
        xdr.query('data[@name="xml_report"]/value/deadlock')
    ) AS deadlock_xml,
    TRY_CAST(
        xdr.value('(data[@name="xml_report"]/value/deadlock/victim-list/victimProcess/@id)[1]', 'nvarchar(50)')
        AS nvarchar(50)
    ) AS victim_process_id
FROM (
    SELECT CAST(target_data AS XML) AS target_data
    FROM sys.dm_xe_session_targets t WITH (NOLOCK)
    JOIN sys.dm_xe_sessions s WITH (NOLOCK) ON s.address = t.event_session_address
    WHERE s.name = N'system_health'
      AND t.target_name = N'ring_buffer'
) AS data
CROSS APPLY target_data.nodes('//RingBufferTarget/event[@name="xml_deadlock_report"]') AS XEventData(xdr)
WHERE xdr.value('@timestamp', 'datetime2') > %s
ORDER BY event_time
"""

# Index inventory: definitions (size + columns) LEFT JOIN usage + fragmentation.
# Pattern from sql-monitor collector/queries/indexes.py.
_INDEX_DEFINITIONS_SQL = """
WITH idx_sizes AS (
    SELECT p.object_id, p.index_id,
           CAST(SUM(CAST(a.total_pages AS BIGINT)) * 8 * 1024 AS BIGINT) AS size_bytes
    FROM sys.partitions p WITH (NOLOCK)
    JOIN sys.allocation_units a WITH (NOLOCK) ON a.container_id = p.hobt_id
    GROUP BY p.object_id, p.index_id
)
SELECT
    DB_NAME() AS database_name,
    s.name AS schema_name,
    t.name AS table_name,
    i.name AS index_name,
    i.index_id,
    i.type_desc,
    CAST(i.is_primary_key AS bit) AS is_primary_key,
    CAST(i.is_unique AS bit) AS is_unique,
    i.filter_definition,
    COALESCE(sz.size_bytes, 0) AS size_bytes,
    STRING_AGG(
        CASE WHEN ic.is_included_column = 0
             THEN c.name + CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE '' END
        END, ', '
    ) WITHIN GROUP (ORDER BY ic.index_column_id) AS key_columns,
    STRING_AGG(
        CASE WHEN ic.is_included_column = 1 THEN c.name END, ', '
    ) WITHIN GROUP (ORDER BY ic.index_column_id) AS included_columns
FROM sys.indexes i WITH (NOLOCK)
JOIN sys.tables t WITH (NOLOCK) ON t.object_id = i.object_id
JOIN sys.schemas s WITH (NOLOCK) ON s.schema_id = t.schema_id
JOIN sys.index_columns ic WITH (NOLOCK)
    ON ic.object_id = i.object_id AND ic.index_id = i.index_id
JOIN sys.columns c WITH (NOLOCK)
    ON c.object_id = ic.object_id AND c.column_id = ic.column_id
LEFT JOIN idx_sizes sz ON sz.object_id = i.object_id AND sz.index_id = i.index_id
WHERE i.type > 0
  AND i.is_disabled = 0
  AND t.is_ms_shipped = 0
GROUP BY s.name, t.name, i.name, i.index_id, i.type_desc,
         i.is_primary_key, i.is_unique, i.filter_definition, sz.size_bytes
ORDER BY t.name, i.index_id
"""

_INDEX_USAGE_SQL = """
SELECT
    SCHEMA_NAME(t.schema_id) AS schema_name,
    t.name AS table_name,
    i.name AS index_name,
    ius.user_seeks,
    ius.user_scans,
    ius.user_lookups,
    ius.user_updates
FROM sys.dm_db_index_usage_stats AS ius WITH (NOLOCK)
JOIN sys.tables AS t WITH (NOLOCK) ON t.object_id = ius.object_id
JOIN sys.indexes AS i WITH (NOLOCK)
    ON i.object_id = ius.object_id AND i.index_id = ius.index_id
WHERE ius.database_id = DB_ID()
  AND t.is_ms_shipped = 0
  AND i.name IS NOT NULL
"""

_INDEX_FRAGMENTATION_SQL = """
SELECT
    SCHEMA_NAME(t.schema_id) AS schema_name,
    t.name AS table_name,
    i.name AS index_name,
    ips.avg_fragmentation_in_percent AS avg_fragmentation_pct,
    ips.page_count
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'SAMPLED') AS ips
JOIN sys.tables AS t WITH (NOLOCK) ON t.object_id = ips.object_id
JOIN sys.indexes AS i WITH (NOLOCK)
    ON i.object_id = ips.object_id AND i.index_id = ips.index_id
WHERE ips.index_id > 0
  AND ips.page_count > 100
  AND t.is_ms_shipped = 0
  AND i.name IS NOT NULL
"""

_MISSING_INDEXES_SQL = """
SELECT
    DB_NAME(mid.database_id) AS database_name,
    SCHEMA_NAME(t.schema_id) AS schema_name,
    t.name AS table_name,
    mid.equality_columns,
    mid.inequality_columns,
    mid.included_columns,
    migs.avg_user_impact,
    migs.user_seeks,
    migs.user_scans
FROM sys.dm_db_missing_index_details AS mid WITH (NOLOCK)
JOIN sys.dm_db_missing_index_groups AS mig WITH (NOLOCK)
    ON mid.index_handle = mig.index_handle
JOIN sys.dm_db_missing_index_group_stats AS migs WITH (NOLOCK)
    ON mig.index_group_handle = migs.group_handle
JOIN sys.tables AS t WITH (NOLOCK)
    ON t.object_id = OBJECT_ID(mid.statement)
    AND mid.database_id = DB_ID()
WHERE mid.database_id = DB_ID()
ORDER BY migs.avg_user_impact * (migs.user_seeks + migs.user_scans) DESC
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

        cur.execute("""
            SELECT COUNT(*)
            FROM sys.dm_xe_sessions WITH (NOLOCK)
            WHERE name = N'system_health'
            """)
        system_health = int(cur.fetchone()[0]) > 0
        features = {
            "query_store": query_store_enabled,
            "deadlock_history": system_health,
            "missing_index_dmv": True,
        }

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


def _normalize_ss_query_key(value: object) -> str | None:
    if value is None:
        return None
    key = str(value)
    if not key or key.upper() == "NULL":
        return None
    return key


def _strip_nul(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\x00", "")
    return text if text else None


def _collect_blocking_sync(params: InstanceConnectionParams) -> list[BlockingRow]:
    """Active blocking chains from ``dm_exec_requests`` (Phase 1 element 4)."""
    with _connect(params) as conn, conn.cursor() as cur:
        cur.execute(_BLOCKING_SQL)
        rows = _fetch_dicts(cur)

    result: list[BlockingRow] = []
    for row in rows:
        wait_ms = row.get("wait_time_ms")
        result.append(
            BlockingRow(
                blocked_engine_query_key=_normalize_ss_query_key(row.get("blocked_engine_query_key")),
                blocking_engine_query_key=_normalize_ss_query_key(row.get("blocking_engine_query_key")),
                blocked_query_text=_strip_nul(row.get("blocked_query_text")),
                blocking_query_text=_strip_nul(row.get("blocking_query_text")),
                blocked_duration_ms=float(wait_ms) if wait_ms is not None else None,
                details={
                    "blocked_session_id": int(row["blocked_session_id"]),
                    "blocking_session_id": int(row["blocking_session_id"]),
                    "wait_type": str(row["wait_type"]) if row.get("wait_type") is not None else None,
                    "blocked_user": str(row.get("blocked_user") or ""),
                    "blocking_user": str(row.get("blocking_user") or ""),
                    "blocked_application": str(row.get("blocked_application") or ""),
                    "blocking_application": str(row.get("blocking_application") or ""),
                    "blocked_client_host": str(row.get("blocked_client_host") or ""),
                    "blocking_client_host": str(row.get("blocking_client_host") or ""),
                },
            )
        )
    return result


def _collect_deadlocks_sync(params: InstanceConnectionParams, *, since: datetime | None) -> list[DeadlockRow]:
    """Deadlock XML from ``system_health`` ring buffer newer than ``since``."""
    # Far-past default when no watermark yet (matches sql-monitor ~25h lookback intent,
    # but we use epoch so a first run still drains whatever the ring still holds).
    since_ts = since if since is not None else datetime(2000, 1, 1)
    try:
        with _connect(params) as conn, conn.cursor() as cur:
            cur.execute(_DEADLOCKS_SQL, (since_ts,))
            rows = _fetch_dicts(cur)
    except Exception:
        # Missing VIEW SERVER STATE / ring buffer unavailable -- capability
        # already reports deadlock_history; empty list keeps the tick healthy.
        return []

    result: list[DeadlockRow] = []
    for row in rows:
        event_time = row.get("event_time")
        if event_time is None:
            continue
        if not isinstance(event_time, datetime):
            continue
        xml = _strip_nul(row.get("deadlock_xml"))
        victim = row.get("victim_process_id")
        result.append(
            DeadlockRow(
                occurred_at=event_time,
                victim_engine_query_key=None,
                details={
                    "xml": xml,
                    "victim_process_id": str(victim) if victim is not None else None,
                },
            )
        )
    return result


def _index_key(schema: str, table: str, index: str) -> tuple[str, str, str]:
    return (schema, table, index)


def _collect_index_inventory_sync(params: InstanceConnectionParams) -> list[IndexInventoryRow]:
    with _connect(params) as conn, conn.cursor() as cur:
        cur.execute(_INDEX_DEFINITIONS_SQL)
        definitions = _fetch_dicts(cur)
        cur.execute(_INDEX_USAGE_SQL)
        usage_rows = _fetch_dicts(cur)
        try:
            cur.execute(_INDEX_FRAGMENTATION_SQL)
            frag_rows = _fetch_dicts(cur)
        except Exception:
            # SAMPLED physical stats can fail without sufficient grants; inventory
            # still succeeds with bloat_ratio=None.
            frag_rows = []

    usage: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in usage_rows:
        key = _index_key(str(row["schema_name"]), str(row["table_name"]), str(row["index_name"]))
        usage[key] = row

    frag: dict[tuple[str, str, str], float] = {}
    for row in frag_rows:
        key = _index_key(str(row["schema_name"]), str(row["table_name"]), str(row["index_name"]))
        pct = row.get("avg_fragmentation_pct")
        if pct is not None:
            frag[key] = float(pct) / 100.0

    results: list[IndexInventoryRow] = []
    for row in definitions:
        schema = str(row["schema_name"])
        table = str(row["table_name"])
        index_name = str(row["index_name"])
        key = _index_key(schema, table, index_name)
        u = usage.get(key)
        seeks = int(u["user_seeks"]) if u and u.get("user_seeks") is not None else 0
        scans_u = int(u["user_scans"]) if u and u.get("user_scans") is not None else 0
        lookups = int(u["user_lookups"]) if u and u.get("user_lookups") is not None else 0
        updates = int(u["user_updates"]) if u and u.get("user_updates") is not None else 0
        scans = seeks + scans_u + lookups
        is_pk = bool(row["is_primary_key"])
        is_unique = bool(row["is_unique"])
        # Unused: zero read activity; never recommend dropping PK (unique may
        # still be a candidate only when not PK -- plan excludes both).
        is_unused = scans == 0 and not is_pk and not is_unique
        size_bytes = int(row["size_bytes"]) if row.get("size_bytes") is not None else None
        results.append(
            IndexInventoryRow(
                database_name=str(row["database_name"]),
                schema_name=schema,
                table_name=table,
                index_name=index_name,
                size_bytes=size_bytes,
                scans=scans,
                is_unused=is_unused,
                bloat_ratio=frag.get(key),
                is_primary_key=is_pk,
                is_unique=is_unique,
                details={
                    "key_columns": row.get("key_columns"),
                    "included_columns": row.get("included_columns"),
                    "type_desc": row.get("type_desc"),
                    "filter_definition": row.get("filter_definition"),
                    "user_seeks": seeks,
                    "user_scans": scans_u,
                    "user_lookups": lookups,
                    "user_updates": updates,
                },
            )
        )
    return results


def _bracket_ident(name: str) -> str:
    return f"[{name.replace(']', ']]')}]"


def _ss_column_list(raw: str | None) -> list[str]:
    """Parse DMV column list like ``[a], [b]`` into bare names."""
    if not raw:
        return []
    parts: list[str] = []
    for chunk in raw.split(","):
        name = chunk.strip()
        if name.startswith("[") and name.endswith("]"):
            name = name[1:-1].replace("]]", "]")
        if name:
            parts.append(name)
    return parts


def _build_missing_index_ddl(
    *,
    schema_name: str,
    table_name: str,
    equality_columns: str | None,
    inequality_columns: str | None,
    included_columns: str | None,
) -> str:
    eq = _ss_column_list(equality_columns)
    ineq = _ss_column_list(inequality_columns)
    included = _ss_column_list(included_columns)
    key_cols = eq + ineq
    if not key_cols:
        key_cols = ["_missing_key"]
    # Stable short name from first few columns.
    suffix = "_".join(c[:20] for c in key_cols[:3])
    index_name = f"IX_{table_name}_{suffix}"[:128]
    key_sql = ", ".join(_bracket_ident(c) for c in key_cols)
    ddl = f"CREATE NONCLUSTERED INDEX {_bracket_ident(index_name)} " f"ON {_bracket_ident(schema_name)}.{_bracket_ident(table_name)} ({key_sql})"
    if included:
        ddl += " INCLUDE (" + ", ".join(_bracket_ident(c) for c in included) + ")"
    return ddl + ";"


def _collect_missing_indexes_sync(params: InstanceConnectionParams) -> list[MissingIndexRow]:
    try:
        with _connect(params) as conn, conn.cursor() as cur:
            cur.execute(_MISSING_INDEXES_SQL)
            rows = _fetch_dicts(cur)
    except Exception:
        return []

    results: list[MissingIndexRow] = []
    for row in rows:
        schema = str(row["schema_name"])
        table = str(row["table_name"])
        eq = str(row["equality_columns"]) if row.get("equality_columns") is not None else None
        ineq = str(row["inequality_columns"]) if row.get("inequality_columns") is not None else None
        included = str(row["included_columns"]) if row.get("included_columns") is not None else None
        user_seeks = int(row["user_seeks"] or 0)
        user_scans = int(row["user_scans"] or 0)
        avg_impact = float(row["avg_user_impact"] or 0.0)
        ddl = _build_missing_index_ddl(
            schema_name=schema,
            table_name=table,
            equality_columns=eq,
            inequality_columns=ineq,
            included_columns=included,
        )
        results.append(
            MissingIndexRow(
                database_name=str(row["database_name"]),
                schema_name=schema,
                table_name=table,
                equality_columns=eq,
                inequality_columns=ineq,
                included_columns=included,
                user_seeks=user_seeks,
                user_scans=user_scans,
                avg_user_impact=avg_impact,
                ddl_suggestion=ddl,
                evidence={
                    "equality_columns": eq,
                    "inequality_columns": ineq,
                    "included_columns": included,
                    "user_seeks": user_seeks,
                    "user_scans": user_scans,
                    "avg_user_impact": avg_impact,
                },
            )
        )
    return results


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

    async def collect_blocking(self, params: InstanceConnectionParams) -> list[BlockingRow]:
        return await asyncio.to_thread(_collect_blocking_sync, params)

    async def collect_deadlocks(self, params: InstanceConnectionParams, *, since: datetime | None) -> list[DeadlockRow]:
        return await asyncio.to_thread(_collect_deadlocks_sync, params, since=since)

    async def collect_index_inventory(self, params: InstanceConnectionParams) -> list[IndexInventoryRow]:
        return await asyncio.to_thread(_collect_index_inventory_sync, params)

    async def collect_missing_indexes(self, params: InstanceConnectionParams) -> list[MissingIndexRow]:
        return await asyncio.to_thread(_collect_missing_indexes_sync, params)


# Re-exported for tests that need to patch the sync entry points without
# reaching into module-private names.
__all__ = [
    "SqlServerEngineAdapter",
    "_detect_capabilities_sync",
    "_collect_trivial_sample_sync",
    "_collect_active_sessions_sync",
    "_collect_query_stats_sync",
    "_collect_query_plans_sync",
    "_collect_blocking_sync",
    "_collect_deadlocks_sync",
    "_collect_index_inventory_sync",
    "_collect_missing_indexes_sync",
    "_build_missing_index_ddl",
]
