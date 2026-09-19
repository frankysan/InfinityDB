#!/usr/bin/env python3
"""Send ignored deployment artifacts to a matching remote checkout over one SSH session."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import tarfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from infinity_db.database import Database
from infinity_db.rules_database import RulesDatabase

try:
    from tools.verify_deployment_assets import verify_deployment_assets
except ImportError:  # pragma: no cover - direct script execution fallback
    from verify_deployment_assets import verify_deployment_assets

DEPLOYMENT_FILES = (
    "data/generated/infinity.db",
    "data/generated/rules.db",
    "data/manifests/army-symbol-build.json",
    "src/infinity_db/web/static/symbol-inventory.json",
)
DEPLOYMENT_TREES = (
    "src/infinity_db/web/static/armies",
    "src/infinity_db/web/static/characteristics",
    "src/infinity_db/web/static/orders",
    "src/infinity_db/web/static/units",
)
GIT_PATHS = (*DEPLOYMENT_FILES, *DEPLOYMENT_TREES)


class DeploymentTransferError(RuntimeError):
    """Raised when deployment artifacts cannot be transferred safely."""


def _run_git(project_root: Path, *args: str, text: bool = True) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), *args],
            check=True,
            capture_output=True,
            text=text,
        )
    except FileNotFoundError as exc:
        raise DeploymentTransferError("git executable was not found") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (
            exc.stderr.strip()
            if isinstance(exc.stderr, str)
            else exc.stderr.decode(errors="replace").strip()
        )
        raise DeploymentTransferError(f"git {' '.join(args)} failed: {stderr}") from exc
    return result.stdout


def _project_root(start: Path) -> Path:
    output = _run_git(start, "rev-parse", "--show-toplevel")
    assert isinstance(output, str)
    return Path(output.strip()).resolve()


def _require_clean_tracked_checkout(project_root: Path) -> str:
    status = _run_git(project_root, "status", "--porcelain", "--untracked-files=no")
    assert isinstance(status, str)
    if status.strip():
        raise DeploymentTransferError(
            "Tracked checkout changes are present; commit, stash, or discard them before transfer"
        )
    commit = _run_git(project_root, "rev-parse", "HEAD")
    assert isinstance(commit, str)
    return commit.strip()


def _ignored_deployment_files(project_root: Path) -> list[PurePosixPath]:
    output = _run_git(
        project_root,
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        "-z",
        "--",
        *GIT_PATHS,
        text=False,
    )
    assert isinstance(output, bytes)
    files = sorted(
        PurePosixPath(raw.decode("utf-8", "surrogateescape"))
        for raw in output.split(b"\0")
        if raw
    )
    return files


def _validate_paths(project_root: Path, files: Iterable[PurePosixPath]) -> list[PurePosixPath]:
    selected = list(files)
    selected_set = set(selected)
    for relative in DEPLOYMENT_FILES:
        path = PurePosixPath(relative)
        if path not in selected_set:
            raise DeploymentTransferError(
                f"Required ignored deployment artifact is missing or no longer ignored: {relative}"
            )

    for tree in DEPLOYMENT_TREES:
        prefix = PurePosixPath(tree)
        tree_files = [path for path in selected if path.is_relative_to(prefix)]
        if not tree_files:
            raise DeploymentTransferError(f"Required ignored deployment tree is empty: {tree}")
        invalid = [path for path in tree_files if path.suffix.lower() != ".svg"]
        if invalid:
            raise DeploymentTransferError(
                f"Deployment symbol tree contains non-SVG ignored file: {invalid[0]}"
            )

    for relative in selected:
        local = project_root.joinpath(*relative.parts)
        if not local.is_file():
            raise DeploymentTransferError(f"Selected deployment artifact is not a file: {relative}")
    return selected


def _validate_local_artifacts(project_root: Path) -> None:
    verify_deployment_assets(
        project_root / "data" / "manifests" / "army-symbol-build.json",
        project_root / "src" / "infinity_db" / "web" / "static",
        project_root=project_root,
    )
    Database(project_root / "data" / "generated" / "infinity.db").validate()
    RulesDatabase(project_root / "data" / "generated" / "rules.db").validate()


def _normalized_tarinfo(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.mode = 0o644
    return info


def write_archive(
    project_root: Path,
    files: Iterable[PurePosixPath],
    output: BinaryIO,
) -> None:
    """Write a deterministic tar stream containing only the selected deployment files."""

    with tarfile.open(fileobj=output, mode="w|") as archive:
        for relative in sorted(files):
            local = project_root.joinpath(*relative.parts)
            archive.add(
                local,
                arcname=relative.as_posix(),
                recursive=False,
                filter=_normalized_tarinfo,
            )


def _remote_script(remote_root: str, expected_commit: str) -> str:
    root = shlex.quote(remote_root)
    commit = shlex.quote(expected_commit)
    file_checks = "\n".join(
        (
            f"[ -f \"$stage/{path}\" ] || {{ "
            f"echo 'Missing transferred artifact: {path}' >&2; exit 4; }}"
        )
        for path in DEPLOYMENT_FILES
    )
    tree_checks = "\n".join(
        f"[ -d \"$stage/{path}\" ] || {{ echo 'Missing transferred tree: {path}' >&2; exit 4; }}"
        for path in DEPLOYMENT_TREES
    )
    replace_trees = "\n".join(
        f'''target="$root/{path}"
mkdir -p "$(dirname "$target")"
rm -rf "$target"
mv "$stage/{path}" "$target"'''
        for path in DEPLOYMENT_TREES
    )
    replace_files = "\n".join(
        f'''target="$root/{path}"
mkdir -p "$(dirname "$target")"
mv "$stage/{path}" "$target"'''
        for path in DEPLOYMENT_FILES
    )
    return f'''set -eu
root={root}
expected_commit={commit}
git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {{
  echo "Remote root is not a Git checkout: $root" >&2
  exit 3
}}
actual_commit=$(git -C "$root" rev-parse HEAD)
[ "$actual_commit" = "$expected_commit" ] || {{
  echo "Remote checkout commit $actual_commit does not match local $expected_commit" >&2
  exit 3
}}
[ -z "$(git -C "$root" status --porcelain --untracked-files=no)" ] || {{
  echo "Remote checkout has tracked changes; refusing artifact transfer" >&2
  exit 3
}}
stage=$(mktemp -d "$root/.deployment-artifacts.XXXXXX")
cleanup() {{ rm -rf "$stage"; }}
trap cleanup EXIT HUP INT TERM
tar -xf - -C "$stage"
{file_checks}
{tree_checks}
{replace_trees}
{replace_files}
printf 'Deployment artifacts installed for commit %s.\n' "$expected_commit"
'''


def _ssh_command(
    destination: str,
    remote_script: str,
    *,
    port: int | None,
    identity_file: Path | None,
) -> list[str]:
    command = ["ssh"]
    if port is not None:
        command.extend(["-p", str(port)])
    if identity_file is not None:
        command.extend(["-i", str(identity_file)])
    command.extend([destination, f"sh -c {shlex.quote(remote_script)}"])
    return command


def transfer(
    project_root: Path,
    files: list[PurePosixPath],
    *,
    destination: str,
    remote_root: str,
    commit: str,
    port: int | None = None,
    identity_file: Path | None = None,
) -> None:
    script = _remote_script(remote_root, commit)
    command = _ssh_command(destination, script, port=port, identity_file=identity_file)
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise DeploymentTransferError("ssh executable was not found") from exc
    assert process.stdin is not None
    try:
        write_archive(project_root, files, process.stdin)
    except BrokenPipeError:
        pass
    finally:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
    result = process.wait()
    if result != 0:
        raise DeploymentTransferError(f"ssh transfer failed with exit code {result}")


def _total_bytes(project_root: Path, files: Iterable[PurePosixPath]) -> int:
    return sum(project_root.joinpath(*path.parts).stat().st_size for path in files)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", help="SSH destination, for example root@docker-infinitydb")
    parser.add_argument(
        "--remote-root",
        default="/srv/infinitydb",
        help="Matching remote Git checkout (default: /srv/infinitydb)",
    )
    parser.add_argument("--port", type=int, help="Optional SSH port")
    parser.add_argument("--identity-file", type=Path, help="Optional SSH private key")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and list the exact ignored deployment artifacts without connecting",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = _project_root(Path.cwd())
        commit = _require_clean_tracked_checkout(root)
        files = _validate_paths(root, _ignored_deployment_files(root))
        _validate_local_artifacts(root)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    total = _total_bytes(root, files)
    print(
        f"Deployment artifact set: {len(files)} files, {total:,} bytes; "
        f"commit {commit[:12]}"
    )
    if args.dry_run:
        for path in files:
            print(path.as_posix())
        return 0

    if not args.remote_root.startswith("/"):
        print("ERROR: --remote-root must be an absolute POSIX path", file=sys.stderr)
        return 2
    if args.port is not None and not 1 <= args.port <= 65535:
        print("ERROR: --port must be between 1 and 65535", file=sys.stderr)
        return 2
    identity_file = args.identity_file.expanduser().resolve() if args.identity_file else None
    if identity_file is not None and not identity_file.is_file():
        print(f"ERROR: SSH identity file does not exist: {identity_file}", file=sys.stderr)
        return 2

    try:
        transfer(
            root,
            files,
            destination=args.destination,
            remote_root=args.remote_root,
            commit=commit,
            port=args.port,
            identity_file=identity_file,
        )
    except DeploymentTransferError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Transferred deployment artifacts to {args.destination}:{args.remote_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
