import json
from pathlib import Path

import pytest

from infinity_db.curated import (
    CURATED_FORMAT_VERSION,
    discover_curated_documents,
    load_curated_directory,
    load_curated_document,
)


def valid_document() -> dict:
    return {
        "format": "InfinityDB curated reference",
        "formatVersion": 19,
        "collection": {
            "id": "n5-core-v5.3",
            "title": "N5 Core Rules v5.3",
            "domain": "core-rules",
            "status": "current",
            "effectiveFrom": "2026-08-10",
            "authority": "primary",
        },
        "vocabularySources": {
            "skillTypes": [
                {
                    "sourceId": "n5-core-v5.3",
                    "heading": "Skills",
                    "page": 76,
                }
            ],
            "labels": [
                {
                    "sourceId": "n5-core-v5.3",
                    "heading": "Labels",
                    "page": 174,
                }
            ],
        },
        "skillTypes": [
            {
                "id": "automatic",
                "name": "Automatic",
                "labels": ["Automatic Skill", "Automatic Skills"],
                "descriptions": {
                    "singular": (
                        "An Automatic Skill can be employed without expending an Order or ARO."
                    ),
                    "plural": "Automatic Skills can be employed without expending an Order or ARO.",
                },
            }
        ],
        "labels": [
            {
                "id": "example-label",
                "name": "Example",
                "description": "An example label.",
            }
        ],
        "sources": [
            {
                "id": "n5-core-v5.3",
                "kind": "pdf",
                "title": "N5 core rules",
                "version": "5.3",
                "publishedDate": "2026-08-10",
                "localPath": "data/pdf/rules/n5-rules-v5-3-en.pdf",
                "url": "https://experience.corvusbelli.com/en/infinity/resources",
                "pageCount": 196,
                "authority": "primary",
            }
        ],
        "records": [
            {
                "id": "skill:example",
                "kind": "skill",
                "name": "Example skill",
                "summary": "A concise human-written summary.",
                "scope": {"game": "N5", "seasons": ["current"]},
                "facts": {"typeIds": ["automatic"]},
                "labelIds": ["example-label"],
                "citations": [{"sourceId": "n5-core-v5.3", "page": 12}],
                "composition": {"role": "definition"},
                "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            }
        ],
    }


def test_load_curated_document_requires_provenance(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(valid_document()), encoding="utf-8")

    assert load_curated_document(path)["records"][0]["citations"][0]["page"] == 12


def test_skill_definition_supports_multiple_categories(tmp_path: Path) -> None:
    document = valid_document()
    document["skillTypes"].append(
        {
            "id": "aro",
            "name": "ARO",
            "labels": ["ARO Skill", "ARO Skills"],
            "descriptions": {
                "singular": "An ARO Skill may be declared as an ARO.",
                "plural": "ARO Skills may be declared as AROs.",
            },
        }
    )
    document["records"][0]["facts"]["typeIds"] = ["automatic", "aro"]
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_curated_document(path)["records"][0]["facts"]["typeIds"] == [
        "automatic",
        "aro",
    ]

    document["records"][0]["facts"]["typeIds"] = ["automatic", "automatic"]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="typeIds.*duplicates"):
        load_curated_document(path)

    document["records"][0]["facts"] = {"typeId": "automatic"}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="facts.typeIds.*non-empty array"):
        load_curated_document(path)


def test_full_skill_categories_override_fallback_declarations(tmp_path: Path) -> None:
    document = valid_document()
    document["skillTypes"].append(
        {
            "id": "aro",
            "name": "ARO",
            "labels": ["ARO Skill", "ARO Skills"],
            "descriptions": {
                "singular": "An ARO Skill may be declared as an ARO.",
                "plural": "ARO Skills may be declared as AROs.",
            },
        }
    )
    skill = document["records"][0]
    skill["facts"]["typeIds"] = ["automatic", "aro"]
    skill["armyLinks"] = [{"entity": "skill", "id": "example"}]
    skill["variantSemantics"] = {"inheritance": "family"}

    def declaration(record_id: str, type_id: str, order: int, page: int) -> dict:
        return {
            "id": record_id,
            "kind": "declaration-category",
            "name": type_id,
            "summary": "Fallback declaration category.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {"typeId": type_id, "order": order},
            "armyLinks": [{"entity": "skill", "id": "example"}],
            "citations": [{"sourceId": "n5-core-v5.3", "page": page}],
            "composition": {"role": "definition"},
            "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
        }

    document["records"].extend(
        [
            declaration(
                "declaration-category:automatic:p12", "automatic", 10, 12
            ),
            declaration("declaration-category:aro:p13", "aro", 20, 13),
        ]
    )
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)["records"][0]["facts"]["typeIds"] == [
        "automatic",
        "aro",
    ]

    document["records"][-1]["facts"]["order"] = 5
    path.write_text(json.dumps(document), encoding="utf-8")
    loaded = load_curated_document(path)
    assert loaded["records"][0]["facts"]["typeIds"] == ["automatic", "aro"]


def test_load_curated_document_requires_structured_scope_and_review(tmp_path: Path) -> None:
    document = valid_document()
    del document["records"][0]["scope"]
    path = tmp_path / "missing-scope.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="missing fields.*scope"):
        load_curated_document(path)

    document = valid_document()
    document["records"][0]["scope"] = {"game": "N5", "seasons": []}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="seasons.*non-empty array"):
        load_curated_document(path)

    document = valid_document()
    document["records"][0]["review"] = {
        "status": "approved",
        "reviewedOn": "2026-09-23",
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="status.*draft.*reviewed"):
        load_curated_document(path)


@pytest.mark.parametrize(
    "facts",
    [{}, {"orderType": "tactical"}, {"orderType": "regular", "level": 1}],
)
def test_training_requires_reviewed_order_type(tmp_path: Path, facts: dict) -> None:
    document = valid_document()
    training = document["records"][0]
    training.update(id="training:regular", kind="training", facts=facts)
    training.pop("labelIds")
    path = tmp_path / "bad-training.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Training"):
        load_curated_document(path)


def test_training_cannot_masquerade_as_army_skill(tmp_path: Path) -> None:
    document = valid_document()
    training = document["records"][0]
    training.update(
        id="training:irregular",
        kind="training",
        facts={"orderType": "irregular"},
        armyLinks=[{"entity": "skill", "id": "regular"}],
    )
    training.pop("labelIds")
    path = tmp_path / "mislinked-training.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="must not link to an Army Skill"):
        load_curated_document(path)


def test_load_curated_document_requires_explicit_composition_role(tmp_path: Path) -> None:
    document = valid_document()
    del document["records"][0]["composition"]
    path = tmp_path / "missing-composition.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="missing fields.*composition"):
        load_curated_document(path)

    document = valid_document()
    document["records"][0]["composition"] = {"role": "override"}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="definition.*supplement"):
        load_curated_document(path)


def test_load_curated_document_requires_typed_relations(tmp_path: Path) -> None:
    document = valid_document()
    document["records"][0]["relatedRecords"] = ["state:example"]
    path = tmp_path / "legacy-relations.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="replaced by typed 'relations'"):
        load_curated_document(path)

    document = valid_document()
    document["records"][0]["relations"] = [
        {"type": "maybe-related", "recordId": "state:example"}
    ]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported relation type"):
        load_curated_document(path)



def test_load_curated_document_requires_variant_semantics_for_army_linked_rules(
    tmp_path: Path,
) -> None:
    document = valid_document()
    document["records"][0]["armyLinks"] = [{"entity": "skill", "id": "example"}]
    path = tmp_path / "missing-variant-semantics.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="require.*variantSemantics"):
        load_curated_document(path)

    document["records"][0]["variantSemantics"] = {
        "inheritance": "family",
        "occurrenceParameters": [
            {
                "source": "army-extra",
                "kind": "distance",
                "positiveSign": "omit",
            }
        ],
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)["records"][0]["variantSemantics"] == (
        document["records"][0]["variantSemantics"]
    )


def test_source_specific_variant_semantics_require_numeric_army_identity(
    tmp_path: Path,
) -> None:
    document = valid_document()
    record = document["records"][0]
    record["armyLinks"] = [{"entity": "skill", "id": "example"}]
    record["variantSemantics"] = {"inheritance": "source"}
    path = tmp_path / "source-variant.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="exact numeric Army source id"):
        load_curated_document(path)

def test_source_specific_variant_semantics_require_typed_source_variant(
    tmp_path: Path,
) -> None:
    document = valid_document()
    record = document["records"][0]
    record["armyLinks"] = [{"entity": "skill", "id": 20}]
    record["variantSemantics"] = {"inheritance": "source"}
    path = tmp_path / "missing-source-variant.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="require 'sourceVariant'"):
        load_curated_document(path)

    record["variantSemantics"]["sourceVariant"] = {"kind": "level", "value": 0}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="positive integer"):
        load_curated_document(path)

    record["variantSemantics"]["sourceVariant"] = {
        "kind": "named",
        "label": "Profile variant",
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)["records"][0]["variantSemantics"] == (
        record["variantSemantics"]
    )

    record["variantSemantics"]["sourceVariant"] = {
        "kind": "attribute-replacement",
        "attribute": "BS",
        "value": 0,
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="positive integer"):
        load_curated_document(path)

    record["variantSemantics"]["sourceVariant"]["value"] = 12
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)["records"][0]["variantSemantics"] == (
        record["variantSemantics"]
    )


def test_catalog_rule_army_links_must_match_record_kind(tmp_path: Path) -> None:
    document = valid_document()
    record = document["records"][0]
    record["armyLinks"] = [{"entity": "weapon", "id": 1}]
    record["variantSemantics"] = {"inheritance": "family"}
    path = tmp_path / "mismatched-army-link.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="skill definitions may only link"):
        load_curated_document(path)


def test_supplements_cannot_define_army_routing(tmp_path: Path) -> None:
    document = valid_document()
    record = document["records"][0]
    record["composition"] = {"role": "supplement"}
    record["armyLinks"] = [{"entity": "skill", "id": "example"}]
    path = tmp_path / "supplement-army-link.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="inherit Army routing"):
        load_curated_document(path)


def test_load_curated_document_rejects_unstructured_json(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    path.write_text(json.dumps({"units": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="must declare format"):
        load_curated_document(path)


def test_load_curated_document_requires_pdf_source_url(tmp_path: Path) -> None:
    document = valid_document()
    del document["sources"][0]["url"]
    path = tmp_path / "missing-pdf-url.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="'url' must be a non-empty string"):
        load_curated_document(path)


def test_load_curated_document_rejects_legacy_reference_locators(tmp_path: Path) -> None:
    document = valid_document()
    reference = document["vocabularySources"]["skillTypes"][0]
    reference["path"] = "legacy.html"
    reference["snapshotDate"] = "2026-09-15"
    path = tmp_path / "legacy-reference.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported legacy fields"):
        load_curated_document(path)


def test_load_curated_document_accepts_archived_wiki_citation(tmp_path: Path) -> None:
    document = valid_document()
    document["sources"] = [
        {
            "id": "wiki-en-20260918-130233",
            "kind": "wiki",
            "title": "Infinity Wiki snapshot (English)",
            "version": "20260918-130233",
            "acquiredAt": "2026-09-18T13:02:33+02:00",
            "localPath": "data/wiki/WIKI-en 20260918-130233.zip",
            "sha256": "a" * 64,
            "language": "en",
            "documentCount": 812,
            "url": "https://infinitythewiki.com/",
            "authority": "secondary",
        }
    ]
    document["vocabularySources"] = {"skillTypes": [], "labels": []}
    document["records"][0]["citations"] = [
        {
            "sourceId": "wiki-en-20260918-130233",
            "member": "Example",
            "heading": "Example",
        }
    ]
    path = tmp_path / "wiki.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_curated_document(path)["sources"][0]["language"] == "en"


def test_load_curated_document_accepts_url_backed_wiki_citation(tmp_path: Path) -> None:
    document = valid_document()
    document["sources"] = [
        {
            "id": "wiki-example-oldid-1",
            "kind": "wiki",
            "title": "Infinity Wiki — Example revision 1",
            "version": "oldid 1",
            "retrievedDate": "2026-09-18",
            "url": "https://infinitythewiki.com/index.php?title=Example&oldid=1",
            "authority": "secondary",
        }
    ]
    document["vocabularySources"] = {"skillTypes": [], "labels": []}
    document["records"][0]["citations"] = [
        {"sourceId": "wiki-example-oldid-1", "heading": "Example"}
    ]
    path = tmp_path / "wiki-url.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_curated_document(path)["sources"][0]["retrievedDate"] == "2026-09-18"


def test_load_curated_document_rejects_older_versions(tmp_path: Path) -> None:
    document = valid_document()
    for version in (1, 2, 3, 4, 5):
        document["formatVersion"] = version
        path = tmp_path / f"v{version}.json"
        path.write_text(json.dumps(document), encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported curated format version"):
            load_curated_document(path)


def test_load_curated_document_rejects_non_json_reference_file(tmp_path: Path) -> None:
    path = tmp_path / "rules.pdf"
    path.write_bytes(b"not an application input")

    with pytest.raises(ValueError, match="must be a .json file"):
        load_curated_document(path)


def test_curated_directory_ignores_example_template(tmp_path: Path) -> None:
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    (curated_dir / "example.json").write_text('{"not": "a collection"}', encoding="utf-8")
    collection_path = curated_dir / "rules.json"
    collection_path.write_text(json.dumps(valid_document()), encoding="utf-8")

    assert discover_curated_documents(curated_dir) == [collection_path]
    assert load_curated_directory(curated_dir)[0][0] == collection_path


def test_curated_example_tracks_current_format_version() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "example.json"
    document = json.loads(path.read_text(encoding="utf-8"))

    assert document["formatVersion"] == CURATED_FORMAT_VERSION


def test_checked_in_n5_collection_is_valid() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"

    document = load_curated_document(path)

    assert document["collection"]["id"] == "n5-core-v5.3"
    sources = {source["id"]: source for source in document["sources"]}
    assert sources["n5-core-v5.3-pdf"]["url"] == (
        "https://experience.corvusbelli.com/en/infinity/resources"
    )
    wiki_source = sources["wiki-en-20260918-130233"]
    assert wiki_source["localPath"] == "data/wiki/WIKI-en 20260918-130233.zip"
    assert wiki_source["sha256"] == (
        "aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a"
    )
    assert wiki_source["documentCount"] == 812
    assert document["vocabularySources"]["skillTypes"][0]["member"] == (
        "Skills_and_Equipment_Module"
    )
    assert document["vocabularySources"]["labels"][0]["member"] == "Labels"
    assert "page" not in document["vocabularySources"]["skillTypes"][0]
    assert "page" not in document["vocabularySources"]["labels"][0]
    assert [skill_type["id"] for skill_type in document["skillTypes"]] == [
        "automatic",
        "deployment-skill",
        "basic-short-skill",
        "short-skill",
        "long-skill",
        "aro",
    ]
    assert {label["id"] for label in document["labels"]} == {
        "airborne-deployment",
        "assignable-transmutation",
        "attack",
        "bs-attack",
        "cc-attack",
        "cc-special-skill",
        "comms-attack",
        "comms-equipment",
        "hackable",
        "hostile",
        "marker",
        "movement",
        "negative-feedback",
        "no-lof",
        "non-reloadable",
        "no-roll",
        "null",
        "obligatory",
        "optional",
        "private-information",
        "states-phase",
        "superior-deployment",
        "supportware",
        "faqs",
    }
    records = {record["id"]: record for record in document["records"]}
    assert records["state:camouflaged"]["kind"] == "state"
    assert records["state:camouflaged"]["labelIds"] == ["marker"]
    assert records["state:camouflaged"]["review"]["status"] == "reviewed"
    assert records["state:camouflaged"]["relations"] == [
        {"type": "enables-use-of", "recordId": "skill:surprise-attack"}
    ]
    assert records["skill:camouflage"]["kind"] == "skill"
    assert records["skill:camouflage"]["review"]["status"] == "reviewed"
    assert records["skill:camouflage"]["labelIds"] == ["optional"]
    assert records["skill:camouflage"]["facts"]["typeIds"] == ["automatic"]
    assert records["skill:camouflage"]["relations"] == [
        {"type": "enters-state", "recordId": "state:camouflaged"}
    ]
    assert records["skill:camouflage"]["armyLinks"] == [
        {"entity": "skill", "id": "camouflage"}
    ]
    assert records["skill:camouflage"]["variantSemantics"] == {
        "inheritance": "family"
    }
    assert records["skill:super-jump"]["variantSemantics"] == {
        "inheritance": "family",
        "occurrenceParameters": [
            {
                "source": "army-extra",
                "kind": "distance",
                "positiveSign": "omit",
            }
        ],
    }
    assert records["skill:discover"]["facts"]["typeIds"] == ["basic-short-skill", "aro"]
    assert records["skill:discover"]["relations"] == [
        {"type": "reveals-state", "recordId": "state:camouflaged"},
        {"type": "reveals-state", "recordId": "state:decoy"},
        {"type": "reveals-state", "recordId": "state:impersonation-2"},
        {"type": "reveals-state", "recordId": "state:holoecho"},
        {"type": "reveals-state", "recordId": "state:holomask"},
    ]
    assert records["trait:suppressive-fire"]["aliases"] == ["Suppressive Fire"]
    assert records["trait:bs-weapon-ph"]["aliases"] == ["Throwing Weapon"]
    assert records["trait:bs-weapon-wip"]["aliases"] == ["Technical Weapon"]
    assert records["trait:concealed"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "state:camouflaged"}
    ]
    assert records["trait:disposable-x"]["facts"]["sourceIdentity"]["prefixes"] == [
        "Disposable ("
    ]
    assert records["trait:disposable-x"]["relations"] == [
        {"type": "causes-state", "recordId": "state:unloaded"}
    ]
    assert records["state:unloaded"]["kind"] == "state"
    assert records["trait:zone-of-control-zc"]["name"] == "Zone of Control (ZoC)"
    assert records["trait:zone-of-control-zc"]["citations"][0]["sourceId"] == (
        "wiki-traits-oldid-4110"
    )
    assert records["weapon:armed-turret"]["armyLinks"] == [
        {"entity": "weapon", "id": "armed-turret"}
    ]
    assert records["weapon:armed-turret"]["facts"]["specialProfile"]["skills"] == [
        "Total Reaction"
    ]
    assert all(len(skill_type["labels"]) == 2 for skill_type in document["skillTypes"])
    assert all(
        set(skill_type["descriptions"]) == {"singular", "plural"}
        for skill_type in document["skillTypes"]
    )


def test_load_curated_document_rejects_invalid_trait_source_identity(tmp_path: Path) -> None:
    document = valid_document()
    document["records"] = [
        {
            "id": "trait:disposable-x",
            "kind": "trait",
            "name": "Disposable (X)",
            "summary": "Limited uses.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {"sourceIdentity": {"prefixes": "Disposable ("}},
            "citations": [{"sourceId": "n5-core-v5.3", "page": 170}],
            "composition": {"role": "definition"},
            "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
        }
    ]
    path = tmp_path / "trait.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="sourceIdentity.prefixes"):
        load_curated_document(path)


def test_skill_parameter_semantics_are_validated(tmp_path: Path) -> None:
    document = valid_document()
    record = next(record for record in document["records"] if record["kind"] == "skill")
    record["armyLinks"] = [{"entity": "skill", "id": "example"}]
    record["variantSemantics"] = {
        "inheritance": "family",
        "occurrenceParameters": [
            {
                "source": "army-extra",
                "kind": "distance",
                "positiveSign": "omit",
            }
        ],
    }
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    loaded = load_curated_document(path)
    assert loaded["records"][0]["variantSemantics"]["occurrenceParameters"] == [
        {
            "source": "army-extra",
            "kind": "distance",
            "positiveSign": "omit",
        }
    ]

    record["variantSemantics"]["occurrenceParameters"][0]["positiveSign"] = "sometimes"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="positiveSign"):
        load_curated_document(path)

def test_load_curated_document_rejects_invalid_weapon_special_profile(tmp_path: Path) -> None:
    document = valid_document()
    document["records"] = [
        {
            "id": "weapon:armed-turret",
            "kind": "weapon",
            "name": "Armed Turret",
            "summary": "A deployable weapon.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {
                "specialProfile": {
                    "stats": [["MOV", "--"]],
                    "equipment": ["360º Visor"],
                    "skills": ["Total Reaction"],
                    "ccWeapon": 7,
                }
            },
            "armyLinks": [{"entity": "weapon", "id": 226}],
            "variantSemantics": {"inheritance": "family"},
            "citations": [{"sourceId": "n5-core-v5.3", "page": 74}],
            "composition": {"role": "definition"},
            "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
        }
    ]
    path = tmp_path / "weapon.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="ccWeapon"):
        load_curated_document(path)


def test_declaration_category_requires_valid_order_and_catalog_links(
    tmp_path: Path,
) -> None:
    document = valid_document()
    document["records"].append(
        {
            "id": "declaration-category:automatic:p12",
            "kind": "declaration-category",
            "name": "Automatic",
            "summary": "The linked skill is declared as Automatic.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {"typeId": "automatic", "order": 10},
            "armyLinks": [{"entity": "skill", "id": 19}],
            "citations": [{"sourceId": "n5-core-v5.3", "page": 12}],
            "composition": {"role": "definition"},
            "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
        }
    )
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_curated_document(path)["records"][-1]["facts"] == {
        "typeId": "automatic",
        "order": 10,
    }

    document["records"][-1]["armyLinks"] = [{"entity": "equipment", "id": "medikit"}]
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)["records"][-1]["armyLinks"] == [
        {"entity": "equipment", "id": "medikit"}
    ]

    document["records"][-1]["armyLinks"] = [{"entity": "weapon", "id": 19}]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="must reference skills or equipment"):
        load_curated_document(path)

    document["records"][-1]["armyLinks"] = [{"entity": "skill", "id": 19}]
    document["records"][-1]["facts"]["typeId"] = "entire-order"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="facts.typeId.*skillTypes"):
        load_curated_document(path)

    del document["records"][-1]["facts"]["typeId"]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="must contain only 'typeId' and 'order'"):
        load_curated_document(path)

    document = valid_document()
    declaration = {
        "id": "declaration-category:automatic:p12",
        "kind": "declaration-category",
        "name": "Automatic",
        "summary": "The linked skill is declared as Automatic.",
        "scope": {"game": "N5", "seasons": ["current"]},
        "facts": {"typeId": "automatic", "order": 10},
        "armyLinks": [{"entity": "skill", "id": 19}],
        "citations": [
            {"sourceId": "n5-core-v5.3", "page": 12},
            {"sourceId": "n5-core-v5.3", "page": 13},
        ],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
    }
    document["records"].append(declaration)
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="requires exactly one citation"):
        load_curated_document(path)


def test_army_links_accept_numeric_ids_and_catalog_slugs(tmp_path: Path) -> None:
    document = valid_document()
    record = document["records"][0]
    record["armyLinks"] = [
        {"entity": "skill", "id": 29},
        {"entity": "skill", "id": "camouflage"},
    ]
    record["variantSemantics"] = {"inheritance": "family"}
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_curated_document(path)["records"][0]["armyLinks"] == record["armyLinks"]

    record["armyLinks"] = [{"entity": "skill", "id": "29"}]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON integers"):
        load_curated_document(path)

    record["armyLinks"] = [{"entity": "state", "id": "camouflaged"}]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="string 'id' references are not supported"):
        load_curated_document(path)

    record["armyLinks"] = [{"entity": "skill", "id": "Camouflage"}]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="lowercase ASCII slug"):
        load_curated_document(path)


def test_skill_records_allow_no_rules_labels(tmp_path: Path) -> None:
    document = valid_document()
    document["records"][0]["labelIds"] = []
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_curated_document(path)["records"][0]["labelIds"] == []


def test_peripheral_type_facts_validate_controller_eligibility(tmp_path: Path) -> None:
    document = valid_document()
    document["records"].extend(
        [
            {
                "id": "skill:doctor",
                "kind": "skill",
                "name": "Doctor",
                "summary": "Doctor skill.",
                "scope": {"game": "N5", "seasons": ["current"]},
                "facts": {"typeIds": ["automatic"]},
                "labelIds": [],
                "relations": [
                    {
                        "type": "controller-eligible-for",
                        "recordId": "rule:peripheral-type:servant",
                    }
                ],
                "citations": [{"sourceId": "n5-core-v5.3", "page": 90}],
                "composition": {"role": "definition"},
                "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            },
            {
                "id": "skill:engineer",
                "kind": "skill",
                "name": "Engineer",
                "summary": "Engineer skill.",
                "scope": {"game": "N5", "seasons": ["current"]},
                "facts": {"typeIds": ["automatic"]},
                "labelIds": [],
                "relations": [
                    {
                        "type": "controller-eligible-for",
                        "recordId": "rule:peripheral-type:servant",
                    }
                ],
                "citations": [{"sourceId": "n5-core-v5.3", "page": 91}],
                "composition": {"role": "definition"},
                "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            },
            {
                "id": "skill:peripheral",
                "kind": "skill",
                "name": "Peripheral",
                "summary": "Peripheral skill.",
                "scope": {"game": "N5", "seasons": ["current"]},
                "facts": {"typeIds": ["automatic"]},
                "labelIds": [],
                "relations": [
                    {
                        "type": "has-subtype",
                        "recordId": "rule:peripheral-type:servant",
                    }
                ],
                "citations": [{"sourceId": "n5-core-v5.3", "page": 106}],
                "composition": {"role": "definition"},
                "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            },
            {
                "id": "rule:peripheral-type:servant",
                "kind": "rule",
                "name": "Peripheral (Servant)",
                "summary": "Servant type.",
                "scope": {"game": "N5", "seasons": ["current"]},
                "facts": {
                    "category": "peripheral-type",
                    "controllerEligibility": {
                        "anyOf": [
                            {"hasSkill": "skill:doctor"},
                            {"hasSkill": "skill:engineer"},
                        ]
                    },
                    "maxPerController": 2,
                    "operatingDistance": "unlimited",
                },
                "citations": [{"sourceId": "n5-core-v5.3", "page": 106}],
                "composition": {"role": "definition"},
                "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            },
        ]
    )
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    loaded = load_curated_document(path)
    servant = next(
        record for record in loaded["records"] if record["id"] == "rule:peripheral-type:servant"
    )
    assert servant["facts"]["maxPerController"] == 2

    source_servant = next(
        record for record in document["records"]
        if record["id"] == "rule:peripheral-type:servant"
    )
    source_servant["facts"]["controllerEligibility"] = {"status": "unknown"}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="must be 'not-stated'"):
        load_curated_document(path)


def test_peripheral_type_rejects_unknown_controller_skill(tmp_path: Path) -> None:
    document = valid_document()
    document["records"].extend(
        [
            {
                "id": "skill:peripheral",
                "kind": "skill",
                "name": "Peripheral",
                "summary": "Peripheral skill.",
                "scope": {"game": "N5", "seasons": ["current"]},
                "facts": {"typeIds": ["automatic"]},
                "labelIds": [],
                "citations": [{"sourceId": "n5-core-v5.3", "page": 106}],
                "composition": {"role": "definition"},
                "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            },
            {
                "id": "rule:peripheral-type:cyberplug",
                "kind": "rule",
                "name": "Peripheral (Cyberplug)",
                "summary": "Cyberplug type.",
                "scope": {"game": "N5", "seasons": ["current"]},
                "facts": {
                    "category": "peripheral-type",
                    "controllerEligibility": {"hasSkill": "skill:missing"},
                    "profileModes": ["connected", "autonomous"],
                },
                "citations": [{"sourceId": "n5-core-v5.3", "page": 106}],
                "composition": {"role": "definition"},
                "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            },
        ]
    )
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown skill 'skill:missing'"):
        load_curated_document(path)


def test_checked_in_n5_collection_has_peripheral_rules_foundation() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:doctor"]["facts"]["typeIds"] == ["short-skill"]
    assert records["skill:engineer"]["facts"]["typeIds"] == ["short-skill"]
    assert records["skill:cyberplug"]["facts"]["typeIds"] == ["automatic"]
    assert records["skill:peripheral"]["facts"]["typeIds"] == ["automatic"]
    assert records["skill:doctor"]["armyLinks"] == [{"entity": "skill", "id": "doctor"}]

    peripheral_types = {
        record_id: record
        for record_id, record in records.items()
        if record.get("facts", {}).get("category") == "peripheral-type"
    }
    assert set(peripheral_types) == {
        "rule:peripheral-type:servant",
        "rule:peripheral-type:synchronized",
        "rule:peripheral-type:control",
        "rule:peripheral-type:ancillary",
        "rule:peripheral-type:cyberplug",
    }
    assert peripheral_types["rule:peripheral-type:servant"]["facts"][
        "controllerEligibility"
    ] == {
        "anyOf": [
            {"hasSkill": "skill:doctor"},
            {"hasSkill": "skill:engineer"},
        ]
    }
    assert peripheral_types["rule:peripheral-type:cyberplug"]["facts"]["profileModes"] == [
        "connected",
        "autonomous",
    ]
    assert {
        relation["recordId"]
        for relation in records["skill:peripheral"]["relations"]
        if relation["type"] == "has-subtype"
    } == set(peripheral_types)
    assert {
        (relation["type"], relation["recordId"])
        for relation in records["skill:doctor"]["relations"]
    } >= {
        ("controller-eligible-for", "rule:peripheral-type:servant"),
    }


def test_checked_in_n5_collection_keeps_common_skill_labels_source_faithful() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_labels = {
        "skill:alert": ["optional", "no-roll"],
        "skill:bs-attack": ["attack"],
        "skill:cautious-movement": ["movement", "no-roll"],
        "skill:cc-attack": ["attack"],
        "skill:climb": ["movement", "no-lof", "no-roll"],
        "skill:discover": [],
        "skill:dodge": ["movement"],
        "skill:idle": ["no-roll"],
        "skill:intuitive-attack": ["bs-attack"],
        "skill:jump": ["movement", "no-lof", "no-roll"],
        "skill:move": ["movement", "no-lof", "no-roll"],
        "skill:look-out": ["no-roll"],
        "skill:place-deployable": ["attack"],
        "skill:reload": ["attack"],
        "skill:request-speedball": ["optional"],
        "skill:reset": ["no-lof"],
        "skill:speculative-attack": ["bs-attack"],
        "skill:suppressive-fire": ["attack"],
    }

    assert {
        record_id: records[record_id]["labelIds"] for record_id in expected_labels
    } == expected_labels


def test_checked_in_n5_collection_links_reviewed_trait_skill_interactions() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected = {
        "trait:bs-weapon-ph": {("modifies-rolls-for", "skill:bs-attack")},
        "trait:bs-weapon-wip": {("modifies-rolls-for", "skill:bs-attack")},
        "trait:cc": {("enables-use-of", "skill:cc-attack")},
        "trait:non-reloadable": {("restricts-use-of", "skill:reload")},
    }

    for trait_id, relations in expected.items():
        assert {
            (relation["type"], relation["recordId"])
            for relation in records[trait_id]["relations"]
        } == relations


def test_checked_in_n5_collection_links_armed_turret_rule_dependencies() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert {
        (relation["type"], relation["recordId"])
        for relation in records["weapon:armed-turret"]["relations"]
    } == {
        ("uses-effects-of", "trait:disposable-x"),
        ("uses-effects-of", "trait:deployable"),
        ("uses-effects-of", "trait:non-reloadable"),
        ("uses-effects-of", "trait:perimeter"),
        ("uses-effects-of", "equipment:360o-visor"),
        ("uses-effects-of", "skill:total-reaction"),
        ("enables-use-of", "skill:bs-attack"),
        ("enables-use-of", "skill:cc-attack"),
    }


def test_checked_in_n5_collection_links_weapon_traits_to_required_common_skills() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_targets = {
        "trait:intuitive-attack": "skill:intuitive-attack",
        "trait:speculative-attack": "skill:speculative-attack",
        "trait:suppressive-fire": "skill:suppressive-fire",
    }

    for trait_id, skill_id in expected_targets.items():
        assert {
            (relation["type"], relation["recordId"])
            for relation in records[trait_id]["relations"]
        } == {("enables-use-of", skill_id)}


def test_checked_in_n5_collection_links_skill_roll_interactions() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:martial-arts"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:cc-attack"}
    ]
    assert records["skill:marksmanship"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:bs-attack"}
    ]
    assert {
        (relation["type"], relation["recordId"])
        for relation in records["skill:sixth-sense"]["relations"]
    } == {
        ("negates-effects-of", "skill:stealth"),
        ("modifies-rolls-for", "skill:dodge"),
        ("modifies-rolls-for", "skill:reset"),
    }


def test_checked_in_n5_collection_links_common_skill_interactions() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:look-out"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:dodge"}
    ]
    assert records["skill:speculative-attack"]["relations"] == [
        {"type": "ignores-modifiers-from", "recordId": "skill:mimetism"}
    ]


def test_checked_in_n5_collection_links_place_deployable_prerequisites() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_sources = (
        "trait:deployable",
        "rule:peripheral-type:ancillary",
    )
    for source_id in expected_sources:
        assert {
            (relation["type"], relation["recordId"])
            for relation in records[source_id]["relations"]
        } == {("enables-use-of", "skill:place-deployable")}


def test_checked_in_n5_collection_keeps_expanded_special_skill_labels_source_faithful() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_labels = {
        "skill:combat-instinct": ["optional"],
        "skill:cyberplug": ["obligatory"],
        "skill:doctor": ["optional"],
        "skill:engineer": ["optional"],
        "skill:forward-deployment": ["superior-deployment", "optional"],
        "skill:limited-cover": ["obligatory"],
        "skill:marksmanship": ["obligatory"],
        "skill:martial-arts": ["cc-special-skill", "optional"],
        "skill:mimetism": ["negative-feedback", "obligatory"],
        "skill:natural-born-warrior": ["cc-special-skill"],
        "skill:no-cover": ["obligatory"],
        "skill:peripheral": ["obligatory"],
        "skill:sixth-sense": ["optional"],
        "skill:stealth": ["optional"],
        "skill:strategos": ["optional"],
        "skill:super-jump": ["movement", "optional"],
    }

    assert {
        record_id: records[record_id]["labelIds"] for record_id in expected_labels
    } == expected_labels

    martial_arts = records["skill:martial-arts"]["facts"]
    assert "Silhouette contact" in martial_arts["requirements"][0]
    assert "declare CC Attack" in martial_arts["requirements"][0]

    strategos = records["skill:strategos"]["facts"]
    assert strategos["requirements"] == ["The user must be the army's Lieutenant."]
    assert "Order Count" in strategos["effects"][0]

    super_jump = records["skill:super-jump"]["facts"]
    assert "Basic Short Skill" in super_jump["effects"][0]
    assert "plus 4 inches" in super_jump["effects"][1]



def test_checked_in_n5_collection_models_combat_reaction_skill_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_types = {
        "skill:berserk": ["long-skill"],
        "skill:guard": ["automatic"],
        "skill:neurocinetics": ["automatic"],
        "skill:total-reaction": ["automatic"],
        "skill:triangulated-fire": ["long-skill"],
    }
    assert {
        record_id: records[record_id]["facts"]["typeIds"]
        for record_id in expected_types
    } == expected_types

    assert records["skill:berserk"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:move"},
        {"type": "uses-effects-of", "recordId": "skill:cc-attack"},
    ]
    assert records["skill:guard"]["relations"] == [
        {"type": "enables-use-of", "recordId": "skill:cc-attack"}
    ]
    assert records["skill:neurocinetics"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:bs-attack"}
    ]
    assert records["skill:total-reaction"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:bs-attack"}
    ]
    assert records["skill:triangulated-fire"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:bs-attack"},
        {"type": "ignores-modifiers-from", "recordId": "skill:mimetism"},
    ]
    assert records["equipment:tinbot-neurocinetics"]["relations"] == [
        {"type": "variant-of", "recordId": "equipment:tinbot"},
        {"type": "uses-effects-of", "recordId": "skill:neurocinetics"},
    ]


def test_checked_in_n5_collection_models_mobility_environment_skill_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_types = {
        "skill:aerial": ["automatic"],
        "skill:climbing-plus": ["automatic"],
        "skill:terrain": ["automatic"],
        "skill:warhorse": ["automatic"],
    }
    assert {
        record_id: records[record_id]["facts"]["typeIds"]
        for record_id in expected_types
    } == expected_types

    assert records["skill:aerial"]["relations"] == [
        {"type": "restricts-use-of", "recordId": "skill:cautious-movement"},
        {"type": "restricts-use-of", "recordId": "skill:guard"},
        {"type": "negates-effects-of", "recordId": "trait:boost"},
    ]
    assert records["skill:climbing-plus"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:climb"},
        {"type": "applies-effects-to", "recordId": "skill:move"},
        {"type": "applies-effects-to", "recordId": "skill:dodge"},
    ]
    assert "relations" not in records["skill:terrain"]
    assert "relations" not in records["skill:warhorse"]


def test_checked_in_n5_collection_models_deployment_skill_and_state_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_types = {
        "skill:combat-jump": ["long-skill"],
        "skill:decoy": ["deployment-skill"],
        "skill:impersonation": ["deployment-skill"],
        "skill:infiltration": ["deployment-skill"],
        "skill:minelayer": ["deployment-skill"],
        "skill:parachutist": ["long-skill"],
        "skill:sapper": ["deployment-skill", "long-skill"],
        "skill:strategic-deployment": ["deployment-skill"],
    }
    assert {
        record_id: records[record_id]["facts"]["typeIds"]
        for record_id in expected_types
    } == expected_types

    assert records["skill:decoy"]["relations"] == [
        {"type": "enters-state", "recordId": "state:decoy"}
    ]
    assert records["skill:impersonation"]["relations"] == [
        {"type": "enters-state", "recordId": "state:impersonation-1"},
        {"type": "enters-state", "recordId": "state:impersonation-2"},
    ]
    assert records["skill:sapper"]["relations"] == [
        {"type": "enters-state", "recordId": "state:foxhole"}
    ]
    assert records["skill:strategic-deployment"]["relations"] == [
        {"type": "enables-use-of", "recordId": "skill:forward-deployment"}
    ]
    assert records["skill:request-speedball"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:combat-jump"}
    ]

    assert records["state:decoy"]["labelIds"] == ["marker"]
    for state_id in {"state:impersonation-1", "state:impersonation-2"}:
        assert records[state_id]["labelIds"] == ["marker"]
        assert records[state_id]["relations"] == [
            {"type": "enables-use-of", "recordId": "skill:surprise-attack"}
        ]
    assert records["state:foxhole"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:mimetism"},
        {"type": "uses-effects-of", "recordId": "skill:courage"},
    ]


def test_checked_in_n5_collection_models_morale_behavior_skill_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_labels = {
        "skill:courage": ["optional"],
        "skill:frenzy": ["obligatory", "states-phase"],
        "skill:impetuous": ["obligatory"],
        "skill:religious-troop": ["obligatory"],
    }
    assert {
        record_id: records[record_id]["labelIds"]
        for record_id in expected_labels
    } == expected_labels
    assert all(
        records[record_id]["facts"]["typeIds"] == ["automatic"]
        for record_id in expected_labels
    )
    assert records["skill:frenzy"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:impetuous"},
        {"type": "uses-effects-of", "recordId": "skill:limited-cover"},
        {"type": "cancels-state", "recordId": "state:camouflaged"},
        {"type": "cancels-state", "recordId": "state:decoy"},
        {"type": "cancels-state", "recordId": "state:impersonation-1"},
        {"type": "cancels-state", "recordId": "state:impersonation-2"},
        {"type": "cancels-state", "recordId": "state:holoecho"},
    ]
    assert "relations" not in records["skill:courage"]
    assert records["skill:impetuous"]["relations"] == [
        {"type": "cancels-state", "recordId": "state:prone"},
        {"type": "cancels-state", "recordId": "state:holoecho"},
        {"type": "cancels-state", "recordId": "state:holomask"},
    ]
    assert "relations" not in records["skill:religious-troop"]


def test_checked_in_n5_collection_keeps_sensor_category_source_faithful() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:sensor"]["facts"]["typeIds"] == ["short-skill"]
    sensor_declarations = [
        record
        for record in document["records"]
        if record["kind"] == "declaration-category"
        and any(
            link == {"entity": "skill", "id": "sensor"}
            for link in record.get("armyLinks", [])
        )
    ]
    assert [
        (record["facts"]["typeId"], record["facts"]["order"])
        for record in sensor_declarations
    ] == [("short-skill", 40)]


def test_checked_in_n5_collection_keeps_new_common_skill_facts_source_faithful() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    look_out = records["skill:look-out"]["facts"]
    assert "LoF" in look_out["requirements"][0]
    assert "Dodge (PH-3)" in look_out["effects"][0]

    speedball = records["skill:request-speedball"]["facts"]
    assert speedball["requirements"] == ["The player must have two Speedball Tokens."]
    assert "two 55 mm Speedball Tokens" in speedball["effects"][0]
    assert "PH 15" in speedball["effects"][0]

    reload = records["skill:reload"]["facts"]
    assert "must both be in non-Null States" in reload["requirements"][0]
    assert any("Non-Reloadable" in restriction for restriction in reload["restrictions"])


def test_checked_in_n5_collection_models_cover_precedence() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:limited-cover"]["armyLinks"] == [
        {"entity": "skill", "id": "limited-cover"}
    ]
    assert records["skill:no-cover"]["relations"] == [
        {"type": "overrides-effects-of", "recordId": "skill:limited-cover"}
    ]


def test_checked_in_n5_collection_models_state_recovery_relations() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["state:immobilized-a"]["labelIds"] == []
    assert {
        relation["recordId"]
        for relation in records["skill:doctor"]["relations"]
        if relation["type"] == "cancels-state"
    } == {
        "state:unconscious",
        "state:stunned",
    }
    assert {
        relation["recordId"]
        for relation in records["skill:engineer"]["relations"]
        if relation["type"] == "cancels-state"
    } == {
        "state:disconnected",
        "state:immobilized-a",
        "state:immobilized-b",
        "state:isolated",
        "state:stunned",
        "state:targeted",
        "state:unconscious",
    }

def test_checked_in_n5_collection_models_targeted_interaction_hub() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:forward-observer"]["relations"] == [
        {"type": "causes-state", "recordId": "state:targeted"}
    ]
    assert {
        relation["recordId"]
        for relation in records["skill:reset"]["relations"]
        if relation["type"] == "cancels-state"
    } == {"state:targeted", "state:immobilized-b", "state:isolated"}
    assert {
        (relation["type"], relation["recordId"])
        for relation in records["state:targeted"]["relations"]
    } == {
        ("modifies-rolls-for", "skill:bs-attack"),
        ("modifies-rolls-for", "skill:discover"),
        ("modifies-rolls-for", "skill:reset"),
        ("restricts-use-of", "skill:cautious-movement"),
        ("restricts-use-of", "skill:stealth"),
    }


def test_checked_in_n5_collection_models_mimetism_affected_rolls() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:mimetism"]["relations"] == [
        {"type": "imposes-modifiers-on", "recordId": "skill:bs-attack"},
        {"type": "imposes-modifiers-on", "recordId": "skill:discover"},
    ]


def test_checked_in_n5_collection_models_silent_dodge_modifier() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["trait:silent-x"]["relations"] == [
        {"type": "imposes-modifiers-on", "recordId": "skill:dodge"}
    ]


def test_checked_in_n5_collection_models_stealth_cautious_movement_exception() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:stealth"]["relations"] == [
        {"type": "enables-use-of", "recordId": "skill:cautious-movement"}
    ]


def test_checked_in_n5_collection_models_state_self_recovery_rolls() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:dodge"]["relations"] == [
        {"type": "cancels-state", "recordId": "state:immobilized-a"},
        {"type": "cancels-state", "recordId": "state:engaged"},
    ]
    assert (
        "modifies-rolls-for",
        "skill:dodge",
    ) in {
        (relation["type"], relation["recordId"])
        for relation in records["state:immobilized-a"]["relations"]
    }
    assert {
        (relation["type"], relation["recordId"])
        for relation in records["state:immobilized-b"]["relations"]
    } >= {("modifies-rolls-for", "skill:reset")}
    assert {
        (relation["type"], relation["recordId"])
        for relation in records["state:isolated"]["relations"]
    } >= {("modifies-rolls-for", "skill:reset")}


def test_checked_in_n5_collection_models_first_full_catalog_equipment_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["equipment:360o-visor"].get("relations", []) == []
    assert records["equipment:nanoscreen"]["relations"] == [
        {"type": "imposes-modifiers-on", "recordId": "skill:bs-attack"}
    ]
    assert records["equipment:x-visor"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:bs-attack"},
        {"type": "modifies-rolls-for", "recordId": "skill:discover"},
        {"type": "modifies-rolls-for", "recordId": "skill:suppressive-fire"},
    ]


def test_checked_in_n5_collection_models_second_full_catalog_equipment_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["equipment:biometric-visor"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:discover"},
        {"type": "ignores-modifiers-from", "recordId": "skill:surprise-attack"},
        {"type": "cancels-state", "recordId": "state:impersonation-1"},
    ]
    assert records["equipment:dazer"].get("relations", []) == []
    assert records["equipment:deactivator"]["relations"] == [
        {"type": "ignores-modifiers-from", "recordId": "skill:mimetism"}
    ]
    assert records["equipment:deployable-cover"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:bs-attack"}
    ]
    assert records["equipment:repeater"].get("relations", []) == []
    for record_id in {"equipment:deployable-repeater", "equipment:fastpanda"}:
        assert records[record_id]["relations"] == [
            {"type": "uses-effects-of", "recordId": "equipment:repeater"}
        ]


def test_checked_in_n5_collection_models_remaining_catalog_equipment_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_equipment = {
        "equipment:ai-motorcycle",
        "equipment:bangbomb",
        "equipment:ecm",
        "equipment:escape-system",
        "equipment:evo-hacking-device",
        "equipment:gizmokit",
        "equipment:hacking-device",
        "equipment:hacking-device-plus",
        "equipment:holomask",
        "equipment:holoprojector",
        "equipment:killer-hacking-device",
        "equipment:medikit",
        "equipment:motorcycle",
        "equipment:symbiomate",
    }
    assert expected_equipment <= records.keys()
    assert records["equipment:bangbomb"]["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:dodge"}
    ]
    assert records["equipment:gizmokit"]["relations"] == [
        {"type": "cancels-state", "recordId": "state:unconscious"}
    ]
    assert records["equipment:medikit"]["relations"] == [
        {"type": "cancels-state", "recordId": "state:unconscious"},
        {"type": "causes-state", "recordId": "state:dead"},
    ]
    assert records["equipment:motorcycle"]["relations"] == [
        {"type": "restricts-use-of", "recordId": "skill:climb"},
        {"type": "restricts-use-of", "recordId": "skill:jump"},
        {"type": "restricts-use-of", "recordId": "skill:cautious-movement"},
    ]
    assert records["equipment:ai-motorcycle"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "equipment:motorcycle"},
        {"type": "uses-effects-of", "recordId": "rule:peripheral-type:synchronized"},
    ]
    assert ("uses-effects-of", "equipment:albedo") in {
        (relation["type"], relation["recordId"])
        for relation in records["equipment:tinbot-albedo"]["relations"]
    }
    assert ("modifies-rolls-for", "skill:discover") in {
        (relation["type"], relation["recordId"])
        for relation in records["equipment:tinbot-discover"]["relations"]
    }
    assert ("uses-effects-of", "equipment:ecm") in {
        (relation["type"], relation["recordId"])
        for relation in records["equipment:tinbot-ecm-guided"]["relations"]
    }
    assert ("uses-effects-of", "equipment:repeater") in {
        (relation["type"], relation["recordId"])
        for relation in records["equipment:tinbot-repeater"]["relations"]
    }
