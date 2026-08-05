"""Migration 074: blocking/deadlocks collector kinds + deadlock_cursor.

Roadmap Faza 1 element 4 (blocking + deadlocks):
`docs/plans/2026-08-05-blocking-deadlocks.md`.

`blocking_event` / `deadlock_event` facts already exist (migration 069). This
migration adds collector_run kinds for the new ticks and a watermark table so
SQL Server `system_health` deadlock drains are idempotent.
"""

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
                CREATE TABLE deadlock_cursor (
                    instance_id TEXT PRIMARY KEY REFERENCES monitored_instance(id) ON DELETE CASCADE,
                    last_event_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """))

        await conn.execute(text("ALTER TABLE collector_run DROP CONSTRAINT collector_run_kind_check"))
        await conn.execute(text("""
                ALTER TABLE collector_run
                ADD CONSTRAINT collector_run_kind_check
                CHECK (kind IN (
                    'trivial',
                    'session_sample',
                    'query_stats',
                    'wait_sampling_history',
                    'query_plans',
                    'blocking',
                    'deadlocks'
                ))
                """))


async def downgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS deadlock_cursor"))

        await conn.execute(text("ALTER TABLE collector_run DROP CONSTRAINT collector_run_kind_check"))
        await conn.execute(text("""
                ALTER TABLE collector_run
                ADD CONSTRAINT collector_run_kind_check
                CHECK (kind IN (
                    'trivial',
                    'session_sample',
                    'query_stats',
                    'wait_sampling_history',
                    'query_plans'
                ))
                """))
