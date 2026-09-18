import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import write_snapshot_manifest
from infinity_db.symbol_manifest import (
    build_symbol_manifest,
    load_symbol_manifest,
    write_symbol_manifest,
)
from tools.symbol_work import audit_symbol_work, materialize_symbol_archive


def _discovery_audit(asset_count: int) -> dict[str, int]:
    return {
        "unitProfileReferenceCount": 0,
        "uniqueUnitUrlCount": 0,
        "factionReferenceCount": 0,
        "uniqueFactionUrlCount": 0,
        "semanticReferenceCount": 0,
        "uniqueSemanticUrlCount": 0,
        "resumeReferenceCount": 0,
        "uniqueResumeUrlCount": 0,
        "staticReferenceCount": 0,
        "recursiveReferenceCount": 0,
        "uniqueRecursiveUrlCount": 0,
        "uniqueDownloadedUrlCount": asset_count,
        "unknownReferenceCount": 0,
    }


def _fixture(tmp_path: Path, members: dict[str, bytes]) -> tuple[Path, Path, Path]:
    army = tmp_path / "JSON 20260918-120000.zip"
    army.write_bytes(b"army")
    symbols = tmp_path / "SYMBOLS 20260918-120100.zip"
    with zipfile.ZipFile(symbols, "w") as output:
        for name, body in members.items():
            output.writestr(name, body)

    assets = [
        {
            "url": f"https://assets.corvusbelli.net/army/img/logo/{index}.svg",
            "sourceFilename": Path(name).name,
            "archivePath": name,
            "sha256": hashlib.sha256(body).hexdigest(),
            "sourceMethod": "network",
        }
        for index, (name, body) in enumerate(sorted(members.items()))
    ]
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 18, 12, 1, tzinfo=UTC),
        army_acquired_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        army_language="en",
        army_source_url="https://api.corvusbelli.com/army",
        source_document_count=2,
        source_revisions={"7.26246.158": 1},
        assets=assets,
        references=[],
        audit=_discovery_audit(len(assets)),
        project_root=tmp_path,
    )
    manifest = tmp_path / "data" / "manifests" / "army-symbol-build.json"
    write_symbol_manifest(document, manifest)
    snapshot_manifest = write_snapshot_manifest(
        symbols,
        tmp_path / "data" / "manifests" / "snapshots",
        snapshot_type="symbols",
        acquired_at=datetime(2026, 9, 18, 12, 1, tzinfo=UTC),
        source_url="https://assets.corvusbelli.net/army/img/",
        document_count=len(assets),
        project_root=tmp_path,
        input_artifact=army,
    )
    return symbols, snapshot_manifest, manifest


def test_materialize_symbol_archive_verifies_and_rebuilds_work_tree(tmp_path: Path) -> None:
    body = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'
    archive, snapshot_manifest, manifest = _fixture(
        tmp_path, {"units/example.svg": body}
    )
    work_base = tmp_path / "data" / "work" / "symbols"

    first = materialize_symbol_archive(archive, snapshot_manifest, manifest, work_base)
    target = first.raw_root / "units" / "example.svg"
    assert target.read_bytes() == body

    target.write_text("mutated", encoding="utf-8")
    second = materialize_symbol_archive(archive, snapshot_manifest, manifest, work_base)

    assert second.work_root == first.work_root
    assert target.read_bytes() == body
    assert second.asset_count == 1


def test_materialize_symbol_archive_rejects_mutated_archive(tmp_path: Path) -> None:
    body = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    archive, snapshot_manifest, manifest = _fixture(
        tmp_path, {"units/example.svg": body}
    )
    with zipfile.ZipFile(archive, "a") as output:
        output.writestr("units/unlisted.svg", body)

    with pytest.raises(ValueError, match="archive SHA-256 mismatch"):
        materialize_symbol_archive(
            archive,
            snapshot_manifest,
            manifest,
            tmp_path / "data" / "work" / "symbols",
        )


def test_svg_preflight_records_text_and_font_declarations(tmp_path: Path) -> None:
    members = {
        "units/no-text.svg": b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>',
        "units/text.svg": (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<style>.x { font-family: "Orbitron", sans-serif; }</style>'
            b'<text style="font-family: Jura">X</text></svg>'
        ),
    }
    archive, snapshot_manifest, manifest = _fixture(tmp_path, members)
    materialized = materialize_symbol_archive(
        archive,
        snapshot_manifest,
        manifest,
        tmp_path / "data" / "work" / "symbols",
    )

    result = audit_symbol_work(
        materialized,
        archive=archive,
        build_manifest_path=manifest,
        reports_base=tmp_path / "data" / "reports" / "symbols",
        project_root=tmp_path,
    )

    assert result.status == "passed"
    assert result.summary == {
        "svgCount": 2,
        "parseErrorCount": 0,
        "activeTextAssetCount": 1,
        "noActiveTextAssetCount": 1,
        "fontDeclaredAssetCount": 1,
        "uniqueDeclaredFontCount": 3,
    }
    report = json.loads(result.report.read_text(encoding="utf-8"))
    assert report["format"] == "InfinityDB SVG preflight audit"
    assert [row["family"] for row in report["fonts"]] == ["Jura", "Orbitron", "sans-serif"]
    text_row = next(row for row in report["assets"] if row["archivePath"] == "units/text.svg")
    assert text_row["activeText"] is True
    assert text_row["fontFamilies"] == ["Jura", "Orbitron", "sans-serif"]

    updated = load_symbol_manifest(manifest)
    assert updated["formatVersion"] == 3
    assert updated["processing"]["svgPreflight"]["status"] == "passed"
    assert updated["processing"]["svgPreflight"]["summary"] == result.summary
    assert updated["processing"]["svgPreflight"]["report"]["sha256"]


def test_svg_preflight_persists_failed_parse_audit(tmp_path: Path) -> None:
    archive, snapshot_manifest, manifest = _fixture(
        tmp_path,
        {"units/broken.svg": b'<svg xmlns="http://www.w3.org/2000/svg"><g></svg>'},
    )
    materialized = materialize_symbol_archive(
        archive,
        snapshot_manifest,
        manifest,
        tmp_path / "data" / "work" / "symbols",
    )

    result = audit_symbol_work(
        materialized,
        archive=archive,
        build_manifest_path=manifest,
        reports_base=tmp_path / "data" / "reports" / "symbols",
        project_root=tmp_path,
    )

    assert result.status == "failed"
    assert result.summary["parseErrorCount"] == 1
    updated = load_symbol_manifest(manifest)
    assert updated["processing"]["svgPreflight"]["status"] == "failed"
