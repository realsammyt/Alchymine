#!/usr/bin/env python3
"""Fail the build when third-party framework vocabulary lands in repo content.

Alchymine's practice engine is generic. Branded practice packs mount from
outside the repo through ``PRACTICE_PACK_DIRS`` and carry their own license and
attribution; the repo itself ships only original content. This script is the
mechanical half of that rail.

The denylist at ``.github/pack-boundary-denylist.txt`` holds one sha256 per
line, each the digest of a *normalized* term. It is hashed rather than
plaintext because the names were deliberately redacted from repo text, and a
plaintext list would publish exactly what the redaction removed. Violations are
reported as ``file:line`` plus the matching digest, never the matched term, so
CI logs stay clean while a human can still find the spot.

The tradeoff is known and accepted: sha256 of a well-known name is recoverable
by anyone who guesses the name. This is not secrecy against determined
analysis. It keeps the names out of repo text, diffs and CI logs.

``.github/pack-boundary-exceptions.txt`` freezes the footprint that predates
the rail: one line per (digest, path) pair, so a file grandfathered for one
term is still checked for every other term, and the same term is still caught
anywhere else. The list can shrink, never silently widen.

Usage::

    python scripts/check_pack_boundary.py            # scan the repo, exit 1 on a hit
    python scripts/check_pack_boundary.py --hash "some term"

Add a term by appending the ``--hash`` output to the denylist, then rerun the
scan. Never commit the term itself.

Standard library only, so CI can run it without installing the project.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

# ─── Configuration ────────────────────────────────────────────────────────────

# The script lives at scripts/, project root is one level up.
DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DENYLIST_RELATIVE = Path(".github") / "pack-boundary-denylist.txt"
EXCEPTIONS_RELATIVE = Path(".github") / "pack-boundary-exceptions.txt"

# Longest denylisted term, in words. Multi-word names are stored as their
# normalized n-gram string, so the scanner has to look this far ahead.
MAX_NGRAM = 3

# Vendored, generated or version-control directories. Nothing here is authored
# content, and node_modules alone would dominate the runtime.
SKIP_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "htmlcov",
        "node_modules",
        "venv",
    }
)

# Dependency lockfiles: machine-written, and full of third-party package names.
SKIP_NAMES = frozenset(
    {
        "Pipfile.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)

# Binary assets. Anything not listed here is still checked for NUL bytes and
# UTF-8 decodability before it is scanned.
SKIP_SUFFIXES = frozenset(
    {
        ".bmp",
        ".docx",
        ".gif",
        ".gz",
        ".ico",
        ".jpeg",
        ".jpg",
        ".pdf",
        ".png",
        ".pyc",
        ".tar",
        ".ttf",
        ".webp",
        ".woff",
        ".woff2",
        ".xlsx",
        ".zip",
    }
)

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
_SEPARATOR_RE = re.compile(r"[\W_]+", re.UNICODE)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class Violation(NamedTuple):
    """One denylist hit: where it is, and which entry matched."""

    path: Path
    line: int
    digest: str


# ─── Normalization ────────────────────────────────────────────────────────────


def normalize(text: str) -> str:
    """Lowercase, reduce every run of non-alphanumerics to one space, trim.

    Both the ``--hash`` helper and the scanner run text through this, so
    "Some-Name", "some name" and "Some  Name!" all reach the same digest.
    """
    return _SEPARATOR_RE.sub(" ", text.lower()).strip()


def hash_term(term: str) -> str:
    """sha256 of the normalized form of `term`, as lowercase hex."""
    return hashlib.sha256(normalize(term).encode("utf-8")).hexdigest()


# ─── Denylist ─────────────────────────────────────────────────────────────────


def load_denylist(path: Path) -> set[str]:
    """Read the hashed denylist. Comments start with '#'; blank lines are skipped.

    Raises ValueError if any entry is not a sha256 digest, which is how a
    plaintext term accidentally pasted into the list gets caught.
    """
    digests: set[str] = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not _SHA256_RE.match(line):
            raise ValueError(
                f"{path}: line {number} is not a lowercase sha256 digest. "
                "The denylist holds hashes only, never plaintext terms."
            )
        digests.add(line)
    return digests


# ─── Exceptions ───────────────────────────────────────────────────────────────


def load_exceptions(path: Path) -> dict[str, tuple[str, ...]]:
    """Read the frozen pre-rail footprint: digest -> the paths it may appear at.

    Each line is ``<sha256> <path>``, the path relative to the repo root, posix
    separators. A trailing slash makes it a directory prefix. Pairing the digest
    with the path is what keeps an exception narrow: the file stays checked for
    every other term, and the term stays caught in every other file.
    """
    entries: dict[str, list[str]] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, location = line.partition(" ")
        location = location.strip()
        if not _SHA256_RE.match(digest) or not location:
            raise ValueError(
                f"{path}: line {number} is not '<sha256> <path>'. "
                "Exceptions pair one digest with one path, never a bare term or a bare path."
            )
        if location.startswith("/") or ".." in Path(location).parts:
            raise ValueError(
                f"{path}: line {number} has a path outside the repository root. "
                "Exception paths are relative to the root."
            )
        entries.setdefault(digest, []).append(location)
    return {digest: tuple(locations) for digest, locations in entries.items()}


def _covers(location: str, relative_path: str) -> bool:
    """True when an exception entry's path covers `relative_path`."""
    if location.endswith("/"):
        return relative_path.startswith(location)
    return relative_path == location or relative_path.startswith(f"{location}/")


def relative_to_root(path: Path, root: Path) -> str:
    """Posix path relative to `root`, or the absolute path when it sits outside."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_excepted(violation: Violation, root: Path, exceptions: dict[str, tuple[str, ...]]) -> bool:
    locations = exceptions.get(violation.digest)
    if not locations:
        return False
    relative = relative_to_root(violation.path, root)
    return any(_covers(location, relative) for location in locations)


def apply_exceptions(
    violations: Iterable[Violation], root: Path, exceptions: dict[str, tuple[str, ...]]
) -> list[Violation]:
    """Drop the violations the frozen footprint already accounts for."""
    return [v for v in violations if not is_excepted(v, root, exceptions)]


def stale_exceptions(root: Path, exceptions: dict[str, tuple[str, ...]]) -> list[str]:
    """Exception entries whose path no longer exists, newest rot first to fix."""
    return sorted(
        f"{digest} {location}"
        for digest, locations in exceptions.items()
        for location in locations
        if not (root / location).exists()
    )


def unused_exceptions(
    violations: Iterable[Violation], root: Path, exceptions: dict[str, tuple[str, ...]]
) -> list[str]:
    """Exception entries that no current content matches, so they can be deleted."""
    matched = {
        (v.digest, location)
        for v in violations
        for location in exceptions.get(v.digest, ())
        if _covers(location, relative_to_root(v.path, root))
    }
    return sorted(
        f"{digest} {location}"
        for digest, locations in exceptions.items()
        for location in locations
        if (digest, location) not in matched
    )


# ─── File discovery ───────────────────────────────────────────────────────────


def _git_tracked_files(root: Path) -> list[Path] | None:
    """Tracked files under `root`, or None when `root` is not a git worktree root.

    Tracked content is the right scope: an untracked scratch file in someone's
    working copy has not landed in the repo.
    """
    git = shutil.which("git")
    if git is None:
        return None
    try:
        # Fixed argv, absolute executable, no shell. `root` comes from the CLI.
        toplevel = subprocess.run(  # noqa: S603
            [git, "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if toplevel.returncode != 0:
            return None
        if Path(toplevel.stdout.strip()).resolve() != root.resolve():
            return None
        listed = subprocess.run(  # noqa: S603
            [git, "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if listed.returncode != 0:
        return None
    return [root / name for name in listed.stdout.split("\0") if name]


def _walked_files(root: Path) -> Iterator[Path]:
    """Every file under `root`, pruning vendored and generated directories."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            yield Path(dirpath) / name


def is_scannable(path: Path, root: Path) -> bool:
    """True when `path` is authored text worth checking.

    Directory names are matched below `root` only, so a checkout that happens to
    sit under a directory called "build" or "dist" still gets scanned.
    """
    relative = relative_to_root(path, root)
    if any(part in SKIP_DIRS for part in Path(relative).parts):
        return False
    if path.name in SKIP_NAMES:
        return False
    return path.suffix.lower() not in SKIP_SUFFIXES


def iter_scannable_files(root: Path, *skip: Path | None) -> Iterator[Path]:
    """Candidate files under `root`, minus the checker's own control files.

    The denylist and the exceptions file are skipped: the first holds digests of
    the terms, the second holds paths that can name one.
    """
    excluded = {path.resolve() for path in skip if path is not None}
    tracked = _git_tracked_files(root)
    candidates: Iterable[Path] = tracked if tracked is not None else _walked_files(root)
    for path in candidates:
        if not is_scannable(path, root) or not path.is_file():
            continue
        if path.resolve() in excluded:
            continue
        yield path


def read_text(path: Path) -> str | None:
    """File contents as UTF-8 text, or None when the file is binary."""
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


# ─── Scanning ─────────────────────────────────────────────────────────────────


def _tokens_with_lines(text: str) -> list[tuple[str, int]]:
    """Normalized words paired with the line each came from."""
    tokens: list[tuple[str, int]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        tokens.extend((match.group(), number) for match in _WORD_RE.finditer(line.lower()))
    return tokens


def scan_text(text: str, digests: set[str], max_ngram: int = MAX_NGRAM) -> list[tuple[int, str]]:
    """Every (line, digest) pair where an n-gram of `text` hits the denylist.

    N-grams are built across line breaks on purpose: a two-word name wrapped
    over a line in prose is still the name.
    """
    tokens = _tokens_with_lines(text)
    total = len(tokens)
    hits: list[tuple[int, str]] = []
    for start in range(total):
        gram = ""
        for offset in range(min(max_ngram, total - start)):
            word, _ = tokens[start + offset]
            gram = word if offset == 0 else f"{gram} {word}"
            digest = hashlib.sha256(gram.encode("utf-8")).hexdigest()
            if digest in digests:
                hits.append((tokens[start][1], digest))
    return hits


def scan_tree(
    root: Path, denylist_path: Path, exceptions_path: Path | None = None
) -> list[Violation]:
    """Scan every scannable file under `root`, minus the frozen pre-rail footprint."""
    digests = load_denylist(denylist_path)
    violations: list[Violation] = []
    if not digests:
        return violations
    # The conventional locations are skipped whether or not they were passed in,
    # so a raw scan does not trip on the exception paths, which can name a term.
    control = (
        denylist_path,
        exceptions_path,
        root / DENYLIST_RELATIVE,
        root / EXCEPTIONS_RELATIVE,
    )
    for path in iter_scannable_files(root, *control):
        text = read_text(path)
        if text is None:
            continue
        violations.extend(
            Violation(path, line, digest) for line, digest in scan_text(text, digests)
        )
    if exceptions_path is None:
        return violations
    return apply_exceptions(violations, root, load_exceptions(exceptions_path))


# ─── Reporting ────────────────────────────────────────────────────────────────


def format_violation(violation: Violation, root: Path) -> str:
    """One report line. Names the location and the digest, never the term."""
    return (
        f"{relative_to_root(violation.path, root)}:{violation.line}: pack-boundary violation "
        f"(denylist entry sha256 {violation.digest})"
    )


# ─── Command line ─────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_pack_boundary.py",
        description=(
            "Fail when third-party framework vocabulary lands in repo content. "
            "Reports file and line plus the matching digest, never the term."
        ),
    )
    parser.add_argument(
        "--hash",
        metavar="TERM",
        help="Print the sha256 of TERM's normalized form and exit. Append it to the denylist.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Tree to scan (default: the repository this script lives in).",
    )
    parser.add_argument(
        "--denylist",
        type=Path,
        default=None,
        help=f"Denylist file (default: <root>/{DENYLIST_RELATIVE.as_posix()}).",
    )
    parser.add_argument(
        "--exceptions",
        type=Path,
        default=None,
        help=(
            "Frozen pre-rail footprint "
            f"(default: <root>/{EXCEPTIONS_RELATIVE.as_posix()} when it exists)."
        ),
    )
    parser.add_argument(
        "--freeze-exceptions",
        type=Path,
        metavar="PATH",
        default=None,
        help=(
            "Write the current hits to PATH as exception entries and exit 0. "
            "For recording a footprint that predates the rail. Adding an entry "
            "after that is a licensing decision, not a tooling step."
        ),
    )
    return parser


def _freeze(violations: Sequence[Violation], root: Path, destination: Path) -> None:
    """Record the current hits as (digest, path) exception entries."""
    entries = sorted({(v.digest, relative_to_root(v.path, root)) for v in violations})
    body = "\n".join(f"{digest} {location}" for digest, location in entries)
    destination.write_text(f"{body}\n" if body else "", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.hash is not None:
        print(hash_term(args.hash))
        words = len(normalize(args.hash).split())
        if words > MAX_NGRAM:
            # Only checkable while the plaintext is in hand, which is here and
            # nowhere else: the list stores digests, so an over-long entry is
            # indistinguishable from a good one once it has been written down.
            print(
                f"pack-boundary: warning, this term normalizes to {words} words. "
                f"The scanner checks up to {MAX_NGRAM}-grams, so this digest can never "
                "match and would sit on the denylist as dead weight. Use a distinctive "
                f"form of {MAX_NGRAM} words or fewer instead.",
                file=sys.stderr,
            )
        return 0

    root = args.root.resolve()
    denylist_path = (
        args.denylist if args.denylist is not None else root / DENYLIST_RELATIVE
    ).resolve()

    if not denylist_path.is_file():
        print(f"pack-boundary: denylist not found at {denylist_path}", file=sys.stderr)
        return 2

    exceptions_path: Path | None = None
    if args.exceptions is not None:
        exceptions_path = args.exceptions.resolve()
        if not exceptions_path.is_file():
            print(f"pack-boundary: exceptions not found at {exceptions_path}", file=sys.stderr)
            return 2
    elif (root / EXCEPTIONS_RELATIVE).is_file():
        exceptions_path = (root / EXCEPTIONS_RELATIVE).resolve()

    if args.freeze_exceptions is not None:
        destination = args.freeze_exceptions.resolve()
        try:
            raw = scan_tree(root, denylist_path)
        except ValueError as exc:
            print(f"pack-boundary: {exc}", file=sys.stderr)
            return 2
        _freeze(raw, root, destination)
        print(f"pack-boundary: froze {len(raw)} hit(s) into {destination}")
        return 0

    try:
        violations = scan_tree(root, denylist_path, exceptions_path)
    except ValueError as exc:
        print(f"pack-boundary: {exc}", file=sys.stderr)
        return 2

    if violations:
        print(
            f"pack-boundary: {len(violations)} violation(s). "
            "Third-party framework vocabulary belongs in an external pack, not in the repo.",
            file=sys.stderr,
        )
        for violation in violations:
            print(f"  {format_violation(violation, root)}", file=sys.stderr)
        return 1

    if exceptions_path is None:
        print("pack-boundary: clean.")
    else:
        frozen = sum(len(locations) for locations in load_exceptions(exceptions_path).values())
        # Printed so a shrinking footprint is visible in CI run history.
        print(f"pack-boundary: clean, {frozen} frozen exception(s) applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
