"""Read-only InfinityDB development checkpoint from canonical sources.

No tests, Git writes, checkout synchronization, CI dispatch, or job control.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tools.check_v1_backlog import ROOT, _note_details, analyze_backlog, review_selection

MAX_RESPONSE = 1024 * 1024
QUEUE_ENTRY = re.compile(
    r"^- \[ \] (?P<id>V[DR]-\d{4}) "
    r"\((?P<date>\d{4}-\d{2}-\d{2}); (?P<status>[^)]+)\):\s*(?P<title>.*)$",
)
QUEUE_ID = re.compile(r"^- \[ \] V[DR]-\d{4}\b")
REPO_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
RUN_NAMES = ("Source checks", "Installed wheel smoke", "Deployment smoke test")
ACTIVE_JOB_STATES = frozenset({"running", "cancelling", "unverified"})


def git(*args: str, root: Path = ROOT, optional: bool = False) -> str | None:
    try:
        result = subprocess.run(
            ("git", "-C", str(root), *args), capture_output=True, text=True,
            check=False, timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if optional:
            return None
        raise ValueError(f"Git inspection unavailable: {exc}") from exc
    if result.returncode:
        if optional:
            return None
        raise ValueError(f"Git inspection failed: {(result.stderr or '')[:160].strip()}")
    if len(result.stdout) > MAX_RESPONSE:
        raise ValueError("Git output exceeds the size limit")
    return result.stdout.strip()


def checkout(root: Path = ROOT) -> dict:
    head = git("rev-parse", "--verify", "HEAD", root=root)
    branch = git("branch", "--show-current", root=root)
    changed = git("status", "--porcelain", "--untracked-files=normal", root=root)
    remote = git("config", "--get", "remote.origin.url", root=root, optional=True)
    assert isinstance(head, str) and isinstance(branch, str)
    assert isinstance(changed, str)
    return {
        "branch": branch or "(detached)",
        "head": head, "dirty": bool(changed),
        "changed_paths": changed.splitlines()[:50],
        "changed_paths_truncated": len(changed.splitlines()) > 50,
        "origin": remote,
    }


def github_repo(origin: str | None) -> str | None:
    if not origin:
        return None
    pattern = (
        r"(?:^|[/:@])github\.com[:/]"
        r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
    )
    match = re.search(pattern, origin)
    if match is None:
        return None
    repo = match.group("repo")
    return repo if REPO_NAME.fullmatch(repo) else None


def backlog(markdown: str) -> dict:
    analysis = analyze_backlog(markdown)
    errors = [item.message for item in analysis.diagnostics if item.severity == "error"]
    if errors:
        return {"status": "invalid", "diagnostics": errors, "next_actionable": None}
    open_tasks = sorted(
        (task for task in analysis.tasks if not task.checked),
        key=lambda task: int(task.task_id[4:]),
    )
    paused: list[str] = []
    suggested = None
    for task in open_tasks:
        kind = "Blocked" if task.blocked is not None else "Deferred"
        note = task.blocked if task.blocked is not None else task.deferred
        valid_pause = note is not None and not (
            task.blocked is not None and task.deferred is not None
        ) and _note_details(note, kind=kind)[1]
        if valid_pause:
            paused.append(task.task_id)
            continue
        review = review_selection(analysis, task.task_id)
        if not any(item.severity == "error" for item in review.diagnostics):
            suggested = task.task_id
            break
    return {
        "status": "ok", "active_task": None,
        "next_actionable": suggested, "open_count": len(open_tasks),
        "documented_pauses": paused,
        "note": (
            "No active assignment is tracked; next_actionable is advisory, "
            "not a selection gate."
        ),
    }


def queue(markdown: str, *, today: date | None = None) -> dict:
    today = today or date.today()
    rules = markdown.split("## Pending test design", 1)[0]
    thresholds = {}
    for name, pattern in (
        ("VD", r"\*\*(\d+)-requirement design threshold\*\*"),
        ("VR", r"\*\*(\d+)-change execution threshold\*\*"),
    ):
        match = re.search(pattern, rules)
        if match is None:
            raise ValueError(f"Cannot establish {name} threshold from queue rules")
        thresholds[name] = int(match.group(1))
    entries: dict[str, list[dict]] = {"VD": [], "VR": []}
    valid_statuses = {
        "VD": {"needs-design", "blocked"},
        "VR": {"awaiting-design", "ready-to-run", "blocked"},
    }
    sections = {
        "VD": ("## Pending test design", "## Pending deferred execution"),
        "VR": ("## Pending deferred execution", "## Next unused IDs"),
    }
    seen: set[str] = set()
    for kind, (begin, end) in sections.items():
        if markdown.count(begin) != 1 or markdown.count(end) != 1:
            raise ValueError(f"Missing or duplicate {kind} queue section")
        section = markdown.split(begin, 1)[1].split(end, 1)[0]
        for line in section.splitlines():
            if not QUEUE_ID.match(line):
                continue
            match = QUEUE_ENTRY.fullmatch(line)
            if match is None or not match["id"].startswith(kind):
                raise ValueError(f"Malformed {kind} queue entry: {line[:120]}")
            if match["status"] not in valid_statuses[kind]:
                raise ValueError(f"Invalid queue status for {match['id']}")
            if match["id"] in seen:
                raise ValueError(f"Duplicate queue ID {match['id']}")
            seen.add(match["id"])
            opened = date.fromisoformat(match["date"])
            entry = {
                "id": match["id"], "date": match["date"], "status": match["status"],
                "age_days": (today - opened).days, "title": match["title"].strip(),
            }
            entries[kind].append(entry)
    result = {}
    for kind, items in entries.items():
        items.sort(key=lambda item: int(item["id"][3:]))
        oldest = (
            max(items, key=lambda item: (item["age_days"], -int(item["id"][3:])))
            if items else None
        )
        eligible = (
            sum(item["status"] == "needs-design" for item in items)
            if kind == "VD" else len(items)
        )
        result[kind] = {
            "count": len(items), "threshold": thresholds[kind],
            "threshold_count": eligible,
            "threshold_due": eligible >= thresholds[kind],
            "oldest": oldest, "blocked": [
                item["id"] for item in items if item["status"] == "blocked"
            ],
            "age_due": [item["id"] for item in items if item["age_days"] >= 7],
            "entries": items,
        }
    return result


def fetch_json(url: str, *, timeout: float = 3, token: str | None = None) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "InfinityDB-dev-status"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers, method="GET")
    with urlopen(req, timeout=timeout) as response:
        content = response.read(MAX_RESPONSE + 1)
    if len(content) > MAX_RESPONSE:
        raise ValueError("Status response exceeds the size limit")
    value = json.loads(content)
    if not isinstance(value, dict):
        raise ValueError("Invalid status response")
    return value


def monitor(*, port: int = 8766) -> dict:
    try:
        payload = fetch_json(f"http://127.0.0.1:{port}/api/status", timeout=1.5)
        raw_jobs = payload["jobs"]
        workers = payload["workers"]
        if not isinstance(raw_jobs, list) or not isinstance(workers, list):
            raise ValueError("Malformed monitor payload")
        jobs = [
            {key: item.get(key) for key in (
                "job_id", "repository", "worker", "module", "status", "git_head",
                "elapsed_seconds",
            )}
            for item in raw_jobs if isinstance(item, dict)
            and isinstance(item.get("repository"), str)
            and (
                item["repository"] == "InfinityDB"
                or item["repository"].startswith("InfinityDB-agent-")
            )
            and item.get("status") in ACTIVE_JOB_STATES
            and item.get("module") not in {"git_operation", "git_sync"}
        ]
        return {
            "status": "ok", "generated_utc": payload.get("generated_utc"),
            "workers": workers, "active_jobs": jobs,
        }
    except (OSError, ValueError, KeyError, TypeError, HTTPError, URLError) as exc:
        return {"status": "unavailable", "reason": str(exc)[:200], "active_jobs": None}


def ci_status(head: str, repo: str | None) -> dict:
    if not repo:
        return {"status": "not_configured", "reason": "No supported GitHub origin"}
    url = (
        f"https://api.github.com/repos/{repo}/actions/runs?"
        + urlencode({"head_sha": head, "per_page": 100})
    )
    try:
        payload = fetch_json(
            url, timeout=4, token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"),
        )
        runs = payload["workflow_runs"]
        if not isinstance(runs, list):
            raise ValueError("Invalid workflow run list")
        if payload.get("total_count", 0) > len(runs):
            raise ValueError("Incomplete workflow list; refusing to infer missing checks")
        checks: dict[str, dict] = {}
        for name in RUN_NAMES:
            matching = [
                run for run in runs if isinstance(run, dict)
                and run.get("head_sha") == head and run.get("name") == name
            ]
            if not matching:
                checks[name] = {"status": "not_triggered", "run_id": None}
                continue
            latest = max(matching, key=lambda item: (item.get("id") or 0,
                                                      item.get("run_attempt") or 0))
            checks[name] = {
                "status": latest.get("status"), "conclusion": latest.get("conclusion"),
                "run_id": latest.get("id"), "url": latest.get("html_url"),
            }
        return {"status": "ok", "head": head, "repository": repo, "workflows": checks,
                "note": "Run-level only; required jobs/matrix legs need separate inspection."}
    except (OSError, ValueError, KeyError, TypeError, HTTPError, URLError) as exc:
        return {"status": "unavailable", "head": head,
                "reason": str(exc)[:200], "repository": repo}


def snapshot(root: Path = ROOT, *, online: bool = True, monitor_port: int = 8766) -> dict:
    current = checkout(root)
    todo = (root / "docs" / "TODO.md").read_text(encoding="utf-8")
    validation = (root / "docs" / "validation-queue.md").read_text(encoding="utf-8")
    repo = github_repo(current["origin"])
    return {
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "checkout": {key: value for key, value in current.items() if key != "origin"},
        "backlog": backlog(todo), "validation": queue(validation),
        "jobs": monitor(port=monitor_port) if online else {"status": "not_checked"},
        "ci": ci_status(current["head"], repo) if online else {"status": "not_checked"},
    }


def format_text(data: dict) -> str:
    checkout_info = data["checkout"]
    backlog_info = data["backlog"]
    lines = [
        f"InfinityDB dev status - {data['generated_utc']}",
        f"Checkout: {checkout_info['branch']} @ {checkout_info['head']}",
        f"Working tree: {'dirty' if checkout_info['dirty'] else 'clean'}",
        "Active task: not recorded; next actionable: "
        + str(backlog_info.get("next_actionable") or "unknown")
        + f" (open: {backlog_info.get('open_count', 'unknown')})",
    ]
    for kind in ("VD", "VR"):
        details = data["validation"][kind]
        oldest = details["oldest"]
        lines.append(
            f"{kind}: {details['count']}/{details['threshold']} threshold"
            + (" DUE" if details["threshold_due"] else "")
            + (f"; oldest {oldest['id']} ({oldest['age_days']}d)" if oldest else "")
            + (f"; age-due {', '.join(details['age_due'])}" if details["age_due"] else "")
            + (f"; blocked {', '.join(details['blocked'])}" if details["blocked"] else "")
        )
    jobs = data["jobs"]
    if jobs["status"] == "ok":
        lines.append(f"MCP test/script jobs: {len(jobs['active_jobs'])} active")
        for job in jobs["active_jobs"]:
            lines.append(
                f"  {job['job_id']} [{job['worker']}/{job['repository']}] "
                f"{job['module']} "
                f"{job['status']} @ {job['git_head'] or 'unknown SHA'}"
            )
    else:
        lines.append(f"MCP jobs: {jobs['status']} ({jobs.get('reason', 'not queried')})")
    ci = data["ci"]
    if ci["status"] == "ok":
        lines.append(f"GitHub CI (exact SHA {ci['head']}):")
        for name, details in ci["workflows"].items():
            lines.append(
                f"  {name}: {details['status']}"
                + (f" / {details['conclusion']}" if details.get("conclusion") else "")
                + (f" (run {details['run_id']})" if details.get("run_id") else "")
            )
        lines.append("CI is a run-level snapshot, not required-job or release acceptance.")
    else:
        lines.append(f"GitHub CI: {ci['status']} ({ci.get('reason', 'not queried')})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Machine-readable status")
    parser.add_argument("--offline", action="store_true", help="Skip MCP and GitHub requests")
    parser.add_argument("--monitor-port", type=int, default=8766,
                        help="Loopback MCP monitor port (default: 8766)")
    args = parser.parse_args(argv)
    if not 1 <= args.monitor_port <= 65535:
        parser.error("--monitor-port must be 1-65535")
    try:
        result = snapshot(online=not args.offline, monitor_port=args.monitor_port)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"dev-status: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json
          else format_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
