"""The API refuses to boot without a usable encryption key.

Before this gate the app started, passed its health check, and raised from
inside SQLAlchemy the first time a request touched an encrypted column. The
lifespan check moves that failure to startup, where the deploy's own health
machinery sees it and uvicorn exits non-zero instead of serving.
"""

from __future__ import annotations

import base64
from collections.abc import Callable

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from alchymine.api.main import app
from alchymine.config import get_settings
from alchymine.db.encryption import _ENV_KEY, EncryptionKeyError


@pytest.fixture
def configured_key(monkeypatch: pytest.MonkeyPatch) -> Callable[[str | None], None]:
    """Set the key at both sources the check reads, or clear both."""

    def _set(value: str | None) -> None:
        monkeypatch.setattr(get_settings(), "alchymine_encryption_key", value or "")
        if value:
            monkeypatch.setenv(_ENV_KEY, value)
        else:
            monkeypatch.delenv(_ENV_KEY, raising=False)

    return _set


def test_startup_is_refused_when_the_key_is_missing(configured_key) -> None:
    configured_key(None)

    with pytest.raises(EncryptionKeyError) as excinfo:
        with TestClient(app):
            pass

    assert _ENV_KEY in str(excinfo.value)


def test_startup_is_refused_when_the_key_is_malformed(configured_key) -> None:
    configured_key(base64.urlsafe_b64encode(b"too-short").decode())

    with pytest.raises(EncryptionKeyError) as excinfo:
        with TestClient(app):
            pass

    assert _ENV_KEY in str(excinfo.value)


def test_startup_succeeds_with_a_valid_key(configured_key) -> None:
    configured_key(Fernet.generate_key().decode())

    with TestClient(app) as client:
        assert client.get("/health").status_code in (200, 503)


def test_no_request_is_served_when_the_key_is_missing(configured_key) -> None:
    """The gate runs before any route, so nothing answers on a bad boot."""
    configured_key(None)

    served = False
    try:
        with TestClient(app) as client:
            client.get("/health")
            served = True
    except EncryptionKeyError:
        pass

    assert served is False
