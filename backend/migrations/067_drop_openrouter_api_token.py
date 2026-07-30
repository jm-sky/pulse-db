"""Migration 067: Drop the openrouter_api_token column from users.

Inherited from the ops-monitor / gear-stack boilerplate, where it held an AI
provider token for billing. PulseDB has no such concept: users bring their own
model through CLI/MCP/API and the product never stores provider credentials.

The column was never exposed through any API and was already being nulled on
soft delete, so no data migration is required.

See docs/issues/2026-07-30--001--boilerplate-dead-code-cleanup.md
"""

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE users
                DROP COLUMN IF EXISTS openrouter_api_token
                """))


async def downgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS openrouter_api_token VARCHAR(255)
                """))
