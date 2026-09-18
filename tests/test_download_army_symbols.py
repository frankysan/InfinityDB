import importlib.util
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    module_path = ROOT / "tools" / "download_army_symbols.py"
    spec = importlib.util.spec_from_file_location("download_army_symbols", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unit_url(name: str) -> str:
    return f"https://assets.corvusbelli.net/army/img/logo/units/{name}.svg"


def faction_url(name: str) -> str:
    return f"https://assets.corvusbelli.net/army/img/logo/factions/{name}.svg"


def static_config(path: Path, assets: list[dict[str, str]] | None = None) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "base_url": "https://assets.corvusbelli.net/army/img/icon/",
                "assets": assets or [],
            }
        ),
        encoding="utf-8",
    )
    return path


def source_documents(module):
    first = unit_url("unit-a-1")
    second = unit_url("unit-a-2")
    shared = unit_url("shared")
    return [
        module.SourceDocument(
            "metadata.json",
            {
                "factions": [
                    {"id": 101, "slug": "panoceania", "logo": faction_url("panoceania")},
                    {"id": 102, "slug": "sectorial", "logo": faction_url("panoceania")},
                ]
            },
        ),
        module.SourceDocument(
            "101-panoceania.json",
            {
                "units": [
                    {
                        "id": 1,
                        "slug": "unit-a",
                        "profileGroups": [
                            {
                                "profiles": [
                                    {"name": "A", "logo": first},
                                    {"name": "B", "logo": second},
                                ]
                            }
                        ],
                    },
                    {
                        "id": 2,
                        "slug": "unit-b",
                        "profileGroups": [{"profiles": [{"logo": shared}]}],
                    },
                ],
                "resume": [
                    {"id": 1, "slug": "unit-a", "logo": first},
                    {"id": 2, "slug": "unit-b", "logo": shared},
                ],
            },
        ),
        module.SourceDocument(
            "102-sectorial.json",
            {
                "units": [
                    {
                        "id": 2,
                        "slug": "unit-b",
                        "profileGroups": [{"profiles": [{"logo": shared}]}],
                    }
                ],
                "resume": [{"id": 2, "slug": "unit-b", "logo": shared}],
            },
        ),
    ]


def test_destination_name_preserves_svg_extension() -> None:
    module = load_module()

    name = module.destination_name(
        "https://assets.corvusbelli.net/army/img/logo/units/Special:Recent Changes?new=1*.svg"
    )
    assert name == "special-recent-changes-new-1.svg"


def test_complete_discovery_preserves_every_reference_and_unique_url() -> None:
    module = load_module()
    static = [
        {
            "key": "cube",
            "category": "characteristics",
            "filename": "cube.svg",
            "label": "Cube",
            "url": "https://assets.corvusbelli.net/army/img/icon/cube.svg",
        }
    ]

    discovery = module.discover_symbols(
        source_documents(module),
        static_symbols=static,
        static_source="config/symbols/static-symbols.json",
    )

    assert discovery.audit == {
        "unitProfileReferenceCount": 4,
        "uniqueUnitUrlCount": 3,
        "factionReferenceCount": 2,
        "uniqueFactionUrlCount": 1,
        "semanticReferenceCount": 6,
        "uniqueSemanticUrlCount": 4,
        "resumeReferenceCount": 3,
        "uniqueResumeUrlCount": 2,
        "staticReferenceCount": 1,
        "recursiveReferenceCount": 9,
        "uniqueRecursiveUrlCount": 4,
        "uniqueDownloadedUrlCount": 5,
        "unknownReferenceCount": 0,
    }
    assert len(discovery.references) == 10
    assert len(discovery.authoritative_urls) == 5

    unit_refs = [row for row in discovery.references if row["kind"] == "unit-profile"]
    assert [row["profileName"] for row in unit_refs[:2]] == ["A", "B"]
    shared = unit_url("shared")
    assert sum(row["assetUrl"] == shared for row in unit_refs) == 2

    faction_refs = [row for row in discovery.references if row["kind"] == "faction"]
    assert len(faction_refs) == 2
    assert faction_refs[0]["assetUrl"] == faction_refs[1]["assetUrl"]

    resume_refs = [row for row in discovery.references if row["kind"] == "resume-audit"]
    assert all(row["authoritative"] is False for row in resume_refs)


def test_unknown_svg_source_field_fails_closed() -> None:
    module = load_module()
    documents = source_documents(module)
    documents[1].data["unexpected"] = {"icon": unit_url("future-source-field")}

    with pytest.raises(ValueError, match="Unknown SVG-bearing") as excinfo:
        module.discover_symbols(
            documents,
            static_symbols=[],
            static_source="config/symbols/static-symbols.json",
        )
    assert "$.unexpected.icon" in str(excinfo.value)


def test_resume_logo_is_audit_only_and_not_download_authority() -> None:
    module = load_module()
    documents = [
        module.SourceDocument(
            "101-test.json",
            {
                "units": [],
                "resume": [{"id": 9, "slug": "audit-only", "logo": unit_url("resume-only")}],
            },
        )
    ]

    discovery = module.discover_symbols(
        documents,
        static_symbols=[],
        static_source="config/symbols/static-symbols.json",
    )

    assert discovery.authoritative_urls == set()
    assert discovery.audit["resumeReferenceCount"] == 1
    assert discovery.audit["recursiveReferenceCount"] == 1


def test_archive_paths_separate_categories_and_disambiguate_collisions() -> None:
    module = load_module()
    first = "https://assets.corvusbelli.net/army/img/logo/units/shared.svg"
    second = "https://assets.corvusbelli.net/army/img/logo/units/shared.svg?variant=2"
    discovery = module.Discovery(
        references=[
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-test.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
                "assetUrl": first,
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-test.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[1].logo",
                "assetUrl": second,
            },
        ],
        authoritative_urls={first, second},
        audit={},
        source_document_count=1,
    )

    paths = module.archive_paths(discovery)
    assert paths[first].startswith("units/")
    assert paths[second].startswith("units/")
    assert paths[first] != paths[second]
    assert "--" in paths[first]
    assert "--" in paths[second]


def test_static_symbol_config_validates_semantic_metadata(tmp_path: Path) -> None:
    module = load_module()
    path = static_config(
        tmp_path / "static.json",
        [
            {
                "key": "cube",
                "category": "characteristics",
                "filename": "cube.svg",
                "label": "Cube",
            }
        ],
    )

    rows = module.load_static_symbols(path)
    assert rows == [
        {
            "key": "cube",
            "category": "characteristics",
            "filename": "cube.svg",
            "label": "Cube",
            "url": "https://assets.corvusbelli.net/army/img/icon/cube.svg",
        }
    ]



def test_static_symbol_config_rejects_unsafe_category(tmp_path: Path) -> None:
    module = load_module()
    path = static_config(
        tmp_path / "static.json",
        [
            {
                "key": "cube",
                "category": "../characteristics",
                "filename": "cube.svg",
                "label": "Cube",
            }
        ],
    )

    with pytest.raises(ValueError, match="category must use lowercase slug syntax"):
        module.load_static_symbols(path)

def test_archive_symbols_uses_timestamp_and_complete_staging_set(tmp_path: Path) -> None:
    module = load_module()
    staging = tmp_path / "staging"
    (staging / "units").mkdir(parents=True)
    (staging / "factions").mkdir(parents=True)
    first = staging / "units" / "first.svg"
    second = staging / "factions" / "second.svg"
    first.write_text("<svg id='first'/>", encoding="utf-8")
    second.write_text("<svg id='second'/>", encoding="utf-8")

    archive = module.archive_symbols(
        [second, first],
        tmp_path / "archives",
        root=staging,
        now=datetime(2026, 9, 16, 21, 30, 45),
    )

    assert archive.name == "SYMBOLS 20260916-213045.zip"
    with zipfile.ZipFile(archive) as output:
        assert output.namelist() == ["factions/second.svg", "units/first.svg"]


def test_main_writes_snapshot_and_build_manifests(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    source = tmp_path / "army.zip"
    destination = tmp_path / "symbols"
    manifest_directory = tmp_path / "manifests"
    build_manifest = tmp_path / "army-symbol-build.json"
    static = static_config(tmp_path / "static.json")

    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(
            "metadata.json",
            json.dumps(
                {"factions": [{"id": 101, "slug": "test", "logo": faction_url("test")}]}
            ),
        )
        archive.writestr(
            "101-test.json",
            json.dumps(
                {
                    "version": "7.26246.158",
                    "units": [
                        {
                            "id": 1,
                            "slug": "test-unit",
                            "profileGroups": [
                                {"profiles": [{"logo": unit_url("test-unit")}]}
                            ],
                        }
                    ],
                    "resume": [{"id": 1, "slug": "test-unit", "logo": unit_url("test-unit")}],
                }
            ),
        )

    from infinity_db.snapshot_provenance import write_snapshot_manifest

    army_manifest = write_snapshot_manifest(
        source,
        manifest_directory,
        snapshot_type="army",
        acquired_at=datetime(2026, 9, 18, 8, 35, 9, tzinfo=UTC),
        source_url="https://api.corvusbelli.com/army",
        document_count=2,
        project_root=tmp_path,
        language="en",
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"<svg/>"

    monkeypatch.setattr(module, "urlopen", lambda *_args, **_kwargs: Response())

    assert (
        module.main(
            [
                str(source),
                str(destination),
                "--static-symbols",
                str(static),
                "--build-manifest",
                str(build_manifest),
                "--manifest-dir",
                str(manifest_directory),
                "--delay",
                "0",
            ]
        )
        == 0
    )

    archives = list(destination.glob("SYMBOLS *.zip"))
    manifests = [
        path
        for path in manifest_directory.glob("*.json")
        if path != army_manifest
    ]
    assert len(archives) == 1
    assert len(manifests) == 1

    from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file
    from infinity_db.symbol_manifest import load_symbol_manifest

    snapshot = load_snapshot_manifest(manifests[0], archive=archives[0])
    assert snapshot["snapshot"]["type"] == "symbols"
    assert snapshot["snapshot"]["documentCount"] == 2
    assert snapshot["inputArtifact"]["sha256"] == sha256_file(source)
    assert snapshot["source"] == {"url": module.ASSET_ROOT_URL}

    build = load_symbol_manifest(build_manifest)
    assert build["formatVersion"] == 2
    assert build["snapshot"]["armySource"] == {
        "acquiredAt": "2026-09-18T08:35:09+00:00",
        "language": "en",
        "url": "https://api.corvusbelli.com/army",
        "documentCount": 2,
        "sourceRevisions": {"7.26246.158": 1},
    }
    assert build["snapshot"]["armyArtifact"]["sha256"] == sha256_file(source)
    assert build["snapshot"]["symbolArtifact"]["sha256"] == sha256_file(archives[0])
    assert len(build["assets"]) == 2
    assert build["audit"]["semanticReferenceCount"] == 2
    assert build["audit"]["resumeReferenceCount"] == 1
    assert build["audit"]["unknownReferenceCount"] == 0
    assert {row["kind"] for row in build["references"]} == {
        "unit-profile",
        "faction",
        "resume-audit",
    }


def _single_asset_army_snapshot(tmp_path: Path, module, *, url: str) -> tuple[Path, Path]:
    source = tmp_path / "army.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("metadata.json", json.dumps({"factions": []}))
        archive.writestr(
            "101-test.json",
            json.dumps(
                {
                    "version": "7.26246.158",
                    "units": [
                        {
                            "id": 1,
                            "slug": "test-unit",
                            "profileGroups": [{"profiles": [{"logo": url}]}],
                        }
                    ],
                    "resume": [],
                }
            ),
        )

    from infinity_db.snapshot_provenance import write_snapshot_manifest

    manifest_directory = tmp_path / "manifests"
    manifest = write_snapshot_manifest(
        source,
        manifest_directory,
        snapshot_type="army",
        acquired_at=datetime(2026, 9, 18, 8, 35, 9, tzinfo=UTC),
        source_url="https://api.corvusbelli.com/army",
        document_count=2,
        project_root=tmp_path,
        language="en",
    )
    return source, manifest


def test_override_resolution_uses_stable_category_and_disambiguates_collisions() -> None:
    module = load_module()
    first = unit_url("shared")
    second = first + "?variant=2"
    discovery = module.Discovery(
        references=[
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-test.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
                "assetUrl": first,
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-test.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[1].logo",
                "assetUrl": second,
            },
        ],
        authoritative_urls={first, second},
        audit={},
        source_document_count=1,
    )

    plan = module.override_resolution_plan(discovery)

    assert len(plan.collisions) == 1
    assert plan.override_paths[first].startswith("units/shared--")
    assert plan.override_paths[second].startswith("units/shared--")
    assert plan.override_paths[first] != plan.override_paths[second]


def test_matching_override_suppresses_cache_and_network(tmp_path: Path) -> None:
    module = load_module()
    url = unit_url("test-unit")
    source, manifest = _single_asset_army_snapshot(tmp_path, module, url=url)
    destination = tmp_path / "symbols"
    build_manifest = tmp_path / "army-symbol-build.json"
    override_root = tmp_path / "image_overrides"
    override = override_root / "units" / "test-unit.svg"
    override.parent.mkdir(parents=True)
    override.write_bytes(b"<svg id='override'/>")
    unused = override_root / "units" / "unused.svg"
    unused.write_bytes(b"<svg id='unused'/>")
    static = static_config(tmp_path / "static.json")
    progress: list[str] = []

    def fail_network(*_args, **_kwargs):
        raise AssertionError("network must not be used for a matching override")

    result = module.acquire_symbol_snapshot(
        source,
        destination,
        manifest.parent,
        build_manifest,
        static_symbols_path=static,
        delay=0,
        project_root=tmp_path,
        opener=fail_network,
        progress=progress.append,
        army_snapshot_manifest=manifest,
        override_root=override_root,
        refresh_symbols=True,
        acquired_at=datetime(2026, 9, 18, 13, 0, tzinfo=UTC),
    )

    from infinity_db.symbol_manifest import load_symbol_manifest

    build = load_symbol_manifest(result.build_manifest)
    assert build["assets"][0]["sourceMethod"] == "override"
    assert any("Symbol sources: override 1 | cache 0 | network 0" in row for row in progress)
    assert any("units/unused.svg" in row for row in progress)
    with zipfile.ZipFile(result.archive) as archive:
        assert archive.read(build["assets"][0]["archivePath"]) == b"<svg id='override'/>"


def test_invalid_matching_override_fails_without_network(tmp_path: Path) -> None:
    module = load_module()
    url = unit_url("test-unit")
    source, manifest = _single_asset_army_snapshot(tmp_path, module, url=url)
    override_root = tmp_path / "image_overrides"
    override = override_root / "units" / "test-unit.svg"
    override.parent.mkdir(parents=True)
    override.write_text("not svg", encoding="utf-8")
    static = static_config(tmp_path / "static.json")

    def fail_network(*_args, **_kwargs):
        raise AssertionError("invalid matching override must not fall through")

    with pytest.raises(ValueError, match="Invalid SVG from override"):
        module.acquire_symbol_snapshot(
            source,
            tmp_path / "symbols",
            manifest.parent,
            tmp_path / "army-symbol-build.json",
            static_symbols_path=static,
            delay=0,
            project_root=tmp_path,
            opener=fail_network,
            army_snapshot_manifest=manifest,
            override_root=override_root,
        )



def test_network_404_is_recorded_and_acquisition_continues(tmp_path: Path) -> None:
    module = load_module()
    url = unit_url("missing-unit")
    source, manifest = _single_asset_army_snapshot(tmp_path, module, url=url)
    static = static_config(tmp_path / "static.json")
    progress: list[str] = []

    def missing(*_args, **_kwargs):
        raise module.HTTPError(url, 404, "Not Found", {}, None)

    result = module.acquire_symbol_snapshot(
        source,
        tmp_path / "symbols",
        manifest.parent,
        tmp_path / "army-symbol-build.json",
        static_symbols_path=static,
        delay=0,
        project_root=tmp_path,
        opener=missing,
        progress=progress.append,
        army_snapshot_manifest=manifest,
        override_root=tmp_path / "image_overrides",
        refresh_symbols=True,
        acquired_at=datetime(2026, 9, 18, 13, 0, tzinfo=UTC),
    )

    from infinity_db.symbol_manifest import load_symbol_manifest

    build = load_symbol_manifest(result.build_manifest)
    assert build["assets"] == []
    assert build["unavailableAssets"] == [
        {
            "url": url,
            "sourceFilename": "missing-unit.svg",
            "archivePath": "units/missing-unit.svg",
            "sourceMethod": "network",
            "httpStatus": 404,
        }
    ]
    assert build["audit"]["uniqueDownloadedUrlCount"] == 0
    assert any("[unavailable HTTP 404]" in row for row in progress)
    assert any("unavailable 1" in row for row in progress)
    with zipfile.ZipFile(result.archive) as archive:
        assert archive.namelist() == []


def test_non_404_network_error_still_aborts_acquisition(tmp_path: Path) -> None:
    module = load_module()
    url = unit_url("server-error")
    source, manifest = _single_asset_army_snapshot(tmp_path, module, url=url)
    static = static_config(tmp_path / "static.json")

    def server_error(*_args, **_kwargs):
        raise module.HTTPError(url, 503, "Unavailable", {}, None)

    with pytest.raises(module.HTTPError) as excinfo:
        module.acquire_symbol_snapshot(
            source,
            tmp_path / "symbols",
            manifest.parent,
            tmp_path / "army-symbol-build.json",
            static_symbols_path=static,
            delay=0,
            project_root=tmp_path,
            opener=server_error,
            army_snapshot_manifest=manifest,
            override_root=tmp_path / "image_overrides",
            refresh_symbols=True,
            acquired_at=datetime(2026, 9, 18, 13, 0, tzinfo=UTC),
        )

    assert excinfo.value.code == 503
    assert not (tmp_path / "army-symbol-build.json").exists()
    assert list((tmp_path / "symbols").glob("SYMBOLS *.zip")) == []

def test_validated_prior_symbol_snapshot_is_used_as_cache(tmp_path: Path) -> None:
    module = load_module()
    url = unit_url("test-unit")
    source, manifest = _single_asset_army_snapshot(tmp_path, module, url=url)
    destination = tmp_path / "symbols"
    destination.mkdir()
    cached_archive = destination / "SYMBOLS 20260918-120000.zip"
    cached_body = b"<svg id='cached'/>"
    with zipfile.ZipFile(cached_archive, "w") as archive:
        archive.writestr("units/test-unit.svg", cached_body)

    from infinity_db.snapshot_provenance import write_snapshot_manifest
    from infinity_db.symbol_manifest import (
        build_symbol_manifest,
        load_symbol_manifest,
        write_symbol_manifest,
    )

    write_snapshot_manifest(
        cached_archive,
        manifest.parent,
        snapshot_type="symbols",
        acquired_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        source_url=module.ASSET_ROOT_URL,
        document_count=1,
        project_root=tmp_path,
        input_artifact=source,
    )
    build_manifest = tmp_path / "army-symbol-build.json"
    previous = build_symbol_manifest(
        army_artifact=source,
        symbol_artifact=cached_archive,
        acquired_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        army_acquired_at=datetime(2026, 9, 18, 8, 35, 9, tzinfo=UTC),
        army_language="en",
        army_source_url="https://api.corvusbelli.com/army",
        source_document_count=2,
        source_revisions={"7.26246.158": 1},
        assets=[
            {
                "url": url,
                "sourceFilename": "test-unit.svg",
                "archivePath": "units/test-unit.svg",
                "sha256": __import__("hashlib").sha256(cached_body).hexdigest(),
                "sourceMethod": "network",
            }
        ],
        references=[
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-test.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
                "assetUrl": url,
                "unitId": 1,
                "unitSlug": "test-unit",
            }
        ],
        audit={
            "unitProfileReferenceCount": 1,
            "uniqueUnitUrlCount": 1,
            "factionReferenceCount": 0,
            "uniqueFactionUrlCount": 0,
            "semanticReferenceCount": 1,
            "uniqueSemanticUrlCount": 1,
            "resumeReferenceCount": 0,
            "uniqueResumeUrlCount": 0,
            "staticReferenceCount": 0,
            "recursiveReferenceCount": 1,
            "uniqueRecursiveUrlCount": 1,
            "uniqueDownloadedUrlCount": 1,
            "unknownReferenceCount": 0,
        },
        project_root=tmp_path,
    )
    write_symbol_manifest(previous, build_manifest)
    static = static_config(tmp_path / "static.json")

    def fail_network(*_args, **_kwargs):
        raise AssertionError("validated cache hit must suppress network")

    result = module.acquire_symbol_snapshot(
        source,
        destination,
        manifest.parent,
        build_manifest,
        static_symbols_path=static,
        delay=0,
        project_root=tmp_path,
        opener=fail_network,
        army_snapshot_manifest=manifest,
        override_root=tmp_path / "image_overrides",
        acquired_at=datetime(2026, 9, 18, 13, 0, tzinfo=UTC),
    )

    current = load_symbol_manifest(result.build_manifest)
    assert current["assets"][0]["sourceMethod"] == "cache"
    with zipfile.ZipFile(result.archive) as archive:
        assert archive.read(current["assets"][0]["archivePath"]) == cached_body


def test_refresh_symbols_bypasses_cache(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    url = unit_url("test-unit")
    source, manifest = _single_asset_army_snapshot(tmp_path, module, url=url)
    static = static_config(tmp_path / "static.json")
    body = b"<svg id='network'/>"

    def fail_cache(*_args, **_kwargs):
        raise AssertionError("refresh mode must not inspect the prior symbol cache")

    monkeypatch.setattr(module, "load_symbol_cache", fail_cache)

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return body

    result = module.acquire_symbol_snapshot(
        source,
        tmp_path / "symbols",
        manifest.parent,
        tmp_path / "army-symbol-build.json",
        static_symbols_path=static,
        delay=0,
        project_root=tmp_path,
        opener=lambda *_args, **_kwargs: Response(),
        army_snapshot_manifest=manifest,
        override_root=tmp_path / "image_overrides",
        refresh_symbols=True,
        acquired_at=datetime(2026, 9, 18, 13, 0, tzinfo=UTC),
    )

    from infinity_db.symbol_manifest import load_symbol_manifest

    build = load_symbol_manifest(result.build_manifest)
    assert build["assets"][0]["sourceMethod"] == "network"


def test_symbol_cache_rejects_mutated_archive(tmp_path: Path) -> None:
    module = load_module()
    army = tmp_path / "army.zip"
    army.write_bytes(b"army")
    destination = tmp_path / "symbols"
    destination.mkdir()
    symbols = destination / "SYMBOLS 20260918-120000.zip"
    url = unit_url("cached")
    body = b"<svg id='cached'/>"
    with zipfile.ZipFile(symbols, "w") as archive:
        archive.writestr("units/cached.svg", body)

    from infinity_db.snapshot_provenance import write_snapshot_manifest
    from infinity_db.symbol_manifest import build_symbol_manifest, write_symbol_manifest

    manifest_directory = tmp_path / "manifests"
    write_snapshot_manifest(
        symbols,
        manifest_directory,
        snapshot_type="symbols",
        acquired_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        source_url=module.ASSET_ROOT_URL,
        document_count=1,
        project_root=tmp_path,
        input_artifact=army,
    )
    build_manifest = tmp_path / "army-symbol-build.json"
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 18, 12, 0, tzinfo=UTC),
        army_acquired_at=datetime(2026, 9, 18, 8, 35, 9, tzinfo=UTC),
        army_language="en",
        army_source_url="https://api.corvusbelli.com/army",
        source_document_count=1,
        source_revisions={},
        assets=[
            {
                "url": url,
                "sourceFilename": "cached.svg",
                "archivePath": "units/cached.svg",
                "sha256": module.hashlib.sha256(body).hexdigest(),
                "sourceMethod": "network",
            }
        ],
        references=[],
        audit={
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
        },
        project_root=tmp_path,
    )
    write_symbol_manifest(document, build_manifest)
    symbols.write_bytes(b"mutated")

    with pytest.raises(ValueError, match="Cached symbol archive SHA-256 mismatch"):
        module.load_symbol_cache(
            build_manifest,
            destination=destination,
            manifest_directory=manifest_directory,
            project_root=tmp_path,
        )
