"""Authentication module for FastAPI applications.

This module provides JWT-based authentication with:
- User registration and login
- Password reset functionality
- Token refresh
- Password change for authenticated users
"""

from .router import router
from .types.jwt import JWTPayload

__all__ = ["router", "JWTPayload"]
