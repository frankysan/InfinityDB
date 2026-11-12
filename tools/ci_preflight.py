#!/usr/bin/env python3
"""Reproduce clean-checkout and wheel-content CI conditions locally.

Local working trees contain Git-ignored and untracked files that CI never sees. This tool:

1. fails when non-ignored files are untracked (CI would not have them);
2. exports only Git-tracked files (index content) to a temporary directory and runs pytest there;
3. builds a wheel from that export and checks all tracked src/ files (except
   explicit design-source exemptions) plus configured setuptools shared data-files.

Use --isolated to verify indexed release artifacts, run Ruff/pytest/Pyright with
declared dependencies, and smoke-test the built wheel in a second fresh environment.
This explicit mode may download Python packages.

It does not replace the installed-wheel smoke workflow; see docs/ci.md.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = "src/"
# Tracked package files deliberately left out of the wheel (design sources).
WHEEL_EXEMPT_PREFIXES = ("infinity_db/web/static/logo/",)


def _git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True
    ).stdout


def tracked_entries() -> list[tuple[str, str]]:
    """Return index paths and modes, rejecting unresolved merges."""
    entries = []
    for record in _git("ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, _object_id, stage = metadata.split()
        name = path.decode("utf-8")
        if stage != b"0":
            raise ValueError(f"unresolved index entry: {name}")
        entries.append((name, mode.decode("ascii")))
    return entries


def tracked_files() -> list[str]:
    return [name for name, _mode in tracked_entries()]


def untracked_files() -> list[str]:
    names = _git("ls-files", "-z", "--others", "--exclude-standard").decode("utf-8")
    return [name for name in names.split("\0") if name]


def export_tracked(destination: Path) -> int:
    """Export the index, preserving executable bits and Git symlinks."""
    count = 0
    for name, mode in tracked_entries():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode not in ("100644", "100755", "120000"):
            raise ValueError(f"unsupported Git index mode {mode}: {name}")
        content = _git("show", f":{name}")
        if mode == "120000":
            # Git stores a symlink's target as the blob contents.
            os.symlink(os.fsdecode(content), target)
        elif mode in ("100644", "100755"):
            target.write_bytes(content)
            if mode == "100755":
                target.chmod(target.stat().st_mode | 0o111)
        count += 1
    return count


def audit_wheel(export: Path, wheel_dir: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-q", "-w", str(wheel_dir)],
        cwd=export,
    )
    if result.returncode != 0:
        return ["wheel build failed"]
    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        return [f"expected one wheel, found {len(wheels)}"]
    with zipfile.ZipFile(wheels[0]) as archive:
        members = set(archive.namelist())
    tracked = set(tracked_files())
    missing = []
    for name in sorted(tracked):
        if not name.startswith(PACKAGE_ROOT):
            continue
        relative = name[len(PACKAGE_ROOT) :]
        if relative.startswith(WHEEL_EXEMPT_PREFIXES):
            continue
        if relative not in members:
            missing.append(f"tracked source file not shipped in wheel: {relative}")

    # Setuptools' data-files are installed in the wheel's .data/data/ tree,
    # not alongside the importable packages under src/.
    with (export / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)
    data_files = project.get("tool", {}).get("setuptools", {}).get("data-files", {})
    wheel_data = {
        member.split(".data/data/", 1)[1]
        for member in members if ".data/data/" in member
    }
    for destination, files in sorted(data_files.items()):
        for source in files:
            if source not in tracked:
                missing.append(f"configured data file absent from Git index: {source}")
                continue
            expected = str(PurePosixPath(destination) / PurePosixPath(source).name)
            if expected not in wheel_data:
                missing.append(f"configured data file not shipped in wheel: {expected}")
    return missing


def check_export(
    export: Path, environment: Path | None, pytest_args: list[str], *,
    include_full_assets: bool = True,
) -> list[str]:
    """Run clean-source checks, optionally without developer-installed packages."""
    python = Path(sys.executable)
    env = os.environ.copy()
    # Do not let editable imports or a caller's disposable index leak into tests
    # (which create their own temporary Git repositories).
    for name in ("PYTHONPATH", "PYTHONHOME", "GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"):
        env.pop(name, None)
    if environment is not None:
        for name in ("PYTEST_ADDOPTS", "PIP_TARGET", "PIP_PREFIX", "PIP_USER"):
            env.pop(name, None)
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(environment)], cwd=export, env=env,
        )
        if result.returncode:
            return ["isolated virtual environment creation failed"]
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        env["VIRTUAL_ENV"] = str(environment)
        env["PATH"] = str(scripts) + os.pathsep + env.get("PATH", "")
        result = subprocess.run(
            [str(python), "-m", "pip", "install", "-e", ".[dev,symbols]"],
            cwd=export, env=env,
        )
        if result.returncode:
            return ["isolated CI dependency installation failed"]

    # Verify the indexed selected set without producing any obsolete JSON.
    # An existing editable install must not replace the exported application.
    result = subprocess.run(
        [str(python), "-m", "infinity_db", "database-health",
         "--db-dir", "data/generated"],
        cwd=export, env={**env, "PYTHONPATH": str(export / "src")},
    )
    if result.returncode:
        return ["clean-export runtime database-set verification failed"]

    problems = []
    if environment is not None:
        artifact_command = [str(python), "-m", "tools.verify_deployment_assets"]
        if not include_full_assets:
            artifact_command.append("--skip-svg")
        result = subprocess.run(artifact_command, cwd=export, env=env)
        if result.returncode:
            problems.append("indexed deployment-artifact verification failed")
        result = subprocess.run(
            [str(python), "-m", "tools.run_checks", "--stage", "lint"], cwd=export, env=env,
        )
        if result.returncode:
            problems.append("Ruff failed in isolated export")
    asset_args = [
        "-m", "full_assets or not full_assets" if include_full_assets else "not full_assets",
    ] if environment is not None else []
    result = subprocess.run(
        [str(python), "-m", "pytest", "-q", *asset_args, *pytest_args], cwd=export, env=env,
    )
    if result.returncode:
        problems.append(f"pytest failed in clean export (exit {result.returncode})")
    if environment is not None:
        result = subprocess.run(
            [str(python), "-m", "pyright", "--pythonpath", str(python)],
            cwd=export, env=env,
        )
        if result.returncode:
            problems.append(f"Pyright failed in isolated export (exit {result.returncode})")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "CI preflight").splitlines()[0])
    parser.add_argument(
        "--skip-wheel", action="store_true",
        help="skip wheel-content audit and installed-wheel smoke",
    )
    parser.add_argument(
        "--assets", choices=("off", "required"), default="required",
        help="off skips SVG files but still verifies indexed database provenance",
    )
    parser.add_argument(
        "--skip-pytest", action="store_true", help="skip the clean-export pytest run"
    )
    parser.add_argument("--allow-untracked", action="store_true", help="warn instead of fail")
    parser.add_argument(
        "--isolated", action="store_true",
        help="run indexed lint, artifacts, pytest/type and installed-wheel checks; may download",
    )
    parser.add_argument(
        "pytest_args", nargs="*", help="arguments passed to pytest (prefix with --)"
    )
    args = parser.parse_args(argv)
    if args.isolated and args.skip_pytest:
        parser.error("--isolated requires the clean-export pytest run; omit --skip-pytest")

    problems: list[str] = []
    untracked = untracked_files()
    if untracked:
        label = "WARNING" if args.allow_untracked else "ERROR"
        print(f"{label}: untracked, non-ignored files are absent in CI:")
        for name in untracked:
            print(f"  {name}")
        if not args.allow_untracked:
            problems.append("untracked files (git add them or ignore them)")

    with tempfile.TemporaryDirectory(prefix="infinitydb-preflight-") as tmp:
        export = Path(tmp) / "checkout"
        export.mkdir()
        print("Exporting Git index...", flush=True)
        print(f"Exported {export_tracked(export)} tracked files to {export}", flush=True)

        wheel_dir = Path(tmp) / "wheel"
        wheel_problems = [] if args.skip_wheel else audit_wheel(export, wheel_dir)
        problems += wheel_problems

        if not args.skip_pytest:
            problems += check_export(
                export, Path(tmp) / "venv" if args.isolated else None, args.pytest_args,
                include_full_assets=args.assets == "required",
            )
        if args.isolated and not args.skip_wheel:
            if wheel_problems:
                print("Installed-wheel smoke skipped: wheel audit failed", flush=True)
            else:
                wheel = next(wheel_dir.glob("*.whl"))
                result = subprocess.run([
                    sys.executable, str(export / "tools/installed_wheel_smoke.py"),
                    "--wheel", str(wheel), "--source-root", str(export),
                    "--work-dir", str(Path(tmp) / "installed-wheel"), "--assets", args.assets,
                ], cwd=export, env={key: value for key, value in os.environ.items() if key not in {
                    "PYTHONPATH", "PYTHONHOME", "GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE",
                }})
                if result.returncode:
                    problems.append("installed-wheel CLI/runtime smoke failed")

    if problems:
        print("\nCI preflight FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nCI preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
