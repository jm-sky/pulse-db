"""User model for user management module.

IMPORTANT: Module Integration Notice
=====================================

This users module has its own User model that is separate from the auth module's
User model. This is intentional for demonstration purposes, but in a real
application you should:

1. If using BOTH auth and users modules together:
   - Modify users/dependencies.py to import from auth module:
     from app.modules.auth.models import User
     from app.modules.auth.repositories import get_user_repository
     from app.modules.auth.dependencies import get_current_user
   - Remove this models.py file from users module
   - Use the auth module's User model as the single source of truth

2. If using ONLY users module (without auth):
   - Keep this model as-is
   - Use the repository pattern with database (see repositories.py)
   - Implement your own authentication in users/dependencies.py

Database Configuration:
-----------------------
This module uses SQLAlchemy with async support. Configure via DATABASE_URL:

Development (SQLite with file):
  DATABASE_URL=sqlite+aiosqlite:///./dev.db

Development (in-memory, data lost on restart):
  DATABASE_URL=sqlite+aiosqlite:///:memory:

Production (PostgreSQL):
  DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """User model with camelCase fields for API responses."""

    id: str  # ULID or UUID as string
    email: EmailStr
    name: str
    role: str = "user"  # user, admin, etc.
    isActive: bool = True
    isEmailVerified: bool = True
    avatarUrl: str | None = None
    createdAt: datetime
    updatedAt: datetime

    def to_response(self) -> dict[str, Any]:
        """Convert to camelCase response format."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "isActive": self.isActive,
            "isEmailVerified": self.isEmailVerified,
            "avatarUrl": getattr(self, "avatarUrl", None),
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }
