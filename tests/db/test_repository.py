"""Tests for the async CRUD repository.

Uses SQLite in-memory database via aiosqlite.  Fixtures from conftest.py
provide a fresh engine and session for each test.
"""

from __future__ import annotations

from datetime import date, time

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from alchymine.db.repository import (
    count_reports_by_user,
    create_journal_entry,
    create_profile,
    create_report,
    delete_journal_entry,
    delete_profile,
    get_journal_entry,
    get_journal_stats,
    get_profile,
    get_report,
    list_journal_entries,
    list_profiles,
    list_reports_by_user,
    update_journal_entry,
    update_layer,
    update_report_content,
    update_report_status,
)

# ─── create_profile ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_profile_minimal(session: AsyncSession) -> None:
    """create_profile with only required fields returns a User with intake."""
    user = await create_profile(
        session,
        full_name="Maria Elena Vasquez",
        birth_date=date(1992, 3, 15),
        intention="family",
    )

    assert user.id is not None
    assert user.version == "2.0"
    assert user.intake is not None
    assert user.intake.full_name == "Maria Elena Vasquez"
    assert user.intake.birth_date == date(1992, 3, 15)
    assert user.intake.intention == "family"


@pytest.mark.asyncio
async def test_create_profile_full(session: AsyncSession) -> None:
    """create_profile with all fields populates intake correctly."""
    user = await create_profile(
        session,
        full_name="Maria Elena Vasquez",
        birth_date=date(1992, 3, 15),
        birth_time=time(14, 14),
        birth_city="Mexico City",
        intention="family",
        assessment_responses={"big_five_1": 4, "big_five_2": 2},
        family_structure="single parent",
    )

    assert user.intake.birth_time == time(14, 14)
    assert user.intake.birth_city == "Mexico City"
    assert user.intake.assessment_responses["big_five_1"] == 4
    assert user.intake.family_structure == "single parent"


# ─── create_profile with intentions ────────────────────────────────────


@pytest.mark.asyncio
async def test_create_profile_with_intentions_list(session: AsyncSession) -> None:
    """create_profile stores and reads back a multi-intention list."""
    user = await create_profile(
        session,
        full_name="Multi Intent User",
        birth_date=date(1990, 5, 20),
        intention="career",
        intentions=["career", "money", "business"],
    )

    assert user.intake is not None
    assert user.intake.intention == "career"
    assert user.intake.intentions == ["career", "money", "business"]
    assert user.intake.resolved_intentions == ["career", "money", "business"]


@pytest.mark.asyncio
async def test_create_profile_legacy_single_intention(session: AsyncSession) -> None:
    """create_profile with intentions=None falls back via resolved_intentions."""
    user = await create_profile(
        session,
        full_name="Legacy User",
        birth_date=date(1985, 8, 10),
        intention="health",
    )

    assert user.intake.intentions is None
    assert user.intake.resolved_intentions == ["health"]


# ─── get_profile ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_profile_found(session: AsyncSession) -> None:
    """get_profile returns the user with all relationships loaded."""
    created = await create_profile(
        session,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="career",
    )

    fetched = await get_profile(session, created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.intake is not None
    assert fetched.intake.full_name == "Test User"


@pytest.mark.asyncio
async def test_get_profile_not_found(session: AsyncSession) -> None:
    """get_profile returns None for a non-existent user."""
    result = await get_profile(session, "nonexistent-uuid")
    assert result is None


# ─── list_profiles ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_profiles_empty(session: AsyncSession) -> None:
    """list_profiles returns empty list when no users exist."""
    result = await list_profiles(session)
    assert result == []


@pytest.mark.asyncio
async def test_list_profiles_pagination(session: AsyncSession) -> None:
    """list_profiles respects offset and limit."""
    for i in range(5):
        await create_profile(
            session,
            full_name=f"User {i}",
            birth_date=date(2000, 1, 1),
            intention="career",
        )

    all_users = await list_profiles(session, offset=0, limit=20)
    assert len(all_users) == 5

    page = await list_profiles(session, offset=2, limit=2)
    assert len(page) == 2


# ─── update_layer ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_layer_identity_create(session: AsyncSession) -> None:
    """update_layer creates a new identity layer when none exists."""
    user = await create_profile(
        session,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="purpose",
    )

    updated = await update_layer(
        session,
        user.id,
        "identity",
        {
            "numerology": {"life_path": 7, "expression": 3},
            "astrology": {"sun_sign": "Pisces"},
        },
    )

    assert updated.identity is not None
    assert updated.identity.numerology["life_path"] == 7
    assert updated.identity.astrology["sun_sign"] == "Pisces"


@pytest.mark.asyncio
async def test_update_layer_identity_update(session: AsyncSession) -> None:
    """update_layer updates an existing identity layer."""
    user = await create_profile(
        session,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="purpose",
    )

    # Create
    await update_layer(
        session,
        user.id,
        "identity",
        {
            "numerology": {"life_path": 7},
        },
    )

    # Update
    updated = await update_layer(
        session,
        user.id,
        "identity",
        {
            "numerology": {"life_path": 7, "expression": 3},
            "strengths_map": ["creativity", "empathy"],
        },
    )

    assert updated.identity.numerology["expression"] == 3
    assert updated.identity.strengths_map == ["creativity", "empathy"]


@pytest.mark.asyncio
async def test_update_layer_healing(session: AsyncSession) -> None:
    """update_layer creates and populates a healing layer."""
    user = await create_profile(
        session,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="health",
    )

    updated = await update_layer(
        session,
        user.id,
        "healing",
        {
            "selected_modalities": [
                {"modality": "breathwork", "preference_score": 0.8},
            ],
            "practice_history": {"breathwork": 3},
            "max_difficulty": "developing",
            "crisis_protocol_active": False,
        },
    )

    assert updated.healing is not None
    assert len(updated.healing.selected_modalities) == 1
    assert updated.healing.max_difficulty == "developing"


@pytest.mark.asyncio
async def test_update_layer_wealth_encrypted(session: AsyncSession) -> None:
    """update_layer correctly handles encrypted wealth columns."""
    user = await create_profile(
        session,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="money",
    )

    updated = await update_layer(
        session,
        user.id,
        "wealth",
        {
            "risk_tolerance": "aggressive",
            "income_range": "$100k-$150k",  # SENSITIVE — encrypted
            "debt_level": "moderate",  # SENSITIVE — encrypted
            "wealth_context": {"has_investments": True},  # SENSITIVE — encrypted
            "lever_priorities": ["EARN", "GROW"],
        },
    )

    assert updated.wealth is not None
    assert updated.wealth.risk_tolerance == "aggressive"
    assert updated.wealth.income_range == "$100k-$150k"
    assert updated.wealth.debt_level == "moderate"
    assert updated.wealth.wealth_context["has_investments"] is True


@pytest.mark.asyncio
async def test_update_layer_creative(session: AsyncSession) -> None:
    """update_layer creates a creative layer."""
    user = await create_profile(
        session,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="purpose",
    )

    updated = await update_layer(
        session,
        user.id,
        "creative",
        {
            "guilford_scores": {"fluency": 72.0, "originality": 80.0},
            "creative_orientation": "expressive-intuitive",
            "active_projects": 3,
        },
    )

    assert updated.creative is not None
    assert updated.creative.guilford_scores["fluency"] == 72.0
    assert updated.creative.active_projects == 3


@pytest.mark.asyncio
async def test_update_layer_perspective(session: AsyncSession) -> None:
    """update_layer creates a perspective layer."""
    user = await create_profile(
        session,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="purpose",
    )

    updated = await update_layer(
        session,
        user.id,
        "perspective",
        {
            "kegan_stage": "self-authoring",
            "mental_models_applied": ["inversion", "second-order thinking"],
            "reframes_completed": 10,
            "strategic_clarity_score": 85.0,
        },
    )

    assert updated.perspective is not None
    assert updated.perspective.kegan_stage == "self-authoring"
    assert updated.perspective.reframes_completed == 10


@pytest.mark.asyncio
async def test_update_layer_intake(session: AsyncSession) -> None:
    """update_layer can update existing intake fields."""
    user = await create_profile(
        session,
        full_name="Original Name",
        birth_date=date(2000, 1, 1),
        intention="career",
    )

    updated = await update_layer(
        session,
        user.id,
        "intake",
        {
            "full_name": "Updated Name",
            "birth_city": "Toronto",
        },
    )

    assert updated.intake.full_name == "Updated Name"
    assert updated.intake.birth_city == "Toronto"


@pytest.mark.asyncio
async def test_update_layer_invalid_layer(session: AsyncSession) -> None:
    """update_layer raises ValueError for unknown layer names."""
    user = await create_profile(
        session,
        full_name="Test User",
        birth_date=date(2000, 1, 1),
        intention="career",
    )

    with pytest.raises(ValueError, match="Unknown layer"):
        await update_layer(session, user.id, "nonexistent", {})


@pytest.mark.asyncio
async def test_update_layer_user_not_found(session: AsyncSession) -> None:
    """update_layer raises LookupError for non-existent user."""
    with pytest.raises(LookupError, match="No user"):
        await update_layer(session, "fake-uuid", "identity", {})


@pytest.mark.asyncio
async def test_update_layer_upsert_idempotent(session: AsyncSession) -> None:
    """update_layer can create and re-create the same layer without error (upsert)."""
    user = await create_profile(
        session,
        full_name="Upsert Test",
        birth_date=date(1990, 1, 1),
        intention="purpose",
    )

    # First call creates the identity layer
    await update_layer(
        session, user.id, "identity", {"numerology": {"life_path": 7}}
    )

    # Second call with same data should succeed (upsert, not duplicate)
    updated = await update_layer(
        session, user.id, "identity", {"numerology": {"life_path": 7}, "archetype": {"name": "Sage"}}
    )
    assert updated.identity.numerology == {"life_path": 7}
    assert updated.identity.archetype == {"name": "Sage"}


# ─── delete_profile ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_profile_success(session: AsyncSession) -> None:
    """delete_profile removes user and all layers."""
    user = await create_profile(
        session,
        full_name="To Delete",
        birth_date=date(2000, 1, 1),
        intention="career",
    )
    user_id = user.id

    # Add a few layers
    await update_layer(session, user_id, "identity", {"numerology": {"life_path": 1}})
    await update_layer(session, user_id, "healing", {"max_difficulty": "foundation"})

    result = await delete_profile(session, user_id)
    assert result is True

    # Verify gone
    assert await get_profile(session, user_id) is None


@pytest.mark.asyncio
async def test_delete_profile_not_found(session: AsyncSession) -> None:
    """delete_profile returns False for non-existent user."""
    result = await delete_profile(session, "fake-uuid")
    assert result is False


# ─── Full profile lifecycle ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_lifecycle(session: AsyncSession) -> None:
    """End-to-end: create, populate all layers, read, update, delete."""
    # 1. Create
    user = await create_profile(
        session,
        full_name="Maria Elena Vasquez",
        birth_date=date(1992, 3, 15),
        birth_time=time(14, 14),
        birth_city="Mexico City",
        intention="family",
    )
    user_id = user.id

    # 2. Populate identity
    await update_layer(
        session,
        user_id,
        "identity",
        {
            "numerology": {"life_path": 3, "expression": 6},
            "astrology": {"sun_sign": "Pisces", "moon_sign": "Scorpio"},
            "archetype": {"primary": "creator", "shadow": "Perfectionism"},
            "personality": {
                "big_five": {"openness": 75.0},
                "attachment_style": "anxious-secure",
            },
        },
    )

    # 3. Populate healing
    await update_layer(
        session,
        user_id,
        "healing",
        {
            "selected_modalities": [{"modality": "breathwork"}],
            "max_difficulty": "developing",
        },
    )

    # 4. Populate wealth (encrypted)
    await update_layer(
        session,
        user_id,
        "wealth",
        {
            "risk_tolerance": "moderate",
            "income_range": "$50k-$75k",
            "wealth_context": {"dependents": 1},
        },
    )

    # 5. Populate creative
    await update_layer(
        session,
        user_id,
        "creative",
        {
            "guilford_scores": {"fluency": 72.0},
            "creative_orientation": "expressive",
        },
    )

    # 6. Populate perspective
    await update_layer(
        session,
        user_id,
        "perspective",
        {
            "kegan_stage": "socialized",
            "reframes_completed": 0,
        },
    )

    # 7. Read full profile
    full = await get_profile(session, user_id)
    assert full is not None
    assert full.intake.full_name == "Maria Elena Vasquez"
    assert full.identity.numerology["life_path"] == 3
    assert full.healing.max_difficulty == "developing"
    assert full.wealth.income_range == "$50k-$75k"
    assert full.creative.guilford_scores["fluency"] == 72.0
    assert full.perspective.kegan_stage == "socialized"

    # 8. Update a layer
    await update_layer(
        session,
        user_id,
        "perspective",
        {
            "kegan_stage": "self-authoring",
            "reframes_completed": 5,
        },
    )
    refreshed = await get_profile(session, user_id)
    assert refreshed.perspective.kegan_stage == "self-authoring"
    assert refreshed.perspective.reframes_completed == 5

    # 9. Delete
    assert await delete_profile(session, user_id) is True
    assert await get_profile(session, user_id) is None


# ═══════════════════════════════════════════════════════════════════════
# Report CRUD
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_and_get_report(session: AsyncSession) -> None:
    """create_report inserts a row that get_report can retrieve."""
    report = await create_report(session, report_id="rpt-1", status="pending", user_input="test")
    assert report.id == "rpt-1"
    assert report.status == "pending"

    fetched = await get_report(session, "rpt-1")
    assert fetched is not None
    assert fetched.user_input == "test"


@pytest.mark.asyncio
async def test_get_report_not_found(session: AsyncSession) -> None:
    """get_report returns None for a non-existent id."""
    result = await get_report(session, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_update_report_status(session: AsyncSession) -> None:
    """update_report_status changes the status field."""
    await create_report(session, report_id="rpt-2", status="pending")
    updated = await update_report_status(session, "rpt-2", "generating")
    assert updated is not None
    assert updated.status == "generating"


@pytest.mark.asyncio
async def test_update_report_status_not_found(session: AsyncSession) -> None:
    """update_report_status returns None for missing report."""
    result = await update_report_status(session, "missing", "generating")
    assert result is None


@pytest.mark.asyncio
async def test_update_report_content(session: AsyncSession) -> None:
    """update_report_content sets result and status."""
    await create_report(session, report_id="rpt-3", status="generating")
    result_data = {"systems": {"intelligence": {}}}
    updated = await update_report_content(session, "rpt-3", result=result_data, status="complete")
    assert updated is not None
    assert updated.status == "complete"
    assert updated.result == result_data


@pytest.mark.asyncio
async def test_update_report_content_not_found(session: AsyncSession) -> None:
    """update_report_content returns None for missing report."""
    result = await update_report_content(session, "missing", result={})
    assert result is None


@pytest.mark.asyncio
async def test_list_reports_by_user(session: AsyncSession) -> None:
    """list_reports_by_user returns only reports for the given user."""
    await create_report(session, report_id="rpt-u1", user_id="user-a")
    await create_report(session, report_id="rpt-u2", user_id="user-a")
    await create_report(session, report_id="rpt-u3", user_id="user-b")
    reports = await list_reports_by_user(session, "user-a")
    assert len(reports) == 2
    assert all(r.user_id == "user-a" for r in reports)


@pytest.mark.asyncio
async def test_count_reports_by_user(session: AsyncSession) -> None:
    """count_reports_by_user returns the correct count."""
    await create_report(session, report_id="cnt-1", user_id="user-c")
    await create_report(session, report_id="cnt-2", user_id="user-c")
    count = await count_reports_by_user(session, "user-c")
    assert count == 2


@pytest.mark.asyncio
async def test_count_reports_by_user_empty(session: AsyncSession) -> None:
    """count_reports_by_user returns 0 for unknown user."""
    count = await count_reports_by_user(session, "nobody")
    assert count == 0


# ═══════════════════════════════════════════════════════════════════════
# Journal Entry CRUD
# ═══════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_and_get_journal_entry(session: AsyncSession) -> None:
    """create_journal_entry inserts a row that get_journal_entry can retrieve."""
    entry = await create_journal_entry(
        session, user_id="user-j1", title="Test", content="Hello world"
    )
    assert entry.id is not None
    assert entry.title == "Test"

    fetched = await get_journal_entry(session, entry.id)
    assert fetched is not None
    assert fetched.content == "Hello world"


@pytest.mark.asyncio
async def test_get_journal_entry_not_found(session: AsyncSession) -> None:
    """get_journal_entry returns None for a non-existent id."""
    result = await get_journal_entry(session, "fake-id")
    assert result is None


@pytest.mark.asyncio
async def test_list_journal_entries_with_pagination(session: AsyncSession) -> None:
    """list_journal_entries respects limit and returns total count."""
    for i in range(5):
        await create_journal_entry(
            session, user_id="user-j2", title=f"Entry {i}", content=f"Content {i}"
        )
    entries, total = await list_journal_entries(session, "user-j2", limit=3)
    assert total == 5
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_list_journal_entries_filter_by_system(session: AsyncSession) -> None:
    """list_journal_entries can filter by system."""
    await create_journal_entry(session, user_id="user-j3", title="A", content="a", system="healing")
    await create_journal_entry(session, user_id="user-j3", title="B", content="b", system="wealth")
    entries, total = await list_journal_entries(session, "user-j3", system="healing")
    assert total == 1
    assert entries[0].system == "healing"


@pytest.mark.asyncio
async def test_list_journal_entries_filter_by_entry_type(session: AsyncSession) -> None:
    """list_journal_entries can filter by entry_type."""
    await create_journal_entry(
        session,
        user_id="user-j3b",
        title="R",
        content="r",
        entry_type="reflection",
    )
    await create_journal_entry(
        session,
        user_id="user-j3b",
        title="G",
        content="g",
        entry_type="gratitude",
    )
    entries, total = await list_journal_entries(session, "user-j3b", entry_type="gratitude")
    assert total == 1
    assert entries[0].entry_type == "gratitude"


@pytest.mark.asyncio
async def test_update_journal_entry(session: AsyncSession) -> None:
    """update_journal_entry modifies the specified fields."""
    entry = await create_journal_entry(session, user_id="user-j4", title="Old", content="old")
    updated = await update_journal_entry(session, entry.id, title="New", content="new")
    assert updated is not None
    assert updated.title == "New"
    assert updated.content == "new"


@pytest.mark.asyncio
async def test_update_journal_entry_not_found(session: AsyncSession) -> None:
    """update_journal_entry returns None for missing entry."""
    result = await update_journal_entry(session, "fake-id", title="X")
    assert result is None


@pytest.mark.asyncio
async def test_delete_journal_entry(session: AsyncSession) -> None:
    """delete_journal_entry removes the entry."""
    entry = await create_journal_entry(session, user_id="user-j5", title="Del", content="del")
    assert await delete_journal_entry(session, entry.id) is True
    assert await get_journal_entry(session, entry.id) is None


@pytest.mark.asyncio
async def test_delete_journal_entry_not_found(session: AsyncSession) -> None:
    """delete_journal_entry returns False for non-existent id."""
    assert await delete_journal_entry(session, "fake-id") is False


@pytest.mark.asyncio
async def test_get_journal_stats_empty(session: AsyncSession) -> None:
    """get_journal_stats returns zeroed stats for a user with no entries."""
    stats = await get_journal_stats(session, "no-entries-user")
    assert stats["total_entries"] == 0
    assert stats["entries_by_system"] == {}
    assert stats["average_mood"] is None


@pytest.mark.asyncio
async def test_get_journal_stats_with_data(session: AsyncSession) -> None:
    """get_journal_stats computes correct aggregations."""
    await create_journal_entry(
        session,
        user_id="user-stats",
        title="A",
        content="a",
        system="healing",
        mood_score=7,
        tags=["tag1"],
    )
    await create_journal_entry(
        session,
        user_id="user-stats",
        title="B",
        content="b",
        system="wealth",
        mood_score=9,
        tags=["tag2"],
    )
    stats = await get_journal_stats(session, "user-stats")
    assert stats["total_entries"] == 2
    assert stats["entries_by_system"]["healing"] == 1
    assert stats["entries_by_system"]["wealth"] == 1
    assert stats["average_mood"] is not None
    assert set(stats["tags_used"]) == {"tag1", "tag2"}
