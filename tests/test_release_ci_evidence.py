from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from tools import prepare_release_ci_evidence as release_ci

COMMIT = "0123456789abcdef0123456789abcdef01234567"
REPOSITORY = "example/InfinityDB"


def _run(
    requirement: release_ci.WorkflowRequirement,
    *,
    conclusion: str = "success",
    run_id: int = 100,
    run_number: int = 20,
    run_attempt: int = 1,
    updated_at: str = "2026-10-06T05:00:00Z",
    head_sha: str = COMMIT,
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": requirement.name,
        "head_branch": "main",
        "head_sha": head_sha,
        "run_number": run_number,
        "event": "push",
        "status": "completed",
        "conclusion": conclusion,
        "html_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
        "created_at": "2026-10-06T04:50:00Z",
        "updated_at": updated_at,
        "run_attempt": run_attempt,
    }


@pytest.mark.parametrize(
    ("tag", "required"),
    [
        ("v0.10.1", False),
        ("v1.0.0", True),
        ("v1.0.1", True),
        ("v1.0.0-rc.1", True),
        ("v1rc1", True),
        ("v1.1.0", False),
        ("v1.2.0", False),
        ("v2.0.0", False),
    ],
)
def test_browser_matrix_is_mandatory_only_for_historical_v1_0_tags(
    tag: str, required: bool,
) -> None:
    assert release_ci.requires_cross_browser(tag) is required


def test_workflow_runs_url_uses_exact_workflow_file_and_commit() -> None:
    url = release_ci.workflow_runs_url(REPOSITORY, "source-checks.yml", COMMIT)

    assert url.startswith(
        "https://api.github.com/repos/example/InfinityDB/actions/workflows/source-checks.yml/runs?"
    )
    assert f"head_sha={COMMIT}" in url
    assert "status=completed" in url
    assert "per_page=100" in url


def test_select_latest_run_requires_latest_completed_attempt_to_succeed() -> None:
    requirement = release_ci.REQUIRED_WORKFLOWS[0]
    payload = {
        "workflow_runs": [
            _run(
                requirement,
                conclusion="failure",
                run_id=102,
                run_number=21,
                updated_at="2026-10-06T06:00:00Z",
            ),
            _run(requirement, run_id=101, run_number=20),
        ]
    }

    with pytest.raises(release_ci.ReleaseEvidenceError, match="concluded 'failure'"):
        release_ci.select_latest_run(
            payload,
            requirement=requirement,
            commit_sha=COMMIT,
        )


def test_select_latest_run_ignores_other_commit_runs() -> None:
    requirement = release_ci.REQUIRED_WORKFLOWS[0]
    other_sha = "f" * 40
    payload = {
        "workflow_runs": [
            _run(
                requirement,
                conclusion="failure",
                run_id=102,
                updated_at="2026-10-06T06:00:00Z",
                head_sha=other_sha,
            ),
            _run(requirement, run_id=101),
        ]
    }

    evidence = release_ci.select_latest_run(
        payload,
        requirement=requirement,
        commit_sha=COMMIT,
    )

    assert evidence.run_id == 101
    assert evidence.conclusion == "success"
    assert evidence.head_sha == COMMIT


def test_collect_release_evidence_requires_every_configured_workflow(monkeypatch) -> None:
    requested: list[str] = []

    def fake_request(url: str, *, token: str | None) -> dict[str, object]:
        requested.append(url)
        assert token == "token"
        if "/jobs?" in url:
            jobs = _source_jobs()
            return {"jobs": jobs, "total_count": len(jobs)}
        requirement = next(
            item for item in release_ci.REQUIRED_WORKFLOWS if item.filename in url
        )
        return {"workflow_runs": [_run(requirement, run_id=100 + len(requested))]}

    monkeypatch.setattr(release_ci, "_request_json", fake_request)

    evidence = release_ci.collect_release_evidence(REPOSITORY, COMMIT, token="token")

    assert evidence["schema_version"] == 1
    assert evidence["repository"] == REPOSITORY
    assert evidence["commit_sha"] == COMMIT
    workflows = evidence["workflows"]
    assert isinstance(workflows, list)
    assert [entry["workflow"] for entry in workflows] == [
        "Source checks",
        "Installed wheel smoke",
        "Deployment smoke test",
    ]
    assert len(requested) == 4
    assert evidence["workflows"][0]["source_validation"] == {"mode": "full"}


def test_collect_release_evidence_can_require_optional_full_asset_run(monkeypatch) -> None:
    requested: list[str] = []

    def fake_request(url: str, *, token: str | None) -> dict[str, object]:
        requested.append(url)
        if "/jobs?" in url:
            jobs = _source_jobs()
            return {"jobs": jobs, "total_count": len(jobs)}
        requirements = release_ci.REQUIRED_WORKFLOWS + (release_ci.OPTIONAL_FULL_ASSET_WORKFLOW,)
        requirement = next(item for item in requirements if item.filename in url)
        return {"workflow_runs": [_run(requirement, run_id=100 + len(requested))]}

    monkeypatch.setattr(release_ci, "_request_json", fake_request)

    evidence = release_ci.collect_release_evidence(
        REPOSITORY,
        COMMIT,
        include_full_assets=True,
    )

    workflows = evidence["workflows"]
    assert isinstance(workflows, list)
    assert [entry["workflow"] for entry in workflows] == [
        "Source checks",
        "Installed wheel smoke",
        "Deployment smoke test",
        "Full-asset checks",
    ]
    assert len(requested) == 5


def _browser_jobs(run_id: int = 200) -> list[dict[str, object]]:
    return [
        {
            "id": 201 + index,
            "run_id": run_id,
            "name": name,
            "status": "completed",
            "conclusion": "success",
            "html_url": f"https://github.com/{REPOSITORY}/actions/jobs/{201 + index}",
        }
        for index, name in enumerate(release_ci.CROSS_BROWSER_JOBS)
    ]


def _source_jobs(run_id: int = 101, *, focused: bool = False):
    names = release_ci.SOURCE_FULL_JOBS
    jobs = [
        {
            "id": 301 + index,
            "run_id": run_id,
            "name": name,
            "status": "completed",
            "conclusion": "success",
            "steps": [{
                "name": (
                    "Reuse validated deterministic baseline"
                    if name == "Cross-platform deterministic outputs"
                    else "Reuse validated Source baseline"
                ),
                "conclusion": "success",
            }] if focused else [],
        }
        for index, name in enumerate(names)
    ]
    if focused:
        jobs.append({
            "id": 309,
            "run_id": run_id,
            "name": release_ci.SOURCE_FAST_JOB,
            "status": "completed",
            "conclusion": "success",
            "steps": [{
                "name": "Run changed tests with verified baseline",
                "conclusion": "success",
            }],
        })
    return jobs


def test_source_evidence_requires_full_matrix_or_proven_focused_run() -> None:
    full = _source_jobs()
    assert release_ci.verify_source_jobs(
        {"jobs": full, "total_count": len(full)}, run_id=101
    ) == {"mode": "full"}
    focused = _source_jobs(focused=True)
    assert release_ci.verify_source_jobs(
        {"jobs": focused, "total_count": len(focused)}, run_id=101
    ) == {"mode": "focused", "basis": "verified hosted baseline"}

    with pytest.raises(release_ci.ReleaseEvidenceError, match="focused tests"):
        missing_steps = [dict(job) for job in focused]
        missing_steps[-1]["steps"] = []
        release_ci.verify_source_jobs(
            {"jobs": missing_steps, "total_count": len(missing_steps)}, run_id=101
        )
    with pytest.raises(release_ci.ReleaseEvidenceError):
        broken = [*full[:-1], dict(full[-1], conclusion="failure")]
        release_ci.verify_source_jobs(
            {"jobs": broken, "total_count": len(broken)}, run_id=101
        )


def test_cross_browser_job_validation_fails_closed() -> None:
    jobs = _browser_jobs()
    expected = release_ci.verify_cross_browser_jobs(
        {"jobs": jobs, "total_count": 4}, run_id=200
    )
    assert [job["name"] for job in expected] == list(release_ci.CROSS_BROWSER_JOBS)

    for changed in (
        jobs[:-1],
        [*jobs[:-1], dict(jobs[-1], conclusion="failure")],
        [*jobs[:-1], dict(jobs[-1], conclusion="skipped")],
        [*jobs[:-1], dict(jobs[-1], status="in_progress")],
        [*jobs[:-1], dict(jobs[-1], name=jobs[0]["name"])],
        [*jobs[:-1], dict(jobs[-1], run_id=999)],
    ):
        with pytest.raises(release_ci.ReleaseEvidenceError):
            release_ci.verify_cross_browser_jobs(
                {"jobs": changed, "total_count": len(changed)}, run_id=200
            )
    with pytest.raises(release_ci.ReleaseEvidenceError, match="incomplete"):
        release_ci.verify_cross_browser_jobs(
            {"jobs": jobs, "total_count": 5}, run_id=200
        )


def test_collect_release_evidence_requires_cross_browser_job_matrix(monkeypatch) -> None:
    requested: list[str] = []
    requirements = release_ci.REQUIRED_WORKFLOWS + (release_ci.CROSS_BROWSER_WORKFLOW,)

    def fake_request(url: str, *, token: str | None) -> dict[str, object]:
        requested.append(url)
        if "/jobs?" in url:
            if url == release_ci.cross_browser_jobs_url(REPOSITORY, 101):
                jobs = _source_jobs()
                return {"jobs": jobs, "total_count": len(jobs)}
            assert url == release_ci.cross_browser_jobs_url(REPOSITORY, 200)
            return {"jobs": _browser_jobs(), "total_count": 4}
        requirement = next(item for item in requirements if item.filename in url)
        return {
            "workflow_runs": [
                _run(requirement, run_id=200 if requirement == release_ci.CROSS_BROWSER_WORKFLOW
                     else 100 + len(requested))
            ],
        }

    monkeypatch.setattr(release_ci, "_request_json", fake_request)
    evidence = release_ci.collect_release_evidence(
        REPOSITORY, COMMIT, include_cross_browser=True
    )
    assert len(requested) == 6
    assert evidence["workflows"][0]["source_validation"] == {"mode": "full"}
    browser = evidence["workflows"][-1]
    assert browser["workflow"] == "Cross-browser compatibility"
    assert len(browser["jobs"]) == 4
    assert all(job["conclusion"] == "success" for job in browser["jobs"])


def test_v1_tag_message_requires_browser_matrix_evidence() -> None:
    workflows = []
    for index, requirement in enumerate(release_ci.REQUIRED_WORKFLOWS):
        workflows.append({
            "workflow": requirement.name,
            "run_number": index + 1,
            "run_attempt": 1,
            "conclusion": "success",
            "url": f"https://github.com/{REPOSITORY}/actions/runs/{index + 1}",
        })
    evidence = {"repository": REPOSITORY, "commit_sha": COMMIT, "workflows": workflows}
    assert "InfinityDB v1.1.0" in release_ci.render_tag_message("v1.1.0", evidence)
    with pytest.raises(release_ci.ReleaseEvidenceError, match="Cross-browser compatibility"):
        release_ci.render_tag_message("v1.0.0", evidence)

    browser = {
        "workflow": release_ci.CROSS_BROWSER_WORKFLOW.name,
        "run_id": 200,
        "run_number": 10,
        "run_attempt": 1,
        "conclusion": "success",
        "url": f"https://github.com/{REPOSITORY}/actions/runs/200",
        "jobs": release_ci.verify_cross_browser_jobs(
            {"jobs": _browser_jobs(), "total_count": 4}, run_id=200
        ),
    }
    evidence["workflows"].append(browser)
    assert "- Cross-browser compatibility: success" in release_ci.render_tag_message(
        "v1.0.0", evidence
    )
    assert "- Cross-browser compatibility: success" in release_ci.render_tag_message(
        "v1.1.0", evidence
    )
    browser["jobs"] = browser["jobs"][:-1]
    with pytest.raises(release_ci.ReleaseEvidenceError):
        release_ci.render_tag_message("v1.0.0", evidence)
    with pytest.raises(release_ci.ReleaseEvidenceError):
        release_ci.render_tag_message("v1.1.0", evidence)


def test_render_tag_message_records_run_identity_and_urls() -> None:
    workflows = []
    for index, requirement in enumerate(release_ci.REQUIRED_WORKFLOWS, start=1):
        workflows.append(
            release_ci.WorkflowRunEvidence(
                workflow=requirement.name,
                workflow_file=requirement.filename,
                run_id=100 + index,
                run_number=20 + index,
                run_attempt=1,
                event="push",
                conclusion="success",
                head_sha=COMMIT,
                head_branch="main",
                created_at="2026-10-06T04:50:00Z",
                updated_at="2026-10-06T05:00:00Z",
                url=f"https://github.com/{REPOSITORY}/actions/runs/{100 + index}",
            )
        )
    evidence = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "commit_sha": COMMIT,
        "workflows": [asdict(workflow) for workflow in workflows],
    }

    message = release_ci.render_tag_message("v0.10.0", evidence)

    assert message.startswith("InfinityDB v0.10.0\n\nHosted CI evidence\n")
    assert f"Commit: {COMMIT}" in message
    assert "- Source checks: success (run 21, attempt 1)" in message
    assert f"https://github.com/{REPOSITORY}/actions/runs/101" in message
    assert "- Deployment smoke test: success (run 23, attempt 1)" in message


def test_main_writes_json_and_annotated_tag_message(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    workflows = []
    for index, requirement in enumerate(release_ci.REQUIRED_WORKFLOWS, start=1):
        workflows.append(
            {
                "workflow": requirement.name,
                "workflow_file": requirement.filename,
                "run_id": 100 + index,
                "run_number": 20 + index,
                "run_attempt": 1,
                "event": "push",
                "conclusion": "success",
                "head_sha": COMMIT,
                "head_branch": "main",
                "created_at": "2026-10-06T04:50:00Z",
                "updated_at": "2026-10-06T05:00:00Z",
                "url": f"https://github.com/{REPOSITORY}/actions/runs/{100 + index}",
            }
        )
    evidence = {
        "schema_version": 1,
        "repository": REPOSITORY,
        "commit_sha": COMMIT,
        "workflows": workflows,
    }
    monkeypatch.setattr(release_ci, "collect_release_evidence", lambda *args, **kwargs: evidence)
    monkeypatch.setattr(release_ci, "verify_release_metadata_for_tag", lambda tag, sha: None)
    json_output = tmp_path / "evidence.json"
    tag_output = tmp_path / "tag.txt"

    result = release_ci.main(
        [
            "--repository",
            REPOSITORY,
            "--commit",
            COMMIT,
            "--tag",
            "v0.10.0",
            "--json-output",
            str(json_output),
            "--tag-message-output",
            str(tag_output),
        ]
    )

    assert result == 0
    assert json.loads(json_output.read_text(encoding="utf-8")) == evidence
    assert tag_output.read_text(encoding="utf-8").startswith("InfinityDB v0.10.0\n")
    assert "3 required workflows" in capsys.readouterr().out


def test_v1_cli_automatically_requires_cross_browser(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_collect(*args, **kwargs):
        assert kwargs["include_cross_browser"] is True
        raise release_ci.ReleaseEvidenceError("Missing required Cross-browser compatibility")

    monkeypatch.setattr(release_ci, "collect_release_evidence", fake_collect)
    result = release_ci.main([
        "--repository", REPOSITORY, "--commit", COMMIT, "--tag", "v1.0.0",
        "--json-output", str(tmp_path / "evidence.json"),
        "--tag-message-output", str(tmp_path / "tag.txt"),
    ])
    assert result == 1
    assert "Cross-browser compatibility" in capsys.readouterr().err
    assert not (tmp_path / "evidence.json").exists()


def test_release_evidence_guard_checks_sha_metadata_and_tag_version(monkeypatch) -> None:
    monkeypatch.setattr(
        release_ci.subprocess, "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 0, stdout=COMMIT + "\n"),
    )
    monkeypatch.setattr(
        release_ci, "check_repository", lambda: ["latest release is still Unreleased"]
    )
    with pytest.raises(release_ci.ReleaseEvidenceError, match="not finalized"):
        release_ci.verify_release_metadata_for_tag("v1.1.0", COMMIT)

    monkeypatch.setattr(release_ci, "check_repository", lambda: [])
    monkeypatch.setattr(
        release_ci.tomllib, "load",
        lambda stream: {"project": {"version": "1.1.0"}},
    )
    release_ci.verify_release_metadata_for_tag("v1.1.0", COMMIT)
    with pytest.raises(release_ci.ReleaseEvidenceError, match="does not match"):
        release_ci.verify_release_metadata_for_tag("v1.1.1", COMMIT)
    with pytest.raises(release_ci.ReleaseEvidenceError, match="HEAD does not match"):
        release_ci.verify_release_metadata_for_tag("v1.1.0", "f" * 40)


def test_v1_1_cli_browser_matrix_is_opt_in(monkeypatch, tmp_path: Path) -> None:
    requested: list[bool] = []

    def fake_collect(*args, **kwargs):
        requested.append(kwargs["include_cross_browser"])
        raise release_ci.ReleaseEvidenceError("sentinel")

    monkeypatch.setattr(release_ci, "collect_release_evidence", fake_collect)
    base_args = [
        "--repository", REPOSITORY, "--commit", COMMIT, "--tag", "v1.1.0",
        "--json-output", str(tmp_path / "evidence.json"),
        "--tag-message-output", str(tmp_path / "tag.txt"),
    ]
    assert release_ci.main(base_args) == 1
    assert release_ci.main([*base_args, "--include-cross-browser"]) == 1
    assert requested == [False, True]


def test_main_rejects_invalid_release_commit_without_traceback(capsys) -> None:
    result = release_ci.main(
        [
            "--repository",
            REPOSITORY,
            "--commit",
            "not-a-sha",
            "--tag",
            "v0.10.0",
            "--json-output",
            "reports/evidence.json",
            "--tag-message-output",
            "reports/tag.txt",
        ]
    )

    assert result == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "full 40-character Git SHA" in captured.err
    assert "Traceback" not in captured.err
