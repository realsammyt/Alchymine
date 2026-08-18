"""Tests for the CI pack-boundary check.

The practice engine is generic: no third-party framework or modality vocabulary
may land in repo content. `scripts/check_pack_boundary.py` enforces that in CI
against a hashed denylist at `.github/pack-boundary-denylist.txt`.

Three things are proven here:

1. Detection works end to end, using a synthetic sentinel term planted through a
   test-only denylist. No real denylisted term appears in this file.
2. Exceptions are narrow: one frozen digest at one frozen path, never a blanket
   pass for a file or a term.
3. The real repository passes the real denylist, so every local pytest run
   enforces the rail alongside CI.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

# ─── Paths ────────────────────────────────────────────────────────────────────

# The tests live at tests/infrastructure/, project root is two levels up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHECKER_PATH = PROJECT_ROOT / "scripts" / "check_pack_boundary.py"
DENYLIST_PATH = PROJECT_ROOT / ".github" / "pack-boundary-denylist.txt"
EXCEPTIONS_PATH = PROJECT_ROOT / ".github" / "pack-boundary-exceptions.txt"

# A term that exists only for this test. It is not on the real denylist, which
# is why planting it below proves detection rather than tripping over a real hit.
SENTINEL = "Zorbatic Sentinel Modality"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def load_checker() -> ModuleType:
    """Import the checker script by path; scripts/ is not an importable package."""
    assert CHECKER_PATH.exists(), f"Checker script does not exist: {CHECKER_PATH}"
    spec = importlib.util.spec_from_file_location("check_pack_boundary", CHECKER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def checker() -> ModuleType:
    return load_checker()


def write_denylist(path: Path, terms: list[str]) -> Path:
    """Write a test-only denylist holding the hashes of `terms`."""
    digests = [hashlib.sha256(t.lower().encode("utf-8")).hexdigest() for t in terms]
    path.write_text("# test-only denylist\n" + "\n".join(digests) + "\n", encoding="utf-8")
    return path


# ─── Normalization ────────────────────────────────────────────────────────────


class TestNormalize:
    """Normalization has to agree between --hash and the scanner, or nothing matches."""

    def test_lowercases(self, checker: ModuleType) -> None:
        assert checker.normalize("Zorbatic SENTINEL") == "zorbatic sentinel"

    def test_collapses_whitespace(self, checker: ModuleType) -> None:
        assert checker.normalize("  zorbatic \t\n sentinel  ") == "zorbatic sentinel"

    def test_strips_punctuation(self, checker: ModuleType) -> None:
        assert checker.normalize("Zorbatic-Sentinel, Modality!") == "zorbatic sentinel modality"

    def test_keeps_digits(self, checker: ModuleType) -> None:
        assert checker.normalize("Method 7") == "method 7"

    def test_hash_term_is_sha256_of_normalized_form(self, checker: ModuleType) -> None:
        expected = hashlib.sha256(b"zorbatic sentinel modality").hexdigest()
        assert checker.hash_term("  Zorbatic-Sentinel,  MODALITY ") == expected


# ─── Denylist loading ─────────────────────────────────────────────────────────


class TestDenylist:
    def test_reads_hashes_and_ignores_comments_and_blanks(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        digest = hashlib.sha256(b"zorbatic").hexdigest()
        path = tmp_path / "denylist.txt"
        path.write_text(f"# a comment\n\n{digest}\n\n", encoding="utf-8")
        assert checker.load_denylist(path) == {digest}

    def test_rejects_a_line_that_is_not_a_sha256(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        path = tmp_path / "denylist.txt"
        path.write_text("not-a-hash\n", encoding="utf-8")
        with pytest.raises(ValueError, match="line 1"):
            checker.load_denylist(path)

    def test_real_denylist_holds_only_hashes(self, checker: ModuleType) -> None:
        """A plaintext term slipping into the real list would undo the redaction."""
        digests = checker.load_denylist(DENYLIST_PATH)
        assert digests, "the real denylist is empty"
        assert all(len(d) == 64 for d in digests)

    def test_real_denylist_is_seeded(self, checker: ModuleType) -> None:
        """Guards against the list being truncated to a token entry by accident."""
        assert len(checker.load_denylist(DENYLIST_PATH)) >= 40


# ─── Detection ────────────────────────────────────────────────────────────────


class TestDetection:
    def test_sentinel_term_is_detected(self, checker: ModuleType, tmp_path: Path) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        offender = tmp_path / "pack.yaml"
        offender.write_text(
            "title: Morning sit\nsummary: adapted from the Zorbatic Sentinel Modality.\n",
            encoding="utf-8",
        )

        violations = checker.scan_tree(tmp_path, denylist)

        assert len(violations) == 1
        assert violations[0].path == offender
        assert violations[0].line == 2
        assert violations[0].digest == checker.hash_term(SENTINEL)

    def test_sentinel_is_detected_across_a_line_break(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        """Prose wraps; a two-line split must not be an escape hatch."""
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        offender = tmp_path / "notes.md"
        offender.write_text("Drawn from the Zorbatic\nSentinel Modality tradition.\n", "utf-8")

        violations = checker.scan_tree(tmp_path, denylist)

        assert len(violations) == 1
        assert violations[0].line == 1

    def test_single_word_term_is_detected(self, checker: ModuleType, tmp_path: Path) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", ["Zorbatic"])
        (tmp_path / "notes.md").write_text("See zorbatic, chapter two.\n", encoding="utf-8")

        assert len(checker.scan_tree(tmp_path, denylist)) == 1

    def test_clean_tree_reports_nothing(self, checker: ModuleType, tmp_path: Path) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "notes.md").write_text("A sentinel stands. A modality helps.\n", "utf-8")

        assert checker.scan_tree(tmp_path, denylist) == []

    def test_every_hit_is_reported_not_just_the_first(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "a.md").write_text("Zorbatic Sentinel Modality\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("x\nZorbatic Sentinel Modality\n", encoding="utf-8")

        violations = checker.scan_tree(tmp_path, denylist)

        assert sorted((v.path.name, v.line) for v in violations) == [("a.md", 1), ("b.md", 2)]


# ─── Scan scope ───────────────────────────────────────────────────────────────


class TestScanScope:
    def test_skips_vendored_and_build_directories(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        for directory in ("node_modules", ".next", ".git", "__pycache__"):
            sub = tmp_path / directory
            sub.mkdir()
            (sub / "f.md").write_text("Zorbatic Sentinel Modality\n", encoding="utf-8")

        assert checker.scan_tree(tmp_path, denylist) == []

    def test_matches_skipped_directory_names_below_the_root_only(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        """A checkout that sits under a directory called 'build' is still scanned."""
        root = tmp_path / "build" / "repo"
        root.mkdir(parents=True)
        denylist = write_denylist(root / "denylist.txt", [SENTINEL])
        (root / "notes.md").write_text("Zorbatic Sentinel Modality\n", encoding="utf-8")

        assert len(checker.scan_tree(root, denylist)) == 1

    def test_skips_lockfiles(self, checker: ModuleType, tmp_path: Path) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "package-lock.json").write_text("Zorbatic Sentinel Modality\n", "utf-8")

        assert checker.scan_tree(tmp_path, denylist) == []

    def test_skips_binary_assets(self, checker: ModuleType, tmp_path: Path) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\nZorbatic Sentinel Modality")

        assert checker.scan_tree(tmp_path, denylist) == []

    def test_skips_files_it_cannot_decode(self, checker: ModuleType, tmp_path: Path) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "blob.dat").write_bytes(b"\xff\xfe\x00\x01 Zorbatic Sentinel Modality")

        assert checker.scan_tree(tmp_path, denylist) == []

    def test_does_not_scan_the_denylist_itself(self, checker: ModuleType, tmp_path: Path) -> None:
        """The denylist holds a hash of the term; it must not trip on its own contents."""
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])

        assert checker.scan_tree(tmp_path, denylist) == []

    def test_does_not_scan_the_exceptions_file_itself(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        """Exception paths can name a term; scanning that file would self-trip."""
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        exceptions = tmp_path / "exceptions.txt"
        exceptions.write_text(
            f"{checker.hash_term(SENTINEL)} docs/zorbatic-sentinel-modality.md\n", encoding="utf-8"
        )

        assert checker.scan_tree(tmp_path, denylist, exceptions) == []

    def test_skips_the_conventional_control_files_even_when_not_passed(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        """A scan with no exceptions argument still must not trip on the repo's own list."""
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "pack-boundary-exceptions.txt").write_text(
            f"{checker.hash_term(SENTINEL)} docs/zorbatic-sentinel-modality.md\n", encoding="utf-8"
        )

        assert checker.scan_tree(tmp_path, denylist) == []


# ─── Exceptions ───────────────────────────────────────────────────────────────


class TestExceptions:
    """Exceptions freeze the footprint that predates the rail. They never widen it."""

    @pytest.fixture()
    def tree(self, checker: ModuleType, tmp_path: Path) -> Path:
        write_denylist(tmp_path / "denylist.txt", [SENTINEL, "Zorbatic"])
        (tmp_path / "engine").mkdir()
        (tmp_path / "engine" / "legacy.py").write_text(
            '"""Zorbatic Sentinel Modality support."""\n', encoding="utf-8"
        )
        (tmp_path / "new.py").write_text('"""Zorbatic Sentinel Modality support."""\n', "utf-8")
        return tmp_path

    @staticmethod
    def pairs(checker: ModuleType, tree: Path, entry: str) -> set[tuple[str, str]]:
        exceptions = tree / "exceptions.txt"
        exceptions.write_text(entry, encoding="utf-8")
        violations = checker.scan_tree(tree, tree / "denylist.txt", exceptions)
        return {(v.path.name, v.digest) for v in violations}

    def test_pair_of_digest_and_path_suppresses_that_hit(
        self, checker: ModuleType, tree: Path
    ) -> None:
        found = self.pairs(checker, tree, f"{checker.hash_term(SENTINEL)} engine/legacy.py\n")

        assert ("legacy.py", checker.hash_term(SENTINEL)) not in found

    def test_directory_prefix_covers_files_beneath_it(
        self, checker: ModuleType, tree: Path
    ) -> None:
        found = self.pairs(checker, tree, f"{checker.hash_term(SENTINEL)} engine/\n")

        assert ("legacy.py", checker.hash_term(SENTINEL)) not in found

    def test_does_not_suppress_the_same_digest_in_another_file(
        self, checker: ModuleType, tree: Path
    ) -> None:
        """Grandfathering one file must not grandfather the term everywhere."""
        found = self.pairs(checker, tree, f"{checker.hash_term(SENTINEL)} engine/legacy.py\n")

        assert ("new.py", checker.hash_term(SENTINEL)) in found

    def test_does_not_suppress_a_different_digest_in_the_same_file(
        self, checker: ModuleType, tree: Path
    ) -> None:
        """A file exempt for one term is still checked for every other term."""
        exceptions = tree / "exceptions.txt"
        exceptions.write_text(f"{checker.hash_term(SENTINEL)} engine/legacy.py\n", encoding="utf-8")

        violations = checker.scan_tree(tree, tree / "denylist.txt", exceptions)
        legacy = [v for v in violations if v.path.name == "legacy.py"]

        assert [v.digest for v in legacy] == [checker.hash_term("Zorbatic")]

    def test_rejects_a_malformed_entry(self, checker: ModuleType, tmp_path: Path) -> None:
        path = tmp_path / "exceptions.txt"
        path.write_text("not-a-hash some/path.py\n", encoding="utf-8")
        with pytest.raises(ValueError, match="line 1"):
            checker.load_exceptions(path)

    def test_rejects_an_entry_with_no_path(self, checker: ModuleType, tmp_path: Path) -> None:
        path = tmp_path / "exceptions.txt"
        path.write_text(f"{checker.hash_term(SENTINEL)}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="line 1"):
            checker.load_exceptions(path)


    def test_rejects_an_entry_whose_path_escapes_the_root(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        path = tmp_path / "exceptions.txt"
        path.write_text(f"{checker.hash_term(SENTINEL)} ../elsewhere.py\n", encoding="utf-8")
        with pytest.raises(ValueError, match="line 1"):
            checker.load_exceptions(path)


# ─── Reporting ────────────────────────────────────────────────────────────────


class TestReporting:
    def test_report_line_names_the_file_and_digest_but_never_the_term(
        self, checker: ModuleType, tmp_path: Path
    ) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "notes.md").write_text("Zorbatic Sentinel Modality\n", encoding="utf-8")

        violation = checker.scan_tree(tmp_path, denylist)[0]
        rendered = checker.format_violation(violation, tmp_path)

        assert "notes.md" in rendered
        assert ":1:" in rendered
        assert checker.hash_term(SENTINEL) in rendered
        for word in SENTINEL.lower().split():
            assert word not in rendered.lower()


# ─── Command line ─────────────────────────────────────────────────────────────


class TestCommandLine:
    def test_hash_mode_prints_the_digest(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert checker.main(["--hash", SENTINEL]) == 0
        assert capsys.readouterr().out.strip() == checker.hash_term(SENTINEL)

    def test_hash_warns_when_a_term_is_too_long_to_ever_match(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A term longer than MAX_NGRAM words is silent dead weight on the list.

        The word count is only knowable while the plaintext is in hand, which is
        here and nowhere else, so this is the one place it can be caught.
        """
        assert checker.main(["--hash", "one two three four"]) == 0

        captured = capsys.readouterr()
        assert captured.out.strip() == checker.hash_term("one two three four")
        assert "4 words" in captured.err
        assert str(checker.MAX_NGRAM) in captured.err

    def test_hash_stays_quiet_at_the_ngram_limit(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert checker.main(["--hash", "one two three"]) == 0
        assert capsys.readouterr().err == ""

    def test_exits_non_zero_on_a_violation(
        self, checker: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "notes.md").write_text("Zorbatic Sentinel Modality\n", encoding="utf-8")

        rc = checker.main(["--root", str(tmp_path), "--denylist", str(denylist)])

        assert rc == 1
        captured = capsys.readouterr()
        assert "notes.md" in captured.out + captured.err
        assert "zorbatic" not in (captured.out + captured.err).lower()

    def test_exits_zero_on_a_clean_tree(
        self, checker: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "notes.md").write_text("Nothing to see.\n", encoding="utf-8")

        assert checker.main(["--root", str(tmp_path), "--denylist", str(denylist)]) == 0
        capsys.readouterr()

    def test_picks_up_the_default_exceptions_file(
        self, checker: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CI runs the checker bare, so the frozen footprint has to load on its own."""
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "notes.md").write_text("Zorbatic Sentinel Modality\n", encoding="utf-8")
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "pack-boundary-exceptions.txt").write_text(
            f"{checker.hash_term(SENTINEL)} notes.md\n", encoding="utf-8"
        )

        assert checker.main(["--root", str(tmp_path), "--denylist", str(denylist)]) == 0
        capsys.readouterr()

    def test_freeze_records_the_current_footprint(
        self, checker: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "notes.md").write_text("Zorbatic Sentinel Modality\n", encoding="utf-8")
        frozen = tmp_path / "frozen.txt"

        rc = checker.main(
            [
                "--root",
                str(tmp_path),
                "--denylist",
                str(denylist),
                "--freeze-exceptions",
                str(frozen),
            ]
        )
        capsys.readouterr()

        assert rc == 0
        assert checker.load_exceptions(frozen) == {checker.hash_term(SENTINEL): ("notes.md",)}
        assert checker.scan_tree(tmp_path, denylist, frozen) == []

    def test_freeze_never_records_the_control_files(
        self, checker: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Freezing scans with no exceptions filter, so it must still skip them.

        Otherwise a second run writes an entry for the exceptions file itself and
        the frozen footprint grows on every invocation.
        """
        denylist = write_denylist(tmp_path / "denylist.txt", [SENTINEL])
        (tmp_path / "notes.md").write_text("Zorbatic Sentinel Modality\n", encoding="utf-8")
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "pack-boundary-exceptions.txt").write_text(
            f"{checker.hash_term(SENTINEL)} docs/zorbatic-sentinel-modality.md\n", encoding="utf-8"
        )
        frozen = tmp_path / "frozen.txt"

        rc = checker.main(
            [
                "--root",
                str(tmp_path),
                "--denylist",
                str(denylist),
                "--freeze-exceptions",
                str(frozen),
            ]
        )
        capsys.readouterr()

        assert rc == 0
        assert checker.load_exceptions(frozen) == {checker.hash_term(SENTINEL): ("notes.md",)}


# ─── The rail itself ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def repo_violations(checker: ModuleType) -> list[object]:
    """One raw scan of the repository, exceptions not yet applied.

    Module-scoped because the scan walks every tracked text file; the three
    tests below all read from this single pass.
    """
    return list(checker.scan_tree(PROJECT_ROOT, DENYLIST_PATH))


@pytest.fixture(scope="module")
def repo_exceptions(checker: ModuleType) -> dict[str, tuple[str, ...]]:
    return checker.load_exceptions(EXCEPTIONS_PATH)


class TestRepositoryHoldsTheRail:
    def test_repository_passes_the_real_denylist(
        self,
        checker: ModuleType,
        repo_violations: list[object],
        repo_exceptions: dict[str, tuple[str, ...]],
    ) -> None:
        """Third-party framework vocabulary must not be present in repo content."""
        remaining = checker.apply_exceptions(repo_violations, PROJECT_ROOT, repo_exceptions)
        rendered = "\n".join(checker.format_violation(v, PROJECT_ROOT) for v in remaining)
        assert not remaining, f"pack-boundary violations found:\n{rendered}"

    def test_a_raw_scan_of_this_repo_never_reports_the_control_files(
        self, checker: ModuleType, repo_violations: list[object]
    ) -> None:
        """Regression: the real exceptions file names terms in its own entries.

        `repo_violations` is a scan of this repository with `exceptions_path`
        set to None while the real exceptions file sits on disk. That is the
        shape that used to trip the denylist against itself, and it is the shape
        `--freeze-exceptions` uses, so it has to skip the control files whether
        or not it is filtering by them.
        """
        assert EXCEPTIONS_PATH.exists(), "this regression needs the real exceptions file present"

        # Not a vacuous pass: the file's own content really does hit the denylist.
        digests = checker.load_denylist(DENYLIST_PATH)
        assert checker.scan_text(EXCEPTIONS_PATH.read_text(encoding="utf-8"), digests), (
            "the exceptions file no longer trips the denylist, so this test proves nothing"
        )

        control = {DENYLIST_PATH.resolve(), EXCEPTIONS_PATH.resolve()}
        reported = sorted(
            {relative for v in repo_violations if (relative := v.path.resolve()) in control}
        )
        assert reported == [], f"a raw scan reported the checker's own control files: {reported}"

    def test_every_exception_points_at_a_path_that_exists(
        self, checker: ModuleType, repo_exceptions: dict[str, tuple[str, ...]]
    ) -> None:
        """A stale exception is a rail that quietly stopped covering something."""
        stale = checker.stale_exceptions(PROJECT_ROOT, repo_exceptions)
        assert stale == [], f"exceptions naming paths that no longer exist: {stale}"

    def test_every_exception_is_still_earning_its_place(
        self,
        checker: ModuleType,
        repo_violations: list[object],
        repo_exceptions: dict[str, tuple[str, ...]],
    ) -> None:
        """The frozen footprint only shrinks. An entry nothing matches gets deleted."""
        unused = checker.unused_exceptions(repo_violations, PROJECT_ROOT, repo_exceptions)
        assert unused == [], f"exceptions no longer matched by any content: {unused}"


# ─── CI wiring ────────────────────────────────────────────────────────────────


class TestCIWiring:
    def test_ci_workflow_runs_the_checker(self) -> None:
        """A checker nobody runs is not a rail."""
        workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "scripts/check_pack_boundary.py" in workflow
