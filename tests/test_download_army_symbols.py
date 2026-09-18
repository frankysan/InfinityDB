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
