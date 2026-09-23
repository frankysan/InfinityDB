import json
from pathlib import Path

import pytest

from infinity_db.curated import (
    discover_curated_documents,
    load_curated_directory,
    load_curated_document,
)


def valid_document() -> dict:
    return {
        "format": "InfinityDB curated reference",
        "formatVersion": 7,
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
                "facts": {"typeId": "automatic"},
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
    assert records["skill:camouflage"]["kind"] == "skill"
    assert records["skill:camouflage"]["labelIds"] == ["optional"]
    assert records["skill:camouflage"]["facts"]["typeId"] == "automatic"
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
    assert records["skill:discover"]["facts"]["typeId"] == "basic-short-skill"
    assert records["skill:discover"]["relations"] == [
        {"type": "reveals-state", "recordId": "state:camouflaged"}
    ]
    assert records["trait:suppressive-fire"]["aliases"] == ["Suppressive Fire"]
    assert records["trait:disposable-x"]["facts"]["sourceIdentity"]["prefixes"] == [
        "Disposable ("
    ]
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
                "facts": {"typeId": "automatic"},
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
                "facts": {"typeId": "automatic"},
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
                "facts": {"typeId": "automatic"},
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
                "facts": {"typeId": "automatic"},
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

    assert records["skill:doctor"]["facts"]["typeId"] == "short-skill"
    assert records["skill:engineer"]["facts"]["typeId"] == "short-skill"
    assert records["skill:cyberplug"]["facts"]["typeId"] == "automatic"
    assert records["skill:peripheral"]["facts"]["typeId"] == "automatic"
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
    assert records["skill:doctor"]["relations"] == [
        {
            "type": "controller-eligible-for",
            "recordId": "rule:peripheral-type:servant",
        }
    ]
