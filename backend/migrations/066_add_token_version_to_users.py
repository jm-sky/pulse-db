"""Migration 066: Add token_version column to users."""

from sqlalchemy import text

from app.core.database import engine


async def upgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0
                """))


async def downgrade() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("""
                ALTER TABLE users
                DROP COLUMN IF EXISTS token_version
                """))
