"""One-time Windows Syncthing sender path migration tests (offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.operations import cutover_syncthing_sender as cutover


def _fixtures(tmp_path: Path) -> tuple[Path, list[dict]]:
    folders = []
    for index, (old, new) in enumerate(cutover.FOLDERS.values(), start=1):
        source = tmp_path / new
        source.mkdir(parents=True)
        (source / "source.zip").write_bytes(b"source")
        folders.append({
            "id": f"folder-{index}", "path": str(tmp_path / old), "type": "sendonly",
        })
    return tmp_path, folders


def test_preview_and_apply_change_only_sender_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, folders = _fixtures(tmp_path)
    calls: list[tuple[str, dict | None]] = []

    def request(_endpoint, path: str, payload=None):
        calls.append((path, payload))
        if path == "/rest/config/folders":
            return folders
        folder = next(item for item in folders if path.endswith(item["id"]))
        if payload is not None:
            folder.update(payload)
        return folder

    monkeypatch.setattr(cutover, "_request", request)
    endpoint = ("http://127.0.0.1:8384", "private-token")
    planned = cutover.cutover(root, endpoint, apply=False)
    assert len(planned) == 4
    assert not any(folder.get("path", "").startswith(str(root / "local")) for folder in folders)
    assert len(calls) == 1
    assert all(not (root / new / ".stfolder").exists() for _, new in cutover.FOLDERS.values())

    updated = cutover.cutover(root, endpoint, apply=True)
    assert len(updated) == 4
    for folder, (_old, new) in zip(folders, cutover.FOLDERS.values(), strict=True):
        assert folder["path"] == str(root / new)
        assert folder["type"] == "sendonly"
        assert (root / new / ".stfolder").is_dir()
    assert cutover.cutover(root, endpoint, apply=True) == []


def test_missing_source_or_wrong_mode_refuses_before_changes(tmp_path: Path) -> None:
    root, folders = _fixtures(tmp_path)
    folders[0]["type"] = "receiveonly"
    with pytest.raises(ValueError, match="sender config"):
        cutover._plan(root, folders)
    folders[0]["type"] = "sendonly"
    (root / "local/data/raw/source.zip").unlink()
    with pytest.raises(ValueError, match="missing or empty"):
        cutover._plan(root, folders)


def test_duplicate_sender_folder_refuses_ambiguous_match(tmp_path: Path) -> None:
    root, folders = _fixtures(tmp_path)
    folders.append(dict(folders[0], id="other"))
    with pytest.raises(ValueError, match="one matching sender"):
        cutover._plan(root, folders)
