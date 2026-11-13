"""Safety and output-contract checks for read-only receiver readiness inspection."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.operations import audit_syncthing_receiver as audit


def _receiver(root: Path) -> Path:
    root.mkdir()
    for folder in audit.FOLDERS:
        (root / folder).mkdir()
    for relative in audit.PROBES.values():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"private source evidence fixture")
    return root


def test_read_only_receiver_probe_reports_only_fixed_labels_and_keeps_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _receiver(tmp_path / "receiver")
    before = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*") if path.is_file()
    }
    monkeypatch.setattr(audit, "_acl_evidence", lambda _path, _user: {
        "status": "available", "access": "r-x", "default": "r-x",
    })
    report = audit.inspect_receiver(root, user="mcpworker")
    assert report["inspector"] == "mcpworker"
    assert report["scope"] == "read-only-receiver-access-not-backup-or-sync-certification"
    assert set(report["folders"]) == set(audit.FOLDERS)
    assert set(report["selected_input_paths"]) == set(audit.PROBES)
    assert all(row["status"] == "present" for row in report["folders"].values())
    assert all(row["status"] == "present" for row in report["selected_input_paths"].values())
    assert report["recursive_acl_verified"] is False
    assert report["syncthing_live_status_verified"] is False
    assert report["independent_backup_restore_verified"] is False
    # No private payload paths or bytes appear in the structured public summary.
    output = json.dumps(report)
    assert "private source evidence fixture" not in output
    assert "JSON 20260929" not in output
    assert {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*") if path.is_file()
    } == before


def test_probe_distinguishes_missing_source_from_missing_family(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _receiver(tmp_path / "receiver")
    (root / "pdf/rules/n5-rules-v5.3-en.pdf").unlink()
    (root / "wiki").rmdir()
    monkeypatch.setattr(audit, "_acl_evidence", lambda _path, _user: {
        "status": "tool-unavailable", "access": None, "default": None,
    })
    report = audit.inspect_receiver(root, user="mcpworker")
    assert report["folders"]["wiki"] == {"status": "missing"}
    assert report["selected_input_paths"]["n5.3-english-pdf"] == {"status": "missing"}
    assert report["folders"]["raw"]["named_acl"]["status"] == "tool-unavailable"


def test_linked_family_is_not_followed(tmp_path: Path) -> None:
    root = _receiver(tmp_path / "receiver")
    (root / "pdf/rules/n5-rules-v5.3-en.pdf").unlink()
    (root / "pdf/rules").rmdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "pdf/rules").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink unavailable: {exc}")
    report = audit.inspect_receiver(root, user="mcpworker")
    assert report["selected_input_paths"]["n5.3-english-pdf"]["status"] == "link-refused"


def test_root_link_refused(tmp_path: Path) -> None:
    root = _receiver(tmp_path / "receiver")
    link = tmp_path / "linked"
    try:
        link.symlink_to(root, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"Symlink unavailable: {exc}")
    with pytest.raises(audit.ReceiverAuditError, match="symlink"):
        audit.inspect_receiver(link)


def test_getfacl_reports_only_inspector_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit.shutil, "which", lambda _name: "/usr/bin/getfacl")
    captured: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> SimpleNamespace:
        captured.append(args)
        return SimpleNamespace(
            returncode=0,
            stdout=chr(10).join((
                "user::rwx", "user:another:rwx", "user:mcpworker:r-x",
                "default:user:mcpworker:r-x", "mask::r-x",
            )),
        )

    monkeypatch.setattr(audit.subprocess, "run", fake_run)
    assert audit._acl_evidence(tmp_path, "mcpworker") == {
        "status": "available", "access": "r-x", "default": "r-x",
    }
    assert captured == [["/usr/bin/getfacl", "-c", str(tmp_path)]]


def test_no_config_does_not_search_implicit_staging(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("INFINITYDB_SYNC_STAGING_ROOT", raising=False)
    assert audit.main([]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "unavailable", "reason": "staging-root-not-configured",
    }
