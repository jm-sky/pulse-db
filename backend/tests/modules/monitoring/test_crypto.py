"""Tests for monitored-instance credential encryption."""

import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.modules.monitoring.crypto import (
    CredentialsEncryptionNotConfigured,
    decrypt_secret,
    encrypt_secret,
)


@pytest.fixture(autouse=True)
def _reset_key():
    original = settings.security.credentials_encryption_key
    yield
    settings.security.credentials_encryption_key = original


def test_encrypt_decrypt_round_trip() -> None:
    settings.security.credentials_encryption_key = Fernet.generate_key().decode()

    ciphertext = encrypt_secret("s3cr3t-password")

    assert ciphertext != b"s3cr3t-password"
    assert decrypt_secret(ciphertext) == "s3cr3t-password"


def test_encrypt_without_key_raises() -> None:
    settings.security.credentials_encryption_key = None

    with pytest.raises(CredentialsEncryptionNotConfigured):
        encrypt_secret("anything")


def test_decrypt_with_wrong_key_raises() -> None:
    settings.security.credentials_encryption_key = Fernet.generate_key().decode()
    ciphertext = encrypt_secret("s3cr3t-password")

    settings.security.credentials_encryption_key = Fernet.generate_key().decode()

    with pytest.raises(CredentialsEncryptionNotConfigured):
        decrypt_secret(ciphertext)
