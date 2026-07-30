"""Migration 070: query stat delta cursor + collector_run.kind.

Roadmap Phase 1 element 1 (session sampler) + element 2 (top queries with
history), PostgreSQL slice (docs/plans/2026-07-30-phase1-diagnostic-core.md).

Two small schema additions needed to make delta/gap bookkeeping correct once
more than one kind of collection tick exists:

- `query_stat_cursor`: pg_stat_statements exposes *cumulative* counters
  (calls, total_exec_time, ...) since the last stats reset, but
  `query_stat_delta` (migration 069) stores *deltas* per bucket (ADR §3).
  Turning cumulative into delta requires remembering what was last seen per
  (instance, query) -- that's this table. Plain, mutable, low-cardinality
  (bounded by distinct queries per instance): same shape as a dimension, not
  a fact, so it isn't partitioned.
- `collector_run.kind`: until now every run was the trivial 60s tick. Adding
  session sampling (~1s cadence) and query-stat collection (~60s cadence)
  as separate tick types means `get_last_collector_run`'s gap detection has
  to compare like with like -- mixing a 1s-cadence sampler's gap math
  against the previous *trivial* run's timestamp would misfire. `kind`
  lets each collection type track its own last-run/gap state.
"""

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE query_stat_cursor (
                    instance_id TEXT NOT NULL REFERENCES monitored_instance(id) ON DELETE CASCADE,
                    engine_query_key TEXT NOT NULL,
                    last_calls BIGINT NOT NULL,
                    last_total_time_ms DOUBLE PRECISION NOT NULL,
                    last_rows BIGINT NOT NULL,
                    last_shared_blks_read BIGINT NOT NULL,
                    last_shared_blks_written BIGINT NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (instance_id, engine_query_key)
                )
                """))

        await conn.execute(text("""
                ALTER TABLE collector_run
                ADD COLUMN kind TEXT NOT NULL DEFAULT 'trivial'
                    CHECK (kind IN ('trivial', 'session_sample', 'query_stats'))
                """))
        await conn.execute(text("ALTER TABLE collector_run ALTER COLUMN kind DROP DEFAULT"))
        await conn.execute(text("CREATE INDEX idx_collector_run_instance_kind ON collector_run (instance_id, kind, started_at DESC)"))


async def downgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DROP INDEX IF EXISTS idx_collector_run_instance_kind"))
        await conn.execute(text("ALTER TABLE collector_run DROP COLUMN IF EXISTS kind"))
        await conn.execute(text("DROP TABLE IF EXISTS query_stat_cursor"))
