import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

import tools.symbol_work as symbol_work
from infinity_db.snapshot_provenance import write_snapshot_manifest
from infinity_db.symbol_manifest import (
    add_font_audit,
    add_svg_preflight,
    build_symbol_manifest,
    load_symbol_manifest,
    validate_symbol_manifest,
    write_symbol_manifest,
)
from tools.symbol_work import (
    audit_symbol_work,
    detect_symbol_duplicates,
    materialize_symbol_archive,
)


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

def test_font_audit_classifies_effective_fonts_and_unused_declarations(
    tmp_path: Path, monkeypatch
) -> None:
    members = {
        "units/available.svg": (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<text style="font-family: Legacy">OK</text></svg>'
        ),
        "units/missing.svg": (
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<text style="font-family: Missing">NO</text></svg>'
        ),
        "units/no-text.svg": b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>',
    }
    archive, snapshot_manifest, manifest = _fixture(tmp_path, members)
    materialized = materialize_symbol_archive(
        archive,
        snapshot_manifest,
        manifest,
        tmp_path / "data" / "work" / "symbols",
    )
    preflight = audit_symbol_work(
        materialized,
        archive=archive,
        build_manifest_path=manifest,
        reports_base=tmp_path / "data" / "reports" / "symbols",
        project_root=tmp_path,
    )
    assert preflight.status == "passed"

    alias_config = tmp_path / "config" / "symbols" / "font-aliases.json"
    alias_config.parent.mkdir(parents=True)
    alias_config.write_text('{"schemaVersion":1,"overrides":[]}\n', encoding="utf-8")

    def normal_key(value: str) -> str:
        return " ".join(value.strip().casefold().split())

    def fake_scan(path: Path):
        if path.name == "available.svg":
            return {
                "used_fonts": {"Legacy": 2},
                "declared_fonts": {"Legacy", "Unused"},
                "text_runs": 2,
                "found_active_text": True,
                "empty_text_objects": 0,
            }, None
        if path.name == "missing.svg":
            return {
                "used_fonts": {"Missing": 1},
                "declared_fonts": {"Missing"},
                "text_runs": 1,
                "found_active_text": True,
                "empty_text_objects": 0,
            }, None
        return {
            "used_fonts": {},
            "declared_fonts": {"UnusedNoText"},
            "text_runs": 0,
            "found_active_text": False,
            "empty_text_objects": 0,
        }, None

    def fake_find(reference, _exact, _compact, *, overrides=None):
        assert overrides == {}
        if reference == "Legacy":
            return {
                "status": "FOUND",
                "match_type": "reference-override",
                "matched_name": "Legacy Installed",
                "family": "Installed",
                "subfamily": "Regular",
                "full_name": "Installed Regular",
                "postscript": "Installed-Regular",
                "font_file": str(tmp_path / "fonts" / "installed.ttf"),
                "normalize": "YES",
                "weight": "400",
                "style": "normal",
                "stretch": "normal",
            }
        return {
            "status": "MISSING",
            "match_type": "",
            "matched_name": "",
            "family": "",
            "subfamily": "",
            "full_name": "",
            "postscript": "",
            "font_file": "",
            "normalize": "",
            "weight": "",
            "style": "",
            "stretch": "",
        }

    fake_tools = type(
        "FakeFontTools",
        (),
        {
            "load_font_reference_overrides": staticmethod(lambda _path: {}),
            "load_font_index": staticmethod(lambda: ({}, {}, 4, 7)),
            "scan_svg": staticmethod(fake_scan),
            "find_font": staticmethod(fake_find),
            "normal_key": staticmethod(normal_key),
        },
    )
    monkeypatch.setattr(symbol_work, "_font_tools", lambda: fake_tools)

    result = symbol_work.audit_symbol_fonts(
        materialized,
        archive=archive,
        build_manifest_path=manifest,
        reports_base=tmp_path / "data" / "reports" / "symbols",
        project_root=tmp_path,
        alias_config=alias_config,
    )

    assert result.status == "failed"
    assert result.summary == {
        "svgCount": 3,
        "fontAvailableAssetCount": 1,
        "fontMissingAssetCount": 1,
        "noActiveTextAssetCount": 1,
        "implicitDefaultAssetCount": 0,
        "effectiveFontReferenceCount": 2,
        "availableFontReferenceCount": 1,
        "missingFontReferenceCount": 1,
        "ambiguousFontReferenceCount": 0,
        "genericFontReferenceCount": 0,
        "normalizedAliasReferenceCount": 1,
        "unusedDeclarationCount": 2,
    }
    report = json.loads(result.report.read_text(encoding="utf-8"))
    assert report["fontIndex"] == {"fontFaceCount": 7, "fontFileCount": 4}
    assert report["fonts"][0]["fontFile"] == "installed.ttf"
    categories = {row["archivePath"]: row["category"] for row in report["assets"]}
    assert categories == {
        "units/available.svg": "fonts_available",
        "units/missing.svg": "fonts_missing",
        "units/no-text.svg": "no_active_text",
    }

    updated = load_symbol_manifest(manifest)
    assert updated["formatVersion"] == 4
    assert updated["processing"]["fontAudit"]["status"] == "failed"
    assert updated["processing"]["fontAudit"]["aliases"]["sha256"]


def test_duplicate_detection_persists_canonical_mapping(tmp_path: Path, monkeypatch) -> None:
    body = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'
    unique = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M1 1"/></svg>'
    archive, snapshot_manifest, manifest_path = _fixture(
        tmp_path,
        {
            "units/a.svg": body,
            "units/b.svg": body,
            "units/c.svg": unique,
        },
    )
    materialized = materialize_symbol_archive(
        archive,
        snapshot_manifest,
        manifest_path,
        tmp_path / "data" / "work" / "symbols",
    )

    preflight_report = tmp_path / "preflight.json"
    preflight_report.write_text("{}\n", encoding="utf-8")
    document = add_svg_preflight(
        load_symbol_manifest(manifest_path),
        status="passed",
        summary={
            "svgCount": 3,
            "parseErrorCount": 0,
            "activeTextAssetCount": 0,
            "noActiveTextAssetCount": 3,
            "fontDeclaredAssetCount": 0,
            "uniqueDeclaredFontCount": 0,
        },
        report=preflight_report,
        project_root=tmp_path,
    )
    alias_config = tmp_path / "font-aliases.json"
    alias_config.write_text("{}\n", encoding="utf-8")
    font_report = tmp_path / "font-audit.json"
    font_report.write_text(
        json.dumps(
            {
                "symbolArtifact": {
                    "name": archive.name,
                    "sha256": document["snapshot"]["symbolArtifact"]["sha256"],
                },
                "assets": [
                    {"archivePath": name, "category": "no_active_text"}
                    for name in ("units/a.svg", "units/b.svg", "units/c.svg")
                ],
            }
        ),
        encoding="utf-8",
    )
    document = add_font_audit(
        document,
        status="passed",
        summary={
            "svgCount": 3,
            "fontAvailableAssetCount": 0,
            "fontMissingAssetCount": 0,
            "noActiveTextAssetCount": 3,
            "implicitDefaultAssetCount": 0,
            "effectiveFontReferenceCount": 0,
            "availableFontReferenceCount": 0,
            "missingFontReferenceCount": 0,
            "ambiguousFontReferenceCount": 0,
            "genericFontReferenceCount": 0,
            "normalizedAliasReferenceCount": 0,
            "unusedDeclarationCount": 0,
        },
        report=font_report,
        aliases=alias_config,
        project_root=tmp_path,
    )
    write_symbol_manifest(document, manifest_path)

    def fake_duplicates(input_root, output_root, categories, **kwargs):
        assert input_root == materialized.raw_root
        assert output_root == materialized.work_root
        assert categories == {
            "units/a.svg": "no_active_text",
            "units/b.svg": "no_active_text",
            "units/c.svg": "no_active_text",
        }
        assert kwargs["render_size"] == 512
        assert kwargs["jobs"] == 4
        assert kwargs["renderer"] == "resvg"
        report_root = kwargs["reports_root"]
        report_root.mkdir(parents=True, exist_ok=True)
        group_report = report_root / "duplicate-groups.csv"
        error_report = report_root / "duplicate-render-errors.csv"
        summary_report = report_root / "duplicate-summary.csv"
        for path in (group_report, error_report, summary_report):
            path.write_text("header\n", encoding="utf-8")
        return {
            "source_svg_files": 3,
            "canonical_svg_files": 2,
            "unique_byte_sets": 2,
            "renders_avoided_exact": 1,
            "exact_groups": 1,
            "visual_groups": 0,
            "redundant_files": 1,
            "render_errors": 0,
            "source_size_bytes": 180,
            "canonical_size_bytes": 120,
            "reclaimed_size_bytes": 60,
            "reduction_percent": 33.333333,
            "render_size": 512,
            "jobs": 4,
            "renderer": "resvg",
            "renderer_version": "0.45.1",
            "duplicate_representatives": {"units/b.svg": "units/a.svg"},
            "report_path": group_report,
            "error_path": error_report,
            "summary_path": summary_report,
        }

    fake_tools = type(
        "FakeDuplicateTools",
        (),
        {"find_duplicate_svgs": staticmethod(fake_duplicates)},
    )
    monkeypatch.setattr(symbol_work, "_font_tools", lambda: fake_tools)

    result = detect_symbol_duplicates(
        materialized,
        archive=archive,
        build_manifest_path=manifest_path,
        font_report=font_report,
        reports_base=tmp_path / "data" / "reports" / "symbols",
        project_root=tmp_path,
    )

    assert result.summary["canonicalAssetCount"] == 2
    assert result.summary["sourceAssetBytes"] == 180
    assert result.summary["canonicalAssetBytes"] == 120
    assert result.summary["reclaimedAssetBytes"] == 60
    assert result.canonical_by_archive_path == {
        "units/a.svg": "units/a.svg",
        "units/b.svg": "units/a.svg",
        "units/c.svg": "units/c.svg",
    }
    updated = load_symbol_manifest(manifest_path)
    assert updated["formatVersion"] == 5
    duplicate = updated["processing"]["duplicateDetection"]
    assert duplicate["canonicalByArchivePath"] == result.canonical_by_archive_path
    assert duplicate["summary"]["sourceAssetBytes"] == 180
    assert duplicate["summary"]["canonicalAssetBytes"] == 120
    assert duplicate["summary"]["reclaimedAssetBytes"] == 60
    assert duplicate["renderer"] == {
        "name": "resvg",
        "version": "0.45.1",
        "renderSize": 512,
        "jobs": 4,
    }

    legacy_v5 = json.loads(json.dumps(updated))
    for field in ("sourceAssetBytes", "canonicalAssetBytes", "reclaimedAssetBytes"):
        legacy_v5["processing"]["duplicateDetection"]["summary"].pop(field)
    validate_symbol_manifest(legacy_v5)
