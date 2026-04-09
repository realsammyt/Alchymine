"""Tests for ChatMessage ORM model and chat repository functions.

Covers:
- Model creation, defaults, and round-trip persistence
- Encryption of the ``content`` column at rest
- ``save_chat_message`` repository function
- ``get_chat_history`` ordering and ``system_key`` filtering
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.db.models import ChatMessage, User
from alchymine.db.repository import get_chat_history, save_chat_message


# ─── Model ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_chat_message_creation(session: AsyncSession) -> None:
    """A ChatMessage row can be created with auto-generated id and timestamp."""
    user = User()
    session.add(user)
    await session.flush()

    msg = ChatMessage(
        user_id=user.id,
        role="user",
        content="Hello assistant",
    )
    session.add(msg)
    await session.flush()
    await session.refresh(msg)

    assert msg.id is not None
    assert len(msg.id) == 36  # UUID
    assert msg.user_id == user.id
    assert msg.role == "user"
    assert msg.content == "Hello assistant"
    assert msg.system_key is None
    assert msg.created_at is not None


@pytest.mark.asyncio
async def test_chat_message_system_key(session: AsyncSession) -> None:
    """system_key column accepts a system identifier."""
    user = User()
    session.add(user)
    await session.flush()

    msg = ChatMessage(
        user_id=user.id,
        role="assistant",
        content="Tell me about your healing journey.",
        system_key="healing",
    )
    session.add(msg)
    await session.flush()
    await session.refresh(msg)

    assert msg.system_key == "healing"
    assert msg.role == "assistant"


@pytest.mark.asyncio
async def test_chat_message_content_encrypted_at_rest(session: AsyncSession) -> None:
    """The content column is stored as ciphertext (Fernet-encrypted).

    We verify by reading the raw column value via a non-ORM query and
    asserting that the plaintext does not appear.
    """
    user = User()
    session.add(user)
    await session.flush()

    plaintext = "this is sensitive personal disclosure"
    msg = ChatMessage(user_id=user.id, role="user", content=plaintext)
    session.add(msg)
    await session.flush()

    raw = await session.execute(
        text("SELECT content FROM chat_messages WHERE id = :id"),
        {"id": msg.id},
    )
    raw_value = raw.scalar_one()
    assert plaintext not in raw_value
    # Round-trip via ORM still returns the plaintext
    fetched = await session.execute(select(ChatMessage).where(ChatMessage.id == msg.id))
    decoded = fetched.scalar_one()
    assert decoded.content == plaintext


@pytest.mark.asyncio
async def test_chat_message_cascade_delete(session: AsyncSession) -> None:
    """Deleting a User cascades to its ChatMessage rows.

    SQLite does not enforce foreign keys by default, so we explicitly
    enable ``PRAGMA foreign_keys = ON`` for this test.  In production
    PostgreSQL the ``ON DELETE CASCADE`` clause on the FK is always
    enforced by the database engine.
    """
    await session.execute(text("PRAGMA foreign_keys = ON"))

    user = User()
    session.add(user)
    await session.flush()

    msg = ChatMessage(user_id=user.id, role="user", content="hi")
    session.add(msg)
    await session.flush()

    user_id = user.id
    msg_id = msg.id

    # Issue a raw DELETE so the FK ON DELETE CASCADE fires (the ORM
    # session's identity map would otherwise hold the dependent rows).
    session.expunge(msg)
    session.expunge(user)
    await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    await session.flush()

    result = await session.execute(select(ChatMessage).where(ChatMessage.id == msg_id))
    assert result.scalar_one_or_none() is None


# ─── save_chat_message ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_chat_message_returns_row(session: AsyncSession) -> None:
    """save_chat_message returns a fully populated ChatMessage."""
    user = User()
    session.add(user)
    await session.flush()

    msg = await save_chat_message(
        session,
        user_id=user.id,
        role="user",
        content="Help me reframe this thought",
        system_key="perspective",
    )

    assert msg.id is not None
    assert msg.user_id == user.id
    assert msg.role == "user"
    assert msg.content == "Help me reframe this thought"
    assert msg.system_key == "perspective"
    assert msg.created_at is not None


@pytest.mark.asyncio
async def test_save_chat_message_default_system_key(session: AsyncSession) -> None:
    """system_key defaults to None when omitted."""
    user = User()
    session.add(user)
    await session.flush()

    msg = await save_chat_message(
        session,
        user_id=user.id,
        role="user",
        content="general question",
    )
    assert msg.system_key is None


# ─── get_chat_history ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_chat_history_chronological_order(session: AsyncSession) -> None:
    """get_chat_history returns messages oldest-first."""
    user = User()
    session.add(user)
    await session.flush()

    await save_chat_message(session, user_id=user.id, role="user", content="first")
    await save_chat_message(session, user_id=user.id, role="assistant", content="second")
    await save_chat_message(session, user_id=user.id, role="user", content="third")

    history = await get_chat_history(session, user_id=user.id)
    assert [m.content for m in history] == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_get_chat_history_filter_by_system_key(session: AsyncSession) -> None:
    """get_chat_history filters by system_key when provided."""
    user = User()
    session.add(user)
    await session.flush()

    await save_chat_message(
        session, user_id=user.id, role="user", content="general msg", system_key=None
    )
    await save_chat_message(
        session, user_id=user.id, role="user", content="healing msg", system_key="healing"
    )
    await save_chat_message(
        session, user_id=user.id, role="user", content="wealth msg", system_key="wealth"
    )
    await save_chat_message(
        session,
        user_id=user.id,
        role="assistant",
        content="healing reply",
        system_key="healing",
    )

    healing = await get_chat_history(session, user_id=user.id, system_key="healing")
    assert [m.content for m in healing] == ["healing msg", "healing reply"]

    wealth = await get_chat_history(session, user_id=user.id, system_key="wealth")
    assert [m.content for m in wealth] == ["wealth msg"]


@pytest.mark.asyncio
async def test_get_chat_history_filter_none_returns_all(session: AsyncSession) -> None:
    """When system_key is None, all messages are returned regardless of scope."""
    user = User()
    session.add(user)
    await session.flush()

    await save_chat_message(session, user_id=user.id, role="user", content="a")
    await save_chat_message(
        session, user_id=user.id, role="user", content="b", system_key="healing"
    )
    await save_chat_message(
        session, user_id=user.id, role="user", content="c", system_key="wealth"
    )

    history = await get_chat_history(session, user_id=user.id)
    assert [m.content for m in history] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_get_chat_history_respects_limit(session: AsyncSession) -> None:
    """get_chat_history caps the number of returned rows at *limit*.

    The latest *limit* messages are returned, in chronological order.
    """
    user = User()
    session.add(user)
    await session.flush()

    for i in range(10):
        await save_chat_message(
            session, user_id=user.id, role="user", content=f"msg-{i:02d}"
        )

    history = await get_chat_history(session, user_id=user.id, limit=3)
    assert len(history) == 3
    # The latest three are msg-07, msg-08, msg-09 — oldest-first
    assert [m.content for m in history] == ["msg-07", "msg-08", "msg-09"]


@pytest.mark.asyncio
async def test_get_chat_history_isolates_users(session: AsyncSession) -> None:
    """Messages for one user are not visible to another."""
    user_a = User()
    user_b = User()
    session.add_all([user_a, user_b])
    await session.flush()

    await save_chat_message(session, user_id=user_a.id, role="user", content="alice")
    await save_chat_message(session, user_id=user_b.id, role="user", content="bob")

    history = await get_chat_history(session, user_id=user_a.id)
    assert [m.content for m in history] == ["alice"]
