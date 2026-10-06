from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from tools.deployment_diagnostics import (
    DiagnosticEvent,
    _load_resource_window,
    _sanitize_message,
    capture_diagnostics,
    collect_log_lines,
    main,
    parse_diagnostic_line,
    summarize_diagnostics,
)


def test_sanitize_message_redacts_request_and_identity_like_values() -> None:
    raw = (
        "ERROR request /search?q=private host=example.invalid remote_ip=192.0.2.42 "
        "url=https://example.invalid/unit/secret?token=abc user-agent=PrivateAgent "
        "mail=test@example.invalid"
    )
    sanitized = _sanitize_message(raw)

    assert "private" not in sanitized
    assert "example.invalid" not in sanitized
    assert "192.0.2.42" not in sanitized
    assert "PrivateAgent" not in sanitized
    assert "test@example.invalid" not in sanitized
    assert "[request-target]" in sanitized
    assert "[redacted]" in sanitized


def test_parse_caddy_json_keeps_only_safe_operational_fields() -> None:
    raw = (
        '2026-10-06T07:00:00.000000000Z '
        '{"level":"error","logger":"http.handlers.reverse_proxy",'
        '"msg":"dial tcp 192.0.2.4:8000: connect: connection refused",'
        '"request":{"remote_ip":"198.51.100.7","uri":"/search?q=private"}}'
    )
    event = parse_diagnostic_line("caddy", raw)

    assert event is not None
    assert event.level == "error"
    assert event.service == "caddy"
    assert event.timestamp == "2026-10-06T07:00:00.000000000Z"
    assert event.message == (
        "http.handlers.reverse_proxy: dial tcp [ip]:8000: connect: connection refused"
    )
    serialized = json.dumps(event.__dict__)
    assert "198.51.100.7" not in serialized
    assert "private" not in serialized


def test_parse_gunicorn_request_error_redacts_target_and_exception_message() -> None:
    request = parse_diagnostic_line(
        "app",
        "2026-10-06T07:00:01Z [2026-10-06 07:00:01 +0000] [7] [ERROR] "
        "Error handling request /search?q=secret",
    )
    exception = parse_diagnostic_line(
        "app",
        "2026-10-06T07:00:02Z ValueError: user supplied secret",
    )
    info = parse_diagnostic_line(
        "app",
        "2026-10-06T07:00:03Z [2026-10-06 07:00:03 +0000] [7] [INFO] Booting worker",
    )

    assert request is not None
    assert request.message == "Error handling request [request-target]"
    assert exception is not None
    assert exception.message == "ValueError: [message redacted]"
    assert info is None


def test_summary_groups_repeated_sanitized_diagnostics_and_caps_output() -> None:
    events = [
        DiagnosticEvent("2026-10-06T07:00:00Z", "app", "error", "worker timeout"),
        DiagnosticEvent("2026-10-06T07:00:01Z", "app", "error", "worker timeout"),
        DiagnosticEvent("2026-10-06T07:00:02Z", "caddy", "warning", "upstream retry"),
    ]
    report = summarize_diagnostics(events, lines_examined=10, max_groups=1)

    assert report["diagnosticLines"] == 3
    assert report["droppedNonDiagnosticLines"] == 7
    assert report["distinctDiagnosticGroups"] == 2
    assert report["retainedGroups"] == 1
    assert report["truncatedGroups"] == 1
    assert report["levelCounts"] == {"error": 2, "warning": 1}
    assert report["groups"][0]["count"] == 2
    assert len(report["groups"][0]["fingerprint"]) == 16


def test_collect_log_lines_uses_container_ids_without_retaining_them(tmp_path: Path) -> None:
    commands: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[:4] == ["docker", "compose", "ps", "-q"]:
            service = command[-1]
            return subprocess.CompletedProcess(command, 0, f"secret-{service}-id\n", "")
        return subprocess.CompletedProcess(
            command,
            0,
            "2026-10-06T07:00:00Z [2026-10-06 07:00:00 +0000] [7] [ERROR] worker timeout\n",
            "",
        )

    logs = collect_log_lines(
        tmp_path,
        ("app", "caddy"),
        since="2026-10-06T07:00:00Z",
        until="2026-10-06T07:01:00Z",
        tail_lines=100,
        runner=runner,
    )

    assert tuple(logs) == ("app", "caddy")
    assert all(len(lines) == 1 for lines in logs.values())
    assert any("secret-app-id" in command for command in commands)
    assert "secret-app-id" not in json.dumps(logs)
    docker_log_commands = [command for command in commands if command[:2] == ["docker", "logs"]]
    assert all("--timestamps" in command for command in docker_log_commands)
    assert all("--until" in command for command in docker_log_commands)


def test_resource_report_supplies_exact_diagnostic_window(tmp_path: Path) -> None:
    resource_report = tmp_path / "resources.json"
    resource_report.write_text(
        json.dumps(
            {
                "format": "InfinityDB deployment resource capture",
                "startedAt": "2026-10-06T07:00:00Z",
                "endedAt": "2026-10-06T07:01:10Z",
            }
        ),
        encoding="utf-8",
        newline="\n",
    )

    assert _load_resource_window(resource_report) == (
        "2026-10-06T07:00:00Z",
        "2026-10-06T07:01:10Z",
    )


def test_capture_report_contains_no_container_ids_or_request_values(tmp_path: Path) -> None:
    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[:4] == ["docker", "compose", "ps", "-q"]:
            return subprocess.CompletedProcess(command, 0, "private-container-id\n", "")
        service_message = (
            "2026-10-06T07:00:00Z "
            '[2026-10-06 07:00:00 +0000] [7] [ERROR] Error handling request /search?q=private\n'
        )
        return subprocess.CompletedProcess(command, 0, service_message, "")

    report = capture_diagnostics(
        tmp_path,
        since="1h",
        tail_lines=20,
        runner=runner,
        now=lambda: datetime(2026, 10, 6, 7, 5, tzinfo=UTC),
    )
    serialized = json.dumps(report)

    assert report["format"] == "InfinityDB deployment diagnostics"
    assert report["summary"]["diagnosticLines"] == 2
    assert "private-container-id" not in serialized
    assert "q=private" not in serialized
    assert "/search" not in serialized


def test_main_writes_deterministic_newline_policy(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "diagnostics.json"

    def fake_capture(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "format": "InfinityDB deployment diagnostics",
            "formatVersion": 1,
            "summary": {"diagnosticLines": 0},
        }

    monkeypatch.setattr("tools.deployment_diagnostics.capture_diagnostics", fake_capture)
    assert main(["--output", str(output)]) == 0
    assert output.read_bytes().endswith(b"\n")
