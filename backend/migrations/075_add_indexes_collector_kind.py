"""Migration 075: collector_run.kind gets `indexes`.

Roadmap Faza 1 element 5 (index analysis):
`docs/plans/2026-08-05-index-analysis.md`.

`index_snapshot` / `recommendation` facts already exist (migration 069). This
migration only adds a collector_run kind so the daily indexes tick tracks
overhead and gaps separately from other collectors.
"""

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    async with engine.begin() as conn:
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
                    'deadlocks',
                    'indexes'
                ))
                """))


async def downgrade() -> None:
    async with engine.begin() as conn:
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
