"""FastAPI dependencies for user management module.

This module is now integrated with the authentication module.
The users module reuses `get_current_user` from `app.modules.auth.dependencies`
and converts the returned auth user into the users module representation.

If you do not include the auth module, replace the implementation of
`get_current_user` with one tailored to your project needs.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.modules.auth.dependencies import get_current_user as auth_get_current_user
from app.modules.auth.models import User as AuthUser

from .models import User


def _map_auth_user(auth_user: AuthUser) -> User:
    # Determine role from auth user flags
    if getattr(auth_user, "isOwner", False):
        role = "owner"
    elif getattr(auth_user, "isAdmin", False):
        role = "admin"
    elif getattr(auth_user, "isPremium", False):
        role = "premium"
    else:
        role = "user"

    return User(
        id=auth_user.id,
        email=auth_user.email,
        name=auth_user.name,
        role=role,
        isActive=auth_user.isActive,
        createdAt=auth_user.createdAt,
        updatedAt=auth_user.createdAt,
    )


async def get_current_user(
    auth_user: Annotated[AuthUser, Depends(auth_get_current_user)],
) -> User:
    """Bridge auth module user dependency with users module model."""
    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return _map_auth_user(auth_user)


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Require the current user to have admin role.

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
