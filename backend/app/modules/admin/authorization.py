"""Shared authorization guards for user-mutation endpoints.

Extracted so the admin module and the users module enforce the same
Owner/protected-user rules instead of maintaining two independent copies
that can silently drift (see docs/reviews for the pulse-db SEC-2 finding
that motivated this: the users module bypassed these checks entirely).
"""

from fastapi import HTTPException, status

from app.core.config import get_settings

settings = get_settings()


def enforce_user_mutation_permissions(
    *,
    actor_is_admin: bool,
    actor_is_owner: bool,
    target_email: str,
    target_is_owner: bool,
    target_is_admin: bool,
    new_role: str | None = None,
    new_is_owner: bool | None = None,
    is_delete: bool = False,
    is_hard_delete: bool = False,
) -> None:
    """Raise HTTPException if the actor isn't allowed to mutate the target user.

    Plain values are used (rather than model objects) because callers hold
    different model types for the target user (pydantic `User` with camelCase
    fields vs. `UserDB` with snake_case fields) depending on which repository
    they fetched it from.
    """
    if is_hard_delete and not actor_is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Owners can permanently delete users",
        )

    if is_delete:
        if settings.security.protected_user_email and target_email.lower() == settings.security.protected_user_email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete protected user",
            )

        if actor_is_admin and not actor_is_owner and target_is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators cannot delete Owner users",
            )

        if target_is_admin and not actor_is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Owners can delete admin users",
            )
        return

    # Update path
    if actor_is_admin and not actor_is_owner:
        if new_is_owner is True or (new_role and new_role == "owner"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators cannot assign Owner role",
            )
        if target_is_owner and (new_is_owner is False or (new_role and new_role != "owner")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrators cannot modify Owner users",
            )
