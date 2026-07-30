"""PostgreSQL EngineAdapter implementation.

Uses asyncpg directly (not the app's own SQLAlchemy engine) because these
connections go out to arbitrary monitored instances, not to PulseDB's own
repository database.
"""

from __future__ import annotations

import asyncpg

from ..engine_adapter import (
    Engine,
    EngineAdapter,
    EngineCapabilities,
    InstanceConnectionParams,
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
