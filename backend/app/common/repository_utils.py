"""Repository utility functions.

Helper functions for common repository operations using composition over inheritance.
These functions can be used by any repository without requiring base class inheritance.
"""

from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class HasId(Protocol):
    """Protocol for ORM models with an id column."""

    id: Any


async def get_by_id[T: HasId](session: AsyncSession, model: type[T], id: str) -> T | None:
    """Get entity by ID.

    Args:
        session: SQLAlchemy async session
        model: Model class
        id: Entity ID

    Returns:
        Entity instance or None if not found
    """
    result = await session.execute(select(model).where(model.id == id))
    return result.scalar_one_or_none()


async def count_all[T](session: AsyncSession, model: type[T]) -> int:
    """Count all entities of given model.

    Args:
        session: SQLAlchemy async session
        model: Model class

    Returns:
        Total count of entities
    """
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar_one()


async def exists_by_field[T](session: AsyncSession, model: type[T], field_name: str, value: Any) -> bool:
    """Check if entity exists with given field value.

    Args:
        session: SQLAlchemy async session
        model: Model class
        field_name: Field name to check
        value: Value to match

    Returns:
        True if entity exists, False otherwise

    Example:
        exists = await exists_by_field(session, UserDB, "email", "test@example.com")
    """
    field = getattr(model, field_name)
    result = await session.execute(select(func.count()).select_from(model).where(field == value))
    count = result.scalar_one()
    return count > 0


def normalize_email(email: str) -> str:
    """Normalize email address for case-insensitive storage.

    Args:
        email: Email address to normalize

    Returns:
        Normalized email (lowercase, stripped whitespace)
    """
    return email.lower().strip()
