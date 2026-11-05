"""Event-scoped, read-only V1S retirement check for hosted Source CI.

Static checks are part of the regular documentation stage. This helper selects
an auditable Git range; it never assumes that the PR merge ref is first-parent
history of the PR branch, nor silently treats a missing baseline as clean.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.check_v1_backlog import ROOT, _git, analyze_backlog, audit_retirements

# First tested adoption commit for Git-aware retirement and selection checks.
ADOPTION_BASE = "0bac336999d102fe94a3bcadbeec83eca1ae7788"
SHA = re.compile(r"[0-9a-f]{40}")


@dataclass(frozen=True)
class AuditRange:
    base: str
    target: str
    origin: str
    complete: bool


def _valid_sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA.fullmatch(value) is None:
        raise ValueError(f"missing or invalid {field} SHA")
    return value


def _first_parent(repository: Path, target: str) -> list[str]:
    revisions = _git(repository, "rev-list", "--first-parent", target).splitlines()
    if not revisions or len(revisions) > 5000:
        raise ValueError("target first-parent history is empty or exceeds 5000 commits")
    return revisions


def choose_ci_range(
    event_name: str, event: dict[str, Any], checkout_head: str, *,
    repository: Path = ROOT, adoption_base: str = ADOPTION_BASE,
) -> AuditRange:
    """Choose a bounded, first-parent-compatible audit range.

    PR: earliest shared first-parent revision, narrowed to the adopted checker
    baseline where it is later. Push: the explicit previous SHA (no force
    assumption). Manual: explicit baseline, otherwise adoption or one commit
    with an *incomplete* label. The caller must expose the coverage level.
    """
    current = _valid_sha(checkout_head, "checkout")
    if event_name == "pull_request":
        pr = event.get("pull_request")
        if not isinstance(pr, dict):
            raise ValueError("pull_request event has no PR object")
        head = pr.get("head")
        base = pr.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise ValueError("pull_request is missing head/base objects")
        target = _valid_sha(head.get("sha"), "PR head")
        base_sha = _valid_sha(base.get("sha"), "PR base")
        first_parent = _first_parent(repository, target)
        base_revisions = set(_git(repository, "rev-list", base_sha).splitlines())
        shared = next((rev for rev in first_parent if rev in base_revisions), None)
        if shared is None:
            raise ValueError("no shared first-parent baseline for PR")
        if adoption_base in first_parent and (
            first_parent.index(adoption_base) < first_parent.index(shared)
        ):
            shared = adoption_base
        return AuditRange(shared, target, "pull_request", True)

    if event_name == "push":
        target = _valid_sha(event.get("after"), "push after")
        before = _valid_sha(event.get("before"), "push before")
        if target != current:
            raise ValueError("push target is not the checked-out commit")
        if before not in _first_parent(repository, target):
            raise ValueError("push before SHA is not in first-parent history")
        return AuditRange(before, target, "push", True)

    if event_name == "workflow_dispatch":
        inputs = event.get("inputs") or {}
        if not isinstance(inputs, dict):
            raise ValueError("manual dispatch inputs must be an object")
        explicit = inputs.get("backlog_base")
        if explicit:
            base = _valid_sha(explicit, "manual backlog base")
            if base not in _first_parent(repository, current):
                raise ValueError("manual baseline is not in first-parent history")
            return AuditRange(base, current, "manual-explicit", True)
        history = _first_parent(repository, current)
        if adoption_base in history:
            return AuditRange(adoption_base, current, "manual-adoption", True)
        # Old branches/main before adoption still get a bounded objective
        # check. Never label that single-commit coverage as full closeout.
        return AuditRange(history[1] if len(history) > 1 else current,
                          current, "manual-last-commit", False)

    raise ValueError(f"unsupported GitHub event {event_name!r}")


def _event_document(environ: Mapping[str, str]) -> dict[str, Any]:
    path = Path(environ.get("GITHUB_EVENT_PATH", ""))
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("GitHub event file is missing or exceeds 1 MiB")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("GitHub event file cannot be parsed") from exc
    if not isinstance(parsed, dict):
        raise ValueError("GitHub event must contain an object")
    return parsed


def main(environ: Mapping[str, str] | None = None, *, repository: Path = ROOT) -> int:
    environment = os.environ if environ is None else environ
    try:
        audit_range = choose_ci_range(
            environment.get("GITHUB_EVENT_NAME", ""),
            _event_document(environment),
            environment.get("GITHUB_SHA", ""),
            repository=repository,
        )
        markdown = _git(repository, "show", f"{audit_range.target}:docs/TODO.md")
        analysis = analyze_backlog(
            markdown, source=f"{audit_range.target[:12]}:docs/TODO.md",
        )
        if any(d.severity == "error" for d in analysis.diagnostics):
            raise ValueError("target V1S backlog has structural errors")
        diagnostics = audit_retirements(
            audit_range.base, audit_range.target,
            repository=repository, enforce=True,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"V1S CI retirement check: SETUP ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        f"V1S CI retirement check: {audit_range.origin} "
        f"{audit_range.base[:12]}..{audit_range.target[:12]} "
        f"({'complete selected range' if audit_range.complete else 'last commit only'})"
    )
    if not audit_range.complete:
        print("WARNING: manual run predates the adopted baseline; "
              "supply backlog_base to audit the intended history.")
    for diagnostic in diagnostics:
        print(
            f"{diagnostic.source}:{diagnostic.line}: "
            f"{diagnostic.severity} {diagnostic.code}: {diagnostic.message}"
        )
    errors = sum(item.severity == "error" for item in diagnostics)
    warnings = sum(item.severity == "warning" for item in diagnostics)
    print(
        f"V1S CI retirement: {'FAIL' if errors else 'PASS'} "
        f"({errors} errors, {warnings} warnings; "
        f"{'complete' if audit_range.complete else 'limited'} history)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
