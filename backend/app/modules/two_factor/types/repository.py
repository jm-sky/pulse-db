"""Repository interface for Two-Factor (TOTP) persistence."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from ..db_models import PasskeyDB, TotpConfigDB


class TwoFactorRepositoryInterface(Protocol):
    """Protocol for Two-Factor repository interface."""

    db: AsyncSession  # Database session

    async def get_totp_config(self, user_id: str) -> TotpConfigDB | None: ...

    async def create_totp_config(
        self,
        user_id: str,
        encrypted_secret: str,
        backup_codes_hashed_json: str,
    ) -> str: ...

    async def mark_totp_verified(self, user_id: str) -> None: ...

    async def update_totp_last_verified(self, user_id: str) -> None: ...

    async def update_backup_codes(self, user_id: str, backup_codes_hashed_json: str) -> None: ...

    async def mark_backup_code_used(self, user_id: str, used_codes_json: str) -> None: ...

    async def disable_totp(self, user_id: str) -> None: ...

    # Passkey methods
    async def get_passkeys(self, user_id: str) -> list[PasskeyDB]: ...

    async def get_passkey_by_credential_id(self, credential_id: str) -> PasskeyDB | None: ...

    async def create_passkey(
        self,
        user_id: str,
        name: str,
        credential_id: str,
        encrypted_public_key: str,
        counter: int,
        aaguid: str | None = None,
        transports_json: str | None = None,
        backup_eligible: bool = False,
        backup_state: bool = False,
        user_agent: str | None = None,
    ) -> str:
        """Create a new passkey."""
        ...

    async def update_passkey_counter(self, passkey_id: str, counter: int) -> None:
        """Update passkey counter after authentication."""
        ...

    async def update_passkey_last_used(self, passkey_id: str) -> None:
        """Update passkey last_used_at timestamp."""
        ...

    async def update_passkey_name(self, passkey_id: str, name: str) -> None:
        """Update passkey name."""
        ...

    async def delete_passkey(self, passkey_id: str) -> None:
        """Delete a passkey."""
        ...

    async def delete_all_passkeys(self, user_id: str) -> None:
        """Delete all passkeys for a user."""
        ...
