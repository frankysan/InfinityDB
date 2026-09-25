from __future__ import annotations

import argparse
import hashlib
import subprocess
import zipfile
from pathlib import Path

try:
    from tools.snapshot_archive import _archive_info
except ModuleNotFoundError:
    from snapshot_archive import _archive_info

_COMPRESSION = zipfile.ZIP_DEFLATED
_COMPRESSLEVEL = 6


def _git_output(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def work_archive_files(root: Path) -> list[Path]:
    """Return tracked and non-ignored untracked work-tree files."""
    output = _git_output(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    paths = [root / Path(item.decode("utf-8")) for item in output.split(b"\0") if item]
    return [path for path in paths if path.is_file()]


def _worktree_dirty(root: Path) -> bool:
    """Return whether tracked or non-ignored untracked work differs from HEAD."""
    return bool(
        _git_output(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        )
    )


def create_work_archive(root: Path, destination: Path | None = None) -> Path:
    """Create a deterministic work-tree ZIP without Git metadata or ignored files."""
    root = root.resolve()
    revision = _git_output(root, "rev-parse", "--short=12", "HEAD").decode().strip()
    default_destination = destination is None
    archive = (
        root.parent / f".InfinityDB-work-{revision}.tmp.zip"
        if default_destination
        else destination
    )
    assert archive is not None
    archive = archive.resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)

    files = work_archive_files(root)
    with zipfile.ZipFile(
        archive,
        "w",
        compression=_COMPRESSION,
        compresslevel=_COMPRESSLEVEL,
    ) as output:
        for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
            arcname = path.relative_to(root).as_posix()
            output.writestr(
                _archive_info(arcname),
                path.read_bytes(),
                compress_type=_COMPRESSION,
                compresslevel=_COMPRESSLEVEL,
            )

    if not default_destination:
        return archive

    if _worktree_dirty(root):
        fingerprint = hashlib.sha256(archive.read_bytes()).hexdigest()[:12]
        final_archive = root.parent / f"InfinityDB-work-{revision}-dirty-{fingerprint}.zip"
    else:
        final_archive = root.parent / f"InfinityDB-work-{revision}.zip"
    archive.replace(final_archive)
    return final_archive.resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a deterministic InfinityDB work-tree archive."
    )
    parser.add_argument("--output", type=Path, help="Optional output ZIP path.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    files = work_archive_files(root)
    archive = create_work_archive(root, args.output)
    print(f"Created {archive} ({len(files)} files, {archive.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
