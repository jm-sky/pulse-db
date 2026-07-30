"""Migration: Create users table.

Creates the users table for authentication.

Usage:
    python migrations/002_create_users_table.py upgrade
    python migrations/002_create_users_table.py downgrade

Note:
    If using `init_db()` from database.py, this migration is not needed
    as the table will be created automatically from the SQLAlchemy model.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from app.modules.auth.db_models import UserDB  # noqa: F401


async def upgrade() -> None:
    """Create users table."""
    print("Creating users table...")

    async with engine.begin() as conn:
        # Create users table
        await conn.run_sync(UserDB.metadata.create_all)

    print("✓ users table created successfully")


async def downgrade() -> None:
    """Drop users table."""
    print("Dropping users table...")

    async with engine.begin() as conn:
        await conn.run_sync(UserDB.metadata.drop_all)

    print("✓ users table dropped successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Create users table migration")
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
