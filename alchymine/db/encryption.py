"""Column-level encryption helpers using Fernet symmetric encryption.

All financial / sensitive data is encrypted before being stored in the
database and decrypted on read.  The encryption key is loaded from the
``ALCHYMINE_ENCRYPTION_KEY`` environment variable (a Fernet-compatible
base64-encoded 32-byte key).

Usage in models::

    from alchymine.db.encryption import EncryptedString

    class WealthProfile(Base):
        income_range = mapped_column(EncryptedString())  # SENSITIVE — encrypted

Generate a key for development::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import json
import os
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import String, Text, TypeDecorator

# ─── Key Management ─────────────────────────────────────────────────────

_ENV_KEY = "ALCHYMINE_ENCRYPTION_KEY"


def _get_fernet() -> Fernet:
    """Return a Fernet instance from the environment key.

    Raises
    ------
    RuntimeError
        If the encryption key is not configured.
    """
    raw_key = os.environ.get(_ENV_KEY)
    if not raw_key:
        raise RuntimeError(
            f"Encryption key not set. "
            f"Export {_ENV_KEY} with a Fernet-compatible key. "
            f"Generate one with: "
            f'python -c "from cryptography.fernet import Fernet; '
            f'print(Fernet.generate_key().decode())"'
        )
    return Fernet(raw_key.encode())


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string and return a base64 ciphertext."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64 ciphertext and return the original string."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# ─── SQLAlchemy Type Decorators ─────────────────────────────────────────


class EncryptedString(TypeDecorator):
    """A SQLAlchemy column type that transparently encrypts/decrypts strings.

    Stores ciphertext in the database; returns plaintext to Python.
    Backed by a ``Text`` column (ciphertext is longer than plaintext).
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return decrypt_value(value)


class EncryptedJSON(TypeDecorator):
    """A SQLAlchemy column type that encrypts JSON data at rest.

    Serialises the Python object to JSON, encrypts it, and stores the
    ciphertext.  On read the ciphertext is decrypted and deserialised
    back to a Python object.  Backed by a ``Text`` column.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any | None, dialect: Any) -> str | None:
        if value is None:
            return None
        json_str = json.dumps(value, default=str)
        return encrypt_value(json_str)

    def process_result_value(self, value: str | None, dialect: Any) -> Any | None:
        if value is None:
            return None
        json_str = decrypt_value(value)
        return json.loads(json_str)


class StringEncryptedString(TypeDecorator):
    """Variant that uses String(512) as the backing column.

    Use for columns where you need a size-limited backing column
    (e.g., for certain database restrictions).
    """

    impl = String(512)
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return decrypt_value(value)
