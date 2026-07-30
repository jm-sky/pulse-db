"""Migration tracking and management utilities.

This module provides functions for tracking which migrations have been applied
to the database. It maintains a schema_migrations table that records the
history of all executed migrations.
"""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import AsyncSessionLocal, Base


class SchemaMigration(Base):
    """Tracks which migrations have been applied to the database.

    This table stores the history of all executed migrations.
    Each row represents one successfully applied migration.
    """

    __tablename__ = "schema_migrations"

    version: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SchemaMigration(version={self.version}, name={self.name}, applied_at={self.applied_at})>"


async def get_applied_migrations() -> list[str]:
    """Get list of migration versions that have been applied.

    Returns:
        List of migration version strings (e.g., ['001', '002'])
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SchemaMigration.version).order_by(SchemaMigration.version))
        return [row[0] for row in result.fetchall()]


async def is_migration_applied(version: str) -> bool:
    """Check if a specific migration version has been applied.

    Args:
        version: Migration version string (e.g., '001')

    Returns:
        True if migration has been applied, False otherwise
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SchemaMigration).where(SchemaMigration.version == version))
        return result.scalar_one_or_none() is not None


async def mark_migration_as_applied(version: str, name: str) -> None:
    """Mark a migration as applied by adding it to schema_migrations table.

    Args:
        version: Migration version string (e.g., '001')
        name: Migration name (e.g., 'add_email_audit_log')
    """
    async with AsyncSessionLocal() as session:
        migration = SchemaMigration(version=version, name=name)
        session.add(migration)
        await session.commit()


async def unmark_migration(version: str) -> None:
    """Remove a migration from schema_migrations table (rollback).

    Args:
        version: Migration version string (e.g., '001')
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SchemaMigration).where(SchemaMigration.version == version))
        migration = result.scalar_one_or_none()
        if migration:
            await session.delete(migration)
            await session.commit()


def get_migration_version_from_filename(filename: str) -> str | None:
    """Extract migration version from filename.

    Args:
        filename: Migration filename (e.g., '001_add_email_audit_log.py' or '001.5_create_users_table.py')

    Returns:
        Migration version string (e.g., '001' or '001.5') or None if invalid format
    """
    # Format: 001_migration_name.py or 001.5_migration_name.py or 001_migration_name.sql
    parts = Path(filename).stem.split("_", 1)
    if len(parts) >= 1:
        version = parts[0]
        # Check if version is numeric (with optional decimal point)
        # Remove dots and check if remaining chars are digits
        if version.replace(".", "").isdigit():
            return version
    return None


def get_migration_name_from_filename(filename: str) -> str | None:
    """Extract migration name from filename.

    Args:
        filename: Migration filename (e.g., '001_add_email_audit_log.py')

    Returns:
        Migration name string (e.g., 'add_email_audit_log') or None if invalid format
    """
    # Format: 001_migration_name.py or 001_migration_name.sql
    parts = Path(filename).stem.split("_", 1)
    if len(parts) >= 2:
        return parts[1]
    return None


def discover_migrations(migrations_dir: Path) -> list[tuple[str, str, Path]]:
    """Discover all migration files in the migrations directory.

    Args:
        migrations_dir: Path to migrations directory

    Returns:
        List of tuples: (version, name, filepath) sorted by version
    """
    migrations: list[tuple[str, str, Path]] = []

    if not migrations_dir.exists():
        return migrations

    # Find all .py migration files (skip .sql files and README)
    for filepath in sorted(migrations_dir.glob("*.py")):
        if filepath.name == "__init__.py":
            continue

        version = get_migration_version_from_filename(filepath.name)
        name = get_migration_name_from_filename(filepath.name)

        if version and name:
            migrations.append((version, name, filepath))

    # Sort by version number (handles both integer and decimal versions)
    def sort_key(item: tuple[str, str, Path]) -> float:
        try:
            return float(item[0])
        except ValueError:
            # Fallback to string sorting if conversion fails
            return float("inf")

    migrations.sort(key=sort_key)

    return migrations


async def is_database_initialized() -> bool:
    """Check if database is initialized (has any tables).

    Returns:
        True if database is initialized, False otherwise
    """
    from sqlalchemy import inspect

    from app.core.database import engine

    try:
        async with engine.begin() as conn:
            # Use run_sync to execute inspect on the sync connection
            def _check_tables(sync_conn: object) -> bool:
                insp = inspect(sync_conn)
                if insp is None:
                    return False
                tables = insp.get_table_names()
                return len(tables) > 0

            return await conn.run_sync(_check_tables)
    except Exception:
        # If we can't inspect tables, assume database is not initialized
        return False


async def ensure_schema_migrations_table() -> None:
    """Ensure schema_migrations table exists.

    Creates the table if it doesn't exist.
    This should be called before any migration operations.
    """
    from app.core.database import engine

    async with engine.begin() as conn:
        await conn.run_sync(SchemaMigration.metadata.create_all)
