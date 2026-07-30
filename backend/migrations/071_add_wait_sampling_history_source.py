"""Migration 071: wait_sampling_cursor + collector_run.kind gets a 4th value.

Roadmap Faza 1 element 1, "richer source": `docs/plans/2026-07-30-phase1-diagnostic-core.md`
adds an explicit-opt-in collector that reads `pg_wait_sampling_history`
(when the extension is installed) instead of a single `pg_stat_activity`
point sample -- the extension's background worker samples every backend at
its own `history_period` (10ms default), independent of PulseDB's poll
cadence, so it catches waits a 1s poll would simply miss.

- `wait_sampling_cursor`: watermark (`last_ts`) per instance so repeat
  collection only reads new rows from the ring buffer, not the whole
  history every time. Same shape/purpose as `query_stat_cursor` (migration
  070): mutable, low-cardinality, not a fact.
- `collector_run.kind` needs a 4th value (`wait_sampling_history`) so this
  source's gap detection tracks its own last-run state, same reasoning as
  migration 070 separating `session_sample` from `trivial`.
"""

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE wait_sampling_cursor (
                    instance_id TEXT PRIMARY KEY REFERENCES monitored_instance(id) ON DELETE CASCADE,
                    last_ts TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """))

        await conn.execute(text("ALTER TABLE collector_run DROP CONSTRAINT collector_run_kind_check"))
        await conn.execute(text("""
                ALTER TABLE collector_run
                ADD CONSTRAINT collector_run_kind_check
                CHECK (kind IN ('trivial', 'session_sample', 'query_stats', 'wait_sampling_history'))
                """))


async def downgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS wait_sampling_cursor"))

        await conn.execute(text("ALTER TABLE collector_run DROP CONSTRAINT collector_run_kind_check"))
        await conn.execute(text("""
                ALTER TABLE collector_run
                ADD CONSTRAINT collector_run_kind_check
                CHECK (kind IN ('trivial', 'session_sample', 'query_stats'))
                """))
