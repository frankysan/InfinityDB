from __future__ import annotations

import io
import tarfile
from pathlib import Path, PurePosixPath

import pytest

from tools.send_deployment_artifacts import (
    DEPLOYMENT_FILES,
    DeploymentTransferError,
    _remote_script,
    _validate_paths,
    write_archive,
)


def test_validate_paths_requires_complete_deployment_scope(tmp_path: Path) -> None:
    files = [PurePosixPath(path) for path in DEPLOYMENT_FILES]
    for relative in files:
        target = tmp_path.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"asset")

    assert _validate_paths(tmp_path, files) == files

    with pytest.raises(DeploymentTransferError, match="missing or no longer ignored"):
        _validate_paths(tmp_path, files[1:])


def test_transfer_scope_excludes_tracked_symbol_publication() -> None:
    assert PurePosixPath("src/infinity_db/web/static/symbol-inventory.json") not in {
        PurePosixPath(path) for path in DEPLOYMENT_FILES
    }
    assert all(not path.startswith("src/infinity_db/web/static/") for path in DEPLOYMENT_FILES)


def test_archive_is_deterministic_and_repository_relative(tmp_path: Path) -> None:
    first = PurePosixPath("data/generated/infinity.db")
    second = PurePosixPath("src/infinity_db/web/static/units/demo.svg")
    for relative, contents in ((first, b"db"), (second, b"svg")):
        target = tmp_path.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents)

    left = io.BytesIO()
    right = io.BytesIO()
    write_archive(tmp_path, [second, first], left)
    write_archive(tmp_path, [first, second], right)
    assert left.getvalue() == right.getvalue()

    with tarfile.open(fileobj=io.BytesIO(left.getvalue()), mode="r:") as archive:
        members = archive.getmembers()
        assert [member.name for member in members] == [first.as_posix(), second.as_posix()]
        assert all(member.mtime == 0 for member in members)
        assert all(member.uid == 0 and member.gid == 0 for member in members)


def test_remote_script_requires_matching_clean_checkout_and_stages_before_replace() -> None:
    script = _remote_script("/srv/infinitydb", "a" * 40)
    assert 'git -C "$root" rev-parse HEAD' in script
    assert "does not match local" in script
    assert "status --porcelain --untracked-files=no" in script
    assert 'tar -xf - -C "$stage"' in script
    assert 'mv "$stage/data/generated/infinity.db" "$target"' in script
    assert "Deployment artifacts installed for commit" in script
