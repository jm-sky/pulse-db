"""Database connection and session management with async support.

This module provides async database connectivity for both SQLite and PostgreSQL.
It uses SQLAlchemy 2.0+ with async engine and sessions.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models.

    All database models should inherit from this class.
    Provides common functionality and metadata management.
    """

    pass


# Create async engine with appropriate settings
# SQLite doesn't support pool_size/max_overflow, so conditionally set them
engine_kwargs: dict = {
    "url": settings.database.url,
    "echo": settings.database.echo,
    "pool_pre_ping": True,  # Verify connections before using
}

# Only add pool settings for PostgreSQL (SQLite uses StaticPool by default)
if settings.database.url.startswith("postgresql"):
    engine_kwargs["pool_size"] = settings.database.pool_size
    engine_kwargs["max_overflow"] = settings.database.max_overflow
    engine_kwargs["pool_recycle"] = settings.database.pool_recycle

engine = create_async_engine(**engine_kwargs)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency that provides a database session.

    Yields an async SQLAlchemy session and ensures it's closed after use.
    Use this as a FastAPI dependency in endpoints.

    Example:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()

    Yields:
        AsyncSession: Database session for async operations
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables asynchronously.

    Creates all tables defined in SQLAlchemy models.

    Note:
        In production, use Alembic migrations instead of this function.
        This is primarily useful for development and testing.

    Example:
        # In app startup
        await init_db()
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections and dispose engine.

    Call this during application shutdown to cleanly close
    all database connections.

    Example:
        # In app shutdown
        await close_db()
    """
    await engine.dispose()
