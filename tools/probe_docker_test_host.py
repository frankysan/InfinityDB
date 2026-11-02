"""Read-only, fixed-command Docker availability probe for Windows test hosts.

This deliberately does not build, pull, create or start a container.
"""

from __future__ import annotations

import shutil
import subprocess


def main() -> int:
    docker = shutil.which("docker")
    if docker is None:
        print("docker-cli: unavailable on MCP server process PATH")
        return 0

    probes = (
        ("client-server-version", (
            "version", "--format", "{{.Client.Version}} | {{.Server.Version}}",
        )),
        ("engine", ("info", "--format", "{{.OSType}} | {{.Architecture}}")),
        ("compose", ("compose", "version", "--short")),
    )
    print("docker-cli: found")
    for label, arguments in probes:
        try:
            result = subprocess.run(
                [docker, *arguments], capture_output=True, text=True, timeout=12,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"{label}: unavailable ({type(exc).__name__})")
            continue
        summary = (result.stdout or result.stderr).strip()
        # Avoid exposing large host configuration, paths or daemon diagnostics.
        if result.returncode == 0:
            print(f"{label}: {summary[:180]}")
        else:
            error = summary.lower()
            if "access is denied" in error or "permission denied" in error:
                reason = "permission denied"
            elif "cannot find the file specified" in error or "pipe" in error:
                reason = "Docker Desktop engine pipe unavailable"
            elif "cannot connect" in error or "connection refused" in error:
                reason = "daemon unreachable"
            else:
                reason = "engine error (details suppressed)"
            print(f"{label}: unavailable (exit {result.returncode}; {reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
