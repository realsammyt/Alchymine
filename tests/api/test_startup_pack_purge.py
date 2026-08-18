"""The API lifespan purges cached envelopes for packs that left the mounts.

Startup is the only place that knows both things at once: which packs are
mounted now, and which ones a stored envelope still names. This module
asserts the wiring, in order. The purge itself is covered in
``tests/db/test_pack_envelope_purge.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from alchymine.api import main
from alchymine.engine.practice import PracticeRegistry, get_practice_registry


@pytest.fixture
def quiet_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub the shutdown half of the lifespan.

    The engine singleton belongs to an autouse fixture running on its own
    event loop, and disposing it from this test's loop is a race with
    nothing to do with startup wiring.
    """

    async def _noop() -> None:
        return None

    monkeypatch.setattr(main, "flush_pending_writes", _noop)
    monkeypatch.setattr(main, "dispose_engine", _noop)


async def test_lifespan_purges_against_the_registry_it_just_installed(
    monkeypatch: pytest.MonkeyPatch, quiet_shutdown: None
) -> None:
    seen: list[Any] = []

    async def _fake_purge(registry: PracticeRegistry) -> dict[str, int]:
        seen.append(registry)
        return {}

    monkeypatch.setattr(main, "purge_unmounted_pack_envelopes_at_startup", _fake_purge)

    async with main.lifespan(main.app):
        pass

    assert len(seen) == 1
    assert seen[0] is get_practice_registry()
    assert "alchymine-foundations" in {manifest.pack_id for manifest in seen[0].list_packs()}
