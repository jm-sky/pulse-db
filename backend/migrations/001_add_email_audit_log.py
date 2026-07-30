"""Migration: Add email_audit_log table.

This migration creates the email_audit_log table for tracking all sent emails.

Usage:
    python migrations/001_add_email_audit_log.py

Note:
    If using `init_db()` from database.py, this migration is not needed
    as the table will be created automatically from the SQLAlchemy model.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.common.models import EmailAuditLog  # noqa: F401
from app.core.database import engine


async def upgrade() -> None:
    """Create email_audit_log table."""
    print("Creating email_audit_log table...")

    async with engine.begin() as conn:
        # Create only the email_audit_log table
        await conn.run_sync(EmailAuditLog.metadata.create_all)

    print("✓ email_audit_log table created successfully")


async def downgrade() -> None:
    """Drop email_audit_log table."""
    print("Dropping email_audit_log table...")

    async with engine.begin() as conn:
        await conn.run_sync(EmailAuditLog.metadata.drop_all)

    print("✓ email_audit_log table dropped successfully")


async def main() -> None:
    """Run migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Email audit log migration")
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
