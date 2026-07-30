"""Unit tests for the shared user-mutation authorization guard.

Regression tests for the SEC-2 finding (pulse-db review, 2026-07-20):
the users module router called UserRepository directly and bypassed every
Owner/protected-user protection that AdminService enforced.
"""

import pytest
from fastapi import HTTPException

from app.modules.admin.authorization import enforce_user_mutation_permissions


def test_non_owner_admin_cannot_assign_owner_role() -> None:
    with pytest.raises(HTTPException) as exc_info:
        enforce_user_mutation_permissions(
            actor_is_admin=True,
            actor_is_owner=False,
            target_email="user@example.com",
            target_is_owner=False,
            target_is_admin=False,
            new_role="owner",
        )
    assert exc_info.value.status_code == 403


def test_non_owner_admin_cannot_set_is_owner_flag() -> None:
    with pytest.raises(HTTPException) as exc_info:
        enforce_user_mutation_permissions(
            actor_is_admin=True,
            actor_is_owner=False,
            target_email="user@example.com",
            target_is_owner=False,
            target_is_admin=False,
            new_is_owner=True,
        )
    assert exc_info.value.status_code == 403


def test_non_owner_admin_cannot_modify_owner_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        enforce_user_mutation_permissions(
            actor_is_admin=True,
            actor_is_owner=False,
            target_email="owner@example.com",
            target_is_owner=True,
            target_is_admin=False,
            new_role="admin",
        )
    assert exc_info.value.status_code == 403


def test_owner_can_modify_owner_user() -> None:
    # Should not raise
    enforce_user_mutation_permissions(
        actor_is_admin=True,
        actor_is_owner=True,
        target_email="owner@example.com",
        target_is_owner=True,
        target_is_admin=False,
        new_role="admin",
    )


def test_non_owner_admin_cannot_delete_owner() -> None:
    with pytest.raises(HTTPException) as exc_info:
        enforce_user_mutation_permissions(
            actor_is_admin=True,
            actor_is_owner=False,
            target_email="owner@example.com",
            target_is_owner=True,
            target_is_admin=False,
            is_delete=True,
        )
    assert exc_info.value.status_code == 403


def test_non_owner_admin_cannot_delete_other_admin() -> None:
    with pytest.raises(HTTPException) as exc_info:
        enforce_user_mutation_permissions(
            actor_is_admin=True,
            actor_is_owner=False,
            target_email="admin2@example.com",
            target_is_owner=False,
            target_is_admin=True,
            is_delete=True,
        )
    assert exc_info.value.status_code == 403


def test_cannot_delete_protected_user_email(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.admin import authorization

    monkeypatch.setattr(authorization.settings.security, "protected_user_email", "root@example.com")
    with pytest.raises(HTTPException) as exc_info:
        enforce_user_mutation_permissions(
            actor_is_admin=True,
            actor_is_owner=True,
            target_email="ROOT@example.com",
            target_is_owner=False,
            target_is_admin=False,
            is_delete=True,
        )
    assert exc_info.value.status_code == 403


def test_hard_delete_requires_owner() -> None:
    with pytest.raises(HTTPException) as exc_info:
        enforce_user_mutation_permissions(
            actor_is_admin=True,
            actor_is_owner=False,
            target_email="user@example.com",
            target_is_owner=False,
            target_is_admin=False,
            is_delete=True,
            is_hard_delete=True,
        )
    assert exc_info.value.status_code == 403


def test_owner_can_hard_delete() -> None:
    # Should not raise
    enforce_user_mutation_permissions(
        actor_is_admin=True,
        actor_is_owner=True,
        target_email="user@example.com",
        target_is_owner=False,
        target_is_admin=False,
        is_delete=True,
        is_hard_delete=True,
    )


def test_owner_can_delete_admin() -> None:
    # Should not raise: only non-owner admins are blocked from deleting admins
    enforce_user_mutation_permissions(
        actor_is_admin=False,
        actor_is_owner=True,
        target_email="admin@example.com",
        target_is_owner=False,
        target_is_admin=True,
        is_delete=True,
    )


def test_regular_update_with_no_role_change_is_allowed() -> None:
    # Should not raise: non-owner admin updating a regular user's name/email
    enforce_user_mutation_permissions(
        actor_is_admin=True,
        actor_is_owner=False,
        target_email="user@example.com",
        target_is_owner=False,
        target_is_admin=False,
    )
