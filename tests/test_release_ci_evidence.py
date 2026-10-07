from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

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
    assert len(requested) == 3


def test_collect_release_evidence_can_require_optional_full_asset_run(monkeypatch) -> None:
    requested: list[str] = []

    def fake_request(url: str, *, token: str | None) -> dict[str, object]:
        requested.append(url)
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
    assert len(requested) == 4


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
