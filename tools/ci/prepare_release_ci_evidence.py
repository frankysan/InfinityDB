#!/usr/bin/env python3
"""Collect hosted GitHub Actions evidence for one immutable release commit."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.ci.release_metadata import ROOT as RELEASE_ROOT
from tools.ci.release_metadata import check_repository

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
CROSS_BROWSER_WORKFLOW = WorkflowRequirement(
    "Cross-browser compatibility", "cross-browser-compatibility.yml"
)
CROSS_BROWSER_JOBS = (
    "ubuntu-latest / chromium",
    "ubuntu-latest / firefox",
    "macos-latest / webkit",
    "windows-latest / msedge",
)
SOURCE_FAST_JOB = "Fast validation and scope"
SOURCE_PINNED_JOBS = (
    "Pinned determinism / ubuntu-24.04",
    "Pinned determinism / ubuntu-26.04",
)
SOURCE_FULL_JOBS = (
    "ubuntu-latest / Python 3.11",
    "windows-latest / Python 3.11",
    "macos-latest / Python 3.11",
    "ubuntu-latest / Python 3.14",
    *SOURCE_PINNED_JOBS,
    "Cross-platform deterministic outputs",
)


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


class ReusedReleaseEvidence(ReleaseEvidenceError):
    """A successful main job reused candidate checks; verify their original evidence."""


def validate_repository(value: str) -> str:
    repository = value.strip()
    if not _REPOSITORY_RE.fullmatch(repository):
        raise ReleaseEvidenceError("Repository must use the GitHub OWNER/REPO form")
    return repository


def requires_cross_browser(tag: str) -> bool:
    """Preserve the v1.0.x release contract; later releases opt in by risk."""
    valid = validate_tag(tag)
    match = re.match(r"^v([0-9]+)(?:\.([0-9]+))?", valid)
    if match is None:
        raise ReleaseEvidenceError("Invalid release tag version")
    major, minor = match.groups()
    return int(major) == 1 and (minor is None or int(minor) == 0)


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


def verify_release_metadata_for_tag(tag: str, commit_sha: str) -> None:
    """Final-tag guard for the exact checkout, not routine PR validation."""
    tag = validate_tag(tag)
    commit_sha = validate_commit_sha(commit_sha)
    try:
        head = subprocess.run(
            ("git", "rev-parse", "HEAD"), cwd=RELEASE_ROOT,
            capture_output=True, text=True, check=False, timeout=8,
        )
        if head.returncode or head.stdout.strip().lower() != commit_sha:
            raise ReleaseEvidenceError(
                "Release checkout HEAD does not match the verified release SHA"
            )
        problems = check_repository()
        if problems:
            raise ReleaseEvidenceError(
                "Release metadata is not finalized: " + "; ".join(problems)
            )
        with (RELEASE_ROOT / "pyproject.toml").open("rb") as handle:
            version = tomllib.load(handle)["project"]["version"]
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        raise ReleaseEvidenceError(f"Could not verify local release metadata: {exc}") from exc
    if tag != f"v{version}":
        raise ReleaseEvidenceError(
            f"Release tag {tag} does not match packaged version {version}"
        )


def _request_payload(url: str, *, token: str | None) -> Any:
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
    return payload


def _request_json(url: str, *, token: str | None) -> dict[str, Any]:
    payload = _request_payload(url, token=token)
    if not isinstance(payload, dict):
        raise ReleaseEvidenceError("GitHub response was not a JSON object")
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


def cross_browser_jobs_url(repository: str, run_id: int) -> str:
    owner_repo = urllib.parse.quote(repository, safe="/")
    return (
        f"{GITHUB_API_BASE}/repos/{owner_repo}/actions/runs/{run_id}/jobs"
        "?per_page=100&filter=latest"
    )


def verify_cross_browser_jobs(payload: dict[str, Any], *, run_id: int) -> list[dict[str, Any]]:
    """Reject missing, skipped, failed, duplicated or incomplete browser matrix legs."""
    jobs = payload.get("jobs")
    total = payload.get("total_count")
    if not isinstance(jobs, list) or type(total) is not int or len(jobs) != total:
        raise ReleaseEvidenceError("Cross-browser jobs response is incomplete")
    names = [job.get("name") for job in jobs if isinstance(job, dict)]
    if len(names) != len(jobs) or len(names) != len(CROSS_BROWSER_JOBS) or set(names) != set(
        CROSS_BROWSER_JOBS
    ):
        raise ReleaseEvidenceError("Cross-browser jobs are missing, unexpected or duplicated")
    result = []
    for job in jobs:
        name = job["name"]
        if job.get("run_id") != run_id or job.get("status") != "completed" or (
            job.get("conclusion") != "success"
        ):
            raise ReleaseEvidenceError(f"Cross-browser job {name!r} did not pass completely")
        result.append({
            "name": name,
            "id": _required_int(job, "id", workflow=name),
            "run_id": run_id,
            "status": "completed",
            "conclusion": "success",
            "url": _required_str(job, "html_url", workflow=name),
        })
    return sorted(result, key=lambda job: CROSS_BROWSER_JOBS.index(job["name"]))


def _passed_step(job: dict[str, Any], name: str) -> bool:
    steps = job.get("steps")
    return isinstance(steps, list) and any(
        isinstance(step, dict)
        and step.get("name") == name
        and step.get("conclusion") == "success"
        for step in steps
    )


def verify_smoke_job(
    payload: dict[str, Any], evidence: WorkflowRunEvidence, *, require_pr_candidate: bool,
) -> None:
    """Require actual smoke execution, not a main-push reuse acknowledgment."""
    job_name, step_name = (
        ("installed-wheel", "Validate installed wheel outside checkout")
        if evidence.workflow_file == "installed-wheel.yml"
        else ("deployment-smoke", "Validate image and production startup")
    )
    jobs = payload.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 1 or payload.get("total_count") != 1:
        raise ReleaseEvidenceError(f"{evidence.workflow} job response is incomplete")
    job = jobs[0]
    if (
        not isinstance(job, dict) or job.get("name") != job_name
        or job.get("run_id") != evidence.run_id or job.get("status") != "completed"
        or job.get("conclusion") != "success"
    ):
        raise ReleaseEvidenceError(f"{evidence.workflow} job did not pass completely")
    if not _passed_step(job, step_name):
        if _passed_step(job, "Verify identical merged PR evidence"):
            raise ReusedReleaseEvidence(f"{evidence.workflow} reused merged PR evidence")
        raise ReleaseEvidenceError(f"{evidence.workflow} did not execute smoke checks")
    if require_pr_candidate and not _passed_step(job, "Check out exact candidate"):
        raise ReleaseEvidenceError(f"{evidence.workflow} PR lacks exact candidate checkout")


def verify_source_jobs(payload: dict[str, Any], *, run_id: int) -> dict[str, str]:
    """Distinguish full Source coverage from justified, focused reuse."""
    jobs = payload.get("jobs")
    total = payload.get("total_count")
    if not isinstance(jobs, list) or type(total) is not int or len(jobs) != total:
        raise ReleaseEvidenceError("Source jobs response is incomplete")
    by_name = {
        job.get("name"): job for job in jobs
        if isinstance(job, dict) and isinstance(job.get("name"), str)
    }
    expected = set(SOURCE_FULL_JOBS)
    has_fast = SOURCE_FAST_JOB in by_name
    if len(by_name) != len(jobs) or set(by_name) != (
        expected | {SOURCE_FAST_JOB} if has_fast else expected
    ):
        raise ReleaseEvidenceError("Source matrix jobs are missing, unexpected or duplicated")
    if any(job.get("run_id") != run_id for job in jobs):
        raise ReleaseEvidenceError("Source matrix contains jobs from a different run")
    if any(job.get("status") != "completed" for job in jobs):
        raise ReleaseEvidenceError("Source matrix contains nonterminal jobs")
    if has_fast and by_name[SOURCE_FAST_JOB].get("conclusion") != "success":
        raise ReleaseEvidenceError("Source fast-validation job did not pass")
    if any(by_name[name].get("conclusion") != "success" for name in SOURCE_FULL_JOBS):
        raise ReleaseEvidenceError("Source matrix contains incomplete or failed jobs")
    if not has_fast:
        return {"mode": "full"}

    reuse = [
        _passed_step(
            by_name[name],
            "Reuse validated determinism baseline"
            if name in SOURCE_PINNED_JOBS
            else (
                "Reuse validated deterministic baseline"
                if name == "Cross-platform deterministic outputs"
                else "Reuse validated Source baseline"
            ),
        )
        for name in SOURCE_FULL_JOBS
    ]
    if all(reuse):
        if not _passed_step(
            by_name[SOURCE_FAST_JOB], "Run changed tests with verified baseline"
        ):
            if _passed_step(by_name[SOURCE_FAST_JOB], "Verify identical merged PR evidence"):
                raise ReusedReleaseEvidence("Source reused merged PR evidence")
            raise ReleaseEvidenceError("Scoped Source run lacks successful focused tests")
        return {"mode": "focused", "basis": "verified hosted baseline"}
    if any(reuse):
        raise ReleaseEvidenceError("Source matrix mixed full and reused jobs")
    for name in SOURCE_FULL_JOBS:
        expected_step = (
            "Build canonical deterministic-output manifest"
            if name in SOURCE_PINNED_JOBS
            else (
                "Compare artifact hashes"
                if name == "Cross-platform deterministic outputs"
                else "Run source checks"
            )
        )
        if not _passed_step(by_name[name], expected_step):
            raise ReleaseEvidenceError(f"Full Source job {name!r} did not run checks")
    return {"mode": "full"}


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
    if latest.get("status") != "completed":
        raise ReleaseEvidenceError(f"Latest {requirement.name} run is not completed")
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
    include_cross_browser: bool = False,
    require_pr_candidate: bool = False,
) -> dict[str, Any]:
    repository = validate_repository(repository)
    commit_sha = validate_commit_sha(commit_sha)
    requirements = REQUIRED_WORKFLOWS + (
        (CROSS_BROWSER_WORKFLOW,) if include_cross_browser else ()
    ) + (
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
        entry = asdict(evidence)
        if require_pr_candidate and requirement in REQUIRED_WORKFLOWS:
            if evidence.event != "pull_request":
                raise ReleaseEvidenceError(f"{requirement.name} is not candidate PR evidence")
        if requirement == REQUIRED_WORKFLOWS[0]:
            source_jobs = _request_json(
                cross_browser_jobs_url(repository, evidence.run_id), token=token,
            )
            entry["source_validation"] = verify_source_jobs(
                source_jobs, run_id=evidence.run_id,
            )
            if require_pr_candidate:
                fast = next(
                    (job for job in source_jobs["jobs"] if job["name"] == SOURCE_FAST_JOB), {}
                )
                if not _passed_step(fast, "Check out exact candidate"):
                    raise ReleaseEvidenceError("Source PR did not verify exact candidate checkout")
        if requirement in REQUIRED_WORKFLOWS[1:]:
            job_payload = _request_json(
                cross_browser_jobs_url(repository, evidence.run_id), token=token,
            )
            verify_smoke_job(job_payload, evidence, require_pr_candidate=require_pr_candidate)
        if requirement == CROSS_BROWSER_WORKFLOW:
            job_payload = _request_json(
                cross_browser_jobs_url(repository, evidence.run_id), token=token,
            )
            entry["jobs"] = verify_cross_browser_jobs(job_payload, run_id=evidence.run_id)
        workflows.append(entry)
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "commit_sha": commit_sha,
        "workflows": workflows,
    }


def _commit_tree(repository: str, sha: str, token: str | None) -> str:
    commit = _request_json(
        f"{GITHUB_API_BASE}/repos/{repository}/git/commits/{sha}", token=token,
    )
    tree = commit.get("tree")
    tree_sha = tree.get("sha") if isinstance(tree, dict) else None
    if commit.get("sha") != sha or not isinstance(tree_sha, str) or not _SHA_RE.fullmatch(tree_sha):
        raise ReleaseEvidenceError("GitHub did not return the exact commit and tree identity")
    return tree_sha.lower()


def collect_identical_merge_evidence(
    repository: str, final_sha: str, *,
    candidate_sha: str | None = None,
    token: str | None = None,
    include_full_assets: bool = False,
    include_cross_browser: bool = False,
) -> dict[str, Any]:
    """Reuse only the actual same-repository PR head merged into main."""
    repository = validate_repository(repository)
    final_sha = validate_commit_sha(final_sha)
    if candidate_sha is not None:
        candidate_sha = validate_commit_sha(candidate_sha)
    prs = _request_payload(
        f"{GITHUB_API_BASE}/repos/{repository}/commits/{final_sha}/pulls?per_page=100",
        token=token,
    )
    if not isinstance(prs, list) or len(prs) >= 100:
        raise ReleaseEvidenceError("Associated pull requests are unavailable or incomplete")
    matches = []
    for pr in prs:
        if not isinstance(pr, dict):
            raise ReleaseEvidenceError("Invalid associated pull request")
        base, head = pr.get("base"), pr.get("head")
        if not isinstance(base, dict) or not isinstance(head, dict):
            continue
        base_repo, head_repo = base.get("repo"), head.get("repo")
        if (
            pr.get("state") == "closed" and pr.get("merged_at")
            and pr.get("merge_commit_sha") == final_sha and base.get("ref") == "main"
            and isinstance(base_repo, dict) and isinstance(head_repo, dict)
            and base_repo.get("full_name") == head_repo.get("full_name") == repository
        ):
            matches.append(pr)
    if len(matches) != 1:
        raise ReleaseEvidenceError("No unique same-repository PR merged into main at this SHA")
    pr = matches[0]
    head_sha = validate_commit_sha(_required_str(pr["head"], "sha", workflow="Merged PR"))
    if head_sha == final_sha or (candidate_sha is not None and candidate_sha != head_sha):
        raise ReleaseEvidenceError("Approved candidate does not match the distinct merged PR head")
    final_tree = _commit_tree(repository, final_sha, token)
    if _commit_tree(repository, head_sha, token) != final_tree:
        raise ReleaseEvidenceError("Candidate and final main Git trees differ")
    evidence = collect_release_evidence(
        repository, head_sha, token=token, include_full_assets=include_full_assets,
        include_cross_browser=include_cross_browser, require_pr_candidate=True,
    )
    return {
        **evidence,
        "commit_sha": final_sha,
        "identical_merge": {
            "candidate_sha": head_sha,
            "final_sha": final_sha,
            "tree_sha": final_tree,
            "pull_request": _required_int(pr, "number", workflow="Merged PR"),
        },
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
    require_browser = requires_cross_browser(tag)
    required = REQUIRED_WORKFLOWS + ((CROSS_BROWSER_WORKFLOW,) if require_browser else ())
    missing = [requirement.name for requirement in required if requirement.name not in names]
    if missing:
        raise ReleaseEvidenceError(
            "Release evidence is missing required workflows: " + ", ".join(missing)
        )
    if require_browser or CROSS_BROWSER_WORKFLOW.name in names:
        browser = next(
            item for item in workflows
            if isinstance(item, dict) and item.get("workflow") == CROSS_BROWSER_WORKFLOW.name
        )
        jobs = browser.get("jobs")
        if not isinstance(jobs, list):
            raise ReleaseEvidenceError("Cross-browser release evidence is missing matrix jobs")
        verify_cross_browser_jobs(
            {"jobs": [dict(job, html_url=job.get("url")) for job in jobs
                      if isinstance(job, dict)], "total_count": len(jobs)},
            run_id=_required_int(browser, "run_id", workflow=CROSS_BROWSER_WORKFLOW.name),
        )

    lines = [
        f"InfinityDB {tag}",
        "",
        "Hosted CI evidence",
        f"Repository: {repository}",
        f"Commit: {commit_sha}",
    ]
    merge = evidence.get("identical_merge")
    if merge is not None:
        if not isinstance(merge, dict) or merge.get("final_sha") != commit_sha:
            raise ReleaseEvidenceError("Invalid identical merge release identity")
        candidate = validate_commit_sha(_required_str(merge, "candidate_sha", workflow="Merge"))
        tree = validate_commit_sha(_required_str(merge, "tree_sha", workflow="Merge"))
        pr = _required_int(merge, "pull_request", workflow="Merge")
        lines.extend([
            f"Identical-tree reuse: PR #{pr}",
            f"Validated candidate: {candidate}",
            f"Shared Git tree: {tree}",
        ])
    for workflow in workflows:
        if not isinstance(workflow, dict):
            raise ReleaseEvidenceError("Release evidence contains an invalid workflow entry")
        if merge is not None and workflow.get("head_sha") != merge["candidate_sha"]:
            raise ReleaseEvidenceError("Reused workflow SHA does not match candidate")
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
        scope = workflow.get("source_validation") if name == "Source checks" else None
        suffix = (
            " [focused; verified hosted baseline]"
            if isinstance(scope, dict) and scope.get("mode") == "focused" else ""
        )
        lines.append(
            f"- {name}: {conclusion} (run {run_number}, attempt {run_attempt}){suffix}"
        )
        if merge is not None:
            lines.append(f"  Validated SHA: {workflow['head_sha']}")
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
        "--candidate", help="approved pre-merge SHA; require verified identical-tree reuse",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="verify candidate CI and metadata without writing release evidence (pre-merge)",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="write new machine-readable evidence JSON (required unless --check-only)",
    )
    parser.add_argument(
        "--tag-message-output",
        type=Path,
        help="write a new annotated Git tag message (required unless --check-only)",
    )
    parser.add_argument(
        "--include-full-assets",
        action="store_true",
        help="also require a successful Full-asset checks run for the release commit",
    )
    parser.add_argument(
        "--include-cross-browser",
        action="store_true",
        help="also require all four browser-matrix jobs (optional from v1.1)",
    )
    return parser


def _check_fresh_outputs(json_output: Path, tag_output: Path) -> None:
    """Guard both immutable release records before work or publication."""
    if json_output.resolve() == tag_output.resolve():
        raise ReleaseEvidenceError("Release evidence outputs must be different files")
    for path in (json_output, tag_output):
        if path.exists() or path.is_symlink():
            raise ReleaseEvidenceError(f"Release evidence output already exists: {path}")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against another writer racing preflight.
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if not args.check_only:
            if args.json_output is None or args.tag_message_output is None:
                raise ReleaseEvidenceError(
                    "Both evidence output paths are required unless --check-only is selected"
                )
            _check_fresh_outputs(args.json_output, args.tag_message_output)
        tag = validate_tag(args.tag)
        options = {
            "token": os.environ.get("GITHUB_TOKEN"),
            "include_full_assets": args.include_full_assets,
            "include_cross_browser": requires_cross_browser(tag) or args.include_cross_browser,
        }
        if args.candidate:
            evidence = collect_identical_merge_evidence(
                args.repository, args.commit, candidate_sha=args.candidate, **options,
            )
        else:
            evidence = collect_release_evidence(args.repository, args.commit, **options)
        tag_message = render_tag_message(tag, evidence)
        verify_release_metadata_for_tag(tag, args.commit)
        if not args.check_only:
            # Hosted lookup may be slow; recheck both outputs before any write.
            _check_fresh_outputs(args.json_output, args.tag_message_output)
            _write_text(
                args.json_output,
                json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            )
            _write_text(args.tag_message_output, tag_message)
    except (ReleaseEvidenceError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "Hosted CI evidence verified for "
        f"{evidence['commit_sha']}: {len(evidence['workflows'])} required workflows"
    )
    if args.check_only:
        print("Pre-merge release evidence check passed; no files written.")
    else:
        print(f"Evidence JSON: {args.json_output}")
        print(f"Annotated-tag message: {args.tag_message_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
