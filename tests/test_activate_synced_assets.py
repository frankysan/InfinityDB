"""Hermetic tests for explicit Syncthing source activation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.activate_synced_assets import main


@pytest.fixture
def staging(tmp_path: Path) -> tuple[Path, Path]:
    staged = tmp_path / "syncthing"
    checkout = tmp_path / "checkout"
    (staged / "snapshots").mkdir(parents=True)
    (staged / "raw").mkdir()
    checkout.mkdir()
    return staged, checkout


def _snapshot(staged: Path, name: str = "JSON 20260929-114335") -> tuple[str, Path]:
    archive = staged / "raw" / f"{name}.zip"
    archive.write_bytes(b"immutable test archive")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = {
        "format": "InfinityDB snapshot provenance",
        "formatVersion": 3,
        "snapshot": {
            "archive": {
                "name": archive.name,
                "path": f"data/raw/{archive.name}",
                "sha256": digest,
            }
        },
    }
    (staged / "snapshots" / f"{name}.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return name, archive


def _run(args: list[str], staged: Path, checkout: Path) -> int:
    return main(args, staging_root=staged, repo_root=checkout)


def test_worker_staging_root_environment_override(
    staging: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    staged, checkout = staging
    name, archive = _snapshot(staged)
    monkeypatch.setenv("INFINITYDB_SYNC_STAGING_ROOT", str(staged))
    assert main(["verify", "--snapshot", name], repo_root=checkout) == 0
    assert main(["activate", "--snapshot", name], repo_root=checkout) == 0
    assert archive.is_file()
    assert list(checkout.iterdir()) == []


def test_worker_staging_root_override_refuses_symlink(
    staging: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    staged, checkout = staging
    name, _ = _snapshot(staged)
    alias = staged.parent / "linked-staging"
    try:
        alias.symlink_to(staged, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlinks not available: {exc}")
    monkeypatch.setenv("INFINITYDB_SYNC_STAGING_ROOT", str(alias))
    assert main(["verify", "--snapshot", name], repo_root=checkout) == 1
    assert list(checkout.iterdir()) == []


def test_verify_snapshot_and_dry_run_do_not_modify_checkout(
    staging: tuple[Path, Path],
) -> None:
    staged, checkout = staging
    name, archive = _snapshot(staged)
    assert _run(["verify", "--snapshot", name], staged, checkout) == 0
    assert _run(["activate", "--snapshot", name], staged, checkout) == 0
    assert archive.exists()
    assert list(checkout.iterdir()) == []


def test_snapshot_activation_copies_both_and_is_idempotent(
    staging: tuple[Path, Path],
) -> None:
    staged, checkout = staging
    name, archive = _snapshot(staged)
    args = ["activate", "--snapshot", name, "--apply"]
    assert _run(args, staged, checkout) == 0
    target = checkout / "data/raw" / archive.name
    manifest = checkout / "data/manifests/snapshots" / f"{name}.json"
    assert target.read_bytes() == archive.read_bytes()
    assert manifest.is_file()
    assert not target.is_symlink()
    assert _run(args, staged, checkout) == 0


def test_hash_mismatch_blocks_both_files(staging: tuple[Path, Path]) -> None:
    staged, checkout = staging
    name, archive = _snapshot(staged)
    archive.write_bytes(b"wrong")
    assert _run(["activate", "--snapshot", name, "--apply"], staged, checkout) == 1
    assert not (checkout / "data").exists()


def test_existing_conflict_blocks_activation_without_overwrite(
    staging: tuple[Path, Path],
) -> None:
    staged, checkout = staging
    name, archive = _snapshot(staged)
    target = checkout / "data/raw" / archive.name
    target.parent.mkdir(parents=True)
    target.write_bytes(b"local version")
    assert _run(["activate", "--snapshot", name, "--apply"], staged, checkout) == 1
    assert target.read_bytes() == b"local version"
    assert not (checkout / "data/manifests").exists()


def test_symlink_mode_targets_staging_and_refuses_differing_link(
    staging: tuple[Path, Path],
) -> None:
    staged, checkout = staging
    name, archive = _snapshot(staged)
    args = ["activate", "--snapshot", name, "--mode", "symlink", "--apply"]
    probe = staged.parent / "symlink-probe"
    try:
        probe.symlink_to(archive)
    except OSError as exc:
        pytest.skip(f"Symlinks not available: {exc}")
    finally:
        probe.unlink(missing_ok=True)
    assert _run(args, staged, checkout) == 0
    target = checkout / "data/raw" / archive.name
    assert target.is_symlink()
    assert target.resolve() == archive.resolve()
    assert _run(args, staged, checkout) == 0
    target.unlink()
    different = checkout / "alternate.zip"
    different.write_bytes(b"alternate")
    target.symlink_to(different)
    assert _run(args, staged, checkout) == 1
    assert target.resolve() == different


def test_unpinned_pdf_requires_explicit_path(staging: tuple[Path, Path]) -> None:
    staged, checkout = staging
    (staged / "pdf" / "rules").mkdir(parents=True)
    (staged / "pdf" / "rules" / "n5.pdf").write_bytes(b"%PDF-example")
    assert _run(
        ["activate", "--file", "data/pdf/rules/n5.pdf", "--apply"],
        staged, checkout,
    ) == 0
    assert (checkout / "data/pdf/rules/n5.pdf").read_bytes() == b"%PDF-example"


@pytest.mark.parametrize(
    "path",
    [
        "../secret.txt",
        "data/pdf/../../secret.txt",
        "data/raw/sample.zip",
        "data/manifests/snapshots/test.json",
        "data/pdf/.stversions/deleted.pdf",
        "data\\pdf\\rules\\n5.pdf",
        "data/pdf/rules/invalid:part.pdf",
    ],
)
def test_unpinned_activation_rejects_unsafe_or_pinned_paths(
    staging: tuple[Path, Path], path: str
) -> None:
    staged, checkout = staging
    assert _run(["activate", "--file", path, "--apply"], staged, checkout) == 1
    assert list(checkout.iterdir()) == []


def test_rejects_staged_symlinks(staging: tuple[Path, Path]) -> None:
    staged, checkout = staging
    (staged / "pdf").mkdir()
    outside = staged.parent / "outside.pdf"
    outside.write_bytes(b"outside")
    try:
        (staged / "pdf" / "n5.pdf").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Symlinks not available: {exc}")
    assert _run(["activate", "--file", "data/pdf/n5.pdf", "--apply"], staged, checkout) == 1
    assert list(checkout.iterdir()) == []
