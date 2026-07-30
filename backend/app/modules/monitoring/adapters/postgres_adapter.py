"""PostgreSQL EngineAdapter implementation.

Uses asyncpg directly (not the app's own SQLAlchemy engine) because these
connections go out to arbitrary monitored instances, not to PulseDB's own
repository database.
"""

from __future__ import annotations

import asyncpg

from ..engine_adapter import (
    ActiveSessionRow,
    Engine,
    EngineAdapter,
    EngineCapabilities,
    InstanceConnectionParams,
    QueryStatRow,
    TrivialSample,
)

# Extensions relevant to capability detection (ADR §1, §4 vision, roadmap Phase 0a spike).
_RELEVANT_EXTENSIONS = ("pg_stat_statements", "pg_wait_sampling", "hypopg")

# Minimum grants a collector account needs; §3.6 vision -- pg_monitor is the
# documented minimal grant for read-only diagnostics.
_RELEVANT_ROLES = ("pg_monitor",)


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
        )

    async def detect_capabilities(self, params: InstanceConnectionParams) -> EngineCapabilities:
        conn = await self._connect(params)
        try:
            version: str = await conn.fetchval("SHOW server_version")

            installed = {row["extname"] for row in await conn.fetch("SELECT extname FROM pg_extension WHERE extname = ANY($1::text[])", list(_RELEVANT_EXTENSIONS))}
            features = {ext: ext in installed for ext in _RELEVANT_EXTENSIONS}

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
