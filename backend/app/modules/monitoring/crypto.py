"""Encryption for monitored-instance credentials at rest.

ADR (docs/research/2026-07-30-data-model.md) §1: "zero sekretow w plikach
montowanych do kontenerow" -- the password never touches disk in
plaintext. The Fernet key comes from CREDENTIALS_ENCRYPTION_KEY (env var
only), never stored alongside the ciphertext in the database.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialsEncryptionNotConfigured(RuntimeError):
    """Raised when CREDENTIALS_ENCRYPTION_KEY is not set but encryption is needed."""


def _fernet() -> Fernet:
    key = settings.security.credentials_encryption_key
    if not key:
        raise CredentialsEncryptionNotConfigured("CREDENTIALS_ENCRYPTION_KEY is not set. Generate one with: " 'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise CredentialsEncryptionNotConfigured("CREDENTIALS_ENCRYPTION_KEY is not a valid urlsafe-base64 32-byte Fernet key.") from exc


def encrypt_secret(plaintext: str) -> bytes:
    """Encrypt a credential (e.g. a monitored instance password) for storage."""
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_secret(ciphertext: bytes) -> str:
    """Decrypt a credential previously produced by encrypt_secret()."""
    try:
        return _fernet().decrypt(bytes(ciphertext)).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialsEncryptionNotConfigured("Stored credential could not be decrypted with the configured CREDENTIALS_ENCRYPTION_KEY (wrong or rotated key?).") from exc
