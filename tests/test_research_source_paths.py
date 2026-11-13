"""Hermetic tests for read-only physical paths with unchanged PDF provenance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.research.source_paths import POLICY, SourcePathError, pinned_pdf_path

LABEL = "data/pdf/rules/reviewed.pdf"
BODY = b"%PDF synthetic path-binding identity fixture"
DIGEST = hashlib.sha256(BODY).hexdigest()


def _pdf(root: Path, layout: str) -> Path:
    relative = LABEL if layout == "legacy" else "local/" + LABEL
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(BODY)
    return path


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_only_explicit_layout_is_selected_without_writes(tmp_path, layout):
    selected = _pdf(tmp_path, layout)
    alternate = _pdf(tmp_path, "local" if layout == "legacy" else "legacy")
    alternate.write_bytes(b"unreviewed alternative")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert pinned_pdf_path(tmp_path, LABEL, DIGEST, layout=layout) == selected
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_missing_selected_source_does_not_use_existing_alternative(tmp_path, layout):
    _pdf(tmp_path, "local" if layout == "legacy" else "legacy")
    with pytest.raises(SourcePathError, match="unavailable"):
        pinned_pdf_path(tmp_path, LABEL, DIGEST, layout=layout)
    assert pinned_pdf_path(tmp_path, LABEL, DIGEST, layout=layout, missing_ok=True) is None


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_hash_conflict_never_becomes_not_supplied(tmp_path, layout):
    selected = _pdf(tmp_path, layout)
    selected.write_bytes(b"different source revision")
    with pytest.raises(SourcePathError, match="hash mismatch"):
        pinned_pdf_path(tmp_path, LABEL, DIGEST, layout=layout, missing_ok=True)
    assert selected.read_bytes() == b"different source revision"


@pytest.mark.parametrize("label", [
    "../outside.pdf", "/data/pdf/rules/x.pdf", "C:/data/pdf/x.pdf",
    r"data\pdf\x.pdf", "data/pdf/../outside.pdf", "data/pdf/rules/./x.pdf",
    "data/pdf//x.pdf", "data/pdf/.stversions/x.pdf", "data/wiki/x.pdf",
    "local/data/pdf/rules/x.pdf", "data/pdf/rules/x.txt", "data/pdf",
])
def test_only_canonical_pdf_labels_are_accepted(tmp_path, label):
    with pytest.raises(SourcePathError):
        pinned_pdf_path(tmp_path, label, DIGEST)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("pin", ["", "f" * 63, "F" * 64, "not-a-sha", None])
def test_sha256_pin_is_required_before_source_access(tmp_path, pin):
    with pytest.raises(SourcePathError):
        pinned_pdf_path(tmp_path, LABEL, pin)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("layout", ["legacy", "local"])
@pytest.mark.parametrize("link", ["root", "directory", "file"])
def test_link_guards_apply_before_hashing(tmp_path, layout, link, monkeypatch):
    selected = _pdf(tmp_path, layout)
    guarded = {"root": tmp_path, "directory": selected.parent, "file": selected}[link]
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == guarded or original(path))
    with pytest.raises(SourcePathError, match="symlink"):
        pinned_pdf_path(tmp_path, LABEL, DIGEST, layout=layout)


@pytest.mark.parametrize("layout", ["legacy", "local"])
def test_real_staged_symlink_is_rejected(tmp_path, layout):
    selected = _pdf(tmp_path, layout)
    selected.unlink()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(BODY)
    try:
        selected.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Symlink privilege unavailable: {exc}")
    with pytest.raises(SourcePathError, match="symlink"):
        pinned_pdf_path(tmp_path, LABEL, DIGEST, layout=layout)


def test_existing_non_directory_parent_is_not_treated_as_missing(tmp_path):
    (tmp_path / "data").write_bytes(b"unexpected file")
    with pytest.raises(SourcePathError, match="not a directory"):
        pinned_pdf_path(tmp_path, LABEL, DIGEST, missing_ok=True)


def test_unreadable_path_is_not_treated_as_missing(tmp_path, monkeypatch):
    selected = _pdf(tmp_path, "legacy")
    original = Path.lstat

    def unreadable(path):
        if path == selected:
            raise PermissionError("synthetic unreadable source")
        return original(path)

    monkeypatch.setattr(Path, "lstat", unreadable)
    with pytest.raises(SourcePathError, match="Cannot inspect"):
        pinned_pdf_path(tmp_path, LABEL, DIGEST, missing_ok=True)


@pytest.mark.parametrize("guard", ["root", "directory", "file"])
def test_reparse_points_are_not_followed_even_when_not_posix_symlinks(tmp_path, guard, monkeypatch):
    selected = _pdf(tmp_path, "legacy")
    target = {"root": tmp_path, "directory": selected.parent, "file": selected}[guard]
    original = Path.lstat

    def reparse(path):
        info = original(path)
        if path == target:
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info

    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(SourcePathError, match="reparse point"):
        pinned_pdf_path(tmp_path, LABEL, DIGEST)


@pytest.mark.parametrize("defect", ["version", "root", "label", "duplicate", "unknown-layout"])
def test_policy_is_validated_without_fallback(tmp_path, defect):
    _pdf(tmp_path, "legacy")
    record = json.loads(POLICY.read_text(encoding="utf-8"))
    if defect == "version":
        record["formatVersion"] = True
    elif defect == "root":
        record["layouts"]["local"] = "../outside"
    elif defect == "label":
        record["sourceLabelPrefix"] = "local/data/pdf"
    elif defect == "unknown-layout":
        record["layouts"]["automatic"] = "data/pdf"
    payload = json.dumps(record)
    if defect == "duplicate":
        payload = payload.replace('"format":', '"format": "shadow", "format":', 1)
    policy = tmp_path / "policy.json"
    policy.write_text(payload, encoding="utf-8")
    with pytest.raises(SourcePathError):
        pinned_pdf_path(tmp_path, LABEL, DIGEST, policy=policy)


def test_unknown_selected_layout_is_not_an_automatic_search(tmp_path):
    _pdf(tmp_path, "legacy")
    with pytest.raises(SourcePathError, match="Unknown"):
        pinned_pdf_path(tmp_path, LABEL, DIGEST, layout="automatic")
