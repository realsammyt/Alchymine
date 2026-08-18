"""Tests for the fail-fast encryption key check.

Every sensitive column in the app is encrypted at rest, so a process that
cannot build a working Fernet has nothing useful to serve. These tests pin
the helper's semantics: missing and malformed keys are both fatal, a valid
key is silent, and no part of the key material ever reaches the error.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable

import pytest
from cryptography.fernet import Fernet

from alchymine.config import get_settings
from alchymine.db.encryption import (
    _ENV_KEY,
    EncryptionKeyError,
    verify_encryption_key,
)


@pytest.fixture
def configured_key(monkeypatch: pytest.MonkeyPatch) -> Callable[[str | None], None]:
    """Set the key at both sources the check reads, or clear both.

    The Settings singleton is ``lru_cache``d and may already hold a value
    read from a developer's ``.env``, so clearing the environment variable
    alone would not produce a missing key. Patching the loaded field as
    well makes these tests independent of whatever the process booted with.
    """

    def _set(value: str | None) -> None:
        monkeypatch.setattr(get_settings(), "alchymine_encryption_key", value or "")
        if value:
            monkeypatch.setenv(_ENV_KEY, value)
        else:
            monkeypatch.delenv(_ENV_KEY, raising=False)

    return _set


def _chain_text(exc: BaseException) -> str:
    """Return the full rendered exception chain, causes included."""
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


# ── Missing ──────────────────────────────────────────────────────────────


def test_missing_key_is_refused(configured_key) -> None:
    configured_key(None)

    with pytest.raises(EncryptionKeyError) as excinfo:
        verify_encryption_key()

    assert _ENV_KEY in str(excinfo.value)


def test_missing_key_message_says_how_to_generate_one(configured_key) -> None:
    configured_key(None)

    with pytest.raises(EncryptionKeyError) as excinfo:
        verify_encryption_key()

    assert "Fernet.generate_key()" in str(excinfo.value)


def test_whitespace_only_key_counts_as_missing(configured_key) -> None:
    configured_key("   ")

    with pytest.raises(EncryptionKeyError) as excinfo:
        verify_encryption_key()

    assert _ENV_KEY in str(excinfo.value)


# ── Malformed ────────────────────────────────────────────────────────────


def test_non_base64_key_is_refused(configured_key) -> None:
    configured_key("this is not a fernet key at all")

    with pytest.raises(EncryptionKeyError) as excinfo:
        verify_encryption_key()

    assert _ENV_KEY in str(excinfo.value)


def test_wrong_length_key_is_refused(configured_key) -> None:
    """Valid url-safe base64, but 16 bytes rather than the required 32."""
    import base64

    configured_key(base64.urlsafe_b64encode(b"x" * 16).decode())

    with pytest.raises(EncryptionKeyError) as excinfo:
        verify_encryption_key()

    assert _ENV_KEY in str(excinfo.value)


def test_malformed_key_message_is_distinct_from_missing(configured_key) -> None:
    """An operator who typo'd a key should not be told the key is unset."""
    configured_key(None)
    with pytest.raises(EncryptionKeyError) as missing:
        verify_encryption_key()

    configured_key("not-a-fernet-key")
    with pytest.raises(EncryptionKeyError) as malformed:
        verify_encryption_key()

    assert str(missing.value) != str(malformed.value)


# ── The rail: no key material anywhere in the error ──────────────────────


def test_error_never_echoes_malformed_key_material(configured_key) -> None:
    """The whole cause chain is checked, not just the top-level message.

    ``cryptography`` raises from inside ``Fernet.__init__`` and the chained
    cause is rendered in any traceback an operator sees, so a message that
    is clean on its own is not enough.
    """
    configured_key("MARKER-typoed-key-value-MARKER")

    with pytest.raises(EncryptionKeyError) as excinfo:
        verify_encryption_key()

    assert "MARKER" not in _chain_text(excinfo.value)


def test_error_never_echoes_a_base64_shaped_key(configured_key) -> None:
    """Base64 decodes cleanly here, so the failure comes from the length check.

    That path renders a different cryptography error than the non-base64 one
    above, and it has to stay just as quiet about the bytes it was handed.
    """
    import base64

    key = base64.urlsafe_b64encode(b"MARKERMARKERMARKER").decode()
    configured_key(key)

    with pytest.raises(EncryptionKeyError) as excinfo:
        verify_encryption_key()

    assert key not in _chain_text(excinfo.value)
    assert "MARKER" not in _chain_text(excinfo.value)


# ── Valid ────────────────────────────────────────────────────────────────


def test_valid_key_passes_silently(configured_key) -> None:
    configured_key(Fernet.generate_key().decode())

    assert verify_encryption_key() is None


def test_key_read_from_the_environment_alone_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings empty, environment set: the documented fallback path."""
    monkeypatch.setattr(get_settings(), "alchymine_encryption_key", "")
    monkeypatch.setenv(_ENV_KEY, Fernet.generate_key().decode())

    assert verify_encryption_key() is None


# ── Entrypoints: Celery worker and the admin CLI ─────────────────────────


def test_celery_worker_init_refuses_without_a_key(configured_key) -> None:
    """The worker decrypts profile columns on every report, so it gates too.

    ``SystemExit`` rather than ``EncryptionKeyError`` on purpose: Celery's
    ``Signal.send`` catches ``Exception`` from receivers and only logs it,
    so anything short of a ``BaseException`` leaves the worker running.
    """
    from celery.signals import worker_init

    import alchymine.workers.celery_app  # noqa: F401 — connects the receiver

    configured_key(None)

    with pytest.raises(SystemExit) as excinfo:
        worker_init.send(sender=None)

    assert _ENV_KEY in str(excinfo.value)


def test_celery_worker_init_refuses_a_malformed_key(configured_key) -> None:
    from celery.signals import worker_init

    import alchymine.workers.celery_app  # noqa: F401 — connects the receiver

    configured_key("not-a-fernet-key")

    with pytest.raises(SystemExit) as excinfo:
        worker_init.send(sender=None)

    assert _ENV_KEY in str(excinfo.value)


def test_celery_worker_init_passes_with_a_valid_key(configured_key) -> None:
    from celery.signals import worker_init

    import alchymine.workers.celery_app  # noqa: F401 — connects the receiver

    configured_key(Fernet.generate_key().decode())

    worker_init.send(sender=None)


async def test_bootstrap_admin_cli_refuses_without_a_key(
    configured_key,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The User row it selects carries encrypted columns."""
    from alchymine.cli.bootstrap_admin import bootstrap

    configured_key(None)
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")

    with pytest.raises(SystemExit) as excinfo:
        await bootstrap()

    assert excinfo.value.code == 1
    assert _ENV_KEY in capsys.readouterr().out
