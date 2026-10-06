#!/usr/bin/env python3
"""Collect hosted GitHub Actions evidence for one immutable release commit."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"
SCHEMA_VERSION = 1
_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_TAG_RE = re.compile(r"^v[0-9][A-Za-z0-9.+-]*$")


@dataclass(frozen=True)
class WorkflowRequirement:
    name: str
    filename: str


REQUIRED_WORKFLOWS = (
    WorkflowRequirement("Source checks", "source-checks.yml"),
    WorkflowRequirement("Installed wheel smoke", "installed-wheel.yml"),
    WorkflowRequirement("Deployment smoke test", "deployment-smoke.yml"),
)
OPTIONAL_FULL_ASSET_WORKFLOW = WorkflowRequirement("Full-asset checks", "full-asset-checks.yml")


@dataclass(frozen=True)
class WorkflowRunEvidence:
    workflow: str
    workflow_file: str
    run_id: int
    run_number: int
    run_attempt: int
    event: str
    conclusion: str
    head_sha: str
    head_branch: str | None
    created_at: str
    updated_at: str
    url: str


class ReleaseEvidenceError(RuntimeError):
    """Raised when hosted CI evidence is missing, stale, or invalid."""


def validate_repository(value: str) -> str:
    repository = value.strip()
    if not _REPOSITORY_RE.fullmatch(repository):
        raise ReleaseEvidenceError("Repository must use the GitHub OWNER/REPO form")
    return repository


def validate_commit_sha(value: str) -> str:
    commit_sha = value.strip().lower()
    if not _SHA_RE.fullmatch(commit_sha):
        raise ReleaseEvidenceError("Release commit must be a full 40-character Git SHA")
    return commit_sha


def validate_tag(value: str) -> str:
    tag = value.strip()
    if not _TAG_RE.fullmatch(tag):
        raise ReleaseEvidenceError("Release tag must use the v<version> form")
    return tag


def _request_json(url: str, *, token: str | None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "InfinityDB-release-evidence",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ReleaseEvidenceError(
            f"GitHub API request failed with HTTP {exc.code}: {exc.reason}"
        ) from exc
    except (OSError, UnicodeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        raise ReleaseEvidenceError(f"Could not read GitHub Actions evidence: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseEvidenceError("GitHub Actions response was not a JSON object")
    return payload


def workflow_runs_url(repository: str, workflow_file: str, commit_sha: str) -> str:
    owner_repo = urllib.parse.quote(repository, safe="/")
    workflow = urllib.parse.quote(workflow_file, safe="")
    query = urllib.parse.urlencode(
        {
            "head_sha": commit_sha,
            "status": "completed",
            "per_page": 100,
        }
    )
    return f"{GITHUB_API_BASE}/repos/{owner_repo}/actions/workflows/{workflow}/runs?{query}"


def _required_int(run: dict[str, Any], key: str, *, workflow: str) -> int:
    value = run.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ReleaseEvidenceError(f"{workflow} run is missing integer field {key!r}")
    return value


def _required_str(run: dict[str, Any], key: str, *, workflow: str) -> str:
    value = run.get(key)
    if not isinstance(value, str) or not value:
        raise ReleaseEvidenceError(f"{workflow} run is missing string field {key!r}")
    return value


def select_latest_run(
    payload: dict[str, Any],
    *,
    requirement: WorkflowRequirement,
    commit_sha: str,
) -> WorkflowRunEvidence:
    raw_runs = payload.get("workflow_runs")
    if not isinstance(raw_runs, list):
        raise ReleaseEvidenceError(f"{requirement.name} response has no workflow_runs list")

    runs = [run for run in raw_runs if isinstance(run, dict) and run.get("head_sha") == commit_sha]
    if not runs:
        raise ReleaseEvidenceError(
            f"No completed {requirement.name} run exists for release commit {commit_sha}"
        )

    def sortable_int(value: object) -> int:
        return value if isinstance(value, int) and not isinstance(value, bool) else 0

    def run_order(run: dict[str, Any]) -> tuple[str, int, int]:
        return (
            str(run.get("updated_at") or ""),
            sortable_int(run.get("run_number")),
            sortable_int(run.get("run_attempt")),
        )

    latest = max(runs, key=run_order)
    conclusion = _required_str(latest, "conclusion", workflow=requirement.name)
    if conclusion != "success":
        run_url = latest.get("html_url")
        detail = f" ({run_url})" if isinstance(run_url, str) and run_url else ""
        raise ReleaseEvidenceError(
            f"Latest completed {requirement.name} run for {commit_sha} concluded "
            f"{conclusion!r}{detail}"
        )

    branch = latest.get("head_branch")
    if branch is not None and not isinstance(branch, str):
        raise ReleaseEvidenceError(f"{requirement.name} run has invalid head_branch")

    run_sha = _required_str(latest, "head_sha", workflow=requirement.name).lower()
    if run_sha != commit_sha:
        raise ReleaseEvidenceError(
            f"{requirement.name} run SHA {run_sha} does not match release commit {commit_sha}"
        )

    return WorkflowRunEvidence(
        workflow=requirement.name,
        workflow_file=requirement.filename,
        run_id=_required_int(latest, "id", workflow=requirement.name),
        run_number=_required_int(latest, "run_number", workflow=requirement.name),
        run_attempt=_required_int(latest, "run_attempt", workflow=requirement.name),
        event=_required_str(latest, "event", workflow=requirement.name),
        conclusion=conclusion,
        head_sha=run_sha,
        head_branch=branch,
        created_at=_required_str(latest, "created_at", workflow=requirement.name),
        updated_at=_required_str(latest, "updated_at", workflow=requirement.name),
        url=_required_str(latest, "html_url", workflow=requirement.name),
    )


def collect_release_evidence(
    repository: str,
    commit_sha: str,
    *,
    token: str | None = None,
    include_full_assets: bool = False,
) -> dict[str, Any]:
    repository = validate_repository(repository)
    commit_sha = validate_commit_sha(commit_sha)
    requirements = REQUIRED_WORKFLOWS + (
        (OPTIONAL_FULL_ASSET_WORKFLOW,) if include_full_assets else ()
    )
    workflows: list[dict[str, Any]] = []
    for requirement in requirements:
        payload = _request_json(
            workflow_runs_url(repository, requirement.filename, commit_sha),
            token=token,
        )
        evidence = select_latest_run(
            payload,
            requirement=requirement,
            commit_sha=commit_sha,
        )
        workflows.append(asdict(evidence))
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "commit_sha": commit_sha,
        "workflows": workflows,
    }


def render_tag_message(tag: str, evidence: dict[str, Any]) -> str:
    tag = validate_tag(tag)
    repository = evidence.get("repository")
    commit_sha = evidence.get("commit_sha")
    workflows = evidence.get("workflows")
    if not isinstance(repository, str) or not isinstance(commit_sha, str):
        raise ReleaseEvidenceError("Release evidence is missing repository/commit identity")
    if not isinstance(workflows, list):
        raise ReleaseEvidenceError("Release evidence does not contain a workflows list")
    names = {
        workflow.get("workflow")
        for workflow in workflows
        if isinstance(workflow, dict) and isinstance(workflow.get("workflow"), str)
    }
    missing = [
        requirement.name for requirement in REQUIRED_WORKFLOWS if requirement.name not in names
    ]
    if missing:
        raise ReleaseEvidenceError(
            "Release evidence is missing required workflows: " + ", ".join(missing)
        )

    lines = [
        f"InfinityDB {tag}",
        "",
        "Hosted CI evidence",
        f"Repository: {repository}",
        f"Commit: {commit_sha}",
    ]
    for workflow in workflows:
        if not isinstance(workflow, dict):
            raise ReleaseEvidenceError("Release evidence contains an invalid workflow entry")
        name = workflow.get("workflow")
        run_number = workflow.get("run_number")
        run_attempt = workflow.get("run_attempt")
        conclusion = workflow.get("conclusion")
        url = workflow.get("url")
        if not (
            isinstance(name, str)
            and isinstance(run_number, int)
            and isinstance(run_attempt, int)
            and isinstance(conclusion, str)
            and isinstance(url, str)
        ):
            raise ReleaseEvidenceError("Release evidence contains incomplete workflow metadata")
        lines.append(
            f"- {name}: {conclusion} (run {run_number}, attempt {run_attempt})"
        )
        lines.append(f"  {url}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify required hosted GitHub Actions runs for one release commit and prepare "
            "durable annotated-tag evidence."
        )
    )
    parser.add_argument("--repository", required=True, help="GitHub repository as OWNER/REPO")
    parser.add_argument("--commit", required=True, help="full 40-character release commit SHA")
    parser.add_argument("--tag", required=True, help="planned release tag, for example v0.10.0")
    parser.add_argument(
        "--json-output",
        type=Path,
        required=True,
        help="write machine-readable evidence JSON to this ignored/local path",
    )
    parser.add_argument(
        "--tag-message-output",
        type=Path,
        required=True,
        help="write the annotated Git tag message to this ignored/local path",
    )
    parser.add_argument(
        "--include-full-assets",
        action="store_true",
        help="also require a successful Full-asset checks run for the release commit",
    )
    return parser


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tag = validate_tag(args.tag)
        evidence = collect_release_evidence(
            args.repository,
            args.commit,
            token=os.environ.get("GITHUB_TOKEN"),
            include_full_assets=args.include_full_assets,
        )
        tag_message = render_tag_message(tag, evidence)
    except ReleaseEvidenceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    _write_text(
        args.json_output,
        json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )
    _write_text(args.tag_message_output, tag_message)
    print(
        "Hosted CI evidence verified for "
        f"{evidence['commit_sha']}: {len(evidence['workflows'])} required workflows"
    )
    print(f"Evidence JSON: {args.json_output}")
    print(f"Annotated-tag message: {args.tag_message_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
