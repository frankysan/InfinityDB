"""The four operational JSON commands preserve run receipts without altering status."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tools import capacity_test, deployment_alerts, deployment_diagnostics, deployment_resources
from tools.operations.receipt_output import require_new_receipt, write_new_json_receipt

MODULES = (
    capacity_test,
    deployment_resources,
    deployment_diagnostics,
    deployment_alerts,
)
ROOT = Path(__file__).resolve().parents[1]
STATUS_ON_OUTPUT_ERROR = {
    capacity_test: 2,
    deployment_resources: 2,
    deployment_diagnostics: 2,
    deployment_alerts: 3,
}


def _args(module: Any, output: Path) -> list[str]:
    if module is capacity_test:
        return ["http://example.invalid", "--output", str(output)]
    if module is deployment_alerts:
        return ["--resource-report", str(output.parent / "resources.json"), "--output", str(output)]
    return ["--output", str(output)]


def _stub_run(
    module: Any, monkeypatch: pytest.MonkeyPatch, report: dict[str, Any],
    *, on_execute: Any = None, command_exit: int = 0,
) -> None:
    def execute(*args: Any, **kwargs: Any) -> Any:
        if on_execute is not None:
            on_execute()
        return (report, command_exit) if module is deployment_resources else report

    if module is capacity_test:
        monkeypatch.setattr(module, "capacity_test", execute)
    elif module is deployment_resources:
        monkeypatch.setattr(module, "capture_resources", execute)
    elif module is deployment_diagnostics:
        monkeypatch.setattr(module, "capture_diagnostics", execute)
    else:
        monkeypatch.setattr(module, "load_resource_report", lambda path: {"format": "example"})
        monkeypatch.setattr(module, "build_report", execute)


def _main(module: Any, args: list[str]) -> int:
    if module is deployment_alerts:
        return module.main(
            args, sleep=lambda seconds: None,
            now=lambda: datetime(2026, 11, 13, tzinfo=UTC),
            metrics_fetcher=lambda *a, **kw: "",
            health_fetcher=lambda *a, **kw: True,
        )
    return module.main(args)


def _report(module: Any, *, failed: bool = False) -> dict[str, Any]:
    if module is capacity_test:
        return {
            "format": "InfinityDB HTTP capacity test",
            "target": {
                "baseUrl": "http://example.invalid",
                "version": "test",
                "snapshotRevision": "snapshot",
            },
            "phases": [{
                "name": "steady", "concurrency": 1, "requestsPerSecond": 1.0,
                "errorRate": 0.0 if not failed else 1.0,
                "errors": 1 if failed else 0, "latency": None,
            }],
        }
    if module is deployment_resources:
        return {"format": "InfinityDB deployment resource capture", "command": {"ran": True}}
    if module is deployment_diagnostics:
        return {"format": "InfinityDB deployment diagnostics", "results": []}
    return {"format": "InfinityDB deployment alert evaluation",
            "exitCode": 2 if failed else 0, "status": "critical" if failed else "ok"}


@pytest.mark.parametrize("module", MODULES, ids=lambda module: module.__name__.split(".")[-1])
def test_cli_rejects_existing_report_before_any_collection(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "prior.json"
    previous = b"previously retained operational data\n"
    output.write_bytes(previous)

    def forbidden() -> None:
        pytest.fail("Occupied report should block all collection and evaluation")

    _stub_run(module, monkeypatch, _report(module), on_execute=forbidden)
    if module is deployment_alerts:
        monkeypatch.setattr(module, "load_resource_report", lambda path: forbidden())

    assert _main(module, _args(module, output)) == STATUS_ON_OUTPUT_ERROR[module]
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == previous


@pytest.mark.parametrize("module", MODULES, ids=lambda module: module.__name__.split(".")[-1])
def test_cli_retains_json_bytes_and_existing_semantics(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "new-run" / "report.json"
    report = _report(module)
    exit_code = 7 if module is deployment_resources else 0
    _stub_run(module, monkeypatch, report, command_exit=exit_code)

    assert _main(module, _args(module, output)) == exit_code
    assert output.read_bytes() == (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    assert str(output) in capsys.readouterr().out


@pytest.mark.parametrize("module", MODULES, ids=lambda module: module.__name__.split(".")[-1])
def test_cli_preserves_existing_bytes_after_late_collision(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "late.json"
    prior = b"another sampler's completed receipt\n"

    def occupy_output() -> None:
        output.write_bytes(prior)

    _stub_run(module, monkeypatch, _report(module), on_execute=occupy_output)
    assert _main(module, _args(module, output)) == STATUS_ON_OUTPUT_ERROR[module]
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    assert str(output) not in captured.out
    assert output.read_bytes() == prior


@pytest.mark.parametrize("module", MODULES, ids=lambda module: module.__name__.split(".")[-1])
def test_cli_handles_unwritable_output_parent_without_clobbering(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    occupied_parent = tmp_path / "not-a-directory"
    prior = b"preserved parent file"
    occupied_parent.write_bytes(prior)
    output = occupied_parent / "new.json"

    _stub_run(module, monkeypatch, _report(module))
    assert _main(module, _args(module, output)) == STATUS_ON_OUTPUT_ERROR[module]
    assert "report failed:" in capsys.readouterr().err.lower()
    assert occupied_parent.read_bytes() == prior


@pytest.mark.parametrize("module", (capacity_test, deployment_alerts),
                         ids=lambda module: module.__name__.split(".")[-1])
def test_optional_output_stdout_only_remains_available(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = _report(module, failed=True)
    _stub_run(module, monkeypatch, report)
    args = ["http://example.invalid"] if module is capacity_test else [
        "--resource-report", str(tmp_path / "source.json")
    ]
    assert _main(module, args) == (1 if module is capacity_test else 2)
    stdout = capsys.readouterr().out
    if module is capacity_test:
        assert "InfinityDB capacity test" in stdout
    else:
        assert json.loads(stdout) == report
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("status", (0, 1, 2, 3))
def test_alert_exit_status_preserved_when_receipt_is_new(
    status: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / f"alert-{status}.json"
    report = _report(deployment_alerts)
    report["exitCode"] = status
    _stub_run(deployment_alerts, monkeypatch, report)
    assert _main(deployment_alerts, _args(deployment_alerts, output)) == status
    assert json.loads(output.read_text(encoding="utf-8"))["exitCode"] == status


@pytest.mark.parametrize("module", (deployment_diagnostics, deployment_alerts),
                         ids=lambda module: module.__name__.split(".")[-1])
def test_input_resource_report_cannot_be_used_as_output(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "resource-report.json"
    prior = b'{"format":"original source"}\n'
    source.write_bytes(prior)

    def forbidden() -> None:
        pytest.fail("Source report must not be treated as an output destination")

    _stub_run(module, monkeypatch, _report(module), on_execute=forbidden)
    if module is deployment_alerts:
        monkeypatch.setattr(module, "load_resource_report", lambda path: forbidden())
    args = ["--resource-report", str(source), "--output", str(source)]
    assert _main(module, args) == STATUS_ON_OUTPUT_ERROR[module]
    assert source.read_bytes() == prior


def test_helper_rejects_dangling_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "dangling.json"
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == output)
    with pytest.raises(FileExistsError, match="already exists"):
        require_new_receipt(output)
    assert not output.exists()


def test_helper_refuses_output_created_between_preflight_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "report.json"
    require_new_receipt(output)
    prior = b"earlier run\n"
    original_open = Path.open

    def concurrent_open(
        target: Path, mode: str = "r", buffering: int = -1,
        encoding: str | None = None, errors: str | None = None,
        newline: str | None = None,
    ):
        if target == output and mode == "x":
            target.write_bytes(prior)
        return original_open(
            target, mode, buffering=buffering, encoding=encoding,
            errors=errors, newline=newline,
        )

    monkeypatch.setattr(Path, "open", concurrent_open)
    with pytest.raises(FileExistsError):
        write_new_json_receipt(output, {"later": True})
    assert output.read_bytes() == prior


@pytest.mark.parametrize("module", MODULES, ids=lambda module: module.__name__.split(".")[-1])
def test_direct_script_help_retains_invocation_compatibility(module: Any) -> None:
    script = ROOT / "tools" / (module.__name__.split(".")[-1] + ".py")
    completed = subprocess.run(
        [sys.executable, str(script), "--help"], cwd=ROOT,
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "--output" in completed.stdout
