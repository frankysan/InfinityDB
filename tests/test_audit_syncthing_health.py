"""Hermetic status checks: local-only API, redaction, and role/path boundaries."""
from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

from tools.operations import audit_syncthing_health as health


def _config(
    tmp_path: Path, root: Path, role: str, *, gui_address: str = "127.0.0.1:8384",
) -> Path:
    document = ET.Element("configuration")
    gui = ET.SubElement(document, "gui", {"enabled": "true", "tls": "false"})
    ET.SubElement(gui, "address").text = gui_address
    ET.SubElement(gui, "apikey").text = "never-print-this-token"
    for family, (sender, receiver) in health.FAMILIES.items():
        relative = sender if role == "sender" else receiver
        folder = ET.SubElement(document, "folder", {
            "id": f"infinity-{family}", "path": str(root / relative),
            "type": "sendonly" if role == "sender" else "receiveonly",
            "paused": "false",
        })
        ET.SubElement(folder, "versioning", {
            "type": "simple" if family == "wiki" else "",
        })
    config = tmp_path / "config.xml"
    ET.ElementTree(document).write(config, encoding="utf-8")
    return config


def test_override_sender_is_in_symbol_tools_not_main_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "InfinityDB"
    config = _config(tmp_path, root, "sender")
    tree = ET.parse(config)
    folder = next(
        item for item in tree.getroot().findall("folder")
        if item.get("id") == "infinity-image-overrides"
    )
    folder.set("path", str(root / "image_overrides"))
    tree.write(config)
    monkeypatch.setattr(health, "_live_status", lambda *_args: {"status": "available"})
    report = health.inspect(config, role="sender", sender_root=root)
    assert report["folders"]["image-overrides"] == {"status": "missing"}


@pytest.mark.parametrize("role", ["sender", "receiver"])
def test_inspects_exact_five_roles_and_reports_versioning_without_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str,
) -> None:
    root = tmp_path / "sources"
    config = _config(tmp_path, root, role)
    called: list[str] = []

    def fake_status(endpoint: tuple[str, str], folder_id: str) -> dict[str, Any]:
        assert endpoint == ("http://127.0.0.1:8384", "never-print-this-token")
        called.append(folder_id)
        return {"status": "available", "state": "idle", "needFiles": 0}

    monkeypatch.setattr(health, "_live_status", fake_status)
    report = health.inspect(
        config, role=role, sender_root=root, receiver_root=root,
    )
    assert report["status"] == "inspected"
    assert report["gui"] == "configured-local"
    assert set(report["folders"]) == set(health.FAMILIES)
    assert len(called) == len(health.FAMILIES)
    assert all(row["mode_matches_role"] for row in report["folders"].values())
    assert all(row["paused"] is False for row in report["folders"].values())
    assert report["folders"]["wiki"]["versioning"] is True
    assert report["folders"]["raw"]["versioning"] is False
    assert all(row["live"]["status"] == "available" for row in report["folders"].values())
    assert "never-print-this-token" not in json.dumps(report)
    assert str(root) not in json.dumps(report)


@pytest.mark.parametrize("address", [
    "remote.example:8384", "https://remote.example:8384", "127.0.0.1:abc",
    "127.0.0.1:8384/elsewhere", "127.0.0.1:8384?redirect=http://remote",
])
def test_gui_rejects_nonlocal_and_invalid_address(
    tmp_path: Path, address: str,
) -> None:
    root = tmp_path / "sources"
    config = _config(tmp_path, root, "sender", gui_address=address)
    report = health.inspect(config, role="sender", sender_root=root)
    assert report["gui"] == "unavailable-or-not-local"
    assert all(
        row["live"]["status"] == "gui-unavailable"
        for row in report["folders"].values()
    )
    assert "never-print-this-token" not in json.dumps(report)


def test_live_api_is_loopback_get_with_no_proxy_no_redirect_and_redacted_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[urllib.request.Request] = []
    handlers: list[Any] = []

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def read(self, _limit: int) -> bytes:
            return json.dumps({
                "state": "idle", "globalFiles": 10, "localFiles": 10,
                "needFiles": 0, "needBytes": 0, "pullErrors": 0,
                "invalid": "", "untrusted": "must-not-be-repeated",
            }).encode()

    class Opener:
        def open(self, request: urllib.request.Request, *, timeout: int) -> Response:
            assert timeout == 2
            captured.append(request)
            return Response()

    def fake_opener(*args: Any) -> Opener:
        handlers.extend(args)
        return Opener()

    monkeypatch.setattr(health.urllib.request, "build_opener", fake_opener)
    result = health._live_status(("http://127.0.0.1:8384", "SECRET"), "abc-def")
    assert result == {
        "status": "available", "state": "idle", "globalFiles": 10,
        "localFiles": 10, "needFiles": 0, "needBytes": 0,
        "pullErrors": 0, "invalid": False,
    }
    assert len(captured) == 1
    assert captured[0].full_url == "http://127.0.0.1:8384/rest/db/status?folder=abc-def"
    assert captured[0].get_method() == "GET"
    assert captured[0].get_header("X-api-key") == "SECRET"
    assert any(isinstance(handler, health._NoRedirect) for handler in handlers)
    assert any(isinstance(handler, urllib.request.ProxyHandler) for handler in handlers)
    assert health._NoRedirect().redirect_request(
        captured[0], None, 302, "redirect", {}, "https://remote.example/"
    ) is None
    assert "SECRET" not in json.dumps(result)
    assert "must-not-be-repeated" not in json.dumps(result)


def test_missing_or_ambiguous_family_and_mismatched_mode_do_not_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "sources"
    config = _config(tmp_path, root, "sender")
    xml = ET.parse(config)
    document = xml.getroot()
    folders = document.findall("folder")
    folders[0].set("type", "receiveonly")
    document.remove(folders[1])
    document.append(ET.fromstring(ET.tostring(folders[2])))
    xml.write(config)
    monkeypatch.setattr(
        health, "_live_status",
        lambda _endpoint, _folder: {"status": "available"},
    )
    report = health.inspect(config, role="sender", sender_root=root)
    assert report["folders"]["raw"]["mode_matches_role"] is False
    assert report["folders"]["wiki"] == {"status": "missing"}
    assert report["folders"]["pdf"] == {"status": "ambiguous"}


def test_unreadable_config_and_receiver_without_root_fail_closed(
    tmp_path: Path,
) -> None:
    assert health.inspect(
        tmp_path / "missing", role="sender", sender_root=tmp_path,
    ) == {"role": "sender", "status": "unavailable", "reason": "config-not-readable"}
    assert health.inspect(
        tmp_path / "missing", role="receiver",
    ) == {
        "role": "receiver", "status": "unavailable",
        "reason": "receiver-root-not-configured",
    }
    with pytest.raises(ValueError, match="unsupported role"):
        health.inspect(tmp_path / "missing", role="both")


def test_cli_does_not_guess_a_receiver_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("INFINITYDB_SYNC_STAGING_ROOT", raising=False)
    monkeypatch.setattr(health, "_discover_config", lambda: tmp_path / "config.xml")
    assert health.main(["--role", "receiver"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["reason"] == "receiver-root-not-configured"
