"""Hermetic tests for explicit Syncthing source activation."""

from __future__ import annotations

import json
import os
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import build_snapshot_manifest
from tools import activate_synced_assets as activation
from tools.activate_synced_assets import main


@pytest.fixture
def staging(tmp_path: Path) -> tuple[Path, Path]:
    staged = tmp_path / "syncthing"
    checkout = tmp_path / "checkout"
    (staged / "snapshots").mkdir(parents=True)
    (staged / "raw").mkdir()
    checkout.mkdir()
    return staged, checkout


def _snapshot(
    staged: Path, name: str = "JSON 20260929-114335", *,
    kind: str = "army", staged_folder: str = "raw", recorded_root: str | None = "data/raw",
) -> tuple[str, Path]:
    archive = staged / staged_folder / f"{name}.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w") as output:
        info = zipfile.ZipInfo("source.txt", date_time=(1980, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        output.writestr(info, b"immutable test archive")
    manifest = build_snapshot_manifest(
        archive, snapshot_type=kind,
        acquired_at=datetime(2026, 9, 29, 11, 43, 35, tzinfo=UTC),
        source_url="https://example.test/source", document_count=1,
        project_root=staged, language="en",
        source_data_changed_on=date(2026, 9, 3) if kind == "army" else None,
    )
    if recorded_root is None:
        manifest["snapshot"]["archive"].pop("path", None)
    else:
        manifest["snapshot"]["archive"]["path"] = f"{recorded_root}/{archive.name}"
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
    # A relative symlink to the same canonical source is also idempotent.
    target.unlink()
    target.symlink_to(Path(os.path.relpath(archive, target.parent)))
    assert target.resolve() == archive.resolve()
    assert _run(args, staged, checkout) == 0
    target.unlink()
    different = checkout / "alternate.zip"
    different.write_bytes(b"alternate")
    target.symlink_to(different)
    assert _run(args, staged, checkout) == 1
    assert target.resolve() == different


def test_unpinned_override_uses_configured_receiver_path(
    staging: tuple[Path, Path],
) -> None:
    staged, checkout = staging
    (staged / "image-overrides").mkdir()
    source = staged / "image-overrides" / "sample.svg"
    source.write_bytes(b"<svg>configured receiver</svg>")
    # A stale sibling must never be selected as an implicit fallback.
    (staged / "image_overrides").mkdir()
    (staged / "image_overrides" / "sample.svg").write_bytes(b"wrong sibling")

    args = ["activate", "--file", "image_overrides/sample.svg"]
    assert _run(args, staged, checkout) == 0
    assert list(checkout.iterdir()) == []
    assert _run([*args, "--apply"], staged, checkout) == 0
    assert (checkout / "image_overrides/sample.svg").read_bytes() == source.read_bytes()


def test_override_refuses_unconfigured_staging_sibling(
    staging: tuple[Path, Path],
) -> None:
    staged, checkout = staging
    (staged / "image_overrides").mkdir()
    (staged / "image_overrides" / "sample.svg").write_bytes(b"wrong sibling")
    assert _run(
        ["activate", "--file", "image_overrides/sample.svg", "--apply"],
        staged, checkout,
    ) == 1
    assert list(checkout.iterdir()) == []


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


@pytest.mark.parametrize("kind", ["army", "wiki", "symbols"])
@pytest.mark.parametrize(
    "selection", ["legacy", "local-old-path", "local-new-path", "local-no-path"],
)
def test_explicit_layout_roundtrip_preserves_pair_bytes(staging, kind, selection, capsys):
    staged, checkout = staging
    folders = {"army": "raw", "wiki": "wiki", "symbols": "raw/symbols"}
    old = {"army": "data/raw", "wiki": "data/wiki", "symbols": "data/raw/symbols"}
    new = {"army": "local/data/raw/army", "wiki": "local/data/wiki",
           "symbols": "local/data/raw/symbols"}
    recorded = new[kind] if selection == "local-new-path" else old[kind]
    if selection == "local-no-path":
        recorded = None
    name, archive = _snapshot(
        staged, f"{kind}-20260929-114335", kind=kind,
        staged_folder=folders[kind], recorded_root=recorded,
    )
    source_manifest = staged / "snapshots" / f"{name}.json"
    original = (archive.read_bytes(), source_manifest.read_bytes())
    layout = "legacy" if selection == "legacy" else "local"
    assert _run(["list", "--layout", layout], staged, checkout) == 0
    assert name in capsys.readouterr().out
    assert _run(["verify", "--layout", layout], staged, checkout) == 0
    args = ["activate", "--layout", layout, "--snapshot", name]
    assert _run(args, staged, checkout) == 0
    assert list(checkout.iterdir()) == []
    assert _run([*args, "--apply"], staged, checkout) == 0
    destination = old[kind] if layout == "legacy" else new[kind]
    manifests = (
        "data/manifests/snapshots" if layout == "legacy"
        else "local/data/manifests/snapshots"
    )
    assert (checkout / destination / archive.name).read_bytes() == original[0]
    assert (checkout / manifests / source_manifest.name).read_bytes() == original[1]
    assert _run([*args, "--apply"], staged, checkout) == 0
    assert (archive.read_bytes(), source_manifest.read_bytes()) == original
    if layout == "local":
        assert not (checkout / "data").exists()


def test_local_layout_never_follows_recorded_path_or_searches_siblings(staging):
    staged, checkout = staging
    name, archive = _snapshot(staged, recorded_root="data/raw/other")
    other = staged / "raw/other" / archive.name
    other.parent.mkdir()
    archive.rename(other)
    for action in ["verify", "activate"]:
        args = [action, "--layout", "local", "--snapshot", name]
        if action == "activate":
            args.append("--apply")
        assert _run(args, staged, checkout) == 1
    assert list(checkout.iterdir()) == []
    assert other.is_file()


@pytest.mark.parametrize("layout", ["legacy", "local"])
@pytest.mark.parametrize(
    "name", ["../outside", "dir/name", "C:/outside", r"dir\name", "", ".stversions"],
)
def test_snapshot_selector_rejects_unsafe_names(staging, layout, name):
    staged, checkout = staging
    assert _run(
        ["activate", "--layout", layout, "--snapshot", name, "--apply"], staged, checkout,
    ) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("layout", ["legacy", "local"])
@pytest.mark.parametrize("field,value", [
    ("path", "../outside.zip"), ("path", "/absolute.zip"),
    ("path", "C:/outside.zip"), ("path", r"data\raw\x.zip"),
    ("path", "data/raw/../outside.zip"), ("name", "../outside.zip"),
    ("name", "different.zip"),
])
def test_manifest_paths_cannot_redirect_activation(staging, layout, field, value):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    path = staged / "snapshots" / f"{name}.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["snapshot"]["archive"][field] = value
    path.write_text(json.dumps(document), encoding="utf-8")
    assert _run(
        ["activate", "--layout", layout, "--snapshot", name, "--apply"], staged, checkout,
    ) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("layout", ["legacy", "local"])
@pytest.mark.parametrize("failure", ["content-hash", "version", "type", "duplicate-key"])
def test_full_provenance_is_required_before_any_activation(staging, layout, failure):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    path = staged / "snapshots" / f"{name}.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if failure == "content-hash":
        document["snapshot"]["contentSha256"] = "f" * 64
    elif failure == "version":
        document["formatVersion"] = 999
    elif failure == "type":
        document["snapshot"]["type"] = "unknown"
    payload = json.dumps(document)
    if failure == "duplicate-key":
        payload = payload.replace('"format":', '"format": "shadow", "format":', 1)
    path.write_text(payload, encoding="utf-8")
    assert _run(
        ["activate", "--layout", layout, "--snapshot", name, "--apply"], staged, checkout,
    ) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_duplicate_explicit_snapshot_names_are_rejected(staging, layout):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    assert _run([
        "verify", "--layout", layout, "--snapshot", name, "--snapshot", name + ".json",
    ], staged, checkout) == 1
    assert list(checkout.iterdir()) == []


def test_case_colliding_manifest_inventory_is_rejected_on_case_sensitive_hosts(staging):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    path = staged / "snapshots" / f"{name}.json"
    second = path.with_name(name.swapcase() + ".json")
    second.write_bytes(path.read_bytes())
    if len(list(path.parent.iterdir())) != 2:
        pytest.skip("filesystem cannot represent case-colliding manifest names")
    assert _run(["list", "--layout", "local"], staged, checkout) == 1
    assert _run(["verify", "--layout", "local"], staged, checkout) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_manifest_destination_conflict_prevents_archive_copy(staging, layout):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    base = "data" if layout == "legacy" else "local/data"
    destination = checkout / base / "manifests/snapshots" / f"{name}.json"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"earlier provenance")
    assert _run(
        ["activate", "--layout", layout, "--snapshot", name, "--apply"], staged, checkout,
    ) == 1
    assert destination.read_bytes() == b"earlier provenance"
    assert not (checkout / base / "raw").exists()


@pytest.mark.parametrize("layout", ["legacy", "local"])
@pytest.mark.parametrize("source", ["archive", "manifest", "archive-directory", "checkout-root"])
def test_symlink_guard_runs_before_destination_creation(staging, layout, source, monkeypatch):
    staged, checkout = staging
    name, archive = _snapshot(staged)
    targets = {"archive": archive, "manifest": staged / "snapshots" / f"{name}.json",
               "archive-directory": archive.parent, "checkout-root": checkout}
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == targets[source] or original(path))
    assert _run(
        ["activate", "--layout", layout, "--snapshot", name, "--apply"], staged, checkout,
    ) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_inaccessible_staged_manifest_fails_without_checkout_writes(staging, layout, monkeypatch):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    target = staged / "snapshots" / f"{name}.json"
    original = Path.read_bytes

    def inaccessible(path):
        if path == target:
            raise PermissionError("staging access denied")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", inaccessible)
    assert _run(
        ["activate", "--layout", layout, "--snapshot", name, "--apply"], staged, checkout,
    ) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_archive_changed_after_preflight_is_not_published(staging, layout, monkeypatch):
    staged, checkout = staging
    name, archive = _snapshot(staged)
    original = activation._destination

    def mutate_after_preflight(root, relative, *, apply):
        result = original(root, relative, apply=apply)
        if relative.endswith(".zip") and not apply:
            archive.write_bytes(b"changed staged source")
        return result

    monkeypatch.setattr(activation, "_destination", mutate_after_preflight)
    assert _run(
        ["activate", "--layout", layout, "--snapshot", name, "--apply"], staged, checkout,
    ) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("field,value", [
    ("staging", "../outside"), ("staging", "/absolute"),
    ("staging", "raw/.stversions"), ("staging", "wiki"),
    ("destination", "../outside"), ("destination", "data/generated"),
    ("destination", "local/data/curated"), ("destination", r"local\data\raw"),
])
def test_layout_configuration_cannot_escape_permitted_families(staging, field, value):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    document = json.loads(activation.LAYOUT_CONFIG.read_text(encoding="utf-8"))
    document["layouts"]["local"]["archives"]["army"][field] = value
    config = staged.parent / "invalid-layouts.json"
    config.write_text(json.dumps(document), encoding="utf-8")
    assert main([
        "activate", "--layout", "local", "--snapshot", name, "--apply",
    ], staging_root=staged, repo_root=checkout, layout_config=config) == 1
    assert list(checkout.iterdir()) == []


def test_layout_configuration_selects_one_explicit_staged_location(staging):
    staged, checkout = staging
    name, archive = _snapshot(staged, staged_folder="raw/selected")
    document = json.loads(activation.LAYOUT_CONFIG.read_text(encoding="utf-8"))
    document["layouts"]["local"]["archives"]["army"]["staging"] = "raw/selected"
    config = staged.parent / "selected-layouts.json"
    config.write_text(json.dumps(document), encoding="utf-8")
    assert main([
        "activate", "--layout", "local", "--snapshot", name, "--apply",
    ], staging_root=staged, repo_root=checkout, layout_config=config) == 0
    assert (checkout / "local/data/raw/army" / archive.name).read_bytes() == archive.read_bytes()


@pytest.mark.parametrize("layout", ["legacy", "local"])
@pytest.mark.parametrize("version", [1, 2])
def test_supported_historical_manifests_keep_their_original_bytes(staging, layout, version):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    path = staged / "snapshots" / f"{name}.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["formatVersion"] = version
    document["source"].pop("dataChangedOn")
    if version == 1:
        document["snapshot"].pop("contentSha256")
    path.write_text(json.dumps(document), encoding="utf-8")
    before = path.read_bytes()
    assert _run([
        "activate", "--layout", layout, "--snapshot", name, "--apply",
    ], staged, checkout) == 0
    base = "data" if layout == "legacy" else "local/data"
    assert (checkout / base / "manifests/snapshots" / path.name).read_bytes() == before


def test_default_layout_never_implicitly_selects_local_paths(staging):
    staged, checkout = staging
    name, _ = _snapshot(staged, recorded_root="local/data/raw/army")
    assert _run(["activate", "--snapshot", name, "--apply"], staged, checkout) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("relative,folder", [
    ("data/pdf/rules/n5.pdf", "pdf/rules"),
    ("image_overrides/sample.svg", "image-overrides"),
])
def test_local_snapshot_layout_preserves_legacy_pdf_and_override_destinations(
    staging, relative, folder,
):
    staged, checkout = staging
    source = staged / folder / Path(relative).name
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"explicit unpinned test evidence")
    args = ["activate", "--layout", "local", "--file", relative]
    assert _run(args, staged, checkout) == 0
    assert list(checkout.iterdir()) == []
    assert _run([*args, "--apply"], staged, checkout) == 0
    assert (checkout / relative).read_bytes() == source.read_bytes()
    assert not (checkout / "local").exists()


@pytest.mark.parametrize(
    "failure", ["version", "unknown-layout", "pdf-relocation", "duplicate-key"],
)
def test_invalid_layout_policy_is_rejected_without_fallback(staging, failure):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    document = json.loads(activation.LAYOUT_CONFIG.read_text(encoding="utf-8"))
    if failure == "version":
        document["formatVersion"] = True
    elif failure == "unknown-layout":
        document["layouts"]["automatic"] = document["layouts"]["local"]
    elif failure == "pdf-relocation":
        document["layouts"]["local"]["files"] = {"local/data/pdf": "pdf"}
    payload = json.dumps(document)
    if failure == "duplicate-key":
        payload = payload.replace('"format":', '"format": "shadow", "format":', 1)
    config = staged.parent / "invalid-policy.json"
    config.write_text(payload, encoding="utf-8")
    assert main([
        "activate", "--layout", "local", "--snapshot", name, "--apply",
    ], staging_root=staged, repo_root=checkout, layout_config=config) == 1
    assert list(checkout.iterdir()) == []


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_changed_manifest_is_rejected_before_destination_creation(staging, layout, monkeypatch):
    staged, checkout = staging
    name, _ = _snapshot(staged)
    path = staged / "snapshots" / f"{name}.json"
    original = activation.validate_snapshot_manifest

    def change_manifest(document, *, archive=None):
        original(document, archive=archive)
        if archive is not None:
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    monkeypatch.setattr(activation, "validate_snapshot_manifest", change_manifest)
    assert _run([
        "activate", "--layout", layout, "--snapshot", name, "--apply",
    ], staged, checkout) == 1
    assert list(checkout.iterdir()) == []
