"""Crypto utilities for 2FA module.

Includes:
- Symmetric encryption for TOTP secrets and WebAuthn public keys
- Backup codes generation and hashing
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_encryption_key() -> bytes:
    """Derive a Fernet key from dedicated TWO_FACTOR_ENCRYPTION_KEY or SECRET_KEY.

    Returns:
        32-byte urlsafe base64-encoded key for Fernet
    """

    key_source = os.getenv("TWO_FACTOR_ENCRYPTION_KEY") or settings.security.secret_key

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"fastapi_2fa_salt_v1",
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(key_source.encode()))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string with Fernet.

    Args:
        plaintext: data to encrypt

    Returns:
        Base64-url encoded ciphertext
    """

    fernet = Fernet(_get_encryption_key())
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a secret string with Fernet.

    Args:
        ciphertext: Base64-url encoded ciphertext

    Returns:
        Decrypted plaintext
    """

    fernet = Fernet(_get_encryption_key())
    return fernet.decrypt(ciphertext.encode()).decode()


def generate_backup_codes(count: int = 10) -> tuple[list[str], list[str]]:
    """Generate human-readable backup codes and their SHA-256 hashes.

    Returns:
        (plain_codes, hashed_codes)
    """

    plain_codes: list[str] = []
    hashed_codes: list[str] = []

    for _ in range(count):
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        part3 = secrets.token_hex(2).upper()
        code = f"{part1}-{part2}-{part3}"
        plain_codes.append(code)
        hashed_codes.append(hashlib.sha256(code.encode()).hexdigest())

    return plain_codes, hashed_codes


def _normalize_backup_code(code: str) -> str:
    """Normalize a user-submitted backup code to its canonical dashed form."""

    normalized = code.replace(" ", "").replace("-", "").upper()
    if len(normalized) == 12:
        normalized = f"{normalized[0:4]}-{normalized[4:8]}-{normalized[8:12]}"
    return normalized


def verify_backup_code(code: str, hashed_codes: list[str], used_codes: list[str]) -> bool:
    """Verify that a backup code exists and has not been used."""

    code_hash = hashlib.sha256(_normalize_backup_code(code).encode()).hexdigest()
    if code_hash not in hashed_codes:
        return False
    if code_hash in used_codes:
        return False
    return True


def mark_backup_code_used(code: str, used_codes: list[str]) -> list[str]:
    """Append backup code hash to used list if not present."""

    code_hash = hashlib.sha256(_normalize_backup_code(code).encode()).hexdigest()
    if code_hash not in used_codes:
        used_codes.append(code_hash)
    return used_codes
