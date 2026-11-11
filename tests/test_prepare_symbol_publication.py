"""External handoff integration with the shared semantic publication mapper."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_verify_processed_symbol_handoff import _csv, _fixture, _pin
from test_verify_symbol_duplicate_handoff import _evidence

from tools import prepare_symbol_publication as candidate
from tools.reorganize_symbols import FactionInfo, SnapshotIndex
from tools.verify_processed_symbol_handoff import FORMAT


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs(root: Path, monkeypatch):
    # Reuse real raw/effective/duplicate verification fixtures. Only Army
    # discovery is injected: these tiny fixture archives have no Unit catalog.
    duplicate_files = _evidence(root)
    effective, effective_manifest, effective_report, font_report, font_receipt = duplicate_files[:5]
    raw = next((root / "snapshots").glob("SYMBOLS *.zip"))
    handoff = candidate.SymbolPublicationHandoff(
        root / "source-plan.json", root / "override-lookups.json",
        root / "JSON 20260917-120000.zip", root / "army-provenance.json",
        raw, effective, root / "stages", root / "processed",
    )
    files = handoff.files()
    handoff.stage_reports.mkdir()
    handoff.processed_root.mkdir()
    (handoff.stage_reports / "duplicates").mkdir()
    _write(handoff.army_manifest, {})
    for src, dst in (
        (root / "manifests" / raw.with_suffix(".json").name, files["raw_manifest"]),
        (root / "raw-report.json", files["raw_report"]),
        (effective_manifest, files["effective_manifest"]),
        (effective_report, files["effective_report"]),
        (font_report, files["font-audit_report"]),
        (font_receipt, files["font-audit_receipt"]),
        *zip(duplicate_files[5:9], (files[k] for k in (
            "duplicate_groups", "duplicate_render-errors", "duplicate_summary", "duplicate_receipt",
        )), strict=True),
    ):
        shutil.copyfile(src, dst)
    aliases = root / "font-aliases.json"
    _write(aliases, {})
    artifact = {"name": effective.name, "sha256": _pin(effective)["sha256"]}
    _write(files["svg-preflight_report"], {
        "symbolArtifact": artifact, "summary": {"svgCount": 3, "parseErrorCount": 0},
    })
    _write(files["svg-preflight_receipt"], {
        "format": FORMAT, "formatVersion": 1, "stage": "svgPreflight", "status": "passed",
        "inputArtifact": artifact, "report": _pin(files["svg-preflight_report"]),
        "summary": {"svgCount": 3, "parseErrorCount": 0},
    })
    font = _load(files["font-audit_receipt"])
    font.update({"fontAliases": _pin(aliases),
                 "preflightReceipt": _pin(files["svg-preflight_receipt"]),
                 "preflightReport": _pin(files["svg-preflight_report"])})
    _write(files["font-audit_receipt"], font)
    duplicate = _load(files["duplicate_receipt"])
    duplicate["fontAuditReceipt"] = _pin(files["font-audit_receipt"])
    _write(files["duplicate_receipt"], duplicate)

    # Start from the separately tested compression format and extend it to
    # the two canonical assets selected by the real duplicate-stage fixture.
    generated = _fixture(handoff.processed_root)
    for src, key in zip(generated, (
        "canonical_archive", "conversion_receipt", "compressed_archive", "compression_receipt",
        "compression_report", "candidates_report", "run_report",
    ), strict=True):
        shutil.move(src, files[key])
    mapping = duplicate["canonicalByArchivePath"]
    with zipfile.ZipFile(effective) as archive:
        bodies = {name: archive.read(name) for name in sorted(set(mapping.values()))}
    for key in ("canonical_archive", "compressed_archive"):
        with zipfile.ZipFile(files[key], "w") as archive:
            for name, body in bodies.items():
                archive.writestr(name, body)
    assets = [{"archivePath": name, "sha256": hashlib.sha256(body).hexdigest(),
               "sourceSha256": hashlib.sha256(body).hexdigest(), "converted": False}
              for name, body in bodies.items()]
    _csv(files["conversion_report"], ["file", "status", "converter", "error"], [])
    totals = {"converter": "fixture", "converter_version": "fixture-1",
              "files_found": "0", "converted": "0", "failed": "0",
              "skipped_existing": "0", "skipped_duplicates": "0"}
    _csv(files["conversion_summary"], list(totals), [totals])
    conversion = {
        "format": FORMAT, "formatVersion": 1, "stage": "textConversion", "status": "passed",
        "inputArtifact": artifact, "outputArtifact": _pin(files["canonical_archive"]),
        "outputAssets": assets, "canonicalByArchivePath": mapping,
        "converter": "fixture", "converterVersion": "fixture-1",
        "summary": {"conversionFailureCount": 0, "sourceAssetCount": 3,
                    "canonicalAssetCount": 2, "textCandidateCount": 0, "convertedCount": 0},
        "fontAliases": _pin(aliases),
        "fontAuditReceipt": _pin(files["font-audit_receipt"]),
        "fontAuditReport": _pin(files["font-audit_report"]),
        "duplicateReceipt": _pin(files["duplicate_receipt"]),
        "duplicateReports": duplicate["reports"],
        "reports": {"conversion": _pin(files["conversion_report"]),
                    "summary": _pin(files["conversion_summary"])},
    }
    _write(files["conversion_receipt"], conversion)
    _csv(files["compression_report"], [
        "file", "profile", "status", "error", "source_bytes", "output_bytes",
    ], [{"file": name, "profile": "balanced", "status": "NO_SMALLER_PASSING_CANDIDATE",
         "error": "", "source_bytes": len(body), "output_bytes": len(body)}
        for name, body in bodies.items()])
    compression = _load(files["compression_receipt"])
    compression.update({
        "inputArtifact": _pin(files["canonical_archive"]),
        "textConversionReceipt": _pin(files["conversion_receipt"]),
        "outputArtifact": _pin(files["compressed_archive"]),
        "outputAssets": [dict(asset, sourceSha256=asset["sha256"]) for asset in assets],
        "summary": {"assetCount": 2, "sourceBytes": sum(map(len, bodies.values())),
                    "outputBytes": sum(map(len, bodies.values()))},
        "reports": {k: _pin(files[f]) for k, f in (
            ("compression", "compression_report"), ("candidates", "candidates_report"),
            ("run", "run_report"),
        )},
    })
    _write(files["compression_receipt"], compression)
    approved_lookup = _load(handoff.override_lookups)
    monkeypatch.setattr(candidate, "build_override_lookup_plan", lambda *a, **kw: approved_lookup)
    refs = [{"kind": "static", "authoritative": True, "staticKey": "cube",
             "staticCategory": "characteristics", "assetUrl":
             "https://assets.corvusbelli.net/army/img/icon/cube.svg"}]
    refs += [{"kind": "unit-profile", "authoritative": True,
              "sourceDocument": "101-test.json", "armyId": 101, "unitId": number,
              "unitSlug": "unit-" + suffix, "profileName": "Unit " + suffix,
              "assetUrl": "https://assets.corvusbelli.net/army/img/logo/units/unit-"
              + suffix + ".svg"} for number, suffix in enumerate(("a", "b"), 1)]
    monkeypatch.setattr(candidate, "discover_symbol_source",
                        lambda *a, **kw: SimpleNamespace(references=refs))
    monkeypatch.setattr(candidate, "_load_snapshot_index", lambda *a: SnapshotIndex(
        {101: FactionInfo(101, "test", 101)},
        {("101-test.json", i, "unit-" + s): 101 for i, s in enumerate(("a", "b"), 1)},
    ))
    return handoff, aliases


def test_external_candidate_preserves_duplicate_semantic_references(tmp_path, monkeypatch):
    handoff, aliases = _inputs(tmp_path, monkeypatch)
    report = candidate.prepare_symbol_publication(handoff, tmp_path / "out", font_aliases=aliases)
    sources = report["sourceArchivePathToPublishedPath"]
    assert sources["units/unit-a.svg"] == sources["units/unit-b.svg"]
    assert report["unitSlugToPublishedPath"]["unit-a"] == sources["units/unit-a.svg"]
    assert report["unitSlugToPublishedPath"]["unit-b"] == sources["units/unit-a.svg"]
    assert report["summary"]["publishedAssetCount"] == 2
    again = candidate.prepare_symbol_publication(handoff, tmp_path / "again", font_aliases=aliases)
    assert again == report
    for name in ("symbol-publication.json", "candidate-evidence.json"):
        assert (tmp_path / "out" / name).read_bytes() == (tmp_path / "again" / name).read_bytes()


@pytest.mark.parametrize("field", [
    "inputArtifact", "canonicalByArchivePath", "duplicateReceipt", "sourceSha256",
])
def test_disconnected_processing_chain_is_rejected(tmp_path, monkeypatch, field):
    handoff, aliases = _inputs(tmp_path, monkeypatch)
    files = handoff.files()
    conversion = _load(files["conversion_receipt"])
    if field == "canonicalByArchivePath":
        conversion[field]["units/unit-b.svg"] = "static/characteristics/cube.svg"
    elif field == "sourceSha256":
        conversion["outputAssets"][0][field] = "0" * 64
    else:
        conversion[field]["sha256"] = "0" * 64
    _write(files["conversion_receipt"], conversion)
    compression = _load(files["compression_receipt"])
    compression["textConversionReceipt"] = _pin(files["conversion_receipt"])
    _write(files["compression_receipt"], compression)
    with pytest.raises(ValueError):
        candidate.prepare_symbol_publication(handoff, tmp_path / "out", font_aliases=aliases)
    assert not (tmp_path / "out").exists()


def test_different_font_alias_bytes_are_rejected(tmp_path, monkeypatch):
    handoff, aliases = _inputs(tmp_path, monkeypatch)
    aliases.write_text('{"changed": true}', encoding="utf-8")
    with pytest.raises(ValueError, match="Font aliases"):
        candidate.prepare_symbol_publication(handoff, tmp_path / "out", font_aliases=aliases)
    assert not (tmp_path / "out").exists()


def test_existing_candidate_is_preserved(tmp_path, monkeypatch):
    handoff, aliases = _inputs(tmp_path, monkeypatch)
    output = tmp_path / "out"
    output.mkdir()
    (output / "keep").write_bytes(b"existing evidence")
    with pytest.raises(FileExistsError):
        candidate.prepare_symbol_publication(handoff, output, font_aliases=aliases)
    assert (output / "keep").read_bytes() == b"existing evidence"


def test_source_mutation_during_mapping_is_rejected(tmp_path, monkeypatch):
    handoff, aliases = _inputs(tmp_path, monkeypatch)
    original = candidate.build_publication

    def mutate(**kwargs):
        result = original(**kwargs)
        aliases.write_text("changed during preparation", encoding="utf-8")
        return result

    monkeypatch.setattr(candidate, "build_publication", mutate)
    with pytest.raises(ValueError, match="inputs changed"):
        candidate.prepare_symbol_publication(handoff, tmp_path / "out", font_aliases=aliases)
    assert not (tmp_path / "out").exists()


def test_unapproved_lookup_plan_is_rejected(tmp_path, monkeypatch):
    handoff, aliases = _inputs(tmp_path, monkeypatch)
    lookup = _load(handoff.override_lookups)
    lookup["lookups"][0]["overridePath"] = "unapproved.svg"
    _write(handoff.override_lookups, lookup)
    with pytest.raises(ValueError, match="authoritative Army discovery"):
        candidate.prepare_symbol_publication(handoff, tmp_path / "out", font_aliases=aliases)
    assert not (tmp_path / "out").exists()


def test_candidate_install_failure_leaves_no_partial_output(tmp_path, monkeypatch):
    handoff, aliases = _inputs(tmp_path, monkeypatch)
    output = tmp_path / "out"
    replace = Path.replace

    def fail_static(source, destination):
        if destination == output / "static":
            raise OSError("simulated candidate install failure")
        return replace(source, destination)

    monkeypatch.setattr(Path, "replace", fail_static)
    with pytest.raises(OSError, match="simulated candidate install"):
        candidate.prepare_symbol_publication(handoff, output, font_aliases=aliases)
    assert not output.exists()
