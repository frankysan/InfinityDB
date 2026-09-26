from __future__ import annotations

import hashlib
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


def test_work_archive_script_runs_from_repository_root(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    tools_dir = root / "tools"
    tools_dir.mkdir()
    source_root = Path(__file__).resolve().parents[1]
    (tools_dir / "create_work_archive.py").write_bytes(
        (source_root / "tools" / "create_work_archive.py").read_bytes()
    )
    (tools_dir / "snapshot_archive.py").write_bytes(
        (source_root / "tools" / "snapshot_archive.py").read_bytes()
    )
    output = tmp_path / "script.zip"

    result = subprocess.run(
        ["python", "tools/create_work_archive.py", "--output", str(output)],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.is_file()
    assert "Created" in result.stdout


def test_default_name_marks_dirty_worktree_with_content_fingerprint(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    revision = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    clean = create_work_archive(root)
    assert clean.name == f"InfinityDB-work-{revision}.zip"

    (root / "tracked.txt").write_text("changed", encoding="utf-8")
    dirty = create_work_archive(root)
    assert dirty.name.startswith(f"InfinityDB-work-{revision}-dirty-")
    assert dirty.name.endswith(".zip")
    fingerprint = dirty.stem.rsplit("-", maxsplit=1)[-1]
    assert len(fingerprint) == 12
    assert fingerprint == hashlib.sha256(dirty.read_bytes()).hexdigest()[:12]

    same = create_work_archive(root)
    assert same == dirty
    assert same.read_bytes() == dirty.read_bytes()

    (root / "tracked.txt").write_text("changed again", encoding="utf-8")
    changed_again = create_work_archive(root)
    assert changed_again.name != dirty.name


def test_default_name_reuses_identical_existing_archive_without_replace(
    tmp_path: Path, monkeypatch
) -> None:
    root = _repo(tmp_path)
    (root / "tracked.txt").write_text("changed", encoding="utf-8")
    first = create_work_archive(root)
    original_replace = Path.replace

    def reject_existing_destination(path: Path, target: Path) -> Path:
        if target.exists():
            raise PermissionError("simulated Windows existing-destination lock")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", reject_existing_destination)

    second = create_work_archive(root)

    assert second == first
    assert second.read_bytes() == first.read_bytes()


def test_default_name_refuses_different_existing_archive(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    archive = create_work_archive(root)
    archive.write_bytes(b"not the deterministic archive")

    try:
        create_work_archive(root)
    except RuntimeError as exc:
        assert "Refusing to replace existing work archive with different content" in str(exc)
    else:
        raise AssertionError("expected mismatched existing archive to be rejected")


def test_work_archive_normalizes_git_text_line_endings_but_preserves_binary(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / ".gitattributes").write_text("* text=auto\n*.bin binary\n", encoding="utf-8")
    (root / "tracked.txt").write_bytes(b"line one\nline two\n")
    (root / "payload.bin").write_bytes(b"binary\r\npayload")
    _git(root, "add", ".gitattributes", "tracked.txt", "payload.bin")
    _git(root, "commit", "-m", "attributes")

    lf_archive = create_work_archive(root, tmp_path / "lf.zip")
    (root / "tracked.txt").write_bytes(b"line one\r\nline two\r\n")
    crlf_archive = create_work_archive(root, tmp_path / "crlf.zip")

    assert lf_archive.read_bytes() == crlf_archive.read_bytes()
    with zipfile.ZipFile(crlf_archive) as archive:
        assert archive.read("tracked.txt") == b"line one\nline two\n"
        assert archive.read("payload.bin") == b"binary\r\npayload"
