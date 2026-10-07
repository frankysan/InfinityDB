#!/usr/bin/env python3
"""Retain bounded, sanitized Caddy/Gunicorn diagnostics from deployment logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FORMAT = "InfinityDB deployment diagnostics"
FORMAT_VERSION = 1
DEFAULT_SINCE = "1h"
DEFAULT_TAIL_LINES = 2000
DEFAULT_MAX_GROUPS = 50
DEFAULT_SERVICES = ("app", "caddy")
_MAX_MESSAGE_LENGTH = 500
_DOCKER_TIMESTAMP_RE = re.compile(r"^(?P<timestamp>\S+)\s+(?P<message>.*)$")
_GUNICORN_RE = re.compile(
    r"^\[[^\]]+\]\s+\[\d+\]\s+\[(?P<level>[A-Z]+)\]\s*(?P<message>.*)$"
)
_EXCEPTION_RE = re.compile(
    r"^(?P<name>(?:[A-Za-z_][\w.]*\.)*[A-Za-z_][\w]*(?:Error|Exception))\s*:(?:\s.*)?$"
)
_URL_RE = re.compile(r"\b(?:https?|wss?)://[^\s\"'<>]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_IPV4_RE = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
_IPV6_RE = re.compile(r"(?<![\w:])(?:[0-9A-F]{1,4}:){2,}[0-9A-F:]*", re.IGNORECASE)
_SENSITIVE_KEY_RE = re.compile(
    r"(?i)\b(?P<key>remote_ip|client_ip|host|hostname|uri|url|request|query|search|"
    r"cookie|authorization|referer|referrer|user-agent|user_agent)"
    r"(?P<separator>\s*[=:]\s*)(?P<value>\"[^\"]*\"|'[^']*'|\S+)"
)
_REQUEST_TARGET_RE = re.compile(
    r"(?i)(?P<prefix>\b(?:error handling )?request(?: target)?(?: for)?\s+)(?P<target>\S+)"
)
_QUERY_SUFFIX_RE = re.compile(r"(?P<path>/[^\s\"'<>?]*)\?[^\s\"'<>]*")
_LEVEL_WORD_RE = re.compile(
    r"\b(?P<level>WARNING|WARN|ERROR|CRITICAL|FATAL|PANIC)\b", re.IGNORECASE
)
_TRACEBACK_RE = re.compile(r"^Traceback \(most recent call last\):$")
_SAFE_LOGGER_RE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")


class DiagnosticsError(RuntimeError):
    """Raised when deployment diagnostics cannot be collected safely."""


@dataclass(frozen=True)
class DiagnosticEvent:
    timestamp: str | None
    service: str
    level: str
    message: str


def _normalize_level(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized in {"warn", "warning"}:
        return "warning"
    if normalized in {"error"}:
        return "error"
    if normalized in {"critical", "fatal", "panic", "dpanic"}:
        return "critical"
    return None


def _sanitize_message(message: str) -> str:
    """Remove request/identity-like values from one software-generated diagnostic."""

    value = " ".join(message.replace("\x00", " ").split())
    value = _REQUEST_TARGET_RE.sub(lambda match: f"{match.group('prefix')}[request-target]", value)
    value = _SENSITIVE_KEY_RE.sub(
        lambda match: f"{match.group('key')}{match.group('separator')}[redacted]",
        value,
    )
    value = _URL_RE.sub("[url]", value)
    value = _EMAIL_RE.sub("[email]", value)
    value = _IPV4_RE.sub("[ip]", value)
    value = _IPV6_RE.sub("[ip]", value)
    value = _QUERY_SUFFIX_RE.sub(lambda match: f"{match.group('path')}?[redacted]", value)
    if len(value) > _MAX_MESSAGE_LENGTH:
        value = value[: _MAX_MESSAGE_LENGTH - 1].rstrip() + "…"
    return value


def _split_docker_timestamp(raw_line: str) -> tuple[str | None, str]:
    line = raw_line.strip()
    match = _DOCKER_TIMESTAMP_RE.match(line)
    if match is None:
        return None, line
    candidate = match.group("timestamp")
    if "T" not in candidate:
        return None, line
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None, line
    return candidate, match.group("message").strip()


def parse_diagnostic_line(service: str, raw_line: str) -> DiagnosticEvent | None:
    """Parse one timestamped Docker log line into a bounded sanitized diagnostic."""

    timestamp, line = _split_docker_timestamp(raw_line)
    if not line:
        return None

    if line.startswith("{"):
        try:
            payload: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            payload = {}
        if payload:
            level = _normalize_level(str(payload.get("level") or ""))
            if level is None:
                return None
            logger = str(payload.get("logger") or "").strip()
            if logger and not _SAFE_LOGGER_RE.fullmatch(logger):
                logger = "unknown"
            message = _sanitize_message(str(payload.get("msg") or "diagnostic"))
            if logger:
                message = f"{logger}: {message}"
            return DiagnosticEvent(timestamp, service, level, message)

    gunicorn = _GUNICORN_RE.match(line)
    if gunicorn is not None:
        level = _normalize_level(gunicorn.group("level"))
        if level is None:
            return None
        message = _sanitize_message(gunicorn.group("message") or "diagnostic")
        return DiagnosticEvent(timestamp, service, level, message)

    exception = _EXCEPTION_RE.match(line)
    if exception is not None:
        return DiagnosticEvent(
            timestamp,
            service,
            "error",
            f"{exception.group('name')}: [message redacted]",
        )
    if _TRACEBACK_RE.match(line):
        return DiagnosticEvent(timestamp, service, "error", line)

    level_match = _LEVEL_WORD_RE.search(line)
    if level_match is None:
        return None
    level = _normalize_level(level_match.group("level"))
    if level is None:
        return None
    return DiagnosticEvent(timestamp, service, level, _sanitize_message(line))


def _fingerprint(event: DiagnosticEvent) -> str:
    payload = f"{event.service}\0{event.level}\0{event.message}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def summarize_diagnostics(
    events: Sequence[DiagnosticEvent],
    *,
    lines_examined: int,
    max_groups: int = DEFAULT_MAX_GROUPS,
) -> dict[str, Any]:
    """Group repeated sanitized diagnostics while retaining bounded representative samples."""

    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    level_counts: Counter[str] = Counter()
    service_counts: Counter[str] = Counter()
    for event in events:
        key = (event.service, event.level, event.message)
        level_counts[event.level] += 1
        service_counts[event.service] += 1
        group = groups.get(key)
        if group is None:
            group = {
                "fingerprint": _fingerprint(event),
                "service": event.service,
                "level": event.level,
                "count": 0,
                "firstTimestamp": event.timestamp,
                "lastTimestamp": event.timestamp,
                "sample": event.message,
            }
            groups[key] = group
        group["count"] = int(group["count"]) + 1
        if group["firstTimestamp"] is None and event.timestamp is not None:
            group["firstTimestamp"] = event.timestamp
        if event.timestamp is not None:
            group["lastTimestamp"] = event.timestamp

    ordered = sorted(
        groups.values(),
        key=lambda item: (-int(item["count"]), str(item["service"]), str(item["sample"])),
    )
    retained = ordered[:max_groups]
    return {
        "linesExamined": lines_examined,
        "diagnosticLines": len(events),
        "droppedNonDiagnosticLines": max(0, lines_examined - len(events)),
        "distinctDiagnosticGroups": len(ordered),
        "retainedGroups": len(retained),
        "truncatedGroups": max(0, len(ordered) - len(retained)),
        "levelCounts": dict(sorted(level_counts.items())),
        "serviceCounts": dict(sorted(service_counts.items())),
        "groups": retained,
    }


def _run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
    )


def _container_ids(
    repo_root: Path,
    service: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_command,
) -> list[str]:
    result = runner(["docker", "compose", "ps", "-q", service], cwd=repo_root)
    if result.returncode != 0:
        raise DiagnosticsError(f"docker compose ps failed for {service}")
    container_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not container_ids:
        raise DiagnosticsError(f"No running container found for Compose service {service!r}")
    return container_ids


def collect_log_lines(
    repo_root: Path,
    services: Sequence[str],
    *,
    since: str,
    until: str | None,
    tail_lines: int,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_command,
) -> dict[str, list[str]]:
    """Collect bounded timestamped Docker logs without retaining container identities."""

    collected: dict[str, list[str]] = {}
    for service in services:
        service_lines: list[str] = []
        for container_id in _container_ids(repo_root, service, runner=runner):
            command = [
                "docker",
                "logs",
                "--timestamps",
                "--tail",
                str(tail_lines),
                "--since",
                since,
            ]
            if until is not None:
                command.extend(("--until", until))
            command.append(container_id)
            result = runner(command, cwd=repo_root)
            if result.returncode != 0:
                raise DiagnosticsError(f"docker logs failed for Compose service {service!r}")
            service_lines.extend(result.stdout.splitlines())
        collected[service] = service_lines
    return collected


def _load_resource_window(path: Path) -> tuple[str, str]:
    try:
        document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DiagnosticsError(f"Cannot read resource report {path}: {exc}") from exc
    if document.get("format") != "InfinityDB deployment resource capture":
        raise DiagnosticsError(f"Unsupported resource report: {path}")
    started = document.get("startedAt")
    ended = document.get("endedAt")
    if not isinstance(started, str) or not isinstance(ended, str):
        raise DiagnosticsError(f"Resource report has no valid capture window: {path}")
    return started, ended


def capture_diagnostics(
    repo_root: Path,
    *,
    services: Sequence[str] = DEFAULT_SERVICES,
    since: str = DEFAULT_SINCE,
    until: str | None = None,
    tail_lines: int = DEFAULT_TAIL_LINES,
    max_groups: int = DEFAULT_MAX_GROUPS,
    runner: Callable[..., subprocess.CompletedProcess[str]] = _run_command,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Capture bounded, sanitized warning/error diagnostics from the deployed containers."""

    logs = collect_log_lines(
        repo_root,
        services,
        since=since,
        until=until,
        tail_lines=tail_lines,
        runner=runner,
    )
    events: list[DiagnosticEvent] = []
    lines_examined = 0
    for service, lines in logs.items():
        lines_examined += len(lines)
        for line in lines:
            event = parse_diagnostic_line(service, line)
            if event is not None:
                events.append(event)

    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "capturedAt": now().isoformat(timespec="seconds").replace("+00:00", "Z"),
        "window": {"since": since, "until": until},
        "tailLinesPerContainer": tail_lines,
        "maxGroups": max_groups,
        "summary": summarize_diagnostics(
            events,
            lines_examined=lines_examined,
            max_groups=max_groups,
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Retain bounded sanitized Caddy/Gunicorn warning and error diagnostics from the "
            "existing Docker log streams."
        )
    )
    parser.add_argument(
        "--since",
        default=DEFAULT_SINCE,
        help=f"Docker log start time/duration (default: {DEFAULT_SINCE})",
    )
    parser.add_argument(
        "--resource-report",
        type=Path,
        help="use startedAt/endedAt from a deployment_resources.py JSON report",
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=DEFAULT_TAIL_LINES,
        help=f"maximum raw lines read per container (default: {DEFAULT_TAIL_LINES})",
    )
    parser.add_argument(
        "--max-groups",
        type=int,
        default=DEFAULT_MAX_GROUPS,
        help=f"maximum distinct sanitized groups retained (default: {DEFAULT_MAX_GROUPS})",
    )
    parser.add_argument(
        "--service",
        action="append",
        dest="services",
        help="Compose service to inspect; repeat as needed (default: app and caddy)",
    )
    parser.add_argument("--output", type=Path, required=True, help="JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.tail <= 0:
        raise SystemExit("--tail must be greater than zero")
    if args.max_groups <= 0:
        raise SystemExit("--max-groups must be greater than zero")
    since = args.since
    until: str | None = None
    if args.resource_report is not None:
        if args.since != DEFAULT_SINCE:
            raise SystemExit("--since cannot be combined with --resource-report")
        try:
            since, until = _load_resource_window(args.resource_report)
        except DiagnosticsError as exc:
            print(f"Diagnostics capture failed: {exc}", file=sys.stderr)
            return 2

    repo_root = Path(__file__).resolve().parents[1]
    try:
        report = capture_diagnostics(
            repo_root,
            services=tuple(args.services or DEFAULT_SERVICES),
            since=since,
            until=until,
            tail_lines=args.tail,
            max_groups=args.max_groups,
        )
    except (DiagnosticsError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"Diagnostics capture failed: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Deployment diagnostics report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
