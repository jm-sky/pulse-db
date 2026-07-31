"""Migration 072: rollup tables (ADR §6, roadmap Phase 0 element 7) --
`ash_1m`, `ash_1h`, `query_stat_1h`, plus `rollup_cursor` (per instance+kind
watermark, same shape/purpose as `wait_sampling_cursor` from migration 071).

Last remaining item of Phase 0 that had no external blocker -- it was
waiting on real `session_sample`/`query_stat_delta` rows to test top-N
cardinality against, which Phase 1 elements 1-2 supplied (self-monitoring,
verified end-to-end). See docs/plans/2026-07-31-rollups.md.

Plain (non-partitioned) tables, unlike migration 069's facts -- ADR §3 lists
rollups separately from "Fakty ... poza rollupami", and top-N+other (ADR §6)
caps volume at N+1 rows per instance-bucket, several orders of magnitude
below what forced daily partitioning on the raw facts.

`ash_1m`/`ash_1h` share one shape: (instance, bucket, query, wait_class) ->
wait_seconds/sample_count, with a single `is_other` overflow row per
instance-bucket for everything outside the top N. A partial unique index
enforces "at most one other row" (a plain UNIQUE constraint would not,
because NULL <> NULL for uniqueness purposes and the overflow row's
query_id/wait_class_id are both NULL by construction).
"""

from sqlalchemy import text

from app.core.database import engine

_ASH_ROLLUP_DDL = """
    CREATE TABLE {table} (
        id TEXT PRIMARY KEY,
        instance_id TEXT NOT NULL REFERENCES monitored_instance(id) ON DELETE CASCADE,
        bucket_start TIMESTAMPTZ NOT NULL,
        query_id TEXT,
        wait_class_id TEXT,
        wait_seconds DOUBLE PRECISION NOT NULL,
        sample_count BIGINT NOT NULL,
        is_other BOOLEAN NOT NULL DEFAULT FALSE,
        UNIQUE (instance_id, bucket_start, query_id, wait_class_id)
    )
"""


async def upgrade() -> None:
    async with engine.begin() as conn:
        for table in ("ash_1m", "ash_1h"):
            await conn.execute(text(_ASH_ROLLUP_DDL.format(table=table)))
            await conn.execute(text(f'CREATE INDEX idx_{table}_lookup ON "{table}" (instance_id, bucket_start)'))
            await conn.execute(text(f'CREATE UNIQUE INDEX idx_{table}_one_other ON "{table}" (instance_id, bucket_start) WHERE is_other'))

        await conn.execute(text("""
                CREATE TABLE query_stat_1h (
                    id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL REFERENCES monitored_instance(id) ON DELETE CASCADE,
                    bucket_start TIMESTAMPTZ NOT NULL,
                    query_id TEXT,
                    calls BIGINT NOT NULL,
                    total_time_ms DOUBLE PRECISION NOT NULL,
                    rows_returned BIGINT NOT NULL,
                    shared_blks_read BIGINT NOT NULL,
                    shared_blks_written BIGINT NOT NULL,
                    is_other BOOLEAN NOT NULL DEFAULT FALSE,
                    UNIQUE (instance_id, bucket_start, query_id)
                )
                """))
        await conn.execute(text('CREATE INDEX idx_query_stat_1h_lookup ON "query_stat_1h" (instance_id, bucket_start)'))
        await conn.execute(text('CREATE UNIQUE INDEX idx_query_stat_1h_one_other ON "query_stat_1h" (instance_id, bucket_start) WHERE is_other'))

        # Same shape as wait_sampling_cursor (migration 071): mutable,
        # low-cardinality watermark, not a fact. One row per (instance, kind)
        # -- kind is 'ash_1m' | 'ash_1h' | 'query_stat_1h', each rollup job
        # advances only its own row.
        await conn.execute(text("""
                CREATE TABLE rollup_cursor (
                    instance_id TEXT NOT NULL REFERENCES monitored_instance(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL CHECK (kind IN ('ash_1m', 'ash_1h', 'query_stat_1h')),
                    watermark TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (instance_id, kind)
                )
                """))


async def downgrade() -> None:
    async with engine.begin() as conn:
        for table in ("rollup_cursor", "query_stat_1h", "ash_1h", "ash_1m"):
            await conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
