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

The key is required in every environment, not only production.  Each
entrypoint that reaches an encrypted column calls
:func:`verify_encryption_key` at startup and refuses to run without a
working one, so a misconfigured deploy stops where the operator can see it
rather than raising from inside SQLAlchemy on the first request.
"""

from __future__ import annotations

import json
import os
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import String, Text, TypeDecorator

# ─── Key Management ─────────────────────────────────────────────────────

_ENV_KEY = "ALCHYMINE_ENCRYPTION_KEY"

_KEY_GEN_COMMAND = (
    'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
)

# What the probe round-trip encrypts. Fixed, public, and derived from
# nothing real: it exists to prove the key works, not to protect anything.
_PROBE_PLAINTEXT = "alchymine-encryption-self-test"


class EncryptionKeyError(RuntimeError):
    """The at-rest encryption key is absent or cannot be used.

    A ``RuntimeError`` subclass so any existing ``except RuntimeError``
    around encrypt/decrypt keeps catching what it always did.
    """


def _read_configured_key() -> str:
    """Return the configured key, preferring Settings over the raw env var.

    Settings first for unified configuration, then the environment variable
    directly. The fallback matters more than it looks: ``get_settings()``
    raises a ``ValidationError`` when any *other* field is misconfigured,
    and the encryption key should not become unreadable because of it.
    """
    key: str | bytes = ""
    try:
        from alchymine.config import get_settings

        key = get_settings().alchymine_encryption_key
    except Exception:  # noqa: S110 — fallback to env var below
        pass

    if not key:
        key = os.environ.get(_ENV_KEY, "")

    if isinstance(key, bytes):
        key = key.decode()
    return key.strip()


def verify_encryption_key() -> None:
    """Raise unless the configured key can actually encrypt and decrypt.

    Called at startup by every entrypoint that reaches an encrypted column:
    the API lifespan, the Celery worker, and the admin CLI. Without it the
    key is resolved lazily on the first ``process_bind_param``, so a
    misconfigured deploy passes its health check, starts serving, and then
    raises from inside SQLAlchemy on whichever request first reads a profile.

    Neither the raised message nor its cause carries any part of the key.
    ``cryptography`` reports the length and the base64 shape but never the
    bytes, which ``tests/db/test_encryption_startup.py`` pins so a future
    version of it cannot quietly start putting them in an operator's log.

    Raises
    ------
    EncryptionKeyError
        If the key is unset, or is not a usable Fernet key.
    """
    key = _read_configured_key()
    if not key:
        raise EncryptionKeyError(
            f"{_ENV_KEY} is not set, so this process cannot read or write any of "
            "the columns it stores encrypted (profile details, journal and chat "
            "content, wealth answers, billing identifiers). Refusing to start "
            "rather than failing on the first request that touches one.\n"
            f"Generate a key and set {_ENV_KEY}:\n"
            f"  {_KEY_GEN_COMMAND}\n"
            "Changing this key later makes existing encrypted rows unreadable."
        )

    try:
        fernet = Fernet(key.encode())
        roundtripped = fernet.decrypt(fernet.encrypt(_PROBE_PLAINTEXT.encode())).decode()
    except Exception as exc:
        raise EncryptionKeyError(
            f"{_ENV_KEY} is set but is not a usable Fernet key. It has to be 32 "
            "bytes, url-safe base64 encoded. Refusing to start rather than "
            "failing on the first request that touches an encrypted column.\n"
            "Generate a replacement:\n"
            f"  {_KEY_GEN_COMMAND}\n"
            "Changing this key makes existing encrypted rows unreadable."
        ) from exc

    if roundtripped != _PROBE_PLAINTEXT:
        raise EncryptionKeyError(
            f"{_ENV_KEY} did not survive a round-trip encrypt and decrypt of a "
            "probe string. The key parses but does not work, which points at the "
            "installed cryptography package rather than at the configured value."
        )


def _get_fernet() -> Fernet:
    """Return a Fernet instance from Settings or the environment key.

    Raises
    ------
    EncryptionKeyError
        If the encryption key is not configured. Startup calls
        :func:`verify_encryption_key`, so reaching this branch in a running
        process means the key went away after boot.
    """
    key = _read_configured_key()
    if not key:
        raise EncryptionKeyError(
            f"Encryption key not configured. Set {_ENV_KEY} environment variable. "
            f"Generate with: {_KEY_GEN_COMMAND}"
        )
    return Fernet(key.encode())


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
