"""Fail-closed, change-aware Source CI with verified baseline reuse.

Only documentation and independent test-module edits can reuse a previously
successful complete release matrix. Browser, wheel and Docker remain separate.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from tools.prepare_release_ci_evidence import (
    ReleaseEvidenceError,
    collect_release_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"^[0-9a-f]{40}$")
TEST_PATH = re.compile(r"^tests/test_[A-Za-z0-9_]+\.py$")
METADATA = frozenset({"README.md", "docs/CHANGELOG.md", "THIRD_PARTY_NOTICES.md"})
RELEASE_WEB_TEST = "tests/test_web.py::test_changes_page_renders_canonical_release_history"


@dataclass(frozen=True)
class ChangeScope:
    full: bool
    reason: str
    test_targets: tuple[str, ...]


def classify_paths(paths: list[str]) -> ChangeScope:
    """Unknown, shared-fixture, runtime and build changes always require full CI."""
    if not paths:
        return ChangeScope(True, "empty change range", ())
    tests: set[str] = set()
    for path in paths:
        if path in METADATA or path == "AGENTS.md":
            continue
        if path.startswith("docs/") and path.endswith(".md"):
            continue
        if TEST_PATH.fullmatch(path):
            if not (ROOT / path).is_file():
                return ChangeScope(True, f"removed test module: {path}", ())
            tests.add(path)
            continue
        return ChangeScope(True, f"broad or unknown change: {path}", ())
    tests.add("tests/test_release_metadata.py")
    tests.add("tests/test_release_notes.py")
    if "tests/test_web.py" not in tests:
        tests.add(RELEASE_WEB_TEST)
    return ChangeScope(False, "documentation/test-only delta", tuple(sorted(tests)))


def changed_paths(base: str, head: str = "HEAD") -> list[str]:
    """NUL-delimited Git diff; both sides of renames remain observable."""
    result = subprocess.run(
        ("git", "diff", "--name-only", "--no-renames", "-z", base, head),
        cwd=ROOT, capture_output=True, check=True,
    )
    return sorted(p.decode("utf-8") for p in result.stdout.split(b"\0") if p)


def baseline_is_valid(repository: str, sha: str, token: str | None) -> bool:
    """Require successful Source, wheel, deployment and all four browser jobs."""
    if SHA.fullmatch(sha) is None:
        return False
    try:
        collect_release_evidence(
            repository, sha, token=token, include_cross_browser=True,
        )
    except (ReleaseEvidenceError, OSError, ValueError):
        return False
    return True


def plan_validation(
    paths: list[str], *, repository: str, base_sha: str, token: str | None,
) -> ChangeScope:
    scope = classify_paths(paths)
    if scope.full:
        return scope
    if not baseline_is_valid(repository, base_sha, token):
        return ChangeScope(True, "baseline has no complete hosted release evidence", ())
    return scope


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)
    scope = ChangeScope(True, "missing or unverified base", ())
    try:
        if SHA.fullmatch(args.base.lower()):
            subprocess.run(
                ("git", "merge-base", "--is-ancestor", args.base, args.head),
                cwd=ROOT, capture_output=True, check=True,
            )
            scope = plan_validation(
                changed_paths(args.base, args.head),
                repository=args.repository, base_sha=args.base.lower(),
                token=os.environ.get("GH_TOKEN"),
            )
    except (OSError, subprocess.CalledProcessError, UnicodeError):
        scope = ChangeScope(True, "Git ancestry or diff unavailable", ())
    full = "true" if scope.full else "false"
    print(f"Source-validation scope: full={full}; {scope.reason}")
    if not scope.full:
        print(f"Reused fully validated baseline: {args.base.lower()}")
    if args.github_output is not None:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"full={full}\n")
            output.write(f"test_targets={' '.join(scope.test_targets)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
