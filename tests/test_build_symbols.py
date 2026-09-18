import importlib.util
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from infinity_db.snapshot_provenance import write_snapshot_manifest

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
