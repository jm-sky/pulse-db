"""Migration: Create schema_migrations table.

This migration creates the schema_migrations table for tracking
which migrations have been applied to the database.

This is the base migration that must be run first.
All other migrations will register themselves in this table.

Usage:
    python migrations/000_create_schema_migrations.py upgrade
    python migrations/000_create_schema_migrations.py downgrade
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.core.migrations import SchemaMigration


async def upgrade() -> None:
    """Create schema_migrations table."""
    print("Creating schema_migrations table...")

    async with engine.begin() as conn:
        await conn.run_sync(SchemaMigration.metadata.create_all)

    print("✓ schema_migrations table created successfully")


async def downgrade() -> None:
    """Drop schema_migrations table."""
    print("Dropping schema_migrations table...")

    async with engine.begin() as conn:
        await conn.run_sync(SchemaMigration.metadata.drop_all)

    print("✓ schema_migrations table dropped successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Create schema_migrations table")
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Migration action (upgrade or downgrade)",
    )
    args = parser.parse_args()

    if args.action == "upgrade":
        await upgrade()
    elif args.action == "downgrade":
        await downgrade()

    # Close database connections
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
