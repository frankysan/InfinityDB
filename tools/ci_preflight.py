#!/usr/bin/env python3
"""Reproduce clean-checkout and wheel-content CI conditions locally.

Local working trees contain Git-ignored and untracked files that CI never sees. This tool:

1. fails when non-ignored files are untracked (CI would not have them);
2. exports only Git-tracked files (index content) to a temporary directory and runs pytest there;
3. builds a wheel from that export and checks tracked package files plus configured
   setuptools shared data-files for presence in the wheel.

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
    packages = {
        p.parent.relative_to(export / "src").parts[0]
        for p in (export / "src").glob("*/__init__.py")
    }
    tracked = set(tracked_files())
    missing = []
    for name in sorted(tracked):
        if not name.startswith(PACKAGE_ROOT):
            continue
        relative = name[len(PACKAGE_ROOT) :]
        if relative.startswith(WHEEL_EXEMPT_PREFIXES):
            continue
        if relative.split("/")[0] in packages and relative not in members:
            missing.append(f"tracked package file not shipped in wheel: {relative}")

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "CI preflight").splitlines()[0])
    parser.add_argument("--skip-wheel", action="store_true", help="skip the wheel-content audit")
    parser.add_argument(
        "--skip-pytest", action="store_true", help="skip the clean-export pytest run"
    )
    parser.add_argument("--allow-untracked", action="store_true", help="warn instead of fail")
    parser.add_argument(
        "pytest_args", nargs="*", help="arguments passed to pytest (prefix with --)"
    )
    args = parser.parse_args(argv)

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
        print(f"Exported {export_tracked(export)} tracked files to {export}")

        if not args.skip_wheel:
            problems += audit_wheel(export, Path(tmp) / "wheel")

        if not args.skip_pytest:
            pytest = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", *args.pytest_args], cwd=export
            )
            if pytest.returncode != 0:
                problems.append(f"pytest failed in clean export (exit {pytest.returncode})")

    if problems:
        print("\nCI preflight FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nCI preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
