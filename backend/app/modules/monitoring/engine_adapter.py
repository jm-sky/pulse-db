"""EngineAdapter: the single interface both supported database engines implement.

Roadmap (docs/roadmap.md) Phase 0 item 5: this must exist *first*, not "by the
way" while building the second engine -- every capability PulseDB offers has
to go through this seam so PostgreSQL and SQL Server stay one product, not
two under the same logo (vision.md §3.1).

Scope for this increment: connection + capability detection + one trivial
sample, enough to prove the seam end to end (roadmap Phase 0 exit criteria).

Phase 1 element 1 (active session sampler) and element 2 (query stats with
history) add `collect_active_sessions` / `collect_query_stats` below --
PostgreSQL implemented and validated locally
(docs/plans/2026-07-30-phase1-diagnostic-core.md); SQL Server explicitly
raises `NotImplementedError` for now rather than silently returning nothing
(vision.md/roadmap.md rule: "dwie implementacje adaptera albo jawnie
zadeklarowany brak wsparcia").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Engine(StrEnum):
    POSTGRESQL = "postgresql"
    SQLSERVER = "sqlserver"


@dataclass(frozen=True, slots=True)
class InstanceConnectionParams:
    """Everything an adapter needs to open a connection to a monitored instance."""

    host: str
    port: int
    database: str
    username: str
    password: str
    engine: Engine
    connect_timeout_seconds: float = 5.0


@dataclass(frozen=True, slots=True)
class EngineCapabilities:
    """Result of capability detection -- persisted as `monitored_instance.capabilities` jsonb.

    ADR §3: "capabilities = wykryte rozszerzenia i uprawnienia" (detected
    extensions/features and grants). Kept as plain data (dict[str, bool]) so
    a newly-detected feature never needs a migration -- see ADR §10 risk on
    `capabilities jsonb` becoming a junk drawer: this stays limited to
    detection results, never configuration.
    """

    engine: Engine
    version: str
    features: dict[str, bool] = field(default_factory=dict)
    grants: dict[str, bool] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now())

    def to_jsonb(self) -> dict:
        return {
            "engine": self.engine.value,
            "version": self.version,
            "features": self.features,
            "grants": self.grants,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class TrivialSample:
    """One minimal, cheap fact the trivial collector can write end to end.

    Proves the adapter -> collector -> repository -> fact table path works
    without pulling in the full ASH sampler (Phase 1). `server_time` lets the
    collector measure `clock_offset_ms` for `collector_run` (ADR §9).
    """

    active_session_count: int
    server_time: datetime


@dataclass(frozen=True, slots=True)
class ActiveSessionRow:
    """One active session at sample time -- the raw material of `session_sample`.

    `wait_event_type`/`wait_event` are both `None` when the backend is
    running on CPU rather than waiting (PostgreSQL has no native "on CPU"
    wait event; a NULL wait is how that's represented -- ADR §5).
    `engine_query_key` is the engine's native query identity (PostgreSQL:
    `pg_stat_activity.query_id`, present from PG14+ when `compute_query_id`
    is on or `pg_stat_statements` is loaded) and may be `None` if the engine
    can't supply one -- the collector falls back to hashing `query_text`
    itself in that case (ADR §5, §10 risk on normalization).
    """

    db_user: str
    application_name: str
    client_host: str
    wait_event_type: str | None
    wait_event: str | None
    query_text: str | None
    engine_query_key: str | None


@dataclass(frozen=True, slots=True)
class QueryStatRow:
    """One query's *cumulative* stats since the engine's last stats reset.

    Cumulative, not delta -- ADR §3 stores deltas on `query_stat_delta`, but
    the engine (pg_stat_statements / Query Store) only ever exposes running
    totals. Turning this into a delta is the collector's job
    (`query_stat_cursor`, migration 070), not the adapter's.
    """

    engine_query_key: str
    normalized_text: str
    calls: int
    total_time_ms: float
    rows: int
    shared_blks_read: int
    shared_blks_written: int


class EngineAdapter(ABC):
    """One adapter implementation per supported engine."""

    engine: Engine

    @abstractmethod
    async def detect_capabilities(self, params: InstanceConnectionParams) -> EngineCapabilities:
        """Connect and report engine version, relevant extensions/features, and grants."""

    @abstractmethod
    async def collect_trivial_sample(self, params: InstanceConnectionParams) -> TrivialSample:
        """Take one minimal, cheap sample -- proves the collector path end to end."""

    @abstractmethod
    async def collect_active_sessions(self, params: InstanceConnectionParams) -> list[ActiveSessionRow]:
        """Snapshot every currently-active session with its wait state (Phase 1 element 1).

        ADR §5 correctness rule: only sessions actually doing work are
        sampled -- idle sessions are excluded at the source, not filtered
        downstream.
        """

    @abstractmethod
    async def collect_query_stats(self, params: InstanceConnectionParams) -> list[QueryStatRow]:
        """Snapshot cumulative per-query stats (Phase 1 element 2). Empty list if the
        engine's stats source (pg_stat_statements / Query Store) isn't enabled --
        never an error, since it's an optional capability (see docs/grants.md)."""
