"""SQL Server EngineAdapter implementation.

python-tds (`pytds`) is a pure-Python TDS driver -- no ODBC/FreeTDS system
package needed, which matters for `docker compose up` staying dependency-free
(vision.md §3.4). It is synchronous, so calls are offloaded to a thread via
asyncio.to_thread; this is Phase 0 (connection + capability detection), not
the Phase 1 sampler, so blocking-driver-in-a-thread is an acceptable seam
for now and revisited if/when SQL Server sampling needs the same 1s cadence
as PostgreSQL.

Capability detection and the trivial collector were validated against a live
SQL Server 2022 instance (docs/plans/2026-07-30-phase0-foundation.md).
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


class SqlServerEngineAdapter(EngineAdapter):
    engine = Engine.SQLSERVER

    async def detect_capabilities(self, params: InstanceConnectionParams) -> EngineCapabilities:
        return await asyncio.to_thread(_detect_capabilities_sync, params)

    async def collect_trivial_sample(self, params: InstanceConnectionParams) -> TrivialSample:
        return await asyncio.to_thread(_collect_trivial_sample_sync, params)

    async def collect_active_sessions(self, params: InstanceConnectionParams) -> list[ActiveSessionRow]:
        # Phase 1 element 1, SQL Server half: deferred, not silently missing.
        # Same shape as the PostgreSQL implementation is planned --
        # sys.dm_exec_requests joined to sys.dm_os_waiting_tasks for wait
        # attribution -- but untested without a live SQL Server instance
        # (same constraint noted in the module docstring for capability
        # detection). See docs/plans/2026-07-30-phase1-diagnostic-core.md.
        raise NotImplementedError("SqlServerEngineAdapter.collect_active_sessions: Phase 1 sampler, SQL Server slice not yet implemented (see docs/plans/2026-07-30-phase1-diagnostic-core.md)")

    async def collect_query_stats(self, params: InstanceConnectionParams) -> list[QueryStatRow]:
        # Planned source: sys.dm_exec_query_stats, or Query Store when
        # enabled (detected via `query_store` feature flag) for history
        # beyond the DMV's cache-eviction-bound window.
        raise NotImplementedError("SqlServerEngineAdapter.collect_query_stats: Phase 1 top-queries, SQL Server slice not yet implemented (see docs/plans/2026-07-30-phase1-diagnostic-core.md)")


# Re-exported for tests that need to patch the sync entry points without
# reaching into module-private names.
__all__ = ["SqlServerEngineAdapter", "_detect_capabilities_sync", "_collect_trivial_sample_sync"]
