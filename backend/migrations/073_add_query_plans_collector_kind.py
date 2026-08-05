"""Migration 073: collector_run.kind gets `query_plans`.

Roadmap Faza 1 element 3 (execution plans + plan-change detection):
`docs/plans/2026-08-05-query-plans.md`.

`plan_text` / `query_plan` dimensions already exist (migration 068). This
migration only adds a collector_run kind so the 10-minute plan tick tracks
its own gap state independently of query_stats / session_sample (same
reasoning as migrations 070 and 071).
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
                    'query_plans'
                ))
                """))


async def downgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE collector_run DROP CONSTRAINT collector_run_kind_check"))
        await conn.execute(text("""
                ALTER TABLE collector_run
                ADD CONSTRAINT collector_run_kind_check
                CHECK (kind IN ('trivial', 'session_sample', 'query_stats', 'wait_sampling_history'))
                """))
