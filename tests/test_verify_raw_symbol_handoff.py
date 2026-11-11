"""Consumer-side acceptance of standalone raw SVG evidence without network access."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import sha256_file, write_snapshot_manifest
from tools.export_symbol_source_plan import FORMAT, VERSION
from tools.snapshot_archive import create_timestamped_archive
from tools.verify_raw_symbol_handoff import (
    REPORT_FORMAT,
    REPORT_VERSION,
    RawHandoffError,
    main,
    verify_raw_handoff,
)

STAMP = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
ROOT = "https://assets.corvusbelli.net/army/img/"
ICON = ROOT + "icon/cube.svg"
UNIT = ROOT + "logo/units/unit.svg"
ICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="2"/></svg>'
UNIT_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="1"/></svg>'


def _canonical(document: dict) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _handoff(
    tmp_path: Path, *, unavailable: bool = False, unit_body: bytes = UNIT_SVG,
) -> tuple[Path, Path, Path, Path, Path]:
    army = tmp_path / "JSON 20260917-120000.zip"
    with zipfile.ZipFile(army, "w") as output:
        output.writestr("metadata.json", "{}")
        output.writestr("101-panoceania.json", '{"version":"7.26246.158","units":[]}')
    requests = [
        {"url": ICON, "archivePath": "static/characteristics/cube.svg"},
        {"url": UNIT, "archivePath": "units/unit.svg"},
    ]
    plan = {
        "format": FORMAT,
        "formatVersion": VERSION,
        "inputArtifact": {"name": army.name, "sha256": sha256_file(army)},
        "sourceDocumentCount": 2,
        "requests": requests,
    }
    plan_path = tmp_path / "source-requests.json"
    plan_path.write_bytes(_canonical(plan))

    staged = tmp_path / "raw"
    (staged / "static/characteristics").mkdir(parents=True)
    icon = staged / "static/characteristics/cube.svg"
    icon.write_bytes(ICON_SVG)
    files = [icon]
    if not unavailable:
        (staged / "units").mkdir()
        unit = staged / "units/unit.svg"
        unit.write_bytes(unit_body)
        files.append(unit)

    symbol_archive = create_timestamped_archive(
        files, tmp_path / "symbols", prefix="SYMBOLS", root=staged, now=STAMP,
    )
    manifest = write_snapshot_manifest(
        symbol_archive, tmp_path / "manifests",
        snapshot_type="symbols", acquired_at=STAMP, source_url=ROOT,
        document_count=len(files), project_root=tmp_path,
        input_artifact=army,
    )
    assets = [
        {
            "url": ICON, "archivePath": "static/characteristics/cube.svg",
            "sha256": hashlib.sha256(ICON_SVG).hexdigest(),
            "sourceMethod": "network",
        },
    ]
    if not unavailable:
        assets.append({
            "url": UNIT, "archivePath": "units/unit.svg",
            "sha256": hashlib.sha256(unit_body).hexdigest(),
            "sourceMethod": "network",
        })
    report = {
        "format": REPORT_FORMAT,
        "formatVersion": REPORT_VERSION,
        "inputArtifact": dict(plan["inputArtifact"]),
        "sourcePlanSha256": hashlib.sha256(_canonical(plan)).hexdigest(),
        "snapshot": {
            "archiveName": symbol_archive.name,
            "sha256": sha256_file(symbol_archive),
            "snapshotManifestName": manifest.name,
            "snapshotManifestSha256": sha256_file(manifest),
            "documentCount": len(files),
            "acquiredAt": STAMP.isoformat(timespec="seconds"),
        },
        "assets": assets,
        "unavailableAssets": (
            [{"url": UNIT, "archivePath": "units/unit.svg", "httpStatus": 404}]
            if unavailable else []
        ),
    }
    report_path = tmp_path / "symbols.raw-report.json"
    report_path.write_bytes(_canonical(report))
    return plan_path, army, symbol_archive, manifest, report_path


def _mutate_json(path: Path, change) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    change(document)
    path.write_bytes(_canonical(document))


def test_raw_handoff_accepts_pinned_svg_archive_and_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    args = _handoff(tmp_path)
    assert verify_raw_handoff(*args) == {"requested": 2, "acquired": 2, "unavailable": 0}
    assert main([
        "--plan", str(args[0]), "--army", str(args[1]),
        "--archive", str(args[2]), "--manifest", str(args[3]),
        "--report", str(args[4]),
    ]) == 0
    assert "2 acquired, 0 unavailable" in capsys.readouterr().out


def test_raw_handoff_accepts_recorded_http_404(tmp_path: Path) -> None:
    args = _handoff(tmp_path, unavailable=True)
    assert verify_raw_handoff(*args) == {"requested": 2, "acquired": 1, "unavailable": 1}


def test_raw_handoff_rejects_modified_input_army(tmp_path: Path) -> None:
    args = _handoff(tmp_path)
    with args[1].open("ab") as output:
        output.write(b"tampered")
    with pytest.raises(RawHandoffError, match="Army source-plan artifact"):
        verify_raw_handoff(*args)


def test_raw_handoff_rejects_modified_symbol_archive(tmp_path: Path) -> None:
    args = _handoff(tmp_path)
    with zipfile.ZipFile(args[2], "a") as output:
        output.writestr("unapproved.svg", UNIT_SVG)
    with pytest.raises(RawHandoffError, match="archive/provenance identity mismatch"):
        verify_raw_handoff(*args)


def test_raw_handoff_rejects_report_with_wrong_plan_digest(tmp_path: Path) -> None:
    args = _handoff(tmp_path)
    _mutate_json(args[4], lambda doc: doc.__setitem__("sourcePlanSha256", "0" * 64))
    with pytest.raises(RawHandoffError, match="source-plan SHA-256 mismatch"):
        verify_raw_handoff(*args)


def test_raw_handoff_rejects_wrong_member_digest(tmp_path: Path) -> None:
    args = _handoff(tmp_path)
    _mutate_json(args[4], lambda doc: doc["assets"][0].__setitem__("sha256", "0" * 64))
    with pytest.raises(RawHandoffError, match="Raw SVG member SHA-256 mismatch"):
        verify_raw_handoff(*args)


def test_raw_handoff_rejects_omitted_request(tmp_path: Path) -> None:
    args = _handoff(tmp_path, unavailable=True)
    _mutate_json(args[4], lambda doc: doc["unavailableAssets"].clear())
    with pytest.raises(RawHandoffError, match="did not account for every requested URL"):
        verify_raw_handoff(*args)


def test_raw_handoff_rejects_non_404_unavailability(tmp_path: Path) -> None:
    args = _handoff(tmp_path, unavailable=True)
    _mutate_json(
        args[4], lambda doc: doc["unavailableAssets"][0].__setitem__("httpStatus", 500),
    )
    with pytest.raises(RawHandoffError, match="Unapproved unavailable source"):
        verify_raw_handoff(*args)


def test_raw_handoff_rejects_non_svg_raw_bytes(tmp_path: Path) -> None:
    args = _handoff(tmp_path, unit_body=b"<html>not an SVG</html>")
    with pytest.raises(RawHandoffError, match="Raw member is not SVG"):
        verify_raw_handoff(*args)


def test_raw_handoff_rejects_wrong_snapshot_manifest_binding(tmp_path: Path) -> None:
    args = _handoff(tmp_path)
    _mutate_json(
        args[3], lambda doc: doc["inputArtifact"].__setitem__("sha256", "0" * 64),
    )
    _mutate_json(
        args[4],
        lambda doc: doc["snapshot"].__setitem__(
            "snapshotManifestSha256", sha256_file(args[3]),
        ),
    )
    with pytest.raises(RawHandoffError, match="not bound to the pinned Army"):
        verify_raw_handoff(*args)
