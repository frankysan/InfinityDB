"""End-to-end offline external raw-symbol bridge and existing build-state parity."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from infinity_db.snapshot_provenance import sha256_file, write_snapshot_manifest
from infinity_db.symbol_manifest import load_symbol_manifest
from tools import build_symbols, download_army_symbols
from tools.download_army_symbols import (
    acquire_symbol_snapshot,
    archive_paths,
    discover_symbol_source,
)
from tools.snapshot_archive import create_timestamped_archive
from tools.verify_raw_symbol_handoff import (
    RawHandoffError,
    load_verified_raw_upstream,
)

STAMP = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
UNIT_A = "https://assets.corvusbelli.net/army/img/logo/units/unit-a.svg"
UNIT_B = "https://assets.corvusbelli.net/army/img/logo/units/unit-b.svg"
STATIC = "https://assets.corvusbelli.net/army/img/icon/cube.svg"
SVG_SHARED = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1"/></svg>'
SVG_STATIC = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="2"/></svg>'
SVG_OVERRIDE = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'


def _canonical(document: dict[str, Any]) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _fixture(
    tmp_path: Path, *, missing: set[str] | None = None,
    unit_b_url: str = UNIT_B,
) -> tuple[Path, Path, Path, Path, Path, Path, Path, dict[str, str]]:
    missing = missing or set()
    army = tmp_path / "JSON 20260917-120000.zip"
    with zipfile.ZipFile(army, "w") as archive:
        archive.writestr("metadata.json", json.dumps({"factions": []}))
        archive.writestr(
            "101-panoceania.json",
            json.dumps({
                "version": "7.26246.158",
                "units": [
                    {"id": 1, "profileGroups": [{"profiles": [{"logo": UNIT_A}]}]},
                    {"id": 2, "profileGroups": [{"profiles": [{"logo": unit_b_url}]}]},
                ],
            }),
        )
    army_manifest = write_snapshot_manifest(
        army, tmp_path / "army-provenance",
        snapshot_type="army", acquired_at=STAMP,
        source_url="https://api.corvusbelli.com/army",
        document_count=2, source_data_changed_on=date(2026, 9, 3),
        language="en", project_root=tmp_path,
    )
    static_path = tmp_path / "static-symbols.json"
    static_path.write_text(
        json.dumps({
            "schema_version": 2,
            "base_url": "https://assets.corvusbelli.net/army/img/icon/",
            "assets": [{
                "key": "cube",
                "category": "characteristics",
                "filename": "cube.svg",
                "label": "Cube",
            }],
        }),
        encoding="utf-8",
    )
    discovery = discover_symbol_source(
        army, static_symbols_path=static_path,
        legacy_armies_path=None, project_root=tmp_path,
    )
    paths = archive_paths(discovery)
    assert set(paths) == {STATIC, UNIT_A, unit_b_url}
    plan = {
        "format": "InfinityDB raw symbol acquisition requests",
        "formatVersion": 1,
        "inputArtifact": {"name": army.name, "sha256": sha256_file(army)},
        "sourceDocumentCount": 2,
        "requests": [
            {"url": url, "archivePath": paths[url]}
            for url in sorted(paths)
        ],
    }
    plan_path = tmp_path / "source-plan.json"
    plan_path.write_bytes(_canonical(plan))

    upstream = {STATIC: SVG_STATIC, UNIT_A: SVG_SHARED, unit_b_url: SVG_SHARED}
    raw_root = tmp_path / "external" / "raw"
    files: list[Path] = []
    assets: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    for url in sorted(upstream):
        if url in missing:
            unavailable.append({
                "url": url, "archivePath": paths[url], "httpStatus": 404,
            })
            continue
        path = raw_root / paths[url]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(upstream[url])
        files.append(path)
        assets.append({
            "url": url,
            "archivePath": paths[url],
            "sha256": hashlib.sha256(upstream[url]).hexdigest(),
            "sourceMethod": "network",
        })
    raw_archive = create_timestamped_archive(
        files, tmp_path / "external" / "symbols",
        prefix="SYMBOLS", root=raw_root, now=STAMP,
    )
    raw_manifest = write_snapshot_manifest(
        raw_archive, tmp_path / "external" / "manifests",
        snapshot_type="symbols", acquired_at=STAMP,
        source_url="https://assets.corvusbelli.net/army/img/",
        document_count=len(assets), project_root=tmp_path,
        input_artifact=army,
    )
    report = {
        "format": "InfinityDB raw symbol acquisition report",
        "formatVersion": 1,
        "inputArtifact": plan["inputArtifact"],
        "sourcePlanSha256": hashlib.sha256(_canonical(plan)).hexdigest(),
        "snapshot": {
            "archiveName": raw_archive.name,
            "sha256": sha256_file(raw_archive),
            "snapshotManifestName": raw_manifest.name,
            "snapshotManifestSha256": sha256_file(raw_manifest),
            "documentCount": len(assets),
            "acquiredAt": STAMP.isoformat(timespec="seconds"),
        },
        "assets": assets,
        "unavailableAssets": unavailable,
    }
    report_path = tmp_path / "external" / "raw-report.json"
    report_path.write_bytes(_canonical(report))
    return (
        army, army_manifest, static_path, plan_path,
        raw_archive, raw_manifest, report_path, paths,
    )


def _upstream(
    paths: tuple[Path, Path, Path, Path, Path, Path, Path, dict[str, str]],
) -> dict[str, bytes | None]:
    army, _army_manifest, _static, plan, archive, manifest, report, names = paths
    return load_verified_raw_upstream(
        plan, army, archive, manifest, report,
        authoritative_paths=names, source_document_count=2,
    )


def _acquire(
    tmp_path: Path,
    paths: tuple[Path, Path, Path, Path, Path, Path, Path, dict[str, str]],
    *,
    overrides: Path | None = None,
) -> tuple[Path, Path]:
    army, army_manifest, static, _plan, _raw, _manifest, _report, _names = paths
    root = tmp_path / "data"
    discovery = discover_symbol_source(
        army, static_symbols_path=static, legacy_armies_path=None,
        project_root=tmp_path,
    )

    def unexpected_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("External raw handoff attempted network acquisition")

    result = acquire_symbol_snapshot(
        army,
        root / "raw" / "symbols",
        root / "manifests" / "snapshots",
        root / "manifests" / "army-symbol-build.json",
        static_symbols_path=static,
        legacy_armies_path=None,
        delay=0,
        project_root=tmp_path,
        discovery=discovery,
        opener=unexpected_network,
        army_snapshot_manifest=army_manifest,
        override_root=overrides or (tmp_path / "no-overrides"),
        raw_upstream=_upstream(paths),
        acquired_at=STAMP,
    )
    return result.archive, result.build_manifest


def test_verified_raw_bridge_preserves_exact_zip_and_v2_build_contract(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    raw_upstream = _upstream(paths)
    assert raw_upstream == {
        STATIC: SVG_STATIC, UNIT_A: SVG_SHARED, UNIT_B: SVG_SHARED,
    }
    archive, manifest = _acquire(tmp_path, paths)
    assert archive.read_bytes() == paths[4].read_bytes()
    document = load_symbol_manifest(manifest)
    assert document["formatVersion"] == 2
    assert [row["sourceMethod"] for row in document["assets"]] == [
        "network", "network", "network",
    ]
    for asset in document["assets"]:
        assert asset["sha256"] == asset["upstreamSha256"]
    assert document["unavailableAssets"] == []
    assert document["snapshot"]["symbolArtifact"]["sha256"] == sha256_file(archive)
    assert document["snapshot"]["armyArtifact"]["sha256"] == sha256_file(paths[0])


def test_raw_bridge_keeps_same_upstream_override_propagation(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    override_root = tmp_path / "overrides"
    (override_root / "units").mkdir(parents=True)
    (override_root / "units" / "unit-a.svg").write_bytes(SVG_OVERRIDE)
    archive, manifest = _acquire(tmp_path, paths, overrides=override_root)
    document = load_symbol_manifest(manifest)
    units = [row for row in document["assets"] if row["url"] in {UNIT_A, UNIT_B}]
    assert len(units) == 2
    assert all(row["sourceMethod"] == "override" for row in units)
    assert {row["upstreamSha256"] for row in units} == {
        hashlib.sha256(SVG_SHARED).hexdigest(),
    }
    with zipfile.ZipFile(archive) as content:
        for row in units:
            assert content.read(row["archivePath"]) == SVG_OVERRIDE


def test_query_qualified_source_urls_keep_approved_identity(tmp_path: Path) -> None:
    qualified = UNIT_B + "?variant=2"
    paths = _fixture(tmp_path, unit_b_url=qualified)
    assert _upstream(paths)[qualified] == SVG_SHARED
    archive, manifest = _acquire(tmp_path, paths)
    assert archive.read_bytes() == paths[4].read_bytes()
    document = load_symbol_manifest(manifest)
    assert qualified in {row["url"] for row in document["assets"]}


def test_external_raw_upstream_matches_existing_network_override_pipeline(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    override_root = tmp_path / "overrides"
    (override_root / "units").mkdir(parents=True)
    (override_root / "units" / "unit-a.svg").write_bytes(SVG_OVERRIDE)
    external_archive, external_manifest = _acquire(
        tmp_path, paths, overrides=override_root,
    )

    army, army_manifest, static = paths[:3]
    discovery = discover_symbol_source(
        army, static_symbols_path=static, legacy_armies_path=None,
        project_root=tmp_path,
    )
    upstream = {STATIC: SVG_STATIC, UNIT_A: SVG_SHARED, UNIT_B: SVG_SHARED}

    class Response:
        def __init__(self, body: bytes):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def read(self) -> bytes:
            return self.body

    def opener(url: str, *, timeout: int) -> Response:
        assert timeout == 30
        return Response(upstream[url])

    original = acquire_symbol_snapshot(
        army,
        tmp_path / "in-tree" / "symbols",
        tmp_path / "in-tree" / "manifests",
        tmp_path / "in-tree" / "army-symbol-build.json",
        static_symbols_path=static,
        legacy_armies_path=None,
        delay=0,
        project_root=tmp_path,
        discovery=discovery,
        opener=opener,
        army_snapshot_manifest=army_manifest,
        override_root=override_root,
        refresh_symbols=True,
        acquired_at=STAMP,
    )
    assert external_archive.read_bytes() == original.archive.read_bytes()
    exported_state = load_symbol_manifest(external_manifest)
    current_state = load_symbol_manifest(original.build_manifest)
    for key in ("assets", "unavailableAssets", "references", "audit"):
        assert exported_state[key] == current_state[key]
    assert exported_state["snapshot"]["armySource"] == current_state["snapshot"]["armySource"]
    assert (
        exported_state["snapshot"]["symbolArtifact"]["sha256"]
        == current_state["snapshot"]["symbolArtifact"]["sha256"]
    )


def test_raw_bridge_retains_http_404_as_unavailable_without_network(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path, missing={UNIT_B})
    assert _upstream(paths)[UNIT_B] is None
    _archive, manifest = _acquire(tmp_path, paths)
    document = load_symbol_manifest(manifest)
    assert [row["url"] for row in document["unavailableAssets"]] == [UNIT_B]
    assert document["unavailableAssets"][0]["httpStatus"] == 404


def test_raw_bridge_refuses_source_plan_stale_against_discovery(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    expected = dict(paths[-1])
    expected[UNIT_B] = "units/different.svg"
    with pytest.raises(RawHandoffError, match="differs from current authoritative"):
        load_verified_raw_upstream(
            paths[3], paths[0], paths[4], paths[5], paths[6],
            authoritative_paths=expected, source_document_count=2,
        )
    with pytest.raises(RawHandoffError, match="differs from current authoritative"):
        load_verified_raw_upstream(
            paths[3], paths[0], paths[4], paths[5], paths[6],
            authoritative_paths=paths[-1], source_document_count=3,
        )


def test_build_symbols_cli_consumes_raw_handoff_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    army, army_manifest, static, plan, raw, raw_manifest, report, _names = paths
    original_discovery = build_symbols.discover_symbol_source
    monkeypatch.setattr(
        build_symbols, "discover_symbol_source",
        lambda source, **kwargs: original_discovery(
            source, legacy_armies_path=None, project_root=tmp_path, **kwargs,
        ),
    )
    monkeypatch.setattr(
        download_army_symbols, "urlopen",
        lambda *_args, **_kwargs: pytest.fail("External acquisition used network"),
    )
    data_root = tmp_path / "data"
    assert build_symbols.main([
        "--snapshot", str(army),
        "--snapshot-manifest", str(army_manifest),
        "--data-root", str(data_root),
        "--static-symbols", str(static),
        "--image-overrides", str(tmp_path / "no-overrides"),
        "--raw-symbol-plan", str(plan),
        "--raw-symbol-archive", str(raw),
        "--raw-symbol-manifest", str(raw_manifest),
        "--raw-symbol-report", str(report),
        "--stop-after", "acquisition",
    ]) == 0
    build_manifest = data_root / "manifests" / "army-symbol-build.json"
    doc = load_symbol_manifest(build_manifest)
    assert doc["formatVersion"] == 2
    output_archive = (
        data_root / "raw" / "symbols" / doc["snapshot"]["symbolArtifact"]["name"]
    )
    assert output_archive.read_bytes() == raw.read_bytes()

    assert build_symbols.main([
        "--resume", "--snapshot", str(army),
        "--snapshot-manifest", str(army_manifest),
        "--data-root", str(data_root),
        "--stop-after", "acquisition",
    ]) == 0
    assert build_symbols.main([
        "--resume", "--snapshot", str(army),
        "--snapshot-manifest", str(army_manifest),
        "--data-root", str(data_root),
        "--stop-after", "materialization",
    ]) == 0
    assert len(list((data_root / "work" / "symbols").rglob("*.svg"))) == 3


def test_build_symbols_cli_requires_complete_raw_handoff() -> None:
    with pytest.raises(SystemExit) as error:
        build_symbols.main(["--snapshot", "army.zip", "--raw-symbol-plan", "plan.json"])
    assert error.value.code == 2
    with pytest.raises(SystemExit) as error:
        build_symbols.main([
            "--resume", "--raw-symbol-plan", "plan.json",
            "--raw-symbol-archive", "raw.zip",
            "--raw-symbol-manifest", "raw.json",
            "--raw-symbol-report", "report.json",
        ])
    assert error.value.code == 2
