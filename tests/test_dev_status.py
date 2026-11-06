from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from tools import dev_status

BACKLOG = """# Backlog
### Pre-planned 1.0 execution slices
#### First workstream
- [ ] **V1S-041 (S, review):** Waiting for a primary source.
  Blocked: Source is unavailable; owner: curator; retry: when received.
- [ ] **V1S-045 (S, review):** Deferred until the source freeze.
  Deferred: Needs frozen inputs; owner: release owner; revisit: after freeze.
#### Current workstream
- [ ] **V1S-082 (L, gate):** Current source review.
"""

QUEUE = """# Queue
Rules use the **3-requirement design threshold** and **5-change execution threshold**.

## Pending test design
- [ ] VD-0001 (2026-10-28; needs-design): Older design.
- [ ] VD-0002 (2026-11-05; blocked): Blocked design.

## Pending deferred execution
- [ ] VR-0001 (2026-10-28; ready-to-run): Older execution.
- [ ] VR-0002 (2026-11-05; awaiting-design): New execution.

## Next unused IDs
Design: VD-0003
Execution: VR-0003
"""


def test_backlog_skips_documented_pauses_and_recommends_next_actionable() -> None:
    result = dev_status.backlog(BACKLOG)

    assert result["status"] == "ok"
    assert result["open_count"] == 3
    assert result["documented_pauses"] == ["V1S-041", "V1S-045"]
    assert result["next_actionable"] == "V1S-082"
    assert "advisory" in result["note"]


def test_backlog_reports_invalid_input_without_recommending_work() -> None:
    duplicate = BACKLOG + "- [ ] **V1S-082 (L, gate):** Duplicate.\n"

    result = dev_status.backlog(duplicate)

    assert result["status"] == "invalid"
    assert result["diagnostics"]
    assert result["next_actionable"] is None


def test_queue_excludes_blocked_designs_from_threshold_and_reports_aging() -> None:
    result = dev_status.queue(QUEUE, today=date(2026, 11, 6))

    assert result["VD"]["count"] == 2
    assert result["VD"]["threshold_count"] == 1
    assert not result["VD"]["threshold_due"]
    assert result["VD"]["blocked"] == ["VD-0002"]
    assert result["VD"]["age_due"] == ["VD-0001"]
    assert result["VR"]["age_due"] == ["VR-0001"]


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("- [ ] VD-0001 (2026-11-05; blocked): Duplicate.", "Duplicate queue ID"),
        ("- [ ] VD-0002 (2026-11-05; unknown): Invalid status.", "Invalid queue status"),
    ],
)
def test_queue_rejects_duplicate_ids_and_invalid_statuses(
    replacement: str, message: str,
) -> None:
    invalid = QUEUE.replace(
        "- [ ] VD-0002 (2026-11-05; blocked): Blocked design.",
        replacement,
    )

    with pytest.raises(ValueError, match=message):
        dev_status.queue(invalid, today=date(2026, 11, 6))


def test_queue_reports_threshold_when_unblocked_designs_reach_limit() -> None:
    queue_text = QUEUE.replace(
        "- [ ] VD-0002 (2026-11-05; blocked): Blocked design.",
        "- [ ] VD-0002 (2026-11-05; needs-design): Second.\n"
        "- [ ] VD-0003 (2026-11-05; needs-design): Third.",
    )

    result = dev_status.queue(queue_text, today=date(2026, 11, 6))

    assert result["VD"]["count"] == 3
    assert result["VD"]["threshold_count"] == 3
    assert result["VD"]["threshold_due"]


@pytest.mark.parametrize(
    ("origin", "expected"),
    [
        ("https://github.com/frankysan/InfinityDB.git", "frankysan/InfinityDB"),
        ("git@github.com:frankysan/InfinityDB.git", "frankysan/InfinityDB"),
        ("ssh://git@github.com/frankysan/InfinityDB", "frankysan/InfinityDB"),
        ("https://example.org/frankysan/InfinityDB.git", None),
        (None, None),
    ],
)
def test_github_repo_accepts_only_supported_github_origins(
    origin: str | None, expected: str | None,
) -> None:
    assert dev_status.github_repo(origin) == expected


def test_ci_status_filters_exact_sha_and_reports_latest_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "total_count": 5,
        "workflow_runs": [
            {
                "id": 10, "run_attempt": 1, "name": "Source checks",
                "head_sha": "wanted", "status": "completed",
                "conclusion": "cancelled", "html_url": "https://example.test/10",
            },
            {
                "id": 11, "run_attempt": 2, "name": "Source checks",
                "head_sha": "wanted", "status": "in_progress",
                "conclusion": None, "html_url": "https://example.test/11",
            },
            {
                "id": 12, "run_attempt": 1, "name": "Source checks",
                "head_sha": "stale", "status": "completed",
                "conclusion": "success", "html_url": "https://example.test/12",
            },
            {
                "id": 13, "run_attempt": 1, "name": "Installed wheel smoke",
                "head_sha": "wanted", "status": "completed",
                "conclusion": "skipped", "html_url": "https://example.test/13",
            },
            {
                "id": 14, "run_attempt": 1, "name": "Deployment smoke test",
                "head_sha": "wanted", "status": "queued",
                "conclusion": None, "html_url": "https://example.test/14",
            },
        ],
    }
    request: dict[str, object] = {}

    def fake_fetch(url: str, *, timeout: float, token: str | None = None) -> dict:
        request.update(url=url, timeout=timeout, token=token)
        return payload

    monkeypatch.setattr(dev_status, "fetch_json", fake_fetch)
    monkeypatch.setenv("GH_TOKEN", "private-test-token")

    result = dev_status.ci_status("wanted", "frankysan/InfinityDB")

    assert parse_qs(urlsplit(str(request["url"])).query)["head_sha"] == ["wanted"]
    assert request["timeout"] == 4
    assert request["token"] == "private-test-token"
    assert result["workflows"]["Source checks"]["run_id"] == 11
    assert result["workflows"]["Source checks"]["status"] == "in_progress"
    assert result["workflows"]["Installed wheel smoke"]["conclusion"] == "skipped"
    assert result["workflows"]["Deployment smoke test"]["status"] == "queued"
    assert "private-test-token" not in json.dumps(result)


def test_ci_status_marks_missing_and_incomplete_workflow_lists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dev_status, "fetch_json",
        lambda *args, **kwargs: {"total_count": 0, "workflow_runs": []},
    )
    missing = dev_status.ci_status("wanted", "frankysan/InfinityDB")
    assert all(
        item["status"] == "not_triggered"
        for item in missing["workflows"].values()
    )
    assert dev_status.ci_status("wanted", None)["status"] == "not_configured"

    monkeypatch.setattr(
        dev_status, "fetch_json",
        lambda *args, **kwargs: {"total_count": 2, "workflow_runs": [{}]},
    )
    incomplete = dev_status.ci_status("wanted", "frankysan/InfinityDB")
    assert incomplete["status"] == "unavailable"
    assert "Incomplete workflow list" in incomplete["reason"]


def test_ci_status_preserves_failed_conclusion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dev_status,
        "fetch_json",
        lambda *args, **kwargs: {
            "total_count": 1,
            "workflow_runs": [{
                "id": 21,
                "name": "Source checks",
                "head_sha": "wanted",
                "status": "completed",
                "conclusion": "failure",
            }],
        },
    )

    result = dev_status.ci_status("wanted", "frankysan/InfinityDB")

    assert result["workflows"]["Source checks"]["conclusion"] == "failure"
    assert result["workflows"]["Installed wheel smoke"]["status"] == "not_triggered"


def test_ci_status_reports_unavailable_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*args, **kwargs):
        raise OSError("GitHub unavailable")

    monkeypatch.setattr(dev_status, "fetch_json", unavailable)

    result = dev_status.ci_status("wanted", "frankysan/InfinityDB")

    assert result["status"] == "unavailable"
    assert result["head"] == "wanted"
    assert "GitHub unavailable" in result["reason"]


def test_monitor_filters_unrelated_and_inactive_jobs_and_uses_short_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request: dict[str, object] = {}
    payload = {
        "workers": [{"name": "linux-dev"}],
        "jobs": [
            {
                "job_id": "primary", "repository": "InfinityDB",
                "module": "model", "status": "running", "git_head": "abc",
            },
            {
                "job_id": "agent", "repository": "InfinityDB-agent-a",
                "module": "browser", "status": "unverified", "git_head": "def",
            },
            {
                "job_id": "other", "repository": "OtherProject",
                "module": "browser", "status": "running", "git_head": "ghi",
            },
            {
                "job_id": "completed", "repository": "InfinityDB",
                "module": "model", "status": "completed", "git_head": "jkl",
            },
            {
                "job_id": "sync", "repository": "InfinityDB",
                "module": "git_sync", "status": "running", "git_head": "mno",
            },
        ],
    }

    def fake_fetch(url: str, *, timeout: float, token: str | None = None) -> dict:
        request.update(url=url, timeout=timeout)
        return payload

    monkeypatch.setattr(dev_status, "fetch_json", fake_fetch)

    result = dev_status.monitor(port=8767)

    assert request == {
        "url": "http://127.0.0.1:8767/api/status", "timeout": 1.5,
    }
    assert [job["job_id"] for job in result["active_jobs"]] == ["primary", "agent"]


def test_monitor_reports_unavailable_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(*args, **kwargs):
        raise OSError("monitor unavailable")

    monkeypatch.setattr(dev_status, "fetch_json", unavailable)

    result = dev_status.monitor()

    assert result["status"] == "unavailable"
    assert result["active_jobs"] is None
    assert "monitor unavailable" in result["reason"]


def test_checkout_uses_only_read_only_git_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(
        *args: str, root: Path, optional: bool = False,
    ) -> str:
        calls.append(args)
        if args[0] == "rev-parse":
            return "a" * 40
        if args[0] == "branch":
            return "dev/v1.0.0"
        if args[0] == "status":
            return ""
        if args[0] == "config":
            return "https://github.com/frankysan/InfinityDB.git"
        raise AssertionError(args)

    monkeypatch.setattr(dev_status, "git", fake_git)

    result = dev_status.checkout()

    assert result["head"] == "a" * 40
    assert result["branch"] == "dev/v1.0.0"
    assert not result["dirty"]
    assert result["origin"] == "https://github.com/frankysan/InfinityDB.git"
    assert {call[0] for call in calls} == {"rev-parse", "branch", "status", "config"}


def test_offline_snapshot_does_not_query_monitor_or_github(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "TODO.md").write_text("backlog", encoding="utf-8")
    (root / "docs" / "validation-queue.md").write_text("queue", encoding="utf-8")
    monkeypatch.setattr(
        dev_status, "checkout",
        lambda root: {
            "branch": "main", "head": "a" * 40, "dirty": False,
            "changed_paths": [], "changed_paths_truncated": False, "origin": None,
        },
    )
    monkeypatch.setattr(dev_status, "backlog", lambda text: {"status": "ok"})
    monkeypatch.setattr(dev_status, "queue", lambda text: {"VD": {}, "VR": {}})

    def unexpected(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline snapshot attempted an online request")

    monkeypatch.setattr(dev_status, "monitor", unexpected)
    monkeypatch.setattr(dev_status, "ci_status", unexpected)

    result = dev_status.snapshot(root, online=False)

    assert result["jobs"] == {"status": "not_checked"}
    assert result["ci"] == {"status": "not_checked"}
