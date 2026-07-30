"""Database repository for Two-Factor (TOTP) configuration.

Uses composition (helper functions) for ID generation.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.id_utils import generate_id
from app.core.database import get_db

from .db_models import PasskeyDB, TotpConfigDB
from .types.repository import TwoFactorRepositoryInterface


class TwoFactorRepository(TwoFactorRepositoryInterface):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_totp_config(self, user_id: str) -> TotpConfigDB | None:
        stmt = select(TotpConfigDB).where(TotpConfigDB.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_totp_config(self, user_id: str, encrypted_secret: str, backup_codes_hashed_json: str) -> str:
        # unique per user enforced by DB
        totp_id = generate_id()
        entity = TotpConfigDB(
            id=totp_id,
            user_id=user_id,
            secret=encrypted_secret,
            backup_codes=backup_codes_hashed_json,
            backup_codes_used=json.dumps([]),
            is_enabled=False,
        )
        self.db.add(entity)
        await self.db.commit()
        return totp_id

    async def mark_totp_verified(self, user_id: str) -> None:
        """Mark TOTP as verified and enabled."""
        stmt = update(TotpConfigDB).where(TotpConfigDB.user_id == user_id).values(is_enabled=True, verified_at=datetime.now(UTC))
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_totp_last_verified(self, user_id: str) -> None:
        """Update last_verified_at timestamp."""
        stmt = update(TotpConfigDB).where(TotpConfigDB.user_id == user_id).values(last_verified_at=datetime.now(UTC))
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_backup_codes(self, user_id: str, backup_codes_hashed_json: str) -> None:
        """Update backup codes and clear used codes."""
        stmt = (
            update(TotpConfigDB)
            .where(TotpConfigDB.user_id == user_id)
            .values(
                backup_codes=backup_codes_hashed_json,
                backup_codes_used=json.dumps([]),
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def mark_backup_code_used(self, user_id: str, used_codes_json: str) -> None:
        """Update list of used backup codes."""
        stmt = update(TotpConfigDB).where(TotpConfigDB.user_id == user_id).values(backup_codes_used=used_codes_json)
        await self.db.execute(stmt)
        await self.db.commit()

    async def disable_totp(self, user_id: str) -> None:
        """Disable TOTP for user by deleting config."""
        stmt = delete(TotpConfigDB).where(TotpConfigDB.user_id == user_id)
        await self.db.execute(stmt)
        await self.db.commit()

    # Passkey methods
    async def get_passkeys(self, user_id: str) -> list[PasskeyDB]:
        """Get all passkeys for a user."""
        stmt = select(PasskeyDB).where(PasskeyDB.user_id == user_id).where(PasskeyDB.is_enabled.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_passkey_by_credential_id(self, credential_id: str) -> PasskeyDB | None:
        """Get passkey by credential ID."""
        stmt = select(PasskeyDB).where(PasskeyDB.credential_id == credential_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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
        passkey_id = generate_id()
        entity = PasskeyDB(
            id=passkey_id,
            user_id=user_id,
            name=name,
            credential_id=credential_id,
            public_key=encrypted_public_key,
            counter=counter,
            aaguid=aaguid,
            transports=transports_json,
            backup_eligible=backup_eligible,
            backup_state=backup_state,
            user_agent=user_agent,
        )
        self.db.add(entity)
        await self.db.commit()
        return passkey_id

    async def update_passkey_counter(self, passkey_id: str, counter: int) -> None:
        """Update passkey counter after authentication."""
        stmt = update(PasskeyDB).where(PasskeyDB.id == passkey_id).values(counter=counter, last_used_at=datetime.now(UTC))
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_passkey_last_used(self, passkey_id: str) -> None:
        """Update passkey last_used_at timestamp."""
        stmt = update(PasskeyDB).where(PasskeyDB.id == passkey_id).values(last_used_at=datetime.now(UTC))
        await self.db.execute(stmt)
        await self.db.commit()

    async def update_passkey_name(self, passkey_id: str, name: str) -> None:
        """Update passkey name."""
        stmt = update(PasskeyDB).where(PasskeyDB.id == passkey_id).values(name=name)
        await self.db.execute(stmt)
        await self.db.commit()

    async def delete_passkey(self, passkey_id: str) -> None:
        """Delete a passkey."""
        stmt = delete(PasskeyDB).where(PasskeyDB.id == passkey_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def delete_all_passkeys(self, user_id: str) -> None:
        """Delete all passkeys for a user."""
        stmt = delete(PasskeyDB).where(PasskeyDB.user_id == user_id)
        await self.db.execute(stmt)
        await self.db.commit()


def get_two_factor_repository(
    db: AsyncSession = Depends(get_db),
) -> TwoFactorRepositoryInterface:
    return TwoFactorRepository(db)
