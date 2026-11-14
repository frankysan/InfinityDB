from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.symbols import symbol_source


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
    module = symbol_source

    name = module.destination_name(
        "https://assets.corvusbelli.net/army/img/logo/units/Special:Recent Changes?new=1*.svg"
    )
    assert name == "special-recent-changes-new-1.svg"


def test_complete_discovery_preserves_every_reference_and_unique_url() -> None:
    module = symbol_source
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


def test_discovery_marks_embedded_peripheral_profiles_from_source_metadata() -> None:
    module = symbol_source
    primary = unit_url("cutter")
    crabbot = unit_url("crabbot")
    documents = [
        module.SourceDocument(
            "metadata.json",
            {
                "factions": [],
                "skills": [{"id": 243, "name": "Peripheral"}],
            },
        ),
        module.SourceDocument(
            "101-panoceania.json",
            {
                "filters": {
                    "peripheral": [
                        {"id": 1, "name": "CRABBOT"},
                        {"id": 2, "name": "PALBOT"},
                    ]
                },
                "units": [
                    {
                        "id": 12,
                        "slug": "cutters",
                        "profileGroups": [
                            {
                                "profiles": [
                                    {"name": "CUTTER", "logo": primary},
                                    {
                                        "name": "Crabbot Ancillary Remote Unit",
                                        "logo": crabbot,
                                        "skills": [{"id": 243}],
                                    },
                                ]
                            }
                        ],
                    }
                ],
                "resume": [],
            },
        ),
    ]

    discovery = module.discover_symbols(
        documents,
        static_symbols=[],
        static_source="config/symbols/static-symbols.json",
    )

    unit_refs = [row for row in discovery.references if row["kind"] == "unit-profile"]
    assert "peripheralName" not in unit_refs[0]
    assert unit_refs[1]["peripheralName"] == "CRABBOT"



def test_legacy_army_logos_are_authoritative_faction_references() -> None:
    module = symbol_source
    legacy = module.LegacyArmy(
        id=906,
        name="Spiral Corps",
        slug="spiral-corps",
        role="non_aligned",
        group_id=901,
        group_name="Non-Aligned Armies",
        group_slug="non-aligned-armies",
        logo=faction_url("spiral-corps"),
        reason="Historical test identity.",
    )

    discovery = module.discover_symbols(
        source_documents(module),
        static_symbols=[],
        static_source="config/symbols/static-symbols.json",
        legacy_armies=(legacy,),
        legacy_source="data/curated/identities/legacy-armies.json",
    )

    legacy_refs = [
        row
        for row in discovery.references
        if row.get("factionId") == 906 and row.get("kind") == "faction"
    ]
    assert legacy_refs == [
        {
            "kind": "faction",
            "authoritative": True,
            "sourceDocument": "data/curated/identities/legacy-armies.json",
            "jsonPath": "$.armies[0].logo",
            "assetUrl": faction_url("spiral-corps"),
            "factionId": 906,
            "factionSlug": "spiral-corps",
        }
    ]
    assert discovery.audit["factionReferenceCount"] == 3
    assert faction_url("spiral-corps") in discovery.authoritative_urls
    plan = module.override_resolution_plan(discovery)
    assert plan.override_paths[faction_url("spiral-corps")] == "factions/spiral-corps.svg"


def test_unknown_svg_source_field_fails_closed() -> None:
    module = symbol_source
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
    module = symbol_source
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
    module = symbol_source
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
    module = symbol_source
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
    module = symbol_source
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

def test_override_resolution_uses_stable_category_and_disambiguates_collisions() -> None:
    module = symbol_source
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
