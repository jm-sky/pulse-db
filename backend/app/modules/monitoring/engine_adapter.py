"""EngineAdapter: the single interface both supported database engines implement.

Roadmap (docs/roadmap.md) Phase 0 item 5: this must exist *first*, not "by the
way" while building the second engine -- every capability PulseDB offers has
to go through this seam so PostgreSQL and SQL Server stay one product, not
two under the same logo (vision.md §3.1).

Scope for this increment: connection + capability detection + one trivial
sample, enough to prove the seam end to end (roadmap Phase 0 exit criteria).
The 1s ASH sampler itself is Phase 1.
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


class EngineAdapter(ABC):
    """One adapter implementation per supported engine."""

    engine: Engine

    @abstractmethod
    async def detect_capabilities(self, params: InstanceConnectionParams) -> EngineCapabilities:
        """Connect and report engine version, relevant extensions/features, and grants."""

    @abstractmethod
    async def collect_trivial_sample(self, params: InstanceConnectionParams) -> TrivialSample:
        """Take one minimal, cheap sample -- proves the collector path end to end."""
