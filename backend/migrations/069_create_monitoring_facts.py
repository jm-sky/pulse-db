"""Migration 069: PulseDB monitoring domain -- fact tables.

Raw DDL (backend/migrations/README.md; docs/research/2026-07-30-data-model.md
§3). High-cadence, time-series facts are declaratively partitioned by day
(`PARTITION BY RANGE`) with a DEFAULT partition as a safety net, plus real
day partitions created here via app.modules.monitoring.partitions so writes
work immediately after this migration -- ongoing partition creation/retention
is `cli monitoring partitions-maintain` (or a future scheduler).

Lower-volume, unbounded-retention audit/event tables (blocking_event,
deadlock_event, deep_mode_window, recommendation, recommendation_outcome,
action_audit -- ADR §7 retention: "bez limitu") are plain tables: partitioning
buys retention-by-DROP, which doesn't apply when nothing is ever dropped.

Every partitioned table's unique key includes its time column (PostgreSQL
partitioning requirement, and what keeps a future Timescale hypertable
migration a no-op per ADR §2). No foreign keys point *at* fact tables
(ADR §2); fact rows reference monitored_instance (low cardinality, always
present before any fact is written) but not per-sample dimensions like
query/session_attr/wait_event, whose FKs would otherwise have to be
re-declared on every partition -- integrity there is enforced by the
collector, which upserts dimensions before writing facts (Phase 1).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.database import engine
from app.modules.monitoring.partitions import PARTITIONED_TABLES, ensure_daily_partitions

# name -> DDL for the partitioned parent (PRIMARY KEY always includes the
# partition/time column) and its DEFAULT partition.
_PARTITIONED_FACT_DDL: dict[str, str] = {
    "session_sample": """
        CREATE TABLE session_sample (
            id TEXT NOT NULL,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            sampled_at TIMESTAMPTZ NOT NULL,
            interval_ms INTEGER NOT NULL,
            query_id TEXT,
            wait_event_engine TEXT,
            wait_event_native_name TEXT,
            session_attr_id TEXT,
            is_idle BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (id, sampled_at)
        ) PARTITION BY RANGE (sampled_at)
    """,
    "query_stat_delta": """
        CREATE TABLE query_stat_delta (
            id TEXT NOT NULL,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            query_id TEXT NOT NULL,
            bucket_start TIMESTAMPTZ NOT NULL,
            calls BIGINT NOT NULL DEFAULT 0,
            total_time_ms DOUBLE PRECISION NOT NULL DEFAULT 0,
            rows_returned BIGINT NOT NULL DEFAULT 0,
            shared_blks_read BIGINT NOT NULL DEFAULT 0,
            shared_blks_written BIGINT NOT NULL DEFAULT 0,
            PRIMARY KEY (id, bucket_start)
        ) PARTITION BY RANGE (bucket_start)
    """,
    "instance_metric": """
        CREATE TABLE instance_metric (
            id TEXT NOT NULL,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            sampled_at TIMESTAMPTZ NOT NULL,
            metric_id TEXT NOT NULL,
            value DOUBLE PRECISION NOT NULL,
            PRIMARY KEY (id, sampled_at)
        ) PARTITION BY RANGE (sampled_at)
    """,
    "index_snapshot": """
        CREATE TABLE index_snapshot (
            id TEXT NOT NULL,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            database_name TEXT NOT NULL,
            schema_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            index_name TEXT NOT NULL,
            snapshot_at TIMESTAMPTZ NOT NULL,
            size_bytes BIGINT,
            scans BIGINT,
            is_unused BOOLEAN NOT NULL DEFAULT FALSE,
            bloat_ratio DOUBLE PRECISION,
            PRIMARY KEY (id, snapshot_at)
        ) PARTITION BY RANGE (snapshot_at)
    """,
    # ADR §9: clock_offset_ms is measured and stored here, not assumed zero.
    "collector_run": """
        CREATE TABLE collector_run (
            id TEXT NOT NULL,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ,
            status TEXT NOT NULL CHECK (status IN ('ok', 'error')),
            interval_ms INTEGER NOT NULL,
            overhead_ms DOUBLE PRECISION,
            clock_offset_ms DOUBLE PRECISION,
            gap_detected BOOLEAN NOT NULL DEFAULT FALSE,
            gap_seconds DOUBLE PRECISION,
            error_message TEXT,
            PRIMARY KEY (id, started_at)
        ) PARTITION BY RANGE (started_at)
    """,
}

_PLAIN_FACT_DDL: dict[str, str] = {
    "blocking_event": """
        CREATE TABLE blocking_event (
            id TEXT PRIMARY KEY,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            blocking_query_id TEXT,
            blocked_query_id TEXT,
            blocked_duration_ms DOUBLE PRECISION,
            details JSONB
        )
    """,
    "deadlock_event": """
        CREATE TABLE deadlock_event (
            id TEXT PRIMARY KEY,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            victim_query_id TEXT,
            details JSONB
        )
    """,
    # Window must be visible in the data so period comparisons don't get
    # silently lied to by a deep-mode sampling-rate change (ADR §1, §4).
    "deep_mode_window": """
        CREATE TABLE deep_mode_window (
            id TEXT PRIMARY KEY,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            started_at TIMESTAMPTZ NOT NULL,
            ended_at TIMESTAMPTZ,
            enabled_by TEXT NOT NULL,
            operations JSONB NOT NULL DEFAULT '[]'::jsonb,
            sampling_interval_ms INTEGER NOT NULL
        )
    """,
    "recommendation": """
        CREATE TABLE recommendation (
            id TEXT PRIMARY KEY,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            category TEXT NOT NULL,
            query_id TEXT,
            evidence JSONB NOT NULL,
            ddl_suggestion TEXT,
            status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'applied', 'dismissed'))
        )
    """,
    "recommendation_outcome": """
        CREATE TABLE recommendation_outcome (
            id TEXT PRIMARY KEY,
            recommendation_id TEXT NOT NULL REFERENCES recommendation(id) ON DELETE CASCADE,
            detected_applied_at TIMESTAMPTZ,
            measured_effect JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """,
    "action_audit": """
        CREATE TABLE action_audit (
            id TEXT PRIMARY KEY,
            instance_id TEXT NOT NULL REFERENCES monitored_instance(id),
            performed_by TEXT NOT NULL,
            performed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            action TEXT NOT NULL,
            sql_text TEXT,
            result TEXT,
            success BOOLEAN NOT NULL
        )
    """,
}

_EXTRA_INDEXES: tuple[str, ...] = (
    "CREATE INDEX idx_instance_metric_lookup ON instance_metric (instance_id, metric_id, sampled_at)",
    "CREATE INDEX idx_collector_run_instance ON collector_run (instance_id, started_at DESC)",
    "CREATE INDEX idx_query_stat_delta_lookup ON query_stat_delta (instance_id, query_id, bucket_start)",
    "CREATE INDEX idx_index_snapshot_lookup ON index_snapshot (instance_id, snapshot_at)",
    "CREATE INDEX idx_blocking_event_instance ON blocking_event (instance_id, detected_at)",
    "CREATE INDEX idx_deadlock_event_instance ON deadlock_event (instance_id, detected_at)",
    "CREATE INDEX idx_recommendation_instance ON recommendation (instance_id, status)",
    "CREATE INDEX idx_action_audit_instance ON action_audit (instance_id, performed_at)",
)


async def _create_default_partition(conn: AsyncConnection, table: str) -> None:
    await conn.execute(text(f'CREATE TABLE "{table}_default" PARTITION OF "{table}" DEFAULT'))


async def upgrade() -> None:
    async with engine.begin() as conn:
        for table_name, ddl in _PARTITIONED_FACT_DDL.items():
            await conn.execute(text(ddl))
            await _create_default_partition(conn, table_name)

        for ddl in _PLAIN_FACT_DDL.values():
            await conn.execute(text(ddl))

        for index_ddl in _EXTRA_INDEXES:
            await conn.execute(text(index_ddl))

        # Cover today +/- a day so the trivial collector can write
        # immediately; `cli monitoring partitions-maintain` keeps this
        # rolling forward and prunes by retention afterwards.
        for table in PARTITIONED_TABLES:
            await ensure_daily_partitions(conn, table)


async def downgrade() -> None:
    async with engine.begin() as conn:
        for table in (
            "action_audit",
            "recommendation_outcome",
            "recommendation",
            "deep_mode_window",
            "deadlock_event",
            "blocking_event",
            "collector_run",
            "index_snapshot",
            "instance_metric",
            "query_stat_delta",
            "session_sample",
        ):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
