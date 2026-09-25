from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

from tools.create_work_archive import create_work_archive, work_archive_files


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / ".gitignore").write_text("ignored/\n*.zip\n", encoding="utf-8")
    (root / "tracked.txt").write_text("tracked", encoding="utf-8")
    _git(root, "add", ".gitignore", "tracked.txt")
    _git(root, "commit", "-m", "baseline")
    return root


def test_work_archive_files_include_tracked_and_nonignored_untracked(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "untracked.txt").write_text("untracked", encoding="utf-8")
    (root / "ignored").mkdir()
    (root / "ignored" / "cache.bin").write_bytes(b"ignored")
    (root / ".git" / "desktop.ini").write_text("not a ref", encoding="utf-8")

    names = {path.relative_to(root).as_posix() for path in work_archive_files(root)}

    assert names == {".gitignore", "tracked.txt", "untracked.txt"}


def test_work_archive_is_deterministic_and_excludes_git_metadata(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "untracked.txt").write_text("untracked", encoding="utf-8")
    first = create_work_archive(root, tmp_path / "first.zip")
    second = create_work_archive(root, tmp_path / "second.zip")

    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert names == [".gitignore", "tracked.txt", "untracked.txt"]
        assert not any(name == ".git" or name.startswith(".git/") for name in names)
