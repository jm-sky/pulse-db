"""Database repository implementation for admin operations."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.db_models import UserDB

logger = logging.getLogger(__name__)


class AdminRepository:
    """Repository for admin-level data access."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> list[tuple[UserDB, UserDB | None]]:
        """Get all users."""
        stmt = select(UserDB).where(UserDB.deleted_at.is_(None)).offset(skip).limit(limit).order_by(UserDB.created_at.desc())
        result = await self.db.execute(stmt)
        users = result.scalars().all()
        return [(user, user) for user in users]

    async def get_user_by_id(self, user_id: str) -> tuple[UserDB | None, UserDB | None]:
        """Get user by ID."""
        stmt = select(UserDB).where(UserDB.id == user_id, UserDB.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            return (None, None)
        return (user, user)
