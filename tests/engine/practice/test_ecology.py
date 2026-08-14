"""Tests for the deterministic ecology recommender.

The seven invariants of design section 5.8 each get their own named
test, at the top of the file, so a reader can find them without knowing
the module. Everything after them tests the machinery those invariants
rest on: eligibility, the four scoring terms, the tie-break chain, the
reason templates and the stored envelope.

There is no LLM, no network and no RNG in the code under test. The only
randomness in this file is in the *fixtures*, seeded explicitly, so a
failure reproduces from the seed printed in the test id.
"""

from __future__ import annotations

import json
import random
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from alchymine.engine.practice import (
    PURPOSE_ORDER,
    PracticeRegistry,
    build_practice_registry,
    get_bundled_packs_dir,
    load_pack,
)
from alchymine.engine.practice.ecology import (
    EcologySettings,
    EcologyStateInput,
    PracticeLogRow,
    compute_pack_fingerprint,
    rank_practices,
    recommend_today,
    summarize_practice,
)

from .conftest import practice_dict, write_pack

NOW = datetime(2026, 8, 14, 9, 0, tzinfo=UTC)
TODAY = "2026-08-14"

# Every window and weight pinned, so a settings default drifting does not
# silently move what these tests assert.
SETTINGS = EcologySettings(
    weight_balance=0.40,
    weight_staleness=0.30,
    weight_progression=0.20,
    weight_featured=0.10,
    staleness_full_days=14,
    balance_window_days=28,
    decline_threshold=3,
    protocol_default_size=5,
)


# ─── Fixtures and helpers ───────────────────────────────────────────────


def day(offset: int) -> str:
    """Return the day_key *offset* days before :data:`TODAY`."""
    return (date.fromisoformat(TODAY) - timedelta(days=offset)).isoformat()


def make_registry(
    tmp_path: Path, practices: list[dict[str, Any]], pack_id: str
) -> PracticeRegistry:
    """Build a one-pack registry from *practices*, through the real loader.

    Going through ``load_pack`` rather than constructing the models means
    a fixture that would fail validation in production fails here too,
    including the ``builds_on`` graph and the prose gate.
    """
    write_pack(tmp_path, pack_id, practices)
    return PracticeRegistry([load_pack(tmp_path / pack_id, expect_bundled=False)])


@pytest.fixture
def bundled() -> PracticeRegistry:
    """The shipped pack: 10 practices, two per purpose, one root each."""
    return PracticeRegistry([load_pack(get_bundled_packs_dir() / "alchymine-foundations", expect_bundled=True)])


@pytest.fixture
def wide(tmp_path: Path) -> PracticeRegistry:
    """Five purposes, three deep: root -> child -> grandchild.

    Deeper than the bundled pack, so prerequisite chains are exercised
    at more than one level.
    """
    practices: list[dict[str, Any]] = []
    for index, purpose in enumerate(PURPOSE_ORDER):
        stem = f"p{index}"
        practices.append(
            practice_dict(
                f"{stem}-root", order=index * 3, purposes=[purpose], builds_on=[]
            )
        )
        practices.append(
            practice_dict(
                f"{stem}-child",
                order=index * 3 + 1,
                purposes=[purpose],
                builds_on=[f"{stem}-root"],
            )
        )
        practices.append(
            practice_dict(
                f"{stem}-grandchild",
                order=index * 3 + 2,
                purposes=[purpose],
                builds_on=[f"{stem}-child"],
            )
        )
    return make_registry(tmp_path, practices, "wide-pack")


def row(
    slug: str,
    *,
    purpose: str,
    day_key: str,
    status: str = "completed",
    pack_id: str = "wide-pack",
) -> PracticeLogRow:
    return PracticeLogRow(
        pack_id=pack_id,
        practice_slug=slug,
        primary_purpose=purpose,
        status=status,
        day_key=day_key,
    )


def state(**overrides: Any) -> EcologyStateInput:
    base: dict[str, Any] = {
        "protocol_size": 5,
        "active_pack_ids": None,
        "rotation_cursor": 0,
        "last_recommendation": None,
    }
    base.update(overrides)
    return EcologyStateInput(**base)


def recommend(registry: PracticeRegistry, log: list[PracticeLogRow], **kwargs: Any):
    kwargs.setdefault("state", state())
    kwargs.setdefault("now", NOW)
    kwargs.setdefault("day_key", TODAY)
    kwargs.setdefault("settings", SETTINGS)
    return recommend_today(registry, log, **kwargs)


def purposes_of(payload: dict[str, Any]) -> list[str]:
    return [item["purpose"] for item in payload["items"]]


def keys_of(payload: dict[str, Any]) -> list[tuple[str, str]]:
    return [(item["pack_id"], item["slug"]) for item in payload["items"]]


# ═══ The seven invariants (design section 5.8) ══════════════════════════


class TestInvariants:
    def test_invariant_1_balance_every_eligible_purpose_appears(
        self, wide: PracticeRegistry
    ) -> None:
        """For N >= eligible purposes, every eligible purpose appears at least once.

        The failure this prevents is a plain top-N returning five
        practices of one purpose, which is the whole reason selection is
        a round-robin rather than a sort.
        """
        # A log that heavily favours one purpose is the case where a
        # score-only ranking would collapse onto its neighbours.
        log = [row("p0-root", purpose="self-knowledge", day_key=day(d)) for d in range(1, 20)]

        result = recommend(wide, log, state=state(protocol_size=5))

        assert len(result.payload["items"]) == 5
        assert set(purposes_of(result.payload)) == set(PURPOSE_ORDER)

    def test_invariant_2_staleness_the_staler_practice_ranks_higher(
        self, tmp_path: Path
    ) -> None:
        """Two practices identical except days since last completion.

        ``fresh`` carries the better ``order`` tie-break, so if staleness
        did not dominate the pair, ``fresh`` would win and this fails.
        """
        registry = make_registry(
            tmp_path,
            [
                practice_dict("fresh", order=0, purposes=["steadiness"]),
                practice_dict("stale", order=1, purposes=["steadiness"]),
            ],
            "pair-pack",
        )
        log = [
            row("fresh", purpose="steadiness", day_key=day(1), pack_id="pair-pack"),
            row("stale", purpose="steadiness", day_key=day(12), pack_id="pair-pack"),
        ]

        ranked = rank_practices(registry, log, state(), today=TODAY, settings=SETTINGS)

        assert [scored.practice.slug for scored in ranked] == ["stale", "fresh"]

    @pytest.mark.parametrize("seed", range(20))
    def test_invariant_3_prerequisites_are_never_unmet(
        self, wide: PracticeRegistry, seed: int
    ) -> None:
        """No returned practice has an unmet ``builds_on``, over random logs.

        The generator is seeded per parametrized case, so a failure names
        the seed that produced it and reproduces exactly.
        """
        rng = random.Random(seed)
        slugs = [f"p{i}-{tier}" for i in range(5) for tier in ("root", "child", "grandchild")]
        log = []
        for _ in range(rng.randrange(0, 60)):
            slug = rng.choice(slugs)
            log.append(
                row(
                    slug,
                    # The purpose a row carries is the one its practice
                    # declares, exactly as the log route denormalizes it.
                    purpose=PURPOSE_ORDER[int(slug[1])],
                    day_key=day(rng.randrange(0, 40)),
                    status=rng.choice(["completed", "completed", "skipped", "started"]),
                )
            )
        completed = {r.practice_slug for r in log if r.status == "completed"}

        result = recommend(wide, log, state=state(rotation_cursor=seed))

        for item in result.payload["items"]:
            definition = wide.get(item["pack_id"], item["slug"])
            unmet = [p for p in definition.builds_on if p not in completed]
            assert not unmet, f"{item['slug']} recommended with unmet {unmet}"

    def test_invariant_4_cold_start_returns_roots_across_distinct_purposes(
        self, bundled: PracticeRegistry
    ) -> None:
        """An empty log yields min(N, eligible purposes) roots, all distinct."""
        result = recommend(bundled, [], state=state(protocol_size=5))

        items = result.payload["items"]
        assert len(items) == 5
        assert len(set(purposes_of(result.payload))) == 5
        for item in items:
            assert bundled.get(item["pack_id"], item["slug"]).builds_on == []

    def test_invariant_5_determinism_byte_identical_across_100_calls(
        self, wide: PracticeRegistry
    ) -> None:
        """The same (registry, log, now) serializes byte-identically, every time."""
        log = [
            row("p0-root", purpose="self-knowledge", day_key=day(3)),
            row("p1-root", purpose="steadiness", day_key=day(9)),
            row("p2-root", purpose="stewardship", day_key=day(1), status="skipped"),
        ]

        first = json.dumps(recommend(wide, log).payload, sort_keys=False)

        for _ in range(99):
            assert json.dumps(recommend(wide, log).payload, sort_keys=False) == first

    def test_invariant_6_stable_day_replays_the_stored_set(
        self, bundled: PracticeRegistry
    ) -> None:
        """Two calls in the same day_key without refresh return the identical set.

        Completing one practice at 9am must not reshuffle the other four
        at 9:05, so the second call carries both a later ``now`` and a new
        completion.
        """
        first = recommend(bundled, [])

        completed = first.payload["items"][0]
        log = [
            row(
                completed["slug"],
                purpose=completed["purpose"],
                day_key=TODAY,
                pack_id=completed["pack_id"],
            )
        ]
        second = recommend(
            bundled,
            log,
            state=state(last_recommendation=first.envelope),
            now=datetime(2026, 8, 14, 21, 30, tzinfo=UTC),
        )

        assert second.recomputed is False
        assert second.payload == first.payload

    def test_invariant_7_declined_practice_is_absent(self, wide: PracticeRegistry) -> None:
        """Three skips and zero completions in the window retires a practice."""
        log = [
            row("p0-root", purpose="self-knowledge", day_key=day(d), status="skipped")
            for d in (2, 5, 9)
        ]

        result = recommend(wide, log)

        assert ("wide-pack", "p0-root") not in keys_of(result.payload)
        # Its sibling root in another purpose is untouched.
        assert ("wide-pack", "p1-root") in keys_of(result.payload)


# ═══ Eligibility (section 5.1) ══════════════════════════════════════════


class TestEligibility:
    def test_a_practice_completed_today_is_not_offered_again(
        self, wide: PracticeRegistry
    ) -> None:
        log = [row("p0-root", purpose="self-knowledge", day_key=TODAY)]

        ranked = rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)

        assert "p0-root" not in {scored.practice.slug for scored in ranked}

    def test_a_practice_skipped_today_is_still_offered(self, wide: PracticeRegistry) -> None:
        """Only a *completion* closes a practice for the day.

        A skip means "not right now", not "done"; the decline rule at
        three skips is what stops it nagging, not a same-day suppression.
        """
        log = [row("p0-root", purpose="self-knowledge", day_key=TODAY, status="skipped")]

        ranked = rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)

        assert "p0-root" in {scored.practice.slug for scored in ranked}

    def test_a_child_unlocks_once_its_prerequisite_is_completed(
        self, wide: PracticeRegistry
    ) -> None:
        log = [row("p0-root", purpose="self-knowledge", day_key=day(4))]

        slugs = {
            scored.practice.slug
            for scored in rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
        }

        assert "p0-child" in slugs
        assert "p0-grandchild" not in slugs

    def test_a_completion_outside_the_window_still_satisfies_a_prerequisite(
        self, wide: PracticeRegistry
    ) -> None:
        """Rule 2 says "ever", not "in the window"."""
        log = [row("p0-root", purpose="self-knowledge", day_key=day(400))]

        slugs = {
            scored.practice.slug
            for scored in rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
        }

        assert "p0-child" in slugs

    def test_three_skips_with_one_completion_in_the_window_is_not_declined(
        self, wide: PracticeRegistry
    ) -> None:
        """The decline rule needs *zero* completions in the window."""
        log = [
            row("p0-root", purpose="self-knowledge", day_key=day(d), status="skipped")
            for d in (2, 5, 9)
        ] + [row("p0-root", purpose="self-knowledge", day_key=day(20))]

        slugs = {
            scored.practice.slug
            for scored in rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
        }

        assert "p0-root" in slugs

    def test_skips_older_than_the_window_do_not_decline_a_practice(
        self, wide: PracticeRegistry
    ) -> None:
        log = [
            row("p0-root", purpose="self-knowledge", day_key=day(d), status="skipped")
            for d in (30, 40, 50)
        ]

        slugs = {
            scored.practice.slug
            for scored in rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
        }

        assert "p0-root" in slugs

    def test_active_pack_ids_narrows_the_pool(self, tmp_path: Path) -> None:
        registry = build_practice_registry(
            [write_pack(tmp_path, "extra-pack", [practice_dict("solo", purposes=["expression"])])]
        )

        result = recommend(registry, [], state=state(active_pack_ids=("extra-pack",)))

        assert keys_of(result.payload) == [("extra-pack", "solo")]

    def test_active_pack_ids_none_means_every_mounted_pack(self, tmp_path: Path) -> None:
        registry = build_practice_registry(
            [write_pack(tmp_path, "extra-pack", [practice_dict("solo", purposes=["expression"])])]
        )

        result = recommend(registry, [], state=state(active_pack_ids=None))

        assert {pack_id for pack_id, _ in keys_of(result.payload)} >= {"alchymine-foundations"}


# ═══ Scoring (section 5.2) ══════════════════════════════════════════════


class TestScoring:
    def test_cold_start_gives_every_term_its_maximum_except_progression(
        self, wide: PracticeRegistry
    ) -> None:
        ranked = rank_practices(wide, [], state(), today=TODAY, settings=SETTINGS)
        root = next(s for s in ranked if s.practice.slug == "p0-root")

        assert root.balance_term == 1.0
        assert root.staleness_term == 1.0
        assert root.progression_term == 0.5
        assert root.featured_term == 0.0
        assert root.score == pytest.approx(0.40 + 0.30 + 0.20 * 0.5)

    def test_balance_term_falls_as_a_purpose_takes_a_larger_share(
        self, wide: PracticeRegistry
    ) -> None:
        # 3 of 4 completions in the window are self-knowledge.
        log = [row("p0-root", purpose="self-knowledge", day_key=day(d)) for d in (2, 3, 4)] + [
            row("p1-root", purpose="steadiness", day_key=day(5))
        ]

        ranked = rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
        crowded = next(s for s in ranked if s.practice.slug == "p0-child")
        neglected = next(s for s in ranked if s.practice.slug == "p2-root")

        assert crowded.balance_term == pytest.approx(1 - 3 / 4)
        assert neglected.balance_term == 1.0

    def test_completions_outside_the_window_do_not_move_the_balance_term(
        self, wide: PracticeRegistry
    ) -> None:
        log = [row("p0-root", purpose="self-knowledge", day_key=day(40))]

        ranked = rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
        child = next(s for s in ranked if s.practice.slug == "p0-child")

        assert child.balance_term == 1.0

    @pytest.mark.parametrize(
        ("days_ago", "expected"),
        # 30 is past the 28-day balance window on purpose: staleness reads
        # the last completion *ever*, not the last one in the window.
        [(1, 1 / 14), (7, 0.5), (14, 1.0), (30, 1.0)],
    )
    def test_staleness_term_ramps_to_one_over_the_full_day_count(
        self, wide: PracticeRegistry, days_ago: int, expected: float
    ) -> None:
        # p0-child is scored while p0-root supplies the completion, so a
        # same-day completion does not remove the row under test.
        log = [row("p0-child", purpose="self-knowledge", day_key=day(days_ago))] + [
            row("p0-root", purpose="self-knowledge", day_key=day(60))
        ]

        ranked = rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
        child = next(s for s in ranked if s.practice.slug == "p0-child")

        assert child.staleness_term == pytest.approx(expected)

    def test_progression_beats_restarting(self, wide: PracticeRegistry) -> None:
        """An unlocked child outscores an untouched root of the same purpose."""
        log = [row("p0-root", purpose="self-knowledge", day_key=day(30))]

        ranked = rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
        child = next(s for s in ranked if s.practice.slug == "p0-child")
        root = next(s for s in ranked if s.practice.slug == "p0-root")

        assert child.progression_term == 1.0
        assert root.progression_term == 0.5
        assert child.score > root.score

    def test_featured_adds_its_weight(self, tmp_path: Path) -> None:
        registry = make_registry(
            tmp_path,
            [
                practice_dict("plain", order=0, purposes=["steadiness"], featured=False),
                practice_dict("starred", order=1, purposes=["steadiness"], featured=True),
            ],
            "feature-pack",
        )

        ranked = rank_practices(registry, [], state(), today=TODAY, settings=SETTINGS)

        by_slug = {s.practice.slug: s for s in ranked}
        assert by_slug["starred"].featured_term == 1.0
        assert by_slug["plain"].featured_term == 0.0
        assert by_slug["starred"].score - by_slug["plain"].score == pytest.approx(0.10)

    def test_weights_that_do_not_sum_to_one_are_normalized(
        self, wide: PracticeRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A typo in an env var must not take the app down, and must be loud."""
        from alchymine.engine.practice import ecology

        ecology._resolve_weights.cache_clear()
        skewed = EcologySettings(
            weight_balance=0.80,
            weight_staleness=0.60,
            weight_progression=0.40,
            weight_featured=0.20,
            staleness_full_days=14,
            balance_window_days=28,
            decline_threshold=3,
            protocol_default_size=5,
        )

        with caplog.at_level("ERROR"):
            ranked = rank_practices(wide, [], state(), today=TODAY, settings=skewed)

        # Same ratios as the defaults, so the scores land where they would
        # have landed with weights that summed to 1.0.
        root = next(s for s in ranked if s.practice.slug == "p0-root")
        assert root.score == pytest.approx(0.40 + 0.30 + 0.20 * 0.5)
        assert any("weight" in record.message.lower() for record in caplog.records)

    def test_the_weight_error_is_logged_once_per_distinct_weighting(
        self, wide: PracticeRegistry, caplog: pytest.LogCaptureFixture
    ) -> None:
        from alchymine.engine.practice import ecology

        ecology._resolve_weights.cache_clear()
        skewed = EcologySettings(
            weight_balance=0.5,
            weight_staleness=0.5,
            weight_progression=0.5,
            weight_featured=0.5,
            staleness_full_days=14,
            balance_window_days=28,
            decline_threshold=3,
            protocol_default_size=5,
        )

        with caplog.at_level("ERROR"):
            for _ in range(5):
                rank_practices(wide, [], state(), today=TODAY, settings=skewed)

        assert sum("weight" in r.message.lower() for r in caplog.records) == 1


# ═══ Tie-breaking (section 5.4) ═════════════════════════════════════════


class TestTieBreaking:
    def test_order_decides_between_otherwise_identical_practices(
        self, tmp_path: Path
    ) -> None:
        registry = make_registry(
            tmp_path,
            [
                practice_dict("later", order=9, purposes=["steadiness"]),
                practice_dict("earlier", order=1, purposes=["steadiness"]),
            ],
            "tie-pack",
        )

        ranked = rank_practices(registry, [], state(), today=TODAY, settings=SETTINGS)

        assert [s.practice.slug for s in ranked] == ["earlier", "later"]

    def test_pack_id_and_slug_break_a_full_tie(self, tmp_path: Path) -> None:
        """The last key is total, so the ordering is a pure function of inputs."""
        first = tmp_path / "first"
        second = tmp_path / "second"
        write_pack(first, "aaa-pack", [practice_dict("shared", order=1, purposes=["steadiness"])])
        write_pack(second, "zzz-pack", [practice_dict("shared", order=1, purposes=["steadiness"])])
        registry = build_practice_registry([first, second])

        ranked = [
            (s.pack_id, s.practice.slug)
            for s in rank_practices(registry, [], state(), today=TODAY, settings=SETTINGS)
            if s.practice.slug == "shared"
        ]

        assert ranked == [("aaa-pack", "shared"), ("zzz-pack", "shared")]


# ═══ Selection and rotation (section 5.3) ═══════════════════════════════


class TestSelection:
    def test_the_most_neglected_purposes_are_chosen_when_n_is_small(
        self, wide: PracticeRegistry
    ) -> None:
        # self-knowledge and steadiness have history; the other three do not.
        log = [row("p0-root", purpose="self-knowledge", day_key=day(d)) for d in (2, 3)] + [
            row("p1-root", purpose="steadiness", day_key=day(4))
        ]

        result = recommend(wide, log, state=state(protocol_size=3))

        chosen = set(purposes_of(result.payload))
        assert len(chosen) == 3
        assert chosen == {"stewardship", "expression", "reframing"}

    def test_rotation_cursor_shifts_which_purpose_leads(
        self, wide: PracticeRegistry
    ) -> None:
        at_zero = recommend(wide, [], state=state(protocol_size=3, rotation_cursor=0))
        at_two = recommend(wide, [], state=state(protocol_size=3, rotation_cursor=2))

        assert purposes_of(at_zero.payload) == list(PURPOSE_ORDER[0:3])
        assert purposes_of(at_two.payload) == list(PURPOSE_ORDER[2:5])

    def test_rotation_cursor_advances_on_a_recomputation(
        self, wide: PracticeRegistry
    ) -> None:
        result = recommend(wide, [], state=state(rotation_cursor=1))

        assert result.recomputed is True
        assert result.rotation_cursor == 2

    def test_rotation_cursor_wraps_rather_than_growing(self, wide: PracticeRegistry) -> None:
        """It is only ever read modulo the purpose count, and Integer overflows."""
        assert recommend(wide, [], state=state(rotation_cursor=4)).rotation_cursor == 0
        assert recommend(wide, [], state=state(rotation_cursor=7)).rotation_cursor == 3

    def test_rotation_cursor_does_not_advance_on_a_replay(
        self, bundled: PracticeRegistry
    ) -> None:
        first = recommend(bundled, [], state=state(rotation_cursor=3))
        second = recommend(
            bundled, [], state=state(rotation_cursor=4, last_recommendation=first.envelope)
        )

        assert second.recomputed is False
        assert second.rotation_cursor == 4

    def test_a_negative_rotation_cursor_still_selects(self, wide: PracticeRegistry) -> None:
        """Python's modulo keeps a negative cursor in range rather than raising."""
        result = recommend(wide, [], state=state(protocol_size=3, rotation_cursor=-1))

        assert purposes_of(result.payload)[0] == PURPOSE_ORDER[4]

    def test_selection_stops_when_the_pool_runs_out(self, tmp_path: Path) -> None:
        registry = make_registry(
            tmp_path,
            [practice_dict("only", purposes=["steadiness"])],
            "small-pack",
        )

        result = recommend(registry, [], state=state(protocol_size=5))

        assert keys_of(result.payload) == [("small-pack", "only")]

    def test_an_exhausted_pool_returns_an_empty_protocol(self, tmp_path: Path) -> None:
        """Everything eligible was completed today. Not an error."""
        registry = make_registry(
            tmp_path, [practice_dict("only", purposes=["steadiness"])], "small-pack"
        )
        log = [row("only", purpose="steadiness", day_key=TODAY, pack_id="small-pack")]

        result = recommend(registry, log)

        assert result.payload["items"] == []
        assert result.payload["slots"] == {"morning": [], "day": [], "evening": []}

    def test_a_second_practice_of_one_purpose_only_appears_after_the_others(
        self, tmp_path: Path
    ) -> None:
        """Round-robin: one per purpose per pass, then wrap."""
        registry = make_registry(
            tmp_path,
            [
                practice_dict("s-one", order=0, purposes=["self-knowledge"]),
                practice_dict("s-two", order=1, purposes=["self-knowledge"]),
                practice_dict("t-one", order=2, purposes=["steadiness"]),
            ],
            "rr-pack",
        )

        result = recommend(registry, [], state=state(protocol_size=3))

        assert purposes_of(result.payload) == ["self-knowledge", "steadiness", "self-knowledge"]

    def test_protocol_size_is_clamped_to_the_supported_range(self, tmp_path: Path) -> None:
        """3 to 7, matching the column comment. A stored 99 is not a protocol."""
        # Two roots per purpose, so ten are eligible from cold and the
        # ceiling is what limits the result rather than the pool.
        registry = make_registry(
            tmp_path,
            [
                practice_dict(f"{purpose}-{n}", order=index * 2 + n, purposes=[purpose])
                for index, purpose in enumerate(PURPOSE_ORDER)
                for n in (0, 1)
            ],
            "big-pack",
        )

        assert len(recommend(registry, [], state=state(protocol_size=99)).payload["items"]) == 7
        assert len(recommend(registry, [], state=state(protocol_size=1)).payload["items"]) == 3


# ═══ The stable-day rule (section 5.6) ══════════════════════════════════


class TestStableDay:
    def test_a_new_day_recomputes(self, bundled: PracticeRegistry) -> None:
        first = recommend(bundled, [])

        second = recommend(
            bundled,
            [],
            state=state(last_recommendation=first.envelope),
            day_key="2026-08-15",
            now=datetime(2026, 8, 15, 9, 0, tzinfo=UTC),
        )

        assert second.recomputed is True
        assert second.payload["day_key"] == "2026-08-15"

    def test_refresh_recomputes_within_the_same_day(self, bundled: PracticeRegistry) -> None:
        first = recommend(bundled, [], state=state(rotation_cursor=0))

        second = recommend(
            bundled,
            [],
            state=state(rotation_cursor=0, last_recommendation=first.envelope),
            refresh=True,
        )

        assert second.recomputed is True
        assert second.rotation_cursor == 1

    def test_a_changed_pack_set_recomputes(self, tmp_path: Path) -> None:
        first = recommend(build_practice_registry([]), [])

        wider = build_practice_registry(
            [write_pack(tmp_path, "extra-pack", [practice_dict("solo", purposes=["expression"])])]
        )
        second = recommend(wider, [], state=state(last_recommendation=first.envelope))

        assert second.recomputed is True

    def test_a_changed_pack_version_recomputes(self, tmp_path: Path) -> None:
        """A revised pack can change what is eligible, so the set is stale."""
        container = write_pack(tmp_path, "extra-pack", [practice_dict("solo")], version="1.0.0")
        first = recommend(build_practice_registry([container]), [])

        write_pack(tmp_path, "extra-pack", [practice_dict("solo")], version="2.0.0")
        second = recommend(
            build_practice_registry([container]),
            [],
            state=state(last_recommendation=first.envelope),
        )

        assert second.recomputed is True

    @pytest.mark.parametrize(
        "stored",
        [
            {},
            {"day_key": TODAY},
            {"envelope_version": 99, "day_key": TODAY, "pack_fingerprint": "x", "payload": {}},
            {"envelope_version": 1, "day_key": TODAY, "pack_fingerprint": "x", "payload": None},
        ],
        ids=["empty", "missing-keys", "future-version", "payload-not-a-mapping"],
    )
    def test_an_unreadable_stored_envelope_recomputes(
        self, bundled: PracticeRegistry, stored: dict[str, Any]
    ) -> None:
        """Fail forward: an envelope this build cannot read is recomputed, not raised."""
        result = recommend(bundled, [], state=state(last_recommendation=stored))

        assert result.recomputed is True
        assert result.payload["items"]

    def test_the_stored_envelope_carries_the_day_and_the_fingerprint(
        self, bundled: PracticeRegistry
    ) -> None:
        result = recommend(bundled, [])

        assert result.envelope["day_key"] == TODAY
        assert result.envelope["pack_fingerprint"] == compute_pack_fingerprint(bundled, None)
        assert result.envelope["payload"] == result.payload


# ═══ The payload (section 5.7) ══════════════════════════════════════════


class TestPayload:
    def test_shape(self, bundled: PracticeRegistry) -> None:
        payload = recommend(bundled, []).payload

        assert set(payload) == {"day_key", "generated_at", "protocol_size", "items", "slots"}
        assert payload["generated_at"] == "2026-08-14T09:00:00+00:00"
        assert payload["protocol_size"] == 5
        assert set(payload["slots"]) == {"morning", "day", "evening"}

    def test_item_fields(self, bundled: PracticeRegistry) -> None:
        item = recommend(bundled, []).payload["items"][0]

        assert set(item) == {
            "pack_id",
            "slug",
            "title",
            "purpose",
            "purposes",
            "category",
            "duration_minutes",
            "reason",
            "reason_template",
        }

    def test_each_slot_carries_that_slot_prompt_for_every_item(
        self, bundled: PracticeRegistry
    ) -> None:
        """The protocol is N practices rendered three times, one per slot."""
        payload = recommend(bundled, []).payload
        first = payload["items"][0]
        definition = bundled.get(first["pack_id"], first["slug"])

        for index, slot in enumerate(("morning", "day", "evening")):
            entries = payload["slots"][slot]
            assert [(e["pack_id"], e["slug"]) for e in entries] == keys_of(payload)
            assert entries[0]["prompt"] == definition.daily_prompts[index]

    def test_the_payload_holds_no_score(self, bundled: PracticeRegistry) -> None:
        """Ranking internals stay internal. ``reason`` is the user-facing answer."""
        payload = recommend(bundled, []).payload

        assert "score" not in json.dumps(payload)


# ═══ Reason templates (section 5.7) ═════════════════════════════════════


class TestReasons:
    def test_a_never_practiced_root_says_so(self, wide: PracticeRegistry) -> None:
        scored = next(
            s
            for s in rank_practices(wide, [], state(), today=TODAY, settings=SETTINGS)
            if s.practice.slug == "p0-root"
        )

        assert scored.reason_template == "never_practiced"
        assert scored.reason == "You have not tried this one yet."

    def test_a_stale_practice_names_the_day_count(self, wide: PracticeRegistry) -> None:
        log = [row("p0-root", purpose="self-knowledge", day_key=day(d)) for d in (16, 30, 44)]

        scored = next(
            s
            for s in rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
            if s.practice.slug == "p0-root"
        )

        assert scored.reason_template == "staleness"
        assert scored.reason == "It has been 16 days since you last did this one."

    def test_one_day_is_singular(self, tmp_path: Path) -> None:
        registry = make_registry(
            tmp_path, [practice_dict("solo", purposes=["steadiness"])], "one-pack"
        )
        log = [row("solo", purpose="steadiness", day_key=day(1), pack_id="one-pack")]

        scored = rank_practices(registry, log, state(), today=TODAY, settings=SETTINGS)[0]

        assert "1 day since" in scored.reason

    def test_an_unlocked_child_names_its_prerequisite(self, wide: PracticeRegistry) -> None:
        log = [row("p0-root", purpose="self-knowledge", day_key=day(1))]

        scored = next(
            s
            for s in rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
            if s.practice.slug == "p0-child"
        )

        assert scored.reason_template == "progression"
        assert scored.reason == "This follows on from P0 Root."

    def test_a_neglected_purpose_is_named(self, wide: PracticeRegistry) -> None:
        # Everything else has recent history, so balance dominates for
        # the one purpose that does not.
        log = [
            row(f"p{i}-root", purpose=purpose, day_key=day(1))
            for i, purpose in enumerate(PURPOSE_ORDER)
            if purpose != "reframing"
        ]

        scored = next(
            s
            for s in rank_practices(wide, log, state(), today=TODAY, settings=SETTINGS)
            if s.practice.slug == "p4-root"
        )

        assert scored.reason_template == "balance"
        assert scored.reason == "You have not logged much reframing practice recently."

    def test_every_reason_is_house_style(self, bundled: PracticeRegistry) -> None:
        """No em-dashes and no AI-tell vocabulary in copy a user reads."""
        banned = (
            "delve",
            "leverage",
            "navigate",
            "robust",
            "comprehensive",
            "seamless",
            "ensure",
            "foster",
            "utilize",
            "streak",
        )
        log = [row("name-the-pattern", purpose="self-knowledge", day_key=day(20),
                   pack_id="alchymine-foundations")]

        for scored in rank_practices(bundled, log, state(), today=TODAY, settings=SETTINGS):
            assert "—" not in scored.reason
            assert "–" not in scored.reason
            lowered = scored.reason.lower()
            for word in banned:
                assert word not in lowered, f"{word!r} in {scored.reason!r}"

    def test_every_template_id_is_declared(self, bundled: PracticeRegistry) -> None:
        """The frontend styles on the id, so an undeclared one is a break."""
        from alchymine.engine.practice.ecology import REASON_TEMPLATES

        log = [row("find-the-floor", purpose="steadiness", day_key=day(3),
                   pack_id="alchymine-foundations")]

        for scored in rank_practices(bundled, log, state(), today=TODAY, settings=SETTINGS):
            assert scored.reason_template in REASON_TEMPLATES


# ═══ The summary (section 5.7) ══════════════════════════════════════════


class TestSummary:
    def test_last_7_is_oldest_first_and_seven_long(self) -> None:
        log = [row("p0-root", purpose="self-knowledge", day_key=day(d)) for d in (0, 3, 6)]

        summary = summarize_practice(log, today=TODAY)

        assert summary.last_7 == [True, False, False, True, False, False, True]
        assert summary.days_practiced_last_7 == 3

    def test_two_completions_on_one_day_count_once(self) -> None:
        log = [
            row("p0-root", purpose="self-knowledge", day_key=TODAY),
            row("p1-root", purpose="steadiness", day_key=TODAY),
        ]

        summary = summarize_practice(log, today=TODAY)

        assert summary.days_practiced_last_7 == 1

    def test_only_completions_count(self) -> None:
        log = [
            row("p0-root", purpose="self-knowledge", day_key=TODAY, status="skipped"),
            row("p1-root", purpose="steadiness", day_key=TODAY, status="started"),
        ]

        summary = summarize_practice(log, today=TODAY)

        assert summary.days_practiced_last_7 == 0
        assert summary.total_completed == 0

    def test_the_eighth_day_back_is_outside_the_window(self) -> None:
        log = [row("p0-root", purpose="self-knowledge", day_key=day(7))]

        summary = summarize_practice(log, today=TODAY)

        assert summary.last_7 == [False] * 7
        assert summary.total_completed == 1

    def test_by_purpose_is_zero_filled_across_all_five(self) -> None:
        summary = summarize_practice([], today=TODAY)

        assert summary.by_purpose == dict.fromkeys(PURPOSE_ORDER, 0)

    def test_by_purpose_counts_every_completion_ever(self) -> None:
        log = [row("p0-root", purpose="self-knowledge", day_key=day(d)) for d in (1, 100)] + [
            row("p1-root", purpose="steadiness", day_key=day(2))
        ]

        summary = summarize_practice(log, today=TODAY)

        assert summary.by_purpose["self-knowledge"] == 2
        assert summary.by_purpose["steadiness"] == 1
        assert summary.total_completed == 3


# ═══ The pack fingerprint ═══════════════════════════════════════════════


class TestPackFingerprint:
    def test_is_stable_for_the_same_registry(self, bundled: PracticeRegistry) -> None:
        assert compute_pack_fingerprint(bundled, None) == compute_pack_fingerprint(bundled, None)

    def test_narrowing_to_active_packs_changes_it(self, tmp_path: Path) -> None:
        registry = build_practice_registry(
            [write_pack(tmp_path, "extra-pack", [practice_dict("solo")])]
        )

        assert compute_pack_fingerprint(registry, None) != compute_pack_fingerprint(
            registry, ("extra-pack",)
        )

    def test_an_unmounted_active_id_is_ignored(self, bundled: PracticeRegistry) -> None:
        """A pack the user opted into but which is no longer mounted is simply absent."""
        assert compute_pack_fingerprint(
            bundled, ("alchymine-foundations", "gone-pack")
        ) == compute_pack_fingerprint(bundled, ("alchymine-foundations",))
