import hashlib
import importlib.util
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from infinity_db.snapshot_provenance import write_snapshot_manifest
from infinity_db.symbol_manifest import (
    add_font_audit,
    build_symbol_manifest,
    load_symbol_manifest,
    write_symbol_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    module_path = ROOT / "tools" / "build_symbols.py"
    spec = importlib.util.spec_from_file_location("build_symbols", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def army_snapshot(tmp_path: Path, *, language: str = "en") -> tuple[Path, Path]:
    archive = tmp_path / "JSON 20260918-120000.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("metadata.json", json.dumps({"factions": []}))
        output.writestr(
            "101-test.json",
            json.dumps({"version": "7.26246.158", "units": []}),
        )
    manifest_dir = tmp_path / "manifests"
    manifest = write_snapshot_manifest(
        archive,
        manifest_dir,
        snapshot_type="army",
        acquired_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        source_url="https://api.corvusbelli.com/army",
        document_count=2,
        project_root=tmp_path,
        language=language,
    )
    return archive, manifest


def resumable_symbol_build(tmp_path: Path) -> tuple[Path, Path, Path]:
    army, army_manifest = army_snapshot(tmp_path)
    data_root = tmp_path / "data"
    manifest_dir = data_root / "manifests" / "snapshots"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / army_manifest.name).write_bytes(army_manifest.read_bytes())

    body = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'
    symbol_dir = data_root / "raw" / "symbols"
    symbol_dir.mkdir(parents=True)
    symbols = symbol_dir / "SYMBOLS 20260918-120100.zip"
    with zipfile.ZipFile(symbols, "w") as output:
        output.writestr("units/example.svg", body)
    write_snapshot_manifest(
        symbols,
        manifest_dir,
        snapshot_type="symbols",
        acquired_at=datetime(2026, 9, 18, 12, 1, tzinfo=UTC),
        source_url="https://assets.corvusbelli.net/army/img/",
        document_count=1,
        project_root=tmp_path,
        input_artifact=army,
    )
    audit = {
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
        "uniqueDownloadedUrlCount": 1,
        "unknownReferenceCount": 0,
    }
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 18, 12, 1, tzinfo=UTC),
        army_acquired_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        army_language="en",
        army_source_url="https://api.corvusbelli.com/army",
        source_document_count=2,
        source_revisions={"7.26246.158": 1},
        assets=[
            {
                "url": "https://assets.corvusbelli.net/army/img/logo/example.svg",
                "sourceFilename": "example.svg",
                "archivePath": "units/example.svg",
                "sha256": hashlib.sha256(body).hexdigest(),
                "sourceMethod": "override",
            }
        ],
        references=[],
        audit=audit,
        project_root=tmp_path,
    )
    build_manifest = data_root / "manifests" / "army-symbol-build.json"
    write_symbol_manifest(document, build_manifest)
    return data_root, army, build_manifest


def stub_post_acquisition(
    module,
    monkeypatch,
    *,
    status: str = "passed",
    font_status: str = "passed",
) -> None:
    materialized = SimpleNamespace(
        raw_root=Path("work/raw"),
        work_root=Path("work"),
        asset_count=0,
        build_manifest={},
    )
    preflight = SimpleNamespace(
        report=Path("reports/svg-preflight.json"),
        status=status,
        summary={
            "svgCount": 0,
            "parseErrorCount": 0 if status == "passed" else 1,
            "activeTextAssetCount": 0,
            "noActiveTextAssetCount": 0,
            "fontDeclaredAssetCount": 0,
            "uniqueDeclaredFontCount": 0,
        },
    )
    monkeypatch.setattr(
        module, "materialize_symbol_archive", lambda *_args, **_kwargs: materialized
    )
    monkeypatch.setattr(module, "audit_symbol_work", lambda *_args, **_kwargs: preflight)
    font_audit = SimpleNamespace(
        report=Path("reports/font-audit.json"),
        status=font_status,
        summary={
            "fontAvailableAssetCount": 0,
            "fontMissingAssetCount": 0 if font_status == "passed" else 1,
            "normalizedAliasReferenceCount": 0,
            "unusedDeclarationCount": 0,
        },
    )
    monkeypatch.setattr(
        module, "audit_symbol_fonts", lambda *_args, **_kwargs: font_audit
    )
    duplicates = SimpleNamespace(
        groups_report=Path("reports/duplicate-groups.csv"),
        errors_report=Path("reports/duplicate-render-errors.csv"),
        summary_report=Path("reports/duplicate-summary.csv"),
        status="passed",
        summary={
            "canonicalAssetCount": 0,
            "redundantAssetCount": 0,
            "sourceAssetBytes": 0,
            "canonicalAssetBytes": 0,
            "reclaimedAssetBytes": 0,
            "exactGroupCount": 0,
            "visualGroupCount": 0,
            "renderErrorCount": 0,
        },
    )
    monkeypatch.setattr(
        module, "detect_symbol_duplicates", lambda *_args, **_kwargs: duplicates
    )
    conversion = SimpleNamespace(
        canonical_root=Path("work/canonical"),
        report=Path("reports/svg-text-to-path-report.csv"),
        summary_report=Path("reports/text-conversion-summary.csv"),
        status="passed",
        converter="inkscape-shell",
        converter_version="Inkscape test",
        summary={
            "canonicalAssetCount": 0,
            "conversionCandidateCount": 0,
            "convertedAssetCount": 0,
            "carriedForwardAssetCount": 0,
            "failedAssetCount": 0,
        },
    )
    monkeypatch.setattr(
        module, "convert_symbol_text", lambda *_args, **_kwargs: conversion
    )
    compression = SimpleNamespace(
        compressed_root=Path("work/compressed"),
        report=Path("reports/compression-report.csv"),
        candidates_report=Path("reports/compression-candidates.csv"),
        run_report=Path("reports/compression-run.json"),
        status="passed",
        renderer="resvg",
        renderer_version="resvg test",
        summary={
            "assetCount": 0,
            "compressedAssetCount": 0,
            "retainedAssetCount": 0,
            "sourceBytes": 0,
            "outputBytes": 0,
            "reclaimedBytes": 0,
        },
    )
    monkeypatch.setattr(
        module, "compress_symbol_work", lambda *_args, **_kwargs: compression
    )
    publication = SimpleNamespace(
        static_root=Path("static"),
        mapping_report=Path("reports/publication-map.json"),
        army_map=Path("static/army-symbols.js"),
        unit_map=Path("static/unit-symbol-map.js"),
        status="passed",
        summary={
            "sourceAssetCount": 0,
            "canonicalAssetCount": 0,
            "publishedAssetCount": 0,
            "factionMappingCount": 0,
            "unitMappingCount": 0,
            "staticMappingCount": 0,
            "publishedBytes": 0,
        },
    )
    monkeypatch.setattr(
        module, "publish_symbols", lambda *_args, **_kwargs: publication
    )


def test_resolve_army_snapshot_verifies_provenance_and_revisions(tmp_path: Path) -> None:
    module = load_module()
    archive, manifest = army_snapshot(tmp_path)

    resolved = module.resolve_army_snapshot(
        archive,
        manifest_directory=manifest.parent,
    )

    assert resolved.archive == archive
    assert resolved.manifest == manifest
    assert resolved.language == "en"
    assert resolved.document_count == 2
    assert resolved.source_revisions == {"7.26246.158": 1}


def test_resolve_army_snapshot_rejects_language_mismatch(tmp_path: Path) -> None:
    module = load_module()
    archive, manifest = army_snapshot(tmp_path, language="es")

    with pytest.raises(ValueError, match="language is 'es', expected 'en'"):
        module.resolve_army_snapshot(
            archive,
            manifest_directory=manifest.parent,
            expected_language="en",
        )


def test_snapshot_only_uses_exact_offline_snapshot(tmp_path: Path, capsys) -> None:
    module = load_module()
    archive, manifest = army_snapshot(tmp_path)
    data_root = tmp_path / "data"
    expected_manifest = data_root / "manifests" / "snapshots" / manifest.name
    expected_manifest.parent.mkdir(parents=True)
    expected_manifest.write_bytes(manifest.read_bytes())

    assert (
        module.main(
            [
                "--snapshot",
                str(archive),
                "--data-root",
                str(data_root),
                "--snapshot-only",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert f"Pinned Army snapshot -> {archive}" in output
    assert "Army source revisions -> 7.26246.158: 1" in output
    assert not (data_root / "raw" / "symbols").exists()


def test_orchestrator_passes_pinned_snapshot_to_symbol_acquisition(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    archive, manifest = army_snapshot(tmp_path)
    data_root = tmp_path / "data"
    expected_manifest = data_root / "manifests" / "snapshots" / manifest.name
    expected_manifest.parent.mkdir(parents=True)
    expected_manifest.write_bytes(manifest.read_bytes())
    seen: dict[str, object] = {}
    stub_post_acquisition(module, monkeypatch)

    discovery = SimpleNamespace(source_document_count=2)

    def fake_discover(source, *, static_symbols_path):
        seen["discovery"] = source
        return discovery

    def fake_acquire(
        source,
        destination,
        manifest_directory,
        build_manifest_path,
        **kwargs,
    ):
        seen["acquisition"] = source
        seen["army_snapshot"] = kwargs["army_snapshot"]
        seen["override_root"] = kwargs["override_root"]
        seen["refresh_symbols"] = kwargs["refresh_symbols"]
        return SimpleNamespace(
            asset_count=3,
            archive=destination / "SYMBOLS 20260918-120100.zip",
            snapshot_manifest=manifest_directory / "SYMBOLS 20260918-120100.json",
            build_manifest=build_manifest_path,
        )

    monkeypatch.setattr(module, "discover_symbol_source", fake_discover)
    monkeypatch.setattr(module, "print_discovery_summary", lambda _discovery: None)
    monkeypatch.setattr(module, "acquire_symbol_snapshot", fake_acquire)

    assert (
        module.main(
            [
                "--snapshot",
                str(archive),
                "--data-root",
                str(data_root),
                "--image-overrides",
                str(tmp_path / "overrides"),
                "--refresh-symbols",
                "--delay",
                "0",
            ]
        )
        == 0
    )

    assert seen["discovery"] == archive
    assert seen["acquisition"] == archive
    assert seen["army_snapshot"].archive == archive
    assert seen["army_snapshot"].source_revisions == {"7.26246.158": 1}
    assert seen["override_root"] == tmp_path / "overrides"
    assert seen["refresh_symbols"] is True


def test_fetch_mode_pins_the_snapshot_returned_by_army_acquisition(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    archive, manifest = army_snapshot(tmp_path)
    data_root = tmp_path / "data"
    discovery = SimpleNamespace(source_document_count=2)
    seen: dict[str, object] = {}
    stub_post_acquisition(module, monkeypatch)

    def fake_army(destination, manifest_directory, **kwargs):
        seen["army_destination"] = destination
        seen["manifest_directory"] = manifest_directory
        seen["language"] = kwargs["language"]
        return SimpleNamespace(archive=archive, manifest=manifest)

    monkeypatch.setattr(module, "acquire_army_snapshot", fake_army)
    monkeypatch.setattr(module, "discover_symbol_source", lambda *_args, **_kwargs: discovery)
    monkeypatch.setattr(module, "print_discovery_summary", lambda _discovery: None)

    def fake_symbols(source, *_args, **kwargs):
        seen["symbol_source"] = source
        seen["army_snapshot"] = kwargs["army_snapshot"]
        return SimpleNamespace(
            asset_count=0,
            archive=tmp_path / "symbols.zip",
            snapshot_manifest=tmp_path / "symbols.json",
            build_manifest=tmp_path / "build.json",
        )

    monkeypatch.setattr(module, "acquire_symbol_snapshot", fake_symbols)

    assert (
        module.main(
            [
                "--fetch-snapshot",
                "--data-root",
                str(data_root),
                "--delay",
                "0",
            ]
        )
        == 0
    )

    assert seen["language"] == "en"
    assert seen["symbol_source"] == archive
    assert seen["army_snapshot"].archive == archive
    assert seen["army_snapshot"].language == "en"


def test_offline_mode_requires_snapshot_provenance(tmp_path: Path, capsys) -> None:
    module = load_module()
    archive, _manifest = army_snapshot(tmp_path)

    assert (
        module.main(
            [
                "--snapshot",
                str(archive),
                "--data-root",
                str(tmp_path / "other-data"),
                "--snapshot-only",
            ]
        )
        == 1
    )
    assert "Army snapshot provenance is required" in capsys.readouterr().err


def test_orchestrator_fails_after_persisting_failed_svg_preflight(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = load_module()
    archive, manifest = army_snapshot(tmp_path)
    data_root = tmp_path / "data"
    expected_manifest = data_root / "manifests" / "snapshots" / manifest.name
    expected_manifest.parent.mkdir(parents=True)
    expected_manifest.write_bytes(manifest.read_bytes())
    stub_post_acquisition(module, monkeypatch, status="failed")
    discovery = SimpleNamespace(source_document_count=2)
    monkeypatch.setattr(module, "discover_symbol_source", lambda *_args, **_kwargs: discovery)
    monkeypatch.setattr(module, "print_discovery_summary", lambda _discovery: None)
    monkeypatch.setattr(
        module,
        "acquire_symbol_snapshot",
        lambda *_args, **_kwargs: SimpleNamespace(
            asset_count=1,
            archive=tmp_path / "symbols.zip",
            snapshot_manifest=tmp_path / "symbols.json",
            build_manifest=tmp_path / "build.json",
        ),
    )

    assert (
        module.main(
            [
                "--snapshot",
                str(archive),
                "--data-root",
                str(data_root),
                "--delay",
                "0",
            ]
        )
        == 1
    )
    assert "SVG preflight failed" in capsys.readouterr().err

def test_orchestrator_fails_after_persisting_failed_font_audit(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = load_module()
    archive, manifest = army_snapshot(tmp_path)
    data_root = tmp_path / "data"
    expected_manifest = data_root / "manifests" / "snapshots" / manifest.name
    expected_manifest.parent.mkdir(parents=True)
    expected_manifest.write_bytes(manifest.read_bytes())
    stub_post_acquisition(module, monkeypatch, font_status="failed")
    discovery = SimpleNamespace(source_document_count=2)
    monkeypatch.setattr(module, "discover_symbol_source", lambda *_args, **_kwargs: discovery)
    monkeypatch.setattr(module, "print_discovery_summary", lambda _discovery: None)
    monkeypatch.setattr(
        module,
        "acquire_symbol_snapshot",
        lambda *_args, **_kwargs: SimpleNamespace(
            asset_count=1,
            archive=tmp_path / "symbols.zip",
            snapshot_manifest=tmp_path / "symbols.json",
            build_manifest=tmp_path / "build.json",
        ),
    )

    assert (
        module.main(
            [
                "--snapshot",
                str(archive),
                "--data-root",
                str(data_root),
                "--delay",
                "0",
            ]
        )
        == 1
    )
    assert "Font audit failed" in capsys.readouterr().err

def test_stop_after_acquisition_does_not_materialize(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = load_module()
    archive, manifest = army_snapshot(tmp_path)
    data_root = tmp_path / "data"
    expected_manifest = data_root / "manifests" / "snapshots" / manifest.name
    expected_manifest.parent.mkdir(parents=True)
    expected_manifest.write_bytes(manifest.read_bytes())
    discovery = SimpleNamespace(source_document_count=2)
    monkeypatch.setattr(module, "discover_symbol_source", lambda *_args, **_kwargs: discovery)
    monkeypatch.setattr(module, "print_discovery_summary", lambda _discovery: None)
    monkeypatch.setattr(
        module,
        "acquire_symbol_snapshot",
        lambda *_args, **_kwargs: SimpleNamespace(
            asset_count=1,
            archive=tmp_path / "symbols.zip",
            snapshot_manifest=tmp_path / "symbols.json",
            build_manifest=tmp_path / "missing-build.json",
        ),
    )
    monkeypatch.setattr(
        module,
        "materialize_symbol_archive",
        lambda *_args, **_kwargs: pytest.fail("materialization must not run"),
    )

    assert (
        module.main(
            [
                "--snapshot",
                str(archive),
                "--data-root",
                str(data_root),
                "--stop-after",
                "acquisition",
                "--delay",
                "0",
            ]
        )
        == 0
    )
    assert "Checkpoint reached -> acquisition" in capsys.readouterr().out


def test_resume_from_v2_materializes_and_runs_preflight_without_reacquisition(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = load_module()
    data_root, army, build_manifest = resumable_symbol_build(tmp_path)
    monkeypatch.setattr(
        module,
        "discover_symbol_source",
        lambda *_args, **_kwargs: pytest.fail("resume must not rediscover symbols"),
    )
    monkeypatch.setattr(
        module,
        "acquire_symbol_snapshot",
        lambda *_args, **_kwargs: pytest.fail("resume must not reacquire symbols"),
    )

    assert (
        module.main(
            [
                "--resume",
                "--snapshot",
                str(army),
                "--data-root",
                str(data_root),
                "--stop-after",
                "preflight",
            ]
        )
        == 0
    )
    assert load_symbol_manifest(build_manifest)["formatVersion"] == 3
    output = capsys.readouterr().out
    assert "Resuming symbol build -> version 2" in output
    assert "Checkpoint reached -> preflight" in output


def test_resume_verifies_existing_work_without_rematerializing(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    data_root, army, _build_manifest = resumable_symbol_build(tmp_path)
    assert (
        module.main(
            [
                "--resume",
                "--snapshot",
                str(army),
                "--data-root",
                str(data_root),
                "--stop-after",
                "preflight",
            ]
        )
        == 0
    )
    work_root = next((data_root / "work" / "symbols").iterdir())
    marker = work_root / "canonical" / "keep-me.txt"
    marker.parent.mkdir()
    marker.write_text("preserve derived work", encoding="utf-8")

    monkeypatch.setattr(
        module,
        "materialize_symbol_archive",
        lambda *_args, **_kwargs: pytest.fail("resume must verify, not rematerialize"),
    )
    assert (
        module.main(
            [
                "--resume",
                "--snapshot",
                str(army),
                "--data-root",
                str(data_root),
                "--stop-after",
                "materialization",
            ]
        )
        == 0
    )
    assert marker.read_text(encoding="utf-8") == "preserve derived work"


def test_resume_retries_failed_v4_font_audit(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = load_module()
    data_root, army, build_manifest = resumable_symbol_build(tmp_path)
    assert (
        module.main(
            [
                "--resume",
                "--snapshot",
                str(army),
                "--data-root",
                str(data_root),
                "--stop-after",
                "preflight",
            ]
        )
        == 0
    )

    report = tmp_path / "font-audit.json"
    report.write_text("{}\n", encoding="utf-8")
    aliases = tmp_path / "font-aliases.json"
    aliases.write_text("{}\n", encoding="utf-8")
    failed = add_font_audit(
        load_symbol_manifest(build_manifest),
        status="failed",
        summary={
            "svgCount": 1,
            "fontAvailableAssetCount": 0,
            "fontMissingAssetCount": 1,
            "noActiveTextAssetCount": 0,
            "implicitDefaultAssetCount": 0,
            "effectiveFontReferenceCount": 1,
            "availableFontReferenceCount": 0,
            "missingFontReferenceCount": 1,
            "ambiguousFontReferenceCount": 0,
            "genericFontReferenceCount": 0,
            "normalizedAliasReferenceCount": 0,
            "unusedDeclarationCount": 0,
        },
        report=report,
        aliases=aliases,
        project_root=tmp_path,
    )
    write_symbol_manifest(failed, build_manifest)

    def rerun_font_audit(*_args, **kwargs):
        path = kwargs["build_manifest_path"]
        document = load_symbol_manifest(path)
        assert document["formatVersion"] == 4
        assert document["processing"]["fontAudit"]["status"] == "failed"
        document["processing"]["fontAudit"]["status"] = "passed"
        summary = document["processing"]["fontAudit"]["summary"]
        summary["fontAvailableAssetCount"] = 1
        summary["fontMissingAssetCount"] = 0
        summary["availableFontReferenceCount"] = 1
        summary["missingFontReferenceCount"] = 0
        write_symbol_manifest(document, path)
        return SimpleNamespace(
            report=report,
            status="passed",
            summary={
                "fontAvailableAssetCount": 1,
                "fontMissingAssetCount": 0,
                "normalizedAliasReferenceCount": 0,
                "unusedDeclarationCount": 0,
            },
        )

    monkeypatch.setattr(module, "audit_symbol_fonts", rerun_font_audit)
    assert (
        module.main(
            [
                "--resume",
                "--snapshot",
                str(army),
                "--data-root",
                str(data_root),
                "--stop-after",
                "font-audit",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "Resuming symbol build -> version 4" in output
    assert "Checkpoint reached -> font-audit" in output
    assert load_symbol_manifest(build_manifest)["processing"]["fontAudit"]["status"] == "passed"
