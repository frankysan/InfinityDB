"""Run the strict v2 determinism manifest in a shared Linux Docker runtime.

This is intentionally separate from the production Dockerfile. The host
checkout is mounted read-only; only a selected local/ report directory is
writable. The container has no network access and runs no deployment steps.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

# Exact linux/amd64 OCI image digest: Python 3.11.18, SQLite 3.40.1,
# standard zlib 1.2.13, and Git 2.39.5. Never use a mutable tag alone.
IMAGE = (
    "python:3.11.18-bookworm@"
    "sha256:726d304906fa5eb468e5531e366548d1903286352f5adb54ef508ac01fbd80c6"
)
PLATFORM = "linux/amd64"


def _docker_command(*args: str, timeout: int = 900) -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker CLI unavailable")
    result = subprocess.run(
        [docker, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"Docker operation failed (exit {result.returncode}): "
            f"{detail[-1400:]}"
        )
    return result.stdout.strip()


def _image_probe() -> None:
    _docker_command("pull", "--platform", PLATFORM, IMAGE, timeout=1200)
    digest = _docker_command(
        "image", "inspect", "--format", "{{json .RepoDigests}}", IMAGE,
    )
    image_id = _docker_command(
        "image", "inspect", "--format", "{{.Id}}", IMAGE,
    )
    runtime = _docker_command(
        "run", "--rm", "--platform", PLATFORM, "--network", "none",
        "--read-only", IMAGE,
        "python", "-c",
        "import sqlite3,sys,zlib; print('Python',sys.version.split()[0],"
        "'SQLite',sqlite3.sqlite_version,'zlib',zlib.ZLIB_RUNTIME_VERSION)",
        timeout=180,
    )
    git = _docker_command(
        "run", "--rm", "--platform", PLATFORM, "--network", "none",
        "--read-only", IMAGE, "git", "--version", timeout=180,
    )
    print(f"OCI image: {IMAGE}")
    print(f"Resolved digests: {digest}")
    print(f"Image ID: {image_id}")
    print(f"Platform: {PLATFORM}")
    print(f"Runtime: {runtime}")
    print(f"Git: {git}")


def _local_report_path(root: Path, requested: Path) -> tuple[Path, Path]:
    output = (root / requested).resolve()
    local = (root / "local").resolve()
    if not output.is_relative_to(local):
        raise ValueError("Determinism output must be beneath repository local/")
    parent = output.parent
    parent.mkdir(parents=True, exist_ok=True)
    if not parent.is_dir() or output.is_dir():
        raise ValueError("Expected a regular report output filename")
    return parent, output


def _run_manifest(root: Path, output: Path) -> None:
    report_dir, absolute_output = _local_report_path(root, output)
    user_args: list[str] = []
    getuid = getattr(os, "getuid", None)
    getgid = getattr(os, "getgid", None)
    if callable(getuid) and callable(getgid):
        user_args = ["--user", f"{getuid()}:{getgid()}"]
    else:
        user_args = ["--user", "1000:1000"]

    report_path = f"/output/{absolute_output.name}"
    command = [
        "run", "--rm", "--platform", PLATFORM, "--network", "none",
        "--read-only", "--tmpfs", "/tmp:rw,exec,nosuid,size=512m",
        "--workdir", "/workspace", *user_args,
        "--mount", f"type=bind,source={root},target=/workspace,readonly",
        "--mount", f"type=bind,source={report_dir},target=/output",
        "--env", "PYTHONPATH=/workspace/src:/workspace",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--env", "HOME=/tmp",
        "--env", "LC_ALL=C.UTF-8",
        "--env", "GIT_CONFIG_COUNT=1",
        "--env", "GIT_CONFIG_KEY_0=safe.directory",
        "--env", "GIT_CONFIG_VALUE_0=/workspace",
        IMAGE,
        "python", "-m", "tools.build_determinism_manifest",
        "--output", report_path,
    ]
    output_text = _docker_command(*command, timeout=1800)
    if not absolute_output.is_file():
        raise RuntimeError(f"Container did not write manifest: {absolute_output}")
    print(output_text)
    print(f"Container manifest: {output}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--probe", action="store_true")
    actions.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        if args.probe:
            _image_probe()
        else:
            assert args.output is not None
            _run_manifest(root, args.output)
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
        parser.exit(1, f"Determinism container: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
