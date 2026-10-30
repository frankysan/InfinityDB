import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import (
    CURATED_FORMAT_VERSION,
    discover_curated_documents,
    load_curated_directory,
    load_curated_document,
)


@pytest.mark.parametrize("digest", ("a" * 64, "A" * 64, None, "", "g" * 64, "a" * 63, 123))
def test_pdf_source_optional_fingerprint_is_validated(tmp_path: Path, digest: object) -> None:
    document = valid_document()
    source = next(source for source in document["sources"] if source["kind"] == "pdf")
    source["sha256"] = digest
    path = tmp_path / "curated.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    if digest in ("a" * 64, "A" * 64):
        assert load_curated_document(path)["sources"][0]["sha256"] == digest
    else:
        with pytest.raises(ValueError, match="sha256"):
            load_curated_document(path)


def valid_document() -> dict:
    return {
        "format": "InfinityDB curated reference",
        "formatVersion": CURATED_FORMAT_VERSION,
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


@pytest.mark.parametrize(
    ("type_ids", "valid"),
    [
        (["short-skill"], True),
        ([], False),
        (["unknown"], False),
        (["short-skill", "short-skill"], False),
        (None, False),
    ],
)
def test_equipment_declaration_types_are_validated_only_when_authored(
    tmp_path: Path, type_ids: object, valid: bool,
) -> None:
    """An Equipment action may use the shared Skill Type vocabulary."""
    document = valid_document()
    document["skillTypes"][0]["id"] = "short-skill"
    record = document["records"][0]
    record["id"] = "equipment:example"
    record["kind"] = "equipment"
    record["facts"] = {"typeIds": type_ids}
    path = tmp_path / "equipment.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    if valid:
        assert load_curated_document(path)["records"][0]["facts"]["typeIds"] == type_ids
    else:
        with pytest.raises(ValueError, match="equipment 'facts.typeIds'"):
            load_curated_document(path)

    # Passive Equipment requires no declaration type and must not gain one
    # as a default; this is distinct from authoring an invalid null type.
    record["facts"] = {}
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)["records"][0]["facts"] == {}


def test_equipment_declaration_rejects_singular_field_and_supplement(
    tmp_path: Path,
) -> None:
    document = valid_document()
    record = document["records"][0]
    record["id"] = "equipment:example"
    record["kind"] = "equipment"
    record["facts"] = {"typeId": "automatic"}
    path = tmp_path / "equipment.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="must use 'facts.typeIds'"):
        load_curated_document(path)

    record["composition"]["role"] = "supplement"
    record["facts"] = {"typeIds": ["automatic"]}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="supplements must not redefine"):
        load_curated_document(path)


def _faq_ruling_document() -> dict:
    """Synthetic dated FAQ data; no unverified ruling is authored for release."""
    document = valid_document()
    document["collection"].update(
        id="n5-faq-v0.1", domain="faq", effectiveFrom="2026-09-01"
    )
    document["sources"][0].update(
        id="n5-faq-v0.1-pdf", title="N5 FAQ", version="0.1",
        publishedDate="2026-09-01",
    )
    for source in document["vocabularySources"].values():
        source[0]["sourceId"] = "n5-faq-v0.1-pdf"
    document["records"] = [{
        "id": "faq-ruling:example-faq-answer",
        "kind": "faq-ruling",
        "name": "Example ruling",
        "summary": "A dated clarification, separate from canonical rule text.",
        "scope": {"game": "N5", "seasons": ["current"]},
        "composition": {"role": "definition"},
        "review": {"status": "draft", "reviewedOn": "2026-10-15"},
        "citations": [{"sourceId": "n5-faq-v0.1-pdf", "page": 3}],
        "facts": {
            "question": "Can the example action be attempted again?",
            "answer": "This answer is intentionally synthetic for validation.",
            "topicIds": ["skill:camouflage"],
            "applicability": [{"rulesRevision": "5.3", "effectiveFrom": "2026-09-01"}],
            "originalPublication": {
                "collectionId": "n5-faq-v0.1",
                "sourceId": "n5-faq-v0.1-pdf",
                "version": "0.1",
                "publishedDate": "2026-09-01",
                "page": 3,
            },
            "selectedCitation": {"sourceId": "n5-faq-v0.1-pdf", "page": 3},
            "selectionReason": "Explicit manual comparison for test fixture.",
            "conflictingCitations": [],
            "supersedes": [],
        },
    }]
    return document


def test_faq_ruling_contract_preserves_identity_scope_and_manual_source_choice(
    tmp_path: Path,
) -> None:
    document = _faq_ruling_document()
    ruling = document["records"][0]["facts"]
    ruling["applicability"].extend([
        {
            "rulesRevision": "5.3",
            "effectiveFrom": "2026-09-01",
            "season": {"id": "its-18", "revision": "2026.09.01"},
            "scenarioIds": ["scenario:double-bind"],
        },
    ])
    document["sources"].append({
        **document["sources"][0],
        "id": "n5-faq-v0.1-es-pdf",
        "title": "Spanish FAQ",
    })
    document["records"][0]["citations"].append({
        "sourceId": "n5-faq-v0.1-es-pdf", "page": 3,
    })
    ruling["conflictingCitations"] = [
        {"sourceId": "n5-faq-v0.1-es-pdf", "page": 3}
    ]
    path = tmp_path / "faq.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = load_curated_document(path)["records"][0]
    assert result["id"] == "faq-ruling:example-faq-answer"
    assert result["facts"]["applicability"][1]["season"]["id"] == "its-18"
    assert result["facts"]["selectedCitation"]["sourceId"] == "n5-faq-v0.1-pdf"
    assert result["facts"]["conflictingCitations"][0]["sourceId"] == "n5-faq-v0.1-es-pdf"


@pytest.mark.parametrize(
    ("path", "value", "problem"),
    [
        (("question",), "", "question"),
        (("answer",), " ", "answer"),
        (("topicIds",), [], "topicIds"),
        (("topicIds",), ["skill:camouflage", "skill:camouflage"], "duplicate"),
        (("topicIds",), ["not-a-reference"], "topicIds"),
        (("applicability",), [], "applicability"),
        (
            ("applicability",),
            [
                {"rulesRevision": "5.3", "effectiveFrom": "2026-09-01"},
                {"rulesRevision": "5.3", "effectiveFrom": "2026-09-02"},
            ],
            "duplicate",
        ),
        (
            ("applicability",),
            [
                {
                    "rulesRevision": "5.3",
                    "effectiveFrom": "2026-09-01",
                    "season": {"id": "its-18"},
                }
            ],
            "season",
        ),
        (
            ("applicability",),
            [{
                "rulesRevision": "5.3",
                "effectiveFrom": "2026-09-01",
                "scenarioIds": ["skill:camouflage"],
            }],
            "scenarioIds",
        ),
        (("applicability",), [{"rulesRevision": "5.3"}], "effectiveFrom"),
        (
            ("applicability",),
            [{
                "rulesRevision": "5.3", "effectiveFrom": "2026-10-01",
                "effectiveUntil": "2026-09-01",
            }],
            "effectiveUntil precedes effectiveFrom",
        ),
        (("topicIds",), ["faq-ruling:other"], "unsupported reference"),
        (("originalPublication", "version"), "0.2", "version/date mismatch"),
        (("originalPublication", "publishedDate"), "2026-02-31", "date"),
        (("originalPublication", "page"), 5, "not in the record citations"),
        (("selectedCitation",), {"sourceId": "n5-faq-v0.1-pdf", "page": 8}, "selectedCitation"),
        (("selectionReason",), "", "selectionReason"),
        (
            ("conflictingCitations",),
            [{"sourceId": "n5-faq-v0.1-pdf", "page": 3}],
            "duplicate or selected",
        ),
        (("supersedes",), ["faq-ruling:example-faq-answer"], "cannot supersede itself"),
        (("supersedes",), ["skill:camouflage"], "supersedes"),
        (("unreviewedField",), "unvalidated", "expected"),
    ],
)
def test_faq_ruling_contract_rejects_implicit_or_conflicting_facts(
    tmp_path: Path, path: tuple[str, ...], value: object, problem: str,
) -> None:
    document = _faq_ruling_document()
    target = document["records"][0]["facts"]
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    filepath = tmp_path / "faq.json"
    filepath.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match=problem):
        load_curated_document(filepath)


def test_faq_ruling_is_not_silently_attached_as_an_unscoped_supplement(
    tmp_path: Path,
) -> None:
    document = _faq_ruling_document()
    document["records"][0]["composition"]["role"] = "supplement"
    path = tmp_path / "faq.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="require a definition"):
        load_curated_document(path)


def test_load_curated_document_requires_provenance(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(valid_document()), encoding="utf-8")

    assert load_curated_document(path)["records"][0]["citations"][0]["page"] == 12


@pytest.mark.parametrize("notes", [[], [""], [None], "not a list"])
def test_curated_source_notes_reject_empty_or_invalid_entries(
    tmp_path: Path, notes: object,
) -> None:
    document = valid_document()
    document["records"][0]["facts"]["sourceNotes"] = notes
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="facts.sourceNotes"):
        load_curated_document(path)


@pytest.mark.parametrize("clarifications", [[], [""], [None], "not a list"])
def test_curated_clarifications_reject_empty_or_invalid_entries(
    tmp_path: Path, clarifications: object,
) -> None:
    document = valid_document()
    document["records"][0]["facts"]["clarifications"] = clarifications
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="facts.clarifications"):
        load_curated_document(path)


def test_curated_clarifications_accept_maintained_text(tmp_path: Path) -> None:
    document = valid_document()
    document["records"][0]["facts"]["clarifications"] = [
        "An explicit [[skill:example|example]] of the rule."
    ]
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)["records"][0]["facts"]["clarifications"] == [
        "An explicit [[skill:example|example]] of the rule."
    ]


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


def test_catalog_definition_requires_stable_army_link_id(tmp_path: Path) -> None:
    document = valid_document()
    record = document["records"][0]
    record["armyLinks"] = [{"entity": "skill", "name": "Example skill"}]
    record["variantSemantics"] = {"inheritance": "family"}
    path = tmp_path / "name-only-link.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="stable numeric source id or domain slug"):
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
            declaration("declaration-category:automatic:p12", "automatic", 10, 12),
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
    "related_categories",
    [[], ["Order Type"], ["order-type", "order-type"]],
)
def test_related_categories_require_unique_category_slugs(
    tmp_path: Path, related_categories: list[str]
) -> None:
    document = valid_document()
    document["records"][0]["facts"]["relatedCategories"] = related_categories
    path = tmp_path / "bad-related-categories.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="relatedCategories"):
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


def test_term_requires_scoped_embedded_vocabulary_facts(tmp_path: Path) -> None:
    document = valid_document()
    term = document["records"][0]
    term.update(
        id="term:marker",
        kind="term",
        name="Marker",
        facts={"scope": "game-element"},
    )
    term.pop("labelIds")
    path = tmp_path / "term.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_curated_document(path)["records"][0]["facts"] == {
        "scope": "game-element"
    }

    term["facts"] = {}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="term 'facts'.*scope"):
        load_curated_document(path)

    term["facts"] = {"scope": "Game Element"}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="facts.scope"):
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
    document["records"][0]["relations"] = [{"type": "maybe-related", "recordId": "state:example"}]
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
    assert (
        load_curated_document(path)["records"][0]["variantSemantics"]
        == (document["records"][0]["variantSemantics"])
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
    assert (
        load_curated_document(path)["records"][0]["variantSemantics"]
        == (record["variantSemantics"])
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
    assert (
        load_curated_document(path)["records"][0]["variantSemantics"]
        == (record["variantSemantics"])
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
            "id": "wiki-en-20260926-200832",
            "kind": "wiki",
            "title": "Infinity Wiki snapshot (English)",
            "version": "20260926-200832",
            "acquiredAt": "2026-09-26T20:08:32+02:00",
            "localPath": "data/wiki/WIKI-en 20260926-200832.zip",
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
            "sourceId": "wiki-en-20260926-200832",
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
    assert document["scenarioCollection"] == {
        "id": "n5-core",
        "title": "N5 Core Scenarios",
        "revision": "5.3",
        "members": [
            {"scenarioId": "scenario:annihilation"},
            {"scenarioId": "scenario:domination"},
            {"scenarioId": "scenario:supplies"},
            {"scenarioId": "scenario:firefight"},
        ],
    }
    sources = {source["id"]: source for source in document["sources"]}
    assert sources["n5-core-v5.3-pdf"]["url"] == (
        "https://experience.corvusbelli.com/en/infinity/resources"
    )
    wiki_source = sources["wiki-en-20260926-200832"]
    assert wiki_source["localPath"] == "data/wiki/WIKI-en 20260926-200832.zip"
    assert wiki_source["sha256"] == (
        "c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987"
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
    profile_help = records["rule:profile-help:troop-type"]
    assert profile_help["facts"] == {
        "category": "unit-profile-help",
        "key": "troop-type",
        "order": 40,
    }
    assert profile_help["citations"] == [
        {
            "sourceId": "n5-core-v5.3-pdf",
            "page": 8,
            "section": "Trooper Characteristics",
        }
    ]
    fto = records["term:fto"]
    assert fto["name"] == "FTO (Fireteam Option)"
    assert fto["aliases"] == ["FTO", "Fireteam Option"]
    assert fto["facts"] == {"scope": "fireteam-eligibility"}
    assert fto["citations"] == [
        {
            "sourceId": "wiki-fireteams-chart-oldid-4116",
            "heading": "Fireteams Chart",
        }
    ]
    assert records["state:camouflaged"]["kind"] == "state"
    assert records["state:camouflaged"]["labelIds"] == ["marker"]
    assert records["state:camouflaged"]["review"]["status"] == "reviewed"
    assert records["state:camouflaged"]["relations"] == [
        {"type": "enables-use-of", "recordId": "skill:surprise-attack"},
        {"type": "restricts-use-of", "recordId": "skill:place-deployable"},
    ]
    assert records["skill:camouflage"]["kind"] == "skill"
    assert records["skill:camouflage"]["review"]["status"] == "reviewed"
    assert records["skill:camouflage"]["labelIds"] == ["optional"]
    assert records["skill:camouflage"]["facts"]["typeIds"] == ["automatic"]
    assert records["skill:camouflage"]["relations"] == [
        {"type": "enters-state", "recordId": "state:camouflaged"}
    ]
    assert records["skill:camouflage"]["armyLinks"] == [{"entity": "skill", "id": "camouflage"}]
    assert records["skill:camouflage"]["variantSemantics"] == {"inheritance": "family"}
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
    assert records["trait:disposable-x"]["facts"]["sourceIdentity"]["prefixes"] == ["Disposable ("]
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
    assert records["weapon:armed-turret"]["facts"]["specialProfile"]["skills"] == ["Total Reaction"]
    turret_citations = records["weapon:armed-turret"]["citations"]
    assert turret_citations[:3] == [
        {"sourceId": "n5-core-v5.3-pdf", "page": 70, "section": "Armed Turret Profile"},
        {"sourceId": "n5-core-v5.3-pdf", "page": 186, "section": "Weapon Chart: E/Mitter"},
        {"sourceId": "n5-core-v5.3-es-pdf", "page": 195, "section": "Tabla de Armas: E/Mitter"},
    ]
    assert len(turret_citations) == 10
    assert "Unresolved source conflict" not in records["weapon:armed-turret"]["summary"]
    assert "Unresolved Silhouette conflict" in (
        records["weapon:armed-turret"]["facts"]["sourceNotes"][0]
    )
    assert "one Saving Roll" in (
        records["weapon:armed-turret"]["facts"]["sourceNotes"][1]
    )
    assert all(len(skill_type["labels"]) == 2 for skill_type in document["skillTypes"])
    assert all(
        set(skill_type["descriptions"]) == {"singular", "plural"}
        for skill_type in document["skillTypes"]
    )

    editorial_text = [
        description
        for skill_type in document["skillTypes"]
        for description in skill_type["descriptions"].values()
    ]
    editorial_text.extend(label["description"] for label in document["labels"])
    for record in document["records"]:
        editorial_text.append(record["summary"])
        facts = record.get("facts", {})
        for key in ("requirements", "effects", "restrictions"):
            editorial_text.extend(facts.get(key, []))
    assert not any(re.search(r"\btroopers?\b", text) for text in editorial_text)


def test_rea037_armed_turret_silhouette_conflict_is_source_scoped() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    turret = next(rec for rec in document["records"] if rec["id"] == "weapon:armed-turret")
    assert turret["facts"]["specialProfile"]["stats"][-1] == ["S", "2"]
    note = turret["facts"]["sourceNotes"][0]
    for expected in (
        "**Unresolved Silhouette conflict:**",
        "**S2**", "**S1**", "English N5.3 p. 70", "Spanish N5.3 p. 74",
        "English pp. 74 and 195", "Spanish p. 203",
        "25 mm high versus 40 mm", "without claiming it overrides",
    ):
        assert expected in note
    cited = {(ref["sourceId"], ref.get("page"), ref.get("member"))
             for ref in turret["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 18, None),
        ("n5-core-v5.3-pdf", 70, None),
        ("n5-core-v5.3-pdf", 74, None),
        ("n5-core-v5.3-pdf", 195, None),
        ("n5-core-v5.3-es-pdf", 74, None),
        ("n5-core-v5.3-es-pdf", 203, None),
        ("wiki-en-20260926-200832", None, "Armed_Turret"),
        ("wiki-es-20261009-211304", None, "es/Torreta_Artillada"),
    }


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


def test_numeric_mod_occurrence_parameter_schema_is_explicit_and_compatible(
    tmp_path: Path,
) -> None:
    document = valid_document()
    record = next(item for item in document["records"] if item["kind"] == "skill")
    record["armyLinks"] = [{"entity": "skill", "id": "example"}]
    numeric = {
        "source": "army-extra",
        "kind": "numeric-mod",
        "owner": "skill-holder",
        "target": "opponent",
        "appliesTo": ["bs-attack-requiring-lof", "discover"],
        "extraValues": [
            {"extraId": 6, "extraType": "TEXT", "rawValue": "-3", "modifier": -3},
            {"extraId": 7, "extraType": "TEXT", "rawValue": "-6", "modifier": -6},
        ],
    }
    distance = {"source": "army-extra", "kind": "distance", "positiveSign": "omit"}
    record["variantSemantics"] = {
        "inheritance": "family", "occurrenceParameters": [numeric, distance]
    }
    path = tmp_path / "numeric-mod.json"

    def check() -> None:
        path.write_text(json.dumps(document), encoding="utf-8")
        load_curated_document(path)

    check()
    for replacement, message in [
        ({"owner": "anyone"}, "owner"),
        ({"target": "both"}, "target"),
        ({"appliesTo": ["unknown"]}, "appliesTo"),
        ({"appliesTo": ["discover", "discover"]}, "appliesTo"),
        ({"target": "skill-holder"}, "target conflicts"),
        ({"positiveSign": "force"}, "require exactly"),
        ({"extraValues": []}, "extraValues"),
        ({"extraValues": [
            {"extraId": 6, "extraType": "DISTANCE", "rawValue": "-3", "modifier": -3}
        ]}, "extraType/rawValue"),
        ({"extraValues": [
            {"extraId": 6, "extraType": "TEXT", "rawValue": "-3", "modifier": 3}
        ]}, "extraType/rawValue"),
        ({"extraValues": [
            {"extraId": 6, "extraType": "TEXT", "rawValue": "-3", "modifier": -3},
            {"extraId": 6, "extraType": "TEXT", "rawValue": "-6", "modifier": -6},
        ]}, "duplicate/invalid extraId"),
    ]:
        candidate = deepcopy(numeric)
        candidate.update(replacement)
        record["variantSemantics"]["occurrenceParameters"][0] = candidate
        path.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_curated_document(path)

    record["variantSemantics"]["occurrenceParameters"][0] = {
        "source": "army-extra",
        "kind": "numeric-mod",
        "owner": "skill-holder",
        "target": "skill-holder",
        "appliesTo": ["dodge-ph-roll"],
        "extraValues": [
            {"extraId": 1, "extraType": "TEXT", "rawValue": "+3", "modifier": 3}
        ],
    }
    check()
    record["variantSemantics"]["occurrenceParameters"].append(deepcopy(distance))
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate parameter"):
        load_curated_document(path)


@pytest.mark.parametrize("defect", (None, "family", "target", "mixed-scope", "positive"))
def test_surprise_attack_numeric_mod_is_bound_to_target_face_to_face_aro(
    tmp_path: Path, defect: str | None,
) -> None:
    document = valid_document()
    record = next(item for item in document["records"] if item["kind"] == "skill")
    record["armyLinks"] = [{"entity": "skill", "id": "surprise-attack"}]
    parameter = {
        "source": "army-extra", "kind": "numeric-mod", "owner": "skill-holder",
        "target": "opponent", "appliesTo": ["surprise-attack-target-face-to-face-aro"],
        "extraValues": [{"extraId": 6, "extraType": "TEXT", "rawValue": "-3", "modifier": -3}],
    }
    record["variantSemantics"] = {"inheritance": "family", "occurrenceParameters": [parameter]}
    if defect == "family":
        record["armyLinks"][0]["id"] = "mimetism"
    elif defect == "target":
        parameter["target"] = "skill-holder"
    elif defect == "mixed-scope":
        parameter["appliesTo"].append("discover")
    elif defect == "positive":
        parameter["extraValues"] = [
            {"extraId": 1, "extraType": "TEXT", "rawValue": "+3", "modifier": 3},
        ]
    path = tmp_path / "surprise-attack.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    if defect is None:
        load_curated_document(path)
    else:
        with pytest.raises(ValueError):
            load_curated_document(path)


def test_reviewed_dodge_extra_parameter_rejects_unscoped_or_mismatched_values(
    tmp_path: Path,
) -> None:
    document = valid_document()
    record = next(item for item in document["records"] if item["kind"] == "skill")
    record["id"] = "skill:dodge"
    record["armyLinks"] = [{"entity": "skill", "id": "dodge"}]
    examples = [
        {"extraId": 6, "extraType": "TEXT", "rawValue": "-3",
         "effect": {"kind": "opponent-roll-mod", "appliesTo": "dodge-face-to-face",
                    "modifier": -3}},
        {"extraId": 27, "extraType": "TEXT", "rawValue": "PH=11",
         "effect": {"kind": "roll-attribute-replacement", "appliesTo": "dodge-ph-roll",
                    "attribute": "PH", "value": 11}},
        {"extraId": 11, "extraType": "DISTANCE", "rawValue": "+2.5",
         "effect": {"kind": "movement-bonus",
                    "appliesTo": "successful-dodge-movement", "centimeters": 2.5}},
        {"extraId": 308, "extraType": "TEXT", "rawValue": "+1SD",
         "effect": {"kind": "special-die", "appliesTo": "dodge-roll", "count": 1}},
        {"extraId": 379, "extraType": "TEXT", "rawValue": "ARM +3",
         "effect": {"kind": "saving-attribute-mod",
                    "appliesTo": "arm-saving-roll-after-dodge",
                    "attribute": "ARM", "modifier": 3}},
    ]
    template = {
        "source": "army-extra", "kind": "reviewed-extra", "extraValues": examples,
    }
    record["variantSemantics"] = {
        "inheritance": "family", "occurrenceParameters": [deepcopy(template)],
    }
    path = tmp_path / "reviewed-dodge-extras.json"

    def validate() -> None:
        path.write_text(json.dumps(document), encoding="utf-8")
        load_curated_document(path)

    validate()
    record["armyLinks"] = [{"entity": "skill", "id": "mimetism"}]
    with pytest.raises(ValueError, match="Dodge family"):
        validate()
    record["armyLinks"] = [{"entity": "skill", "id": "dodge"}]
    for index, changes, message in [
        (0, {"rawValue": "+3"}, "extraType/rawValue"),
        (0, {"extraType": "DISTANCE"}, "extraType/rawValue"),
        (0, {"effect": {"kind": "opponent-roll-mod",
                        "appliesTo": "dodge-ph-roll", "modifier": -3}},
         "invalid opponent-roll-mod"),
        (1, {"effect": {"kind": "roll-attribute-replacement",
                        "appliesTo": "dodge-ph-roll", "attribute": "BS", "value": 11}},
         "invalid roll-attribute-replacement"),
        (2, {"effect": {"kind": "movement-bonus",
                        "appliesTo": "successful-dodge-movement",
                        "centimeters": 3.5}}, "invalid game distance"),
        (3, {"effect": {"kind": "special-die",
                        "appliesTo": "dodge-roll", "count": 2}}, "invalid special-die"),
        (4, {"effect": {"kind": "saving-attribute-mod",
                        "appliesTo": "arm-saving-roll-after-dodge",
                        "attribute": "PH", "modifier": 3}}, "invalid saving-attribute-mod"),
        (4, {"effect": {"kind": "unknown"}}, "unsupported reviewed effect"),
        (4, {"extraId": 6}, "duplicate extraId"),
    ]:
        invalid = deepcopy(template)
        invalid["extraValues"][index].update(changes)
        record["variantSemantics"]["occurrenceParameters"] = [invalid]
        with pytest.raises(ValueError, match=message):
            validate()

    record["variantSemantics"]["occurrenceParameters"] = [
        {
            "source": "army-extra",
            "kind": "numeric-mod",
            "owner": "skill-holder",
            "target": "skill-holder",
            "appliesTo": ["dodge-ph-roll"],
            "extraValues": [
                {"extraId": 6, "extraType": "TEXT", "rawValue": "+3", "modifier": 3}
            ],
        },
        deepcopy(template),
    ]
    with pytest.raises(ValueError, match="duplicate occurrence extraId"):
        validate()


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
        record for record in document["records"] if record["id"] == "rule:peripheral-type:servant"
    )
    source_servant["facts"]["controllerEligibility"] = {"status": "unknown"}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="must be 'not-stated'"):
        load_curated_document(path)


def test_peripheral_subtype_explanation_groups_require_nonempty_text(
    tmp_path: Path,
) -> None:
    document = valid_document()
    document["records"].append(
        {
            "id": "skill:peripheral",
            "kind": "skill",
            "name": "Peripheral",
            "summary": "The general Peripheral Skill.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {"typeIds": ["automatic"]},
            "labelIds": [],
            "citations": [{"sourceId": "n5-core-v5.3", "page": 106}],
            "composition": {"role": "definition"},
            "review": {"status": "reviewed", "reviewedOn": "2026-10-13"},
            "relations": [
                {"type": "has-subtype", "recordId": "rule:peripheral-type:sample"}
            ],
        }
    )
    document["records"].append(
        {
            "id": "rule:peripheral-type:sample",
            "kind": "rule",
            "name": "Peripheral (Sample)",
            "summary": "Example subtype for validation.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {
                "category": "peripheral-type",
                "controllerEligibility": {"status": "not-stated"},
                "effects": ["A valid effect."],
                "restrictions": ["A valid restriction."],
                "clarifications": ["A valid clarification."],
            },
            "citations": [{"sourceId": "n5-core-v5.3", "page": 106}],
            "composition": {"role": "definition"},
            "review": {"status": "reviewed", "reviewedOn": "2026-10-13"},
        }
    )
    path = tmp_path / "peripheral.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)["records"][-1]["facts"]["effects"] == [
        "A valid effect."
    ]

    for field in ("effects", "restrictions", "clarifications"):
        for invalid in ([], [""], [" ", 123], "not-an-array"):
            changed = json.loads(json.dumps(document))
            changed["records"][-1]["facts"][field] = invalid
            path.write_text(json.dumps(changed), encoding="utf-8")
            with pytest.raises(
                ValueError, match=rf"records\[2\]\.facts\.{field}"
            ):
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
    assert peripheral_types["rule:peripheral-type:servant"]["facts"]["controllerEligibility"] == {
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


def test_n5_cyberplug_connected_controller_idle_and_reactive_split() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {r["id"]: r for r in document["records"]}
    peripheral = records["skill:peripheral"]
    subtype = records["rule:peripheral-type:cyberplug"]
    facts = subtype["facts"]
    assert peripheral["facts"]["typeIds"] == ["automatic"]
    assert facts["profileModes"] == ["connected", "autonomous"]
    assert facts["maxPerController"] == 2
    assert "At the start of each Order or [[trait:aro|ARO]]" in facts["effects"][0]
    assert "Connected or Autonomous for each" in facts["effects"][0]
    assert "no more than one can use its Connected Profile" in facts["effects"][1]
    assert "the other Autonomous" in facts["effects"][1]
    assert "The Controller then performs the recovery Skill and makes the Roll" in (
        facts["clarifications"][0]
    )
    assert "allied target" in facts["clarifications"][0]
    assert "only one target can be treated per Order" in facts["clarifications"][0]
    pages = {c["page"] for c in subtype["citations"] if c["sourceId"] == "n5-core-v5.3-pdf"}
    assert pages >= {107, 108}
    assert "separate [[trait:aro|ARO]] entitlements" in peripheral["facts"]["effects"][3]
    assert "Controller declares a reaction but performs [[skill:idle|Idle]]" in facts["effects"][2]
    assert "both units become Autonomous" in facts["effects"][2]
    assert "A Connected unit is an exception" in facts["clarifications"][0]
    active, reactive = facts["clarifications"][2:]
    assert "are activated by the same Order" in active
    assert "valid target" in active and "unopposed Roll" in active
    assert "Face to Face Roll" in active
    assert "declare an [[trait:aro|ARO]]" in reactive
    assert "both [[skill:cyberplug|Cyberplugs]] become Autonomous" in reactive
    assert "without ordinary reaction eligibility" in reactive


def test_n5_cyberplug_aro_examples_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    manifest = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["corePdfSha256"]
    with pdf.open(source) as book:
        reactive = " ".join(book[106].get_text().split())
        examples = " ".join(book[107].get_text().split())
    for fragment in (
        "Controller performs an Idle instead of any ARO they declare",
        "other Peripheral uses its Autonomous Profile",
        "Controller can declare and perform an ARO normally",
        "Peripherals switch to their Autonomous Profiles",
    ):
        assert fragment in reactive, fragment
    for fragment in (
        "PERIPHERAL (CYBERPLUG) EXAMPLES",
        "The Controller has been activated by the Order",
        "If the ARO is an Attack, it is a Normal Roll",
        "the Controller is performing an Idle",
        "the Autonomous Peripheral declares a Dodge",
        "the two Peripherals (Cyberplug) switch to their Autonomous Profiles",
    ):
        assert fragment in examples, fragment


def test_n5_speculative_attack_template_aro_sequence() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {r["id"]: r for r in document["records"]}
    record = records["skill:speculative-attack"]
    facts = record["facts"]
    assert facts["typeIds"] == ["long-skill"]
    assert record["labelIds"] == ["bs-attack"]
    assert record["citations"][0] == {
        "sourceId": "n5-core-v5.3-pdf",
        "page": 48,
        "section": "Speculative Attack",
    }
    assert record["citations"][1]["sourceId"] == "wiki-en-20260926-200832"
    assert "trajectory" in facts["requirements"][1]
    assert "Burst 1" in facts["effects"][0]
    assert "-6 MOD" in facts["restrictions"][0]
    assert "vertical surface" in facts["restrictions"][1]
    assert len(facts["clarifications"]) == 3
    template, reactions, example = facts["clarifications"]
    assert "Main Target" in template and "impact point" in template
    assert "Neither the target nor the impact point requires LoF" in template
    assert "identify their eligible [[trait:aro|AROs]]" in reactions
    assert "Only then measure the distance" in reactions
    assert "behind Total Cover" in reactions
    assert "target behind a wall" in example
    assert "[[skill:dodge|Dodge]] suffers -3" in example
    assert "[[rule:face-to-face-rolls|Face to Face Roll]]" in example
    assert "[[skill:mimetism|Mimetism]]" in example
    assert {"type": "ignores-modifiers-from", "recordId": "skill:mimetism"} in (
        record["relations"]
    )


def test_n5_speculative_attack_aro_procedure_matches_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    manifest = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["corePdfSha256"]
    with pdf.open(source) as book:
        page = " ".join(book[47].get_text().split())
    for clause in (
        "SPECULATIVE ATTACK LONG SKILL BS Attack",
        "possible to draw a trajectory between the Trooper and the impact point",
        "Main Target must be inside the Area of Effect",
        "both the target of the attack and the impact point",
        "Then, a check is made to ascertain which other Troopers are affected",
        "to determine all AROs",
        "Measure the distance between the Trooper and the impact point",
        "The Blink declares his ARO",
        "he may declare Dodge",
        "A Face to Face Roll ensues",
        "-3 to Dodge a Template without LoF to the attacker",
        "-6 for Speculative Attack",
    ):
        assert clause in page, clause


def test_n5_suppressive_fire_aro_scope_and_g_jumper_exception() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {r["id"]: r for r in document["records"]}
    skill = records["skill:suppressive-fire"]
    state = records["state:suppressive-fire"]
    facts = skill["facts"]
    assert facts["typeIds"] == ["long-skill"]
    assert skill["labelIds"] == ["attack"]
    assert skill["citations"][:2] == [
        {"sourceId": "n5-core-v5.3-pdf", "page": 85, "section": "Suppressive Fire"},
        {"sourceId": "n5-core-v5.3-pdf", "page": 171,
         "section": "Suppressive Fire State"},
    ]
    assert skill["citations"][2]["sourceId"] == "wiki-en-20260926-200832"
    assert facts["requirements"] == [
        "The user must select a Weapon with the "
        "[[trait:suppressive-fire|Suppressive Fire]] Trait."
    ]
    assert "[[state:suppressive-fire]]" in facts["effects"][0]
    assert "[[skill:g-jumper|G: Jumper]]" in facts["effects"][1]
    assert "another Proxy is activated" in facts["effects"][1]
    assert len(facts["clarifications"]) == 2
    assert "Long Skill, not an [[trait:aro|ARO]]" in facts["clarifications"][0]
    assert "Burst 3" in facts["clarifications"][0]
    assert "one target" in facts["clarifications"][0]
    assert "other cancellation conditions" in facts["clarifications"][1]
    assert {"type": "enters-state", "recordId": "state:suppressive-fire"} in (
        skill["relations"]
    )
    assert "full B3 against one target" in state["facts"]["effects"][1]
    assert "other than [[skill:bs-attack|BS Attack]]" in (
        state["facts"]["clarifications"][0]
    )


def test_n5_suppressive_fire_proxy_and_reactive_burst_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    manifest = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["corePdfSha256"]
    with pdf.open(source) as document:
        declaration = " ".join(document[84].get_text().split())
        state = " ".join(document[170].get_text().split())
    for fragment in (
        "SUPPRESSIVE FIRE LONG SKILL Attack",
        "The user must select a weapon with the Suppressive Fire Trait",
        "G: Jumper and Suppressive Fire",
        "that Proxy stays in Suppressive Fire State",
        "even if another Proxy is activated",
    ):
        assert fragment in declaration, fragment
    for fragment in (
        "SF Mode profile replaces the selected weapon",
        "react in ARO with the full B3 value",
        "full Burst must always be directed against a single target",
        "declares any ARO other than a BS Attack using the SF Mode profile",
        "The Trooper declares an Order",
        "Trooper joins any Fireteam",
    ):
        assert fragment in state, fragment


def test_n5_hacking_area_aro_windows_and_marker_delay() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    area = records["rule:hacking-area"]
    facts = area["facts"]
    assert facts["category"] == "basic-rule"
    assert area["citations"][:2] == [
        {"sourceId": "n5-core-v5.3-pdf", "page": 55,
         "section": "Hacking Area"},
        {"sourceId": "n5-core-v5.3-pdf", "page": 57,
         "section": "Hacking Area and Camouflaged ARO examples"},
    ]
    assert area["citations"][2]["sourceId"] == "wiki-hacking-area-oldid-3974"
    assert "Line of Fire is not required" in facts["effects"][0]
    assert "enemy [[equipment:repeater]]" in facts["restrictions"][0]
    assert "performs [[skill:idle]] instead" in facts["restrictions"][0]
    assert len(facts["clarifications"]) == 4
    active, marker = facts["clarifications"][2:]
    assert "inside an enemy [[skill:hacker|Hacker]]'s Hacking Area" in active
    assert "may declare an [[trait:aro|ARO]]" in active
    assert "cannot react to that initial [[skill:idle|Idle]]" in active
    assert "the affected Trooper gains its own [[skill:reset|Reset]]" in active
    assert "[[state:camouflaged|Camouflaged]] Marker" in marker
    assert "delay its [[trait:aro|ARO]]" in marker
    assert "only if the Marker reveals itself during the second Short Skill" in marker
    assert "does not turn an unrevealed Marker into a valid" in marker


def test_n5_hacking_area_source_heading_and_aro_examples_match_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    manifest = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["corePdfSha256"]
    with pdf.open(source) as book:
        definition = " ".join(book[54].get_text().split())
        next_page = " ".join(book[55].get_text().split())
        examples = " ".join(book[56].get_text().split())
    for clause in (
        "HACKING AREA This term refers to the Area of Effect",
        "HACKING AREA IN ARO",
        "while remaining outside that Hacker",
        "measurements show that the Active Trooper is within the Hacking Area",
        "HOLOMASK AND HACKING AREA",
    ):
        assert clause in definition, clause
    assert "REPEATER AUTOMATIC EQUIPMENT" in next_page
    for clause in (
        "During his Active Turn, a Hacker decides to declare Idle",
        "The Enemy Heavy Infantry (HI) cannot declare an ARO",
        "they can declare an ARO, choosing to declare a Reset",
        "EXAMPLE OF CAMOUFLAGED STATE AND ARO THROUGH A REPEATER",
        "can delay their ARO in case the Camouflaged Marker is a Hacker",
        "only if the Camouflaged Marker reveals themselves",
    ):
        assert clause in examples, clause


def test_n5_alert_is_optional_automatic_conclusion_not_an_aro() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    record = records["skill:alert"]
    facts = record["facts"]
    assert facts["category"] == "common-skill"
    assert facts["typeIds"] == ["automatic"]
    assert record["labelIds"] == ["optional", "no-roll"]
    assert record["citations"][0] == {
        "sourceId": "n5-core-v5.3-pdf",
        "page": 77,
        "section": "Alert!",
    }
    assert record["citations"][1]["sourceId"] == "wiki-en-20260926-200832"
    assert any("Allied Trooper" in rule and "Zone of Control" in rule
               for rule in facts["requirements"])
    assert any("has not activated in the same Order" in rule
               for rule in facts["requirements"])
    assert any("declared an [[trait:aro|ARO]]" in rule
               for rule in facts["requirements"])
    assert any("during the Conclusion Step" in item
               and "[[rule:saving-rolls|Saving Rolls]]" in item
               for item in facts["effects"])
    assert any("without changing position or generating AROs" in item
               for item in facts["effects"])
    assert any("not a declared [[trait:aro|ARO]]" in text
               and "at the Order's Conclusion" in text
               for text in facts["clarifications"])
    assert any("not activate in the Order" in text
               and "allied Trooper" in text
               for text in facts["clarifications"])
    assert not facts["restrictions"]


def test_n5_alert_conclusion_and_activation_rules_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    manifest = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text(
            encoding="utf8"
        )
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == manifest["corePdfSha256"]
    with pdf.open(source) as document:
        page = document[76].get_text()
        start = page.index("ALERT!\nAUTOMATIC SKILL")
        end = page.index("BS ATTACK\nCommon Skill", start)
        alert = " ".join(page[start:end].split())
    for clause in (
        "ALERT! AUTOMATIC SKILL Optional, No Roll",
        "not have been activated by an Order or ARO in the same Order",
        "an Allied Trooper within their Zone of Control",
        "has been the target of an Attack",
        "at the end of the Order, during its Conclusion",
        "after performing any Saving Rolls",
        "turn on the spot, without changing position",
        "movement is automatic, it does not require a Roll",
        "does not generate AROs",
    ):
        assert clause.casefold() in alert.casefold(), clause


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
            (relation["type"], relation["recordId"]) for relation in records[trait_id]["relations"]
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
        ("enables-use-of", "skill:place-deployable"),
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
            (relation["type"], relation["recordId"]) for relation in records[trait_id]["relations"]
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
            (relation["type"], relation["recordId"]) for relation in records[source_id]["relations"]
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
    assert "declare [[skill:cc-attack]]" in martial_arts["requirements"][0]

    strategos = records["skill:strategos"]["facts"]
    assert strategos["requirements"] == ["The user must be the army's [[skill:lieutenant]]."]
    assert "Order Count" in strategos["effects"][0]

    strategos_l1 = records["skill:strategos-l1"]["facts"]
    assert strategos_l1["requirements"] == strategos["requirements"]
    assert len(strategos_l1["effects"]) == 2
    assert "two Troopers" in strategos_l1["effects"][0]
    assert "Special Lieutenant Orders" in strategos_l1["effects"][1]
    assert "Regular Orders" in strategos_l1["effects"][1]

    strategos_l2 = records["skill:strategos-l2"]["facts"]
    assert strategos_l2["requirements"] == strategos["requirements"]
    assert len(strategos_l2["effects"]) == 3
    assert "without spending a Command Token" in strategos_l2["effects"][0]
    assert strategos_l2["effects"][1:] == strategos_l1["effects"]

    impetuous = records["skill:impetuous"]["facts"]
    assert impetuous["relatedCategories"] == ["order-type"]

    regular_order = records["rule:regular-order"]
    assert regular_order["facts"]["category"] == "order-type"
    assert regular_order["citations"] == [
        {
            "sourceId": "n5-core-v5.3-pdf",
            "page": 11,
            "section": "Types of Orders",
        }
    ]
    irregular_order = records["rule:irregular-order"]
    assert irregular_order["facts"]["category"] == "order-type"
    assert "not added" in irregular_order["facts"]["restrictions"][0]

    super_jump = records["skill:super-jump"]["facts"]
    assert "Basic Short Skill" in super_jump["effects"][0]
    assert "plus [[distance:4:inch]]" in super_jump["effects"][1]


def test_n5_impetuous_separates_movement_and_end_of_order_prone_limits() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    impetuous = next(
        record for record in document["records"] if record["id"] == "skill:impetuous"
    )
    restrictions = impetuous["facts"]["restrictions"]
    assert "In the Impetuous Phase" in restrictions[0]
    assert all(
        link in restrictions[0]
        for link in ("[[skill:move]]", "[[skill:jump]]", "[[skill:climb]]")
    )
    assert "at the end of the movement" in restrictions[0]
    assert restrictions[1] == (
        "Impetuous Troopers cannot enter Marker States or any other States "
        "that explicitly prohibit entry."
    )
    assert "at the end of an Order" in restrictions[2]
    assert "[[state:prone]]" in restrictions[2]
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 97, "section": "Impetuous"} in (
        impetuous["citations"]
    )


def test_n53_berserk_prone_transition_exception_is_scoped_and_linked() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    berserk = records["skill:berserk"]
    prone = records["state:prone"]
    assert berserk["labelIds"].count("movement") == 1
    restriction = berserk["facts"]["restrictions"][-1]
    assert "General Movement Rules exclude Berserk" in restriction
    assert "enter or leave [[state:prone|Prone]]" in restriction
    assert "start or end of movement" in restriction
    assert "Movement Label" in restriction
    assert not any("cannot declare Berserk" in rule for rule in berserk["facts"]["restrictions"])
    assert any(
        "[[skill:berserk|Berserk]] from voluntary Prone transitions" in note
        for note in prone["facts"]["clarifications"]
    )
    assert {
        "sourceId": "n5-core-v5.3-pdf",
        "page": 29,
        "section": "General Movement Rules",
    } in berserk["citations"]


def test_n5_cautious_movement_aro_suppression_has_scoped_exceptions() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    cautious = records["skill:cautious-movement"]
    stealth = records["skill:stealth"]
    assert cautious["facts"]["typeIds"] == ["long-skill"]
    assert cautious["labelIds"] == ["movement", "no-roll"]
    assert cautious["citations"][:2] == [
        {"sourceId": "n5-core-v5.3-pdf", "page": 32,
         "section": "Cautious Movement"},
        {"sourceId": "n5-core-v5.3-pdf", "page": 112,
         "section": "Stealth: Cautious Movement"},
    ]
    assert cautious["citations"][2]["sourceId"] == "wiki-cautious-movement-oldid-3931"
    facts = cautious["facts"]
    assert "first MOV value" in facts["effects"][0]
    for term in ("TAGs", "Remotes", "Vehicles", "motorcycle",
                 "[[skill:aerial]]", "[[state:targeted]]"):
        assert term.lower() in facts["restrictions"][0].lower()
    notes = facts["clarifications"]
    assert len(notes) == 4
    assert "**both**" in notes[0]
    assert "every enemy Model and Marker" in notes[0]
    assert "[[trait:zone-of-control-zc|Zone of Control]]" in notes[0]
    assert "[[trait:aro|ARO]] eligibility" in notes[0]
    assert "Hackable Trooper in Model form" in notes[1]
    assert "[[skill:non-hackable|non-Hackable]]" in notes[1]
    assert "[[rule:hacking-area|Hacking Area]]" in notes[1]
    assert "[[skill:stealth|Stealth]]" in notes[2]
    assert "enemies with LoF" in notes[2]
    assert "[[skill:sixth-sense|Sixth Sense]]" in notes[2]
    assert "[[skill:combat-instinct|Combat Instinct]]" in notes[2]
    assert "[[trait:deployable|Deployable]]" in notes[2]
    assert "[[state:hidden-deployment|Hidden Deployment]]" in notes[3]
    assert "neither a Model nor a Marker" in notes[3]
    assert {"type": "enables-use-of", "recordId": "skill:cautious-movement"} in (
        stealth["relations"]
    )


def test_n5_cautious_movement_aro_conditions_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    config = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config["corePdfSha256"]
    with pdf.open(source) as book:
        cautious = " ".join(book[31].get_text().split())
        stealth = " ".join(book[111].get_text().split())
    for clause in (
        "CAUTIOUS MOVEMENT LONG SKILL Movement, No LoF, No Roll",
        "move up to the first value of his MOV Attribute",
        "outside the LoF and ZoC of all enemy Models and Markers",
        "Hackable Trooper in Model form",
        "outside the Hacking Area of any enemy Hackers",
        "non-Hackable Trooper is in Model form",
        "does not cause the Trooper to generate AROs",
        "Troopers in Hidden Deployment are neither Models nor Markers",
        "TAGs, Remotes, Vehicles",
        "Troopers in Targeted State",
    ):
        assert clause in cautious, clause
    for clause in (
        "STEALTH AUTOMATIC SKILL Optional",
        "declare Cautious Movement inside the Zone of Control",
        "Hacking Zones of enemy Models and Markers",
        "only grant AROs to enemies that have LoF to them",
        "Stealth is not effective against Troopers with the Combat Instinct",
        "Sixth Sense Special Skills",
    ):
        assert clause in stealth, clause


def test_n5_conditional_climb_jump_declarations_keep_base_types() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    assert records["skill:climb"]["facts"]["typeIds"] == ["long-skill"]
    assert records["skill:jump"]["facts"]["typeIds"] == ["long-skill"]
    for helper, page in (
        ("climbing-plus", 88),
        ("super-jump", 113),
    ):
        record = records[f"skill:{helper}"]
        facts = record["facts"]
        assert facts["typeIds"] == ["automatic"]
        assert record["citations"][0] == {
            "sourceId": "n5-core-v5.3-pdf",
            "page": page,
            "section": "Climbing Plus" if helper == "climbing-plus" else "Super-Jump",
        }
        assert "Basic Short Skill" in facts["effects"][0]
        assert "first Basic Short Skill" in facts["effects"][0]
        assert any("once per Order" in rule for rule in facts["restrictions"])
        assert any("[[skill:impetuous|Impetuous]] Phase" in item for item in facts["effects"])
        assert any(
            "entire exact" in item and ("360" + chr(176) + " LoF") in item
            for item in facts["clarifications"]
        )
    climbing = records["skill:climbing-plus"]["facts"]
    assert any("base's underside" in note for note in climbing["clarifications"])
    assert any("vertical surface" in effect and "ARO" in effect
               for effect in climbing["effects"])
    jumping = records["skill:super-jump"]["facts"]
    assert any("second MOV value" in rule for rule in jumping["restrictions"])
    assert any("Jet Propulsion" in note and "Unit Profile" in note
               for note in jumping["clarifications"])
    assert any("[[state:prone]]" in note for note in jumping["clarifications"])


def test_n5_conditional_movement_clauses_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    provenance = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text(
            encoding="utf8"
        )
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["corePdfSha256"]
    with pdf.open(source) as book:
        climb = " ".join(book[87].get_text().split())
        jump = " ".join(book[112].get_text().split())
    for fragment in (
        "CLIMBING PLUS AUTOMATIC SKILL",
        "Climbing Plus turns the Climb Long Skill into a Basic Short Skill",
        "if declared as the first Basic Short Skill of the Order",
        "half of their base",
        "use Climbing Plus in the Impetuous Phase",
        "complete and exact trajectory",
        "360" + chr(176) + " LoF",
    ):
        assert fragment.casefold() in climb.casefold(), fragment
    for fragment in (
        "SUPER-JUMP AUTOMATIC SKILL",
        "Jump Long Skill is turned into a Basic Short Skill",
        "if declared as the first Basic Short Skill of the Order",
        "second value of their MOV Attribute",
        "use Super-Jump in the Impetuous Phase",
        "Super-Jump (Jet Propulsion)",
        "complete and exact trajectory",
        "360" + chr(176) + " LoF",
        "Prone State is automatically cancelled",
    ):
        assert fragment.casefold() in jump.casefold(), fragment


def test_esx02_jet_propulsion_is_variant_only_and_distance_neutral() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    super_jump = records["skill:super-jump"]
    facts = super_jump["facts"]
    jet = facts["clarifications"][1]
    assert "Unit Profile lists [[skill:super-jump|Super-Jump]] (Jet Propulsion)" in jet
    assert "change direction and heading in mid-air as many times as desired" in jet
    assert "declared [[skill:jump|Jump]] trajectory" in jet
    assert "not a general benefit" in jet
    assert "does not add [[skill:jump|Jump]] distance or remove the once-per-Order limit" in jet
    assert "Long Skill [[skill:jump|Jump]] uses the first MOV value plus" in (
        facts["effects"][1]
    )
    assert "a Short Skill [[skill:jump]] adds that distance instead" in (
        facts["effects"][1]
    )
    assert "only once per Order" in facts["restrictions"][0]
    assert "entire exact trajectory before [[trait:aro|ARO]] declarations" in (
        facts["clarifications"][0]
    )
    assert len(facts["sourceNotes"]) == 1
    assert "English N5.3 p. 113" in facts["sourceNotes"][0]
    assert "Spanish N5.3 p. 116" in facts["sourceNotes"][0]
    assert "p. 117 trajectory example" in facts["sourceNotes"][0]
    assert {
        (citation["sourceId"], citation.get("page"))
        for citation in super_jump["citations"]
    } >= {("n5-core-v5.3-pdf", 113), ("n5-core-v5.3-es-pdf", 116)}


def test_esx02_jet_propulsion_wording_in_pinned_source_versions() -> None:
    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    old = root / "data/pdf/rules/n5-rules-v5-2-en.pdf"
    current = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    spanish = root / "data/pdf/rules/esp-n5-update-5-3.pdf"
    if not all(path.exists() for path in (old, current, spanish)):
        pytest.skip("Required pinned N5.2/N5.3 PDFs unavailable")
    with pdf.open(old) as book:
        old_text = " ".join(book[111].get_text().split())
    with pdf.open(current) as book:
        current_text = " ".join(book[112].get_text().split())
    with pdf.open(spanish) as book:
        spanish_text = " ".join(book[115].get_text().split())
        example = " ".join(book[116].get_text().split())
    assert "change the direction and heading of the jump before" in old_text
    assert "change direction and heading in mid-air as many times as they wish" in (
        current_text
    )
    assert "variar la dirección y sentido de su trayectoria en el aire" in (
        spanish_text
    )
    assert "antes de situarse sobre la superficie de aterrizaje" in spanish_text
    assert "variar libremente su trayectoria por el aire" in example


def test_guard_neurocinetics_total_reaction_n53_citations() -> None:
    path = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    records = {r["id"]: r for r in load_curated_document(path)["records"]}
    for skill, page, mode in (
        ("guard", 95, "optional"),
        ("neurocinetics", 104, "obligatory"),
        ("total-reaction", 116, "optional"),
    ):
        record = records[f"skill:{skill}"]
        assert record["facts"]["typeIds"] == ["automatic"]
        assert record["labelIds"] == [mode]
        assert record["citations"][0]["sourceId"] == "n5-core-v5.3-pdf"
        assert record["citations"][0]["page"] == page


def test_reactive_combat_automatic_conditions_match_n53_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    config = json.loads((root / "config/validation/weaponry-family-clauses.json").read_text("utf8"))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config["corePdfSha256"]
    cases = (
        (95, "GUARD", "Optional", "Silhouette contact"),
        (104, "NEUROCINETICS", "Obligatory", "against a single target"),
        (116, "TOTAL REACTION", "Optional", "Troopers activated by the Order"),
    )
    with pdf.open(source) as book:
        for page, title, mode, clause in cases:
            body = " ".join(book[page - 1].get_text().split())
            assert f"{title} AUTOMATIC SKILL {mode}" in body
            assert clause in body


def test_n5_stealth_counters_preserve_attack_only_sixth_sense_scope() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {r["id"]: r for r in document["records"]}
    combat = records["skill:combat-instinct"]
    sixth = records["skill:sixth-sense"]
    stealth = records["skill:stealth"]
    assert combat["facts"]["typeIds"] == ["automatic"]
    assert sixth["facts"]["typeIds"] == ["automatic"]
    assert stealth["facts"]["typeIds"] == ["automatic"]
    assert combat["labelIds"] == sixth["labelIds"] == ["optional"]
    assert combat["citations"][0] == {
        "sourceId": "n5-core-v5.3-pdf",
        "page": 88,
        "section": "Combat Instinct",
    }
    for record in (combat, sixth):
        assert any(
            c["sourceId"] == "n5-core-v5.3-pdf" and c["page"] == 112
            for c in record["citations"]
        )
        assert any(
            c["sourceId"] == "n5-core-v5.3-pdf" and c["page"] == 20
            for c in record["citations"]
        )
        assert {"type": "negates-effects-of", "recordId": "skill:stealth"} in (
            record["relations"]
        )
    assert {
        "type": "ignores-modifiers-from", "recordId": "skill:surprise-attack"
    } in combat["relations"]
    assert not any(
        r["recordId"] == "skill:surprise-attack"
        for r in sixth["relations"]
    )
    assert any(
        "does not grant" in note and "360-degree LoF" in note
        for note in combat["facts"]["clarifications"]
    )
    assert any(
        "only to Attacks directed at the user" in note
        and "[[skill:stealth|Stealth]]" in note
        and "[[trait:zone-of-control-zc|Zone of Control]]" in note
        for note in sixth["facts"]["clarifications"]
    )
    assert any(
        c["sourceId"] == "wiki-combat-instinct-oldid-3135"
        for c in combat["citations"]
    )
    assert any(
        c["sourceId"] == "wiki-sixth-sense-oldid-3901"
        for c in sixth["citations"]
    )


def test_n5_stealth_counter_scope_matches_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    config = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config["corePdfSha256"]
    with pdf.open(source) as book:
        combat = " ".join(book[87].get_text().split())
        sixth = " ".join(book[110].get_text().split())
        stealth = " ".join(book[111].get_text().split())
        zoc = " ".join(book[19].get_text().split())
    assert "COMBAT INSTINCT AUTOMATIC SKILL Optional" in combat
    assert "user ignores Surprise Attack MODs from attackers" in combat
    assert "Stealth Special Skill is not effective" in combat
    assert "SIXTH SENSE AUTOMATIC SKILL Optional" in sixth
    assert "respond to Attacks (and only Attacks) directed at" in sixth
    assert "360" in sixth and "LoF arc" in sixth
    assert "STEALTH AUTOMATIC SKILL Optional" in stealth
    assert "they only grant AROs to enemies that have LoF to them" in stealth
    assert "not effective against Troopers with the Combat Instinct" in stealth
    assert "Sixth Sense Special Skills" in stealth
    assert "Enemies entering or acting inside the Zone of Control" in zoc
    assert "while remaining outside that Trooper" in zoc


def test_esx01_stealth_contact_reaction_choices_are_explicit_and_scoped() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    stealth = records["skill:stealth"]
    effects = stealth["facts"]["effects"]
    assert "Basic Short Skills with the Movement Label" in effects[1]
    assert "Other declared Skills grant AROs normally" in effects[2]
    assert "Silhouette contact without entering the enemy's LoF" in effects[4]
    contact = effects[5]
    assert "when a subsequent declaration grants the enemy an [[trait:aro|ARO]]" in contact
    for option in (
        "[[skill:cc-attack|CC Attack]]",
        "[[skill:dodge|Dodge]]",
        "[[skill:reset|Reset]]",
        "[[state:engaged|Engaged State]]",
    ):
        assert option in contact
    assert "protected movement itself does not grant a reaction" in contact
    assert any(
        "[[trait:deployable|Deployable]] Weapons or Equipment" in restriction
        for restriction in stealth["facts"]["restrictions"]
    )
    assert {
        (citation["sourceId"], citation.get("page"))
        for citation in stealth["citations"]
    } >= {("n5-core-v5.3-pdf", 112), ("n5-core-v5.3-es-pdf", 114)}


def test_esx01_current_spanish_stealth_agrees_with_english_primary_source() -> None:
    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    english = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    spanish = root / "data/pdf/rules/esp-n5-update-5-3.pdf"
    if not english.exists() or not spanish.exists():
        pytest.skip("Pinned current N5.3 English/Spanish PDFs unavailable")
    with pdf.open(english) as book:
        english_text = " ".join(book[111].get_text().split())
    with pdf.open(spanish) as book:
        spanish_text = " ".join(book[113].get_text().split())
    for fragment in (
        "STEALTH AUTOMATIC SKILL",
        "they only grant AROs to enemies that have LoF to them",
        "only declare CC Attack, Dodge, Reset",
        "Combat Instinct or",
        "Deployable Weapons",
    ):
        assert fragment in english_text, fragment
    for fragment in (
        "SIGILO",
        "Movimiento Cauteloso, Inacción",
        "Ataque CC, Esquivar, Reset",
        "Intuición de Combate o Sexto Sentido",
        "Posicionable",
    ):
        assert fragment in spanish_text, fragment
    # Without the Spanish N5.2 PDF this proves current alignment, not
    # which wording was changed between Spanish releases.


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
        record_id: records[record_id]["facts"]["typeIds"] for record_id in expected_types
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


def test_n5_guard_aerial_unconscious_exception_is_conditional() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {r["id"]: r for r in document["records"]}
    aerial = records["skill:aerial"]
    guard = records["skill:guard"]
    unconscious = records["state:unconscious"]
    assert aerial["facts"]["typeIds"] == ["automatic"]
    assert guard["facts"]["typeIds"] == ["automatic"]
    assert aerial["labelIds"] == ["obligatory"]
    assert guard["labelIds"] == ["optional"]
    assert aerial["citations"][0] == {
        "sourceId": "n5-core-v5.3-pdf", "page": 86, "section": "Aerial"
    }
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 86,
            "section": "Aerial: Guard exception"} in guard["citations"]
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 172,
            "section": "Unconscious State: Automatic Skills"} in guard["citations"]
    assert any(c["sourceId"] == "wiki-aerial-oldid-4040" for c in aerial["citations"])
    assert {"type": "restricts-use-of", "recordId": "skill:guard"} in aerial["relations"]
    assert {"type": "enables-use-of", "recordId": "skill:cc-attack"} in guard["relations"]
    assert "Line of Fire and Zone of Control" in guard["facts"]["requirements"][0]
    assert "[[state:unconscious|Unconscious]]" in guard["facts"]["restrictions"][0]
    assert any("independently of Silhouette contact" in x
               for x in guard["facts"]["clarifications"])
    assert any("requires the target" in x and "Zone of Control" in x
               for x in guard["facts"]["clarifications"])
    assert any("Silhouette-contact requirement" in x
               for x in aerial["facts"]["clarifications"])
    assert any("Automatic Special Skills" in x and "have no effect" in x
               for x in unconscious["facts"]["effects"])


def test_n5_guard_aerial_exception_matches_pinned_pdf() -> None:
    import hashlib
    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    config = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config["corePdfSha256"]
    with pdf.open(source) as document:
        aerial = " ".join(document[85].get_text().split())
        guard = " ".join(document[94].get_text().split())
        unconscious = " ".join(document[171].get_text().split())
    for clause in (
        "AERIAL AUTOMATIC SKILL Obligatory",
        "Guard Special Skill may not be used against Troopers with the Aerial",
        "unless they are in Unconscious State",
        "never in Silhouette contact",
    ):
        assert clause in aerial, clause
    for clause in (
        "GUARD AUTOMATIC SKILL Optional",
        "target of the CC Attack must be in LoF and ZoC",
        "no need to reach or be in Silhouette contact",
    ):
        assert clause in guard, clause
    assert "Automatic Special Skills and Automatic Equipment have no effect" in unconscious


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
        record_id: records[record_id]["facts"]["typeIds"] for record_id in expected_types
    } == expected_types

    assert records["skill:aerial"]["relations"] == [
        {"type": "restricts-use-of", "recordId": "skill:cautious-movement"},
        {"type": "restricts-use-of", "recordId": "skill:guard"},
        {"type": "negates-effects-of", "recordId": "trait:boost"},
        {"type": "prevents-state-entry", "recordId": "state:prone"},
        {"type": "prevents-state-entry", "recordId": "state:engaged"},
    ]
    assert records["skill:climbing-plus"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:climb"},
        {"type": "applies-effects-to", "recordId": "skill:move"},
        {"type": "applies-effects-to", "recordId": "skill:dodge"},
    ]
    assert "relations" not in records["skill:terrain"]
    assert records["skill:warhorse"]["relations"] == [
        {"type": "negates-effects-of", "recordId": "rule:loss-of-lieutenant"},
        {"type": "prevents-state-entry", "recordId": "state:isolated"},
    ]


def test_checked_in_n5_collection_models_deployment_skill_and_state_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_types = {
        "skill:booty": ["deployment-skill"],
        "skill:metachemistry": ["deployment-skill"],
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
        record_id: records[record_id]["facts"]["typeIds"] for record_id in expected_types
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

    assert records["skill:booty"]["labelIds"] == ["optional"]
    assert records["skill:metachemistry"]["labelIds"] == ["optional"]
    assert "relations" not in records["skill:booty"]
    assert "relations" not in records["skill:metachemistry"]

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


def test_checked_in_n5_collection_models_profile_runtime_identity_skill_slice() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    expected_types = {
        "skill:g-jumper": ["automatic"],
        "skill:infinity-spec-ops": ["automatic"],
        "skill:request-specball": ["automatic"],
        "skill:morpho-scan": ["short-skill"],
        "skill:remdriver": ["deployment-skill"],
        "skill:transmutation": ["automatic"],
    }
    assert {
        record_id: records[record_id]["facts"]["typeIds"] for record_id in expected_types
    } == expected_types
    assert records["skill:g-jumper"]["labelIds"] == ["obligatory"]
    assert records["skill:infinity-spec-ops"]["labelIds"] == ["optional"]
    assert records["skill:morpho-scan"]["labelIds"] == [
        "comms-attack",
        "no-roll",
        "optional",
    ]
    assert records["skill:morpho-scan"]["relations"] == [
        {"type": "imposes-modifiers-on", "recordId": "skill:reset"}
    ]
    assert records["skill:remdriver"]["labelIds"] == ["optional"]
    assert records["skill:transmutation"]["labelIds"] == []
    assert "relations" not in records["skill:g-jumper"]
    assert records["skill:infinity-spec-ops"]["relations"] == [
        {"type": "enables-use-of", "recordId": "skill:request-specball"}
    ]
    assert "relations" not in records["skill:remdriver"]
    assert "relations" not in records["skill:transmutation"]


def test_request_specball_is_a_bilingual_source_cited_separate_core_procedure() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}
    specball = records["skill:request-specball"]
    speedball = records["skill:request-speedball"]
    assert specball["name"] == "Request SpecBall"
    assert specball["labelIds"] == ["optional"]
    assert specball["facts"]["typeIds"] == ["automatic"]
    assert specball["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:combat-jump"}
    ]
    assert "one 55 mm SpecBall Token" in " ".join(specball["facts"]["effects"])
    assert "PH 15" in specball["summary"]
    assert "Game Round 2 or 3" in specball["summary"]
    assert "once per game" in " ".join(specball["facts"]["restrictions"])
    assert "two different items" in " ".join(specball["facts"]["effects"])
    assert "Enhanced Profile" in " ".join(specball["facts"]["effects"])
    assert "Marker form" in " ".join(specball["facts"]["effects"])
    assert "SpecBot" in " ".join(specball["facts"]["effects"])
    assert "[[equipment:deactivator|Deactivators]]" in " ".join(
        specball["facts"]["effects"]
    )
    assert "two 55 mm Speedball Tokens" in speedball["facts"]["effects"][0]
    assert "English printing discrepancy" in specball["facts"]["sourceNotes"][0]
    assert "TEAM-OPS" in specball["facts"]["sourceNotes"][1]
    cited = {(ref["sourceId"], ref["page"]) for ref in specball["citations"]}
    assert {
        ("n5-core-v5.3-pdf", 98),
        ("n5-core-v5.3-es-pdf", 98),
        ("its-season-18-en-pdf", 26),
        ("its-season-18-en-pdf", 28),
    } == cited
    assert any(source["id"] == "its-season-18-en-pdf" for source in document["sources"])


def test_checked_in_n5_collection_models_final_semantic_link_cleanup() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:super-jump"]["relations"] == [
        {"type": "modifies-use-of", "recordId": "skill:jump"}
    ]
    assert records["trait:perimeter"]["relations"] == [
        {"type": "modifies-use-of", "recordId": "skill:place-deployable"}
    ]
    assert records["trait:non-lethal"]["relations"] == [
        {"type": "restricts-use-of", "recordId": "skill:immunity"}
    ]
    assert records["skill:explode"]["relations"] == [
        {"type": "enters-state", "recordId": "state:dead"},
        {"type": "triggered-by-state-entry", "recordId": "state:unconscious"},
    ]


def test_checked_in_n5_collection_models_hacker_core_skill() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    hacker = records["skill:hacker"]
    assert hacker["facts"]["typeIds"] == ["automatic"]
    assert hacker["labelIds"] == ["obligatory"]
    assert hacker["armyLinks"] == [{"entity": "skill", "id": "hacker"}]
    effects = " ".join(hacker["facts"]["effects"])
    assert "[[equipment:hacking-device]]" in effects
    assert "Upgrade Programs" in effects
    assert "Null State" in effects
    assert hacker["relations"] == [
        {"type": "enables-use-of", "recordId": "equipment:hacking-device"}
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
        record_id: records[record_id]["labelIds"] for record_id in expected_labels
    } == expected_labels
    assert all(
        records[record_id]["facts"]["typeIds"] == ["automatic"] for record_id in expected_labels
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
        {"type": "prevents-state-entry", "recordId": "state:prone"},
    ]
    assert "relations" not in records["skill:religious-troop"]


def test_n5_declaration_categories_follow_exact_source_headings() -> None:
    path = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    document = load_curated_document(path)
    mapping: dict[str, list[tuple[str, int]]] = {}
    for record in document["records"]:
        if record["kind"] != "declaration-category":
            continue
        source = record["citations"][0]
        assert source["sourceId"] == "n5-core-v5.3-pdf"
        assert record["id"].endswith(f":p{source['page']}")
        for link in record["armyLinks"]:
            if link["entity"] == "skill":
                mapping.setdefault(str(link["id"]), []).append(
                    (record["facts"]["typeId"], source["page"])
                )
    expected = {
        "bs-attack": {("short-skill", 39), ("aro", 39)},
        "cc-attack": {("short-skill", 51), ("aro", 51)},
        "discover": {("basic-short-skill", 77), ("aro", 77)},
        "dodge": {("short-skill", 79), ("aro", 79)},
        "forward-observer": {("short-skill", 92), ("aro", 92)},
        "morpho-scan": {("short-skill", 103)},
    }
    for skill, types in expected.items():
        assert set(mapping[skill]) == types, skill
        assert len(mapping[skill]) == len(types), skill
        record = next(r for r in document["records"] if r["id"] == f"skill:{skill}")
        assert set(record["facts"]["typeIds"]) == {type_id for type_id, _ in types}
        pages = {
            citation["page"] for citation in record["citations"]
            if citation["sourceId"] == "n5-core-v5.3-pdf"
        }
        if skill in {"bs-attack", "cc-attack", "discover", "morpho-scan"}:
            assert {page for _, page in types} <= pages, skill
    for retired in (
        "declaration-category:short-skill:p40",
        "declaration-category:aro:p40",
        "declaration-category:short-skill:p45",
        "declaration-category:aro:p45",
        "declaration-category:basic-short-skill:p78",
        "declaration-category:aro:p78",
        "declaration-category:basic-short-skill:p103",
        "declaration-category:aro:p103",
    ):
        assert retired not in {r["id"] for r in document["records"]}


def test_n5_declaration_source_headings_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    provenance = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text(
            encoding="utf8"
        )
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["corePdfSha256"]
    patterns = {
        39: r"BS ATTACK\s+SHORT SKILL\s*/\s*ARO",
        51: r"CC ATTACK\s+SHORT SKILL\s*/\s*ARO",
        77: r"DISCOVER\s+BASIC SHORT SKILL\s*/\s*ARO",
        79: r"DODGE\s+SHORT SKILL\s*/\s*ARO",
        92: r"FORWARD OBSERVER\s+SHORT SKILL\s*/\s*ARO",
        103: r"MORPHO SCAN\s+SHORT SKILL\s+Comms Attack",
    }
    with pdf.open(source) as document:
        for page, pattern in patterns.items():
            assert re.search(pattern, document[page - 1].get_text(), re.I), page


def test_n5_discover_marker_retry_and_attack_sequence() -> None:
    root = Path(__file__).resolve().parents[1]
    document = load_curated_document(root / "data/curated/rules/n5-core-v5.3.json")
    records = {record["id"]: record for record in document["records"]}
    discover = records["skill:discover"]
    facts = discover["facts"]
    assert facts["typeIds"] == ["basic-short-skill", "aro"]
    assert discover["citations"][0] == {
        "sourceId": "n5-core-v5.3-pdf", "page": 77, "section": "Discover"
    }
    assert len(facts["requirements"]) == 2
    assert "draw LoF to the target Marker" in facts["requirements"][0]
    assert "same target" in facts["requirements"][1]
    assert "twice during one Order" in facts["requirements"][1]
    assert "Discover a Marker" in facts["restrictions"][2]
    assert "next Player Turn" in facts["restrictions"][2]
    assert "A different allied Trooper" in facts["restrictions"][2]
    assert "original Trooper may try a different Marker" in facts["restrictions"][2]
    assert "[[state:camouflaged|Camouflaged]]" in facts["restrictions"][2]
    assert "[[state:impersonation-1|Impersonation-1]]" in facts["restrictions"][2]
    assert "[[state:impersonation-2|Impersonation-2]]" in facts["restrictions"][2]
    assert any("another Basic Short Skill or Short Skill" in x
               for x in facts["clarifications"])
    assert any("before resolving an Attack" in x
               for x in facts["clarifications"])
    assert any("declares an [[trait:aro|ARO]]" in x
               and "not needed" in x for x in facts["clarifications"])
    assert any("a different target" in x for x in facts["clarifications"])
    assert {"type": "reveals-state", "recordId": "state:camouflaged"} in (
        discover["relations"]
    )


def test_n5_discover_retry_and_aro_exception_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    config = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config["corePdfSha256"]
    with pdf.open(source) as document:
        page = " ".join(document[76].get_text().split())
    for clause in (
        "DISCOVER BASIC SHORT SKILL / ARO",
        "The user must be able to draw LoF to the target",
        "cannot be used against the same Target twice",
        "fails a WIP Roll to Discover a Marker",
        "same Marker until the next Player Turn",
        "attempt to Discover a different Marker",
        "re-entered Camouflaged State or Impersonation-1 or 2 State",
        "as in a BS Attack (Cover, Range, Mimetism",
        "Discover is a Basic Short Skill",
        "If the Camouflaged target declares an ARO",
        "no need to perform the Discover Roll",
        "does not declare an ARO",
        "need to pass the Discover Roll before resolving any Attack",
        "Discover one target and Attack a different target",
    ):
        assert clause in page, clause


def test_n5_short_skill_pages_match_source_headings() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    short = [
        record for record in document["records"]
        if record["kind"] == "declaration-category"
        and record["facts"]["typeId"] == "short-skill"
    ]
    expected = {
        "bs-attack": 39, "cc-attack": 51, "dodge": 79,
        "doctor": 90, "engineer": 91, "forward-observer": 92,
        "morpho-scan": 103, "sensor": 111, "deactivator": 121,
        "gizmokit": 123, "medikit": 124,
    }
    assert len(short) == len(expected)
    for record in short:
        assert len(record["armyLinks"]) == 1
        name = record["armyLinks"][0]["id"]
        assert name in expected
        page = expected[name]
        assert record["id"] == f"declaration-category:short-skill:p{page}"
        assert record["citations"] == [
            {"sourceId": "n5-core-v5.3-pdf", "page": page}
        ]
    sensor = next(
        record for record in document["records"]
        if record["id"] == "skill:sensor"
    )
    assert any(
        item["sourceId"] == "n5-core-v5.3-pdf" and item["page"] == 111
        for item in sensor["citations"]
    )


def test_n5_short_skill_declarations_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    provenance = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text(
            encoding="utf8"
        )
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["corePdfSha256"]
    headings = {
        39: "BS ATTACK", 51: "CC ATTACK", 79: "DODGE", 90: "DOCTOR",
        91: "ENGINEER", 92: "FORWARD OBSERVER", 103: "MORPHO SCAN",
        111: "SENSOR", 121: "DEACTIVATOR", 123: "GIZMOKIT", 124: "MEDIKIT",
    }
    with pdf.open(source) as document:
        for page, name in headings.items():
            pattern = rf"(?<![A-Za-z]){re.escape(name)}\s+SHORT SKILL"
            assert re.search(pattern, document[page - 1].get_text(), re.I), (page, name)


def test_n5_numeric_replacement_variants_preserve_army_skill_ids() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    records = {record["id"]: record for record in document["records"]}
    expected = {
        "bs-11": (279, "BS=11", "bs-attack", 39),
        "bs-12": (278, "BS=12", "bs-attack", 39),
        "cc-21": (274, "CC=21", "cc-attack", 51),
    }
    for slug, (source_id, name, parent, page) in expected.items():
        record = records[f"skill:{slug}"]
        assert record["name"] == name
        assert record["armyLinks"] == [{"entity": "skill", "id": source_id}]
        assert record["facts"]["typeIds"] == ["short-skill", "aro"]
        assert {"type": "variant-of", "recordId": f"skill:{parent}"} in record["relations"]
        assert record["citations"][0] == {
            "sourceId": "n5-core-v5.3-pdf", "page": page,
            "section": "BS Attack" if parent == "bs-attack" else "CC Attack",
        }
        assert "page" in record["citations"][1]
    # These names and values originate in the Army source dictionary,
    # not in independent named N5 rulebook entries.


def test_n5_numeric_replacement_variants_match_pinned_army_snapshot() -> None:
    import hashlib
    import zipfile
    from collections import Counter

    archive = Path(__file__).parents[1] / "data/raw/JSON 20260929-114335.zip"
    if not archive.exists():
        pytest.skip("Pinned private Army snapshot is not installed")
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == (
        "f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75"
    )
    names = {274: "CC=21", 278: "BS=12", 279: "BS=11"}
    counts: Counter[int] = Counter()
    dictionary_ids: set[int] = set()
    with zipfile.ZipFile(archive) as snapshot:
        files = [name for name in snapshot.namelist() if name.endswith(".json")]
        assert len(files) == 59
        for filename in files:
            data = json.loads(snapshot.read(filename))
            for item in data.get("filters", {}).get("skills", []):
                if item.get("id") in names:
                    assert item["name"] == names[item["id"]], filename
                    dictionary_ids.add(item["id"])
            for unit in data.get("units", []):
                for group in unit.get("profileGroups", []):
                    for option in group.get("options", []):
                        for item in option.get("skills", []):
                            if item.get("id") in names:
                                assert item.get("q") == 1, filename
                                counts[item["id"]] += 1
    assert dictionary_ids == set(names)
    assert counts == {274: 6, 278: 9, 279: 2}
    # Counts include repeat appearances in different faction files;
    # they are not unique-unit counts.


def test_n5_deployment_and_long_skill_categories_use_own_headings() -> None:
    root = Path(__file__).parents[1]
    document = load_curated_document(root / "data/curated/rules/n5-core-v5.3.json")
    expected: dict[str, tuple[str, int]] = {
        "infiltration": ("deployment-skill", 97),
        "forward-deployment": ("deployment-skill", 92),
        "impersonation": ("deployment-skill", 96),
        "hidden-deployment": ("deployment-skill", 95),
        "minelayer": ("deployment-skill", 102),
        "climb": ("long-skill", 32),
        "jump": ("long-skill", 34),
        "combat-jump": ("long-skill", 89),
        "parachutist": ("long-skill", 105),
        "triangulated-fire": ("long-skill", 118),
        "berserk": ("long-skill", 86),
    }
    records = {record["id"]: record for record in document["records"]}
    categories = [
        record
        for record in document["records"]
        if record["kind"] == "declaration-category"
    ]
    for skill, (category, page) in expected.items():
        matches = [
            record for record in categories
            if any(link == {"entity": "skill", "id": skill} for link in record["armyLinks"])
            and record["facts"]["typeId"] == category
        ]
        assert len(matches) == 1, skill
        category_slug = "deployment" if category == "deployment-skill" else "long-skill"
        assert matches[0]["id"] == f"declaration-category:{category_slug}:p{page}"
        assert matches[0]["citations"] == [
            {"sourceId": "n5-core-v5.3-pdf", "page": page}
        ]
        definition = records[f"skill:{skill}"]
        assert category in definition["facts"]["typeIds"], skill
        if skill in {
            "infiltration", "impersonation", "hidden-deployment",
            "climb", "jump", "combat-jump", "parachutist",
        }:
            assert any(
                citation["sourceId"] == "n5-core-v5.3-pdf"
                and citation["page"] == page
                for citation in definition["citations"]
            ), skill
    sapper = [
        record for record in categories
        if any(link == {"entity": "skill", "id": "sapper"} for link in record["armyLinks"])
    ]
    assert {
        (record["facts"]["typeId"], record["citations"][0]["page"])
        for record in sapper
    } == {("deployment-skill", 111), ("long-skill", 111)}
    assert len(sapper) == 2
    for retired in (
        "declaration-category:deployment:p89",
        "declaration-category:deployment:p93",
        "declaration-category:deployment:p94",
        "declaration-category:long-skill:p25",
    ):
        assert retired not in records


def test_n5_deployment_and_long_skill_headings_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    provenance = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text(
            encoding="utf8"
        )
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["corePdfSha256"]
    patterns = {
        32: r"CLIMB\s+LONG SKILL",
        34: r"JUMP\s+LONG SKILL",
        86: r"BERSERK\s+LONG SKILL",
        89: r"COMBAT JUMP\s+LONG SKILL",
        92: r"FORWARD DEPLOYMENT\s+DEPLOYMENT SKILL",
        95: r"HIDDEN DEPLOYMENT\s+DEPLOYMENT SKILL",
        96: r"IMPERSONATION\s+DEPLOYMENT SKILL",
        97: r"INFILTRATION\s+DEPLOYMENT SKILL",
        102: r"MINELAYER\s+DEPLOYMENT SKILL",
        105: r"PARACHUTIST\s+LONG SKILL",
        111: r"SAPPER\s+DEPLOYMENT SKILL\s*/\s*LONG SKILL",
        118: r"TRIANGULATED FIRE\s+LONG SKILL",
    }
    with pdf.open(source) as document:
        for page, pattern in patterns.items():
            assert re.search(pattern, document[page - 1].get_text(), re.I), page


def test_n5_deployment_only_skills_are_not_automatic_metadata() -> None:
    path = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}
    declarations = [
        record for record in document["records"]
        if record["kind"] == "declaration-category"
    ]
    expected = {
        "booty": 86,
        "decoy": 90,
        "metachemistry": 101,
        "remdriver": 110,
        "strategic-deployment": 112,
    }
    assert len(declarations) == 63
    for slug, page in expected.items():
        found = [
            record for record in declarations
            if {"entity": "skill", "id": slug} in record["armyLinks"]
        ]
        assert len(found) == 1, slug
        item = found[0]
        assert item["id"] == f"declaration-category:deployment:p{page}"
        assert item["facts"] == {"typeId": "deployment-skill", "order": 20}
        assert item["citations"] == [{"sourceId": "n5-core-v5.3-pdf", "page": page}]
        definition = records[f"skill:{slug}"]
        assert definition["facts"]["typeIds"] == ["deployment-skill"]
        assert any(
            citation["sourceId"] == "n5-core-v5.3-pdf"
            and citation["page"] == page
            for citation in definition["citations"]
        ), slug
    assert "declaration-category:automatic:p89" not in records


def test_n5_deployment_only_headings_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    provenance = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text(
            encoding="utf8"
        )
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["corePdfSha256"]
    headings = {
        86: "BOOTY",
        90: "DECOY",
        101: "METACHEMISTRY",
        110: "REMDRIVER",
        112: "STRATEGIC DEPLOYMENT",
    }
    with pdf.open(source) as document:
        for page, heading in headings.items():
            pattern = rf"(?<![A-Za-z]){re.escape(heading)}\s+DEPLOYMENT SKILL\s+Optional"
            assert re.search(pattern, document[page - 1].get_text(), re.I), page


def test_n5_automatic_category_pages_reconcile_to_actual_skill_headings() -> None:
    path = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}
    automatics = [
        record for record in document["records"]
        if record["kind"] == "declaration-category"
        and record["facts"]["typeId"] == "automatic"
    ]
    assert len(automatics) == 28
    pages = {
        "surprise-attack": 114, "chain-of-command": 87,
        "no-wound-incapacitation": 104, "g-jumper": 93, "hacker": 54,
        "immunity": 95, "natural-born-warrior": 103,
        "remote-presence": 110, "sixth-sense": 111,
        "lieutenant": 99, "super-jump": 113, "regeneration": 109,
        "terrain": 116, "total-reaction": 116,
    }
    for name, page in pages.items():
        mapping = [
            r for r in automatics
            if {"entity": "skill", "id": name} in r["armyLinks"]
        ]
        assert len(mapping) == 1, name
        assert mapping[0]["id"] == f"declaration-category:automatic:p{page}"
        assert mapping[0]["citations"] == [
            {"sourceId": "n5-core-v5.3-pdf", "page": page}
        ]
        definition = records[f"skill:{name}"]
        assert "automatic" in definition["facts"]["typeIds"]
        assert any(
            c["sourceId"] == "n5-core-v5.3-pdf" and c["page"] == page
            for c in definition["citations"]
        ), name
    for mapping in automatics:
        assert mapping["id"].endswith(f":p{mapping['citations'][0]['page']}")
        assert mapping["armyLinks"]
        assert {"entity": "skill", "id": "regular"} not in mapping["armyLinks"]
    assert records["training:regular"]["facts"]["orderType"] == "regular"
    assert "skill:regular" not in records
    for obsolete in (
        "declaration-category:automatic:p94",
        "declaration-category:automatic:p96",
        "declaration-category:automatic:p101",
    ):
        assert obsolete not in records


def test_n5_reconciled_automatic_heading_pages_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    provenance = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text(
            encoding="utf8"
        )
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["corePdfSha256"]
    headings = {
        54: "HACKER", 87: "CHAIN OF COMMAND",
        93: "G: JUMPER", 95: "IMMUNITY",
        99: "LIEUTENANT", 103: "NATURAL BORN WARRIOR",
        104: "NO WOUND INCAPACITATION", 109: "REGENERATION",
        110: "REMOTE PRESENCE", 111: "SIXTH SENSE",
        113: "SUPER-JUMP", 114: "SURPRISE ATTACK",
        116: "TERRAIN",
    }
    with pdf.open(source) as document:
        for page, heading in headings.items():
            pattern = rf"(?<![A-Za-z]){re.escape(heading)}\s+AUTOMATIC SKILL"
            assert re.search(pattern, document[page - 1].get_text(), re.I), page
        assert re.search(
            r"TOTAL REACTION\s+AUTOMATIC SKILL",
            document[115].get_text(), re.I,
        )


def test_checked_in_n5_collection_keeps_sensor_category_source_faithful() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    assert records["skill:sensor"]["facts"]["typeIds"] == ["short-skill"]
    sensor_declarations = [
        record
        for record in document["records"]
        if record["kind"] == "declaration-category"
        and any(link == {"entity": "skill", "id": "sensor"} for link in record.get("armyLinks", []))
    ]
    assert [
        (record["facts"]["typeId"], record["facts"]["order"]) for record in sensor_declarations
    ] == [("short-skill", 40)]


def test_n5_look_out_alerted_aro_is_dodge_only_and_conditional() -> None:
    root = Path(__file__).resolve().parents[1]
    document = load_curated_document(root / "data/curated/rules/n5-core-v5.3.json")
    records = {r["id"]: r for r in document["records"]}
    skill = records["skill:look-out"]
    facts = skill["facts"]
    assert facts["typeIds"] == ["aro"]
    assert skill["labelIds"] == ["no-roll"]
    assert skill["citations"][0] == {
        "sourceId": "n5-core-v5.3-pdf",
        "page": 81,
        "section": "Look Out!",
    }
    assert skill["citations"][1]["sourceId"] == "wiki-en-20260926-200832"
    assert skill["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:dodge"}
    ]
    assert "LoF to an enemy Trooper or Marker" in facts["requirements"][0]
    assert "[[skill:dodge]] (PH-3)" in facts["effects"][0]
    assert "other allied Troopers" in facts["effects"][0]
    assert "Reactive Player names" in facts["effects"][0]
    assert "same Order" in facts["effects"][0]
    assert "outside their LoF" in facts["effects"][0]
    assert "Zone of Control" in facts["effects"][0]
    assert "without changing position" in facts["effects"][0]
    assert "Face to Face Roll" in facts["effects"][1]
    assert "unopposed PH Roll" in facts["effects"][1]
    assert "not declared another ARO" in facts["restrictions"][0]
    assert "not a general permission" in facts["restrictions"][1]
    assert "neither LoF" in facts["clarifications"][0]
    assert "Face to Face" in facts["clarifications"][1]
    assert "without displacing it" in facts["clarifications"][1]
    assert records["skill:dodge"]["facts"]["typeIds"] == ["short-skill", "aro"]


def test_n5_look_out_aro_procedure_matches_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    provenance = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == provenance["corePdfSha256"]
    with pdf.open(source) as document:
        page = " ".join(document[80].get_text().split())
    clauses = (
        "LOOK OUT! ARO No Roll",
        "The user must have LoF to an enemy Trooper or Marker",
        "all other Troopers of the same player to modify their LoF",
        "without displacing",
        "considered as if the Troopers modifying their LoF had declared an ARO",
        "Normal or Face to Face Dodge (PH-3) Roll",
        "unless the alerted Trooper has been targeted by an Attack",
        "as long as they had not declared any other previous ARO",
        "Reactive Player must indicate which Troopers will modify their LoF",
        "All the other Troopers",
        "same Order as the Trooper using the Look Out! ARO",
        "outside his Line of Fire and Zone of Control",
    )
    for clause in clauses:
        assert clause in page, clause


def test_n5_reload_place_deployable_aro_rules_preserve_timing() -> None:
    root = Path(__file__).resolve().parents[1]
    document = load_curated_document(root / "data/curated/rules/n5-core-v5.3.json")
    records = {r["id"]: r for r in document["records"]}
    reload = records["skill:reload"]
    deploy = records["skill:place-deployable"]
    baggage = records["equipment:baggage"]
    for record in (reload, deploy):
        assert record["facts"]["typeIds"] == ["short-skill", "aro"]
        assert record["labelIds"] == ["attack"]
        assert any(c["sourceId"].startswith("wiki-") for c in record["citations"])

    assert reload["citations"][0] == {
        "sourceId": "n5-core-v5.3-pdf", "page": 83, "section": "Reload"
    }
    assert {"sourceId": "n5-core-v5.3-pdf", "page": 120,
            "section": "Baggage"} in reload["citations"]
    assert baggage["citations"][0] == {
        "sourceId": "n5-core-v5.3-pdf", "page": 120, "section": "Baggage"
    }
    assert "both be in non-Null States" in reload["facts"]["requirements"][0]
    assert "holder's Zone of Control" in reload["facts"]["requirements"][0]
    assert any("one Allied Trooper" in rule for rule in reload["facts"]["restrictions"])
    assert any("already deployed" in rule for rule in reload["facts"]["restrictions"])
    assert any("ordinary [[trait:aro|ARO]] eligibility" in line
               for line in reload["facts"]["clarifications"])
    assert any("separate automatic recovery timing" in line
               and "[[equipment:baggage|Baggage]]" in line
               for line in reload["facts"]["clarifications"])
    assert "States Phase" in baggage["facts"]["effects"][1]
    assert {"type": "enables-use-of", "recordId": "skill:reload"} in (
        baggage["relations"]
    )

    assert any(c["sourceId"] == "n5-core-v5.3-pdf" and c["page"] == 82
               for c in deploy["citations"])
    assert "LoF to the Active Trooper" in deploy["facts"]["requirements"][1]
    assert "Silhouette contact" in deploy["facts"]["effects"][1]
    assert "Conclusion of the Order" in deploy["facts"]["effects"][2]
    assert any("Perimeter" in note and "LoF requirement" in note
               for note in deploy["facts"]["clarifications"])
    assert any("only the placing Trooper" in note
               and "subsequent Orders" in note for note in deploy["facts"]["clarifications"])
    assert any("Trigger Area" in item for item in deploy["facts"]["restrictions"])
    assert any("occupies" in item and "N5 FAQ" in item
               for item in deploy["facts"]["restrictions"])


def test_n5_reload_place_deployable_aro_clauses_match_pinned_pdf() -> None:
    import hashlib

    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    source = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not source.exists():
        pytest.skip("Pinned N5.3 PDF unavailable")
    config = json.loads(
        (root / "config/validation/weaponry-family-clauses.json").read_text("utf8")
    )
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config["corePdfSha256"]
    with pdf.open(source) as document:
        deploy = " ".join(document[81].get_text().split())
        reload = " ".join(document[82].get_text().split())
        baggage = " ".join(document[119].get_text().split())
    for phrase in (
        "PLACE DEPLOYABLE SHORT SKILL / ARO",
        "In the Reactive Turn, LoF to the Active Trooper is required",
        "In the Reactive Turn, the Trooper must deploy it in Silhouette contact",
        "placed at the Conclusion of the Order",
        "enemy may only react against the Trooper that declares the Skill",
        "activated and can be used in subsequent Orders/AROs",
        "totally inside the Zone of Control",
        "path cannot be blocked by an impassable obstacle",
    ):
        assert phrase in deploy, phrase
    for phrase in (
        "RELOAD SHORT SKILL /ARO",
        "Trooper must be inside the Zone of Control",
        "Trooper with Baggage must be in a non-Null State",
        "Trooper is in Unloaded State",
        "single Allied Trooper per Order",
        "already deployed on the gaming table",
    ):
        assert phrase in reload, phrase
    for phrase in (
        "BAGGAGE AUTOMATIC EQUIPMENT",
        "An Allied Trooper in a Non-Null state",
        "perform the Reload Common Skill",
        "In the States Phase, each Allied Trooper",
        "automatically cancel their Unloaded State",
    ):
        assert phrase in baggage, phrase


def test_checked_in_n5_collection_keeps_new_common_skill_facts_source_faithful() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    look_out = records["skill:look-out"]["facts"]
    assert "LoF" in look_out["requirements"][0]
    assert "[[skill:dodge]] (PH-3)" in look_out["effects"][0]

    speedball = records["skill:request-speedball"]["facts"]
    assert speedball["requirements"] == ["The player must have two Speedball Tokens."]
    assert "two 55 mm Speedball Tokens" in speedball["effects"][0]
    assert "PH 15" in speedball["effects"][0]
    assert (
        "[[hacking-program:controlled-jump]]"
        in records["skill:request-speedball"]["summary"]
    )
    assert "FAQ restricts that Program to Troopers" in speedball["effects"][1]
    assert "Speedballs are Tokens" in speedball["effects"][1]
    assert {
        (citation["sourceId"], citation.get("page"))
        for citation in records["skill:request-speedball"]["citations"]
    } >= {
        ("n5-core-v5.3-pdf", 84),
        ("n5-faq-v0.1-en-pdf", 1),
    }

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


def test_esx03_msv3_marker_attack_is_not_global_revelation() -> None:
    document = load_curated_document(
        Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    )
    record = next(
        item for item in document["records"]
        if item["id"] == "equipment:multispectral-visor"
    )
    facts = record["facts"]
    assert [level["level"] for level in facts["levels"]] == [1, 2, 3]
    assert [len(level["effects"]) for level in facts["levels"]] == [4, 3, 6]
    level3 = facts["levels"][2]["effects"][5]
    assert "During the Active Turn" in level3
    assert "without first succeeding at [[skill:discover]]" in level3
    assert "Marker's [[skill:mimetism]] MOD still applies" in level3
    assert "usual [[state:camouflaged|Camouflaged State]] Cancellation" in level3

    explanation = facts["clarifications"][1]
    assert "merely declaring the attack does not reveal the Marker" in explanation
    assert "Ordinary [[state:camouflaged|Camouflaged State]] cancellation" in explanation
    assert "must make a [[rule:saving-rolls|Saving Roll]]" in explanation
    assert "neither a Reactive Turn attack permission" in explanation
    assert "The attack declaration alone is not a general" in facts["sourceNotes"][0]
    assert "rest of the army" in facts["sourceNotes"][0]
    assert "historical Spanish wording change remains unverified" in (
        facts["sourceNotes"][0]
    )
    assert {
        (citation["sourceId"], citation.get("page"))
        for citation in record["citations"]
    } >= {
        ("n5-core-v5.3-pdf", 125),
        ("n5-core-v5.3-pdf", 158),
        ("n5-core-v5.3-es-pdf", 131),
        ("n5-core-v5.3-es-pdf", 163),
    }


def test_esx03_msv3_source_disclosure_and_state_cancellation_are_scoped() -> None:
    pdf = pytest.importorskip("pymupdf")
    root = Path(__file__).resolve().parents[1]
    english = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    spanish = root / "data/pdf/rules/esp-n5-update-5-3.pdf"
    if not english.exists() or not spanish.exists():
        pytest.skip("Pinned current English/Spanish N5.3 PDFs unavailable")
    with pdf.open(english) as book:
        english_visor = " ".join(book[124].get_text().split())
        english_state = " ".join(book[157].get_text().split())
    with pdf.open(spanish) as book:
        spanish_visor = " ".join(book[130].get_text().split())
        spanish_state = " ".join(book[162].get_text().split())
    for fragment in (
        "in the Active Turn the user may perform a BS Attack",
        "without making a previous Discover Roll",
        "Cancellation clauses for Camouflaged State",
    ):
        assert fragment in english_visor, fragment
    for fragment in (
        "en Turno Activo permite efectuar un Ataque CD",
        "sin realizar una tirada de Descubrir previa",
        "Efectuar dicho Ataque no revela al objetivo ante el",
        "resto del ejército",
    ):
        assert fragment in spanish_visor, fragment
    assert "Camouflaged Marker is forced to make a Saving Roll" in english_state
    assert "deba realizar una Tirada de Salvación" in spanish_state


def test_checked_in_n5_collection_models_multispectral_visor_levels() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    facts = records["equipment:multispectral-visor"]["facts"]
    assert len(facts["effects"]) == 1
    levels = facts["levels"]
    assert [level["level"] for level in levels] == [1, 2, 3]
    assert [len(level["effects"]) for level in levels] == [4, 3, 6]
    assert "[[ammunition:smoke|Smoke Ammunition]]" in levels[0]["effects"][3]
    assert "[[state:camouflaged|Camouflage Marker]]" in levels[2]["effects"][5]


def test_rea042_dodge_arm_modifier_preserves_pdf_and_wiki_disagreement() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    doc = load_curated_document(path)
    dodge = next(r for r in doc["records"] if r["id"] == "skill:dodge")
    effects = " ".join(dodge["facts"]["effects"])
    clarifications = " ".join(dodge["facts"]["clarifications"])
    notes = dodge["facts"]["sourceNotes"]
    assert "Only Troopers whose Unit Profile lists this modifier" in effects
    assert "+3 [[attribute:arm|ARM]]" in effects
    assert "[[rule:saving-rolls|ARM Saving Roll]]" in effects
    assert "not conditional on failing the Dodge PH Roll" in effects
    assert "does not add +3 to Dodge PH" in clarifications
    assert "improve BTS" in clarifications
    assert "simultaneous Attacks" in clarifications
    assert len(notes) == 2
    assert "English p. 75" in notes[0] and "Spanish p. 75" in notes[0]
    assert "*siempre*" in notes[0]
    assert "archived English Wiki" in notes[1]
    assert "revision 4012" in notes[1]
    assert "failed Dodge PH Roll" in notes[1]
    assert "pending official clarification" in notes[1]
    references = {(c["sourceId"], c.get("page"), c.get("member")) for c in dodge["citations"]}
    assert ("n5-core-v5.3-pdf", 75, None) in references
    assert ("n5-core-v5.3-es-pdf", 75, None) in references
    assert ("wiki-en-20260926-200832", None, "Template_Modifiers-explained") in references
    assert (
        "wiki-es-20261009-211304", None, "es/Plantilla_Modifiers-explained"
    ) in references
    spanish = next(s for s in doc["sources"] if s["id"] == "wiki-es-20261009-211304")
    assert spanish["documentCount"] == 786
    assert len(spanish["sha256"]) == 64


def test_rea038_direct_vs_delegated_recovery_source_scope() -> None:
    source = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(source)
    records = {record["id"]: record for record in document["records"]}
    for skill_id, kit_id in (
        ("skill:doctor", "equipment:medikit"),
        ("skill:engineer", "equipment:gizmokit"),
    ):
        direct = records[skill_id]
        kit = records[kit_id]
        assert all("Allied" not in req for req in direct["facts"]["requirements"])
        assert any("Allied" in req for req in kit["facts"]["requirements"])
        assert "[[state:engaged|Engaged State]]" in " ".join(direct["facts"]["restrictions"])
        assert "one target" in " ".join(direct["facts"]["clarifications"])
        note = direct["facts"]["sourceNotes"][0]
        assert "blanket permission" in note
        assert "Engaged State" in note
        pdf_pages = {
            c["page"] for c in direct["citations"]
            if c["sourceId"] == "n5-core-v5.3-pdf"
        }
        assert pdf_pages >= {51}


def test_rea010_immunity_arm_bts_trait_baseline_and_printed_examples() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    records = {r["id"]: r for r in load_curated_document(path)["records"]}
    immunity = records["skill:immunity"]
    baseline = next(x for x in immunity["facts"]["effects"] if "non-Comms" in x)
    assert "using the matching Saving Roll Attribute" in baseline
    for ref in (
        "[[trait:state|States]]", "[[trait:continuous-damage|Continuous Damage]]",
        "[[trait:arm-0|ARM = 0]]", "[[trait:bts-0|BTS = 0]]",
        "[[ammunition:normal|Normal]]",
    ):
        assert ref in baseline
    assert "neither protection removes the ordinary Saving Roll" in baseline
    monofilament = immunity["facts"]["clarifications"][0]
    assert "[[weapon-property:monofilament|Monofilament]]" in monofilament
    assert "[[trait:arm-0|ARM = 0]]" in monofilament
    assert "[[trait:state|State: Dead]]" in monofilament
    assert "full ARM" in monofilament
    assert "two ARM Saving Rolls" in monofilament
    assert "[[skill:immunity|Immunity (Critical)]]" in monofilament
    flash = immunity["facts"]["clarifications"][1]
    assert "[[weapon:flash-pulse|Flash Pulse]]" in flash
    assert "Saving Roll stays BTS, not ARM" in flash
    assert "[[trait:non-lethal|Non-Lethal]]" in flash
    assert "[[state:stunned|Stunned]] only on a failed BTS roll" in flash
    assert immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"][0][
        "evidence"
    ] == "explicit-pinned-wiki-example"
    assert len(immunity["facts"]["immunityInteraction"]["reviewedCombinedCases"]) == 6
    cited = {(c["sourceId"], c.get("page")) for c in immunity["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 95), ("n5-core-v5.3-pdf", 96),
        ("n5-core-v5.3-es-pdf", 99),
    }


def test_rea009_positive_before_negative_recovery_is_canonical_and_crosslinked() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    records = {r["id"]: r for r in load_curated_document(path)["records"]}
    sequence = records["rule:order-expenditure-sequence"]
    engineer = records["skill:engineer"]
    doctor = records["skill:doctor"]
    imm_a = records["state:immobilized-a"]
    para = records["ammunition:para"]
    clauses = " ".join(sequence["facts"]["clarifications"])
    assert "**Positive-before-negative resolution:**" in clauses
    assert "first resolve the beneficial removal/cancellation" in clauses
    assert "not which action was declared earlier" in clauses
    example = next(x for x in sequence["facts"]["clarifications"] if "Riotstopper" in x)
    for phrase in (
        "**[[skill:engineer|Engineer]] versus [[ammunition:para|PARA]] example:**",
        "Resolve the [[skill:engineer|Engineer]]'s [[attribute:wip|WIP]] Roll first",
        "original [[state:immobilized-a|IMM-A]] is canceled",
        "Riotstopper's PH-6 [[rule:saving-rolls|Saving Roll]]",
        "A failed Saving Roll inflicts a **new** [[state:immobilized-a|IMM-A]]",
        "passed Saving Roll leaves the Trooper free of [[state:immobilized-a|IMM-A]]",
        "WIP Roll fails, the original [[state:immobilized-a|IMM-A]] is not removed",
        "does **not** grant protection from a new hit",
    ):
        assert phrase in example
    for rec in (engineer, doctor, imm_a):
        assert "[[rule:order-expenditure-sequence|Order Expenditure Sequence]]" in " ".join(
            rec["facts"].get("restrictions", []) + rec["facts"].get("clarifications", [])
        )
    assert "[[skill:engineer|Engineer]]" in imm_a["facts"]["clarifications"][0]
    assert "[[ammunition:para|PARA Ammunition]]" in imm_a["facts"]["clarifications"][0]
    assert para["facts"]["ammunitionResolution"]["stateEffects"] == [
        {"stateId": "state:immobilized-a", "condition": "failed-saving-roll"}
    ]
    for rid in ("rule:order-expenditure-sequence", "state:immobilized-a"):
        citations = {(c["sourceId"], c.get("page")) for c in records[rid]["citations"]}
        assert citations >= {
            ("n5-core-v5.3-pdf", 15),
            ("n5-core-v5.3-es-pdf", 15),
        }
    assert not any(
        rel["type"] == "causes-state" for rel in sequence.get("relations", [])
    )


def test_rea007_speedball_ph15_excludes_only_controlled_jump_mods() -> None:
    root = Path(__file__).parents[1] / "data" / "curated" / "rules"
    core = load_curated_document(root / "n5-core-v5.3.json")
    hacking = load_curated_document(root / "n5-hacking-programs-v5.3.json")
    speedball = next(r for r in core["records"] if r["id"] == "skill:request-speedball")
    program = next(r for r in hacking["records"] if r["id"] == "hacking-program:controlled-jump")
    effects = " ".join(speedball["facts"]["effects"])
    assert "two 55 mm Speedball Tokens" in effects
    assert "PH 15 Roll for each token" in effects
    assert "FAQ restricts that Program to Troopers" in effects
    assert "Speedballs are Tokens" in effects
    assert len(speedball["facts"]["clarifications"]) == 1
    example = speedball["facts"]["clarifications"][0]
    assert "**Speedball PH 15 versus" in example
    assert "[[hacking-program:controlled-jump|Controlled Jump]]" in example
    assert "Each Token still uses its own PH 15 Roll" in example
    assert "PH 18" in example and "PH 12" in example
    assert "not allied or enemy Troopers" in example
    assert "not every other possible modifier to placement" in example
    assert "[[hacking-program:controlled-jump|Controlled Jump]]'s +3/-3" in example
    assert "?s" not in example
    assert speedball["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:combat-jump"}
    ]
    assert any("does not affect Speedball Tokens" in x for x in program["facts"]["restrictions"])
    for record in (speedball, program):
        assert any(
            c["sourceId"] == "n5-faq-v0.1-en-pdf" and c["page"] == 1
            for c in record["citations"]
        )


def test_rea006_controlled_jump_sourced_timing_cancellation_and_tokens() -> None:
    root = Path(__file__).parents[1] / "data" / "curated" / "rules"
    doc = load_curated_document(root / "n5-hacking-programs-v5.3.json")
    program = next(r for r in doc["records"] if r["id"] == "hacking-program:controlled-jump")
    effects = " ".join(program["facts"]["effects"])
    restrictions = " ".join(program["facts"]["restrictions"])
    assert "as soon as it is declared" in effects
    assert "before the Resolution step" in effects
    assert "same [[skill:combat-jump]] PH Roll" in effects
    assert "ARO is optional" in restrictions
    assert "their Programs' effects cancel" in restrictions
    assert "independent MODs" in restrictions
    assert "Speedball Tokens" in restrictions
    assert "one Controlled Jump Program active" in restrictions
    aro, opposing, tokens = program["facts"]["clarifications"]
    assert "**Reactive landing example:**" in aro
    assert "**same PH landing Roll**" in aro
    assert "before Resolution" in aro
    assert "[[trait:aro|ARO]]" in aro
    assert "[[rule:hacking-area|Hacking Area]]" in aro
    assert "**Both Programs active in Firefight:**" in opposing
    assert "**neither Program gives +3 or -3**" in opposing
    assert "not a general rule" in opposing
    assert "**Designated Landing Area**" in opposing
    assert "that scenario MOD is not canceled" in opposing
    assert "**Troopers versus Speedball Tokens:**" in tokens
    assert "Troopers without the Hackable Characteristic" in tokens
    assert "[[skill:request-speedball|Speedball]]" in tokens
    assert "expressly excludes these Tokens" in tokens
    cited = {(c["sourceId"], c.get("page")) for c in program["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 59),
        ("n5-core-v5.3-pdf", 155),
        ("n5-core-v5.3-es-pdf", 61),
        ("n5-faq-v0.1-en-pdf", 1),
    }
    assert any(s["id"] == "n5-core-v5.3-es-pdf" for s in doc["sources"])
    assert program["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:combat-jump"}
    ]
    core = load_curated_document(root / "n5-core-v5.3.json")
    landing = next(r for r in core["records"] if r["id"] == "rule:scenario:designated-landing-area")
    assert "cumulative with MODs provided by other rules" in " ".join(landing["facts"]["effects"])


def test_rea005_bs_weapon_wip_named_attack_skill_exclusions() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    records = {r["id"]: r for r in load_curated_document(path)["records"]}
    record = records["trait:bs-weapon-wip"]
    assert "BS Attack (Shock)" in record["summary"]
    assert "BS Attack (Guided)" in record["summary"]
    assert "not [[ammunition:shock|Shock Ammunition]] in general" in record["summary"]
    ordinary, shock, guided = record["facts"]["clarifications"]
    assert "[[weapon:flash-pulse|Flash Pulse]]" in ordinary
    assert "rolling the attacker's WIP instead of BS" in ordinary
    assert "[[skill:discover|Discover]]" in ordinary
    assert "[[skill:bs-attack|BS Attack (Shock)]]" in shock
    assert "**not** prohibit" in shock
    assert "[[ammunition:shock|Shock Ammunition]]" in shock
    assert "[[state:targeted|Targeted]]" in guided
    assert "[[skill:bs-attack|BS Attack (Guided)]]" in guided
    assert "without Line of Fire" in guided
    assert "standard [[skill:bs-attack|BS Attack]]" in guided
    assert record["relations"] == [
        {"type": "modifies-rolls-for", "recordId": "skill:bs-attack"}
    ]
    cited = {(c["sourceId"], c.get("page")) for c in record["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 175),
        ("n5-core-v5.3-pdf", 39),
        ("n5-core-v5.3-es-pdf", 39),
    }


def test_rea004_continuous_damage_critical_extra_roll_does_not_chain() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    records = {r["id"]: r for r in load_curated_document(path)["records"]}
    continuous = records["trait:continuous-damage"]
    immunity = records["skill:immunity"]
    assert "failing it does not start another chain" in continuous["summary"]
    examples = continuous["facts"]["clarifications"]
    assert len(examples) == 2
    hit, immune = examples
    assert "ordinary hit Roll and one additional Critical Roll" in hit
    assert "one succeeds or the target enters [[state:dead|Dead State]]" in hit
    assert "If only the additional Critical Roll fails" in hit
    assert "does not start a Continuous Damage chain" in hit
    assert "only the failed ordinary-hit branch triggers repetition" in hit
    assert "[[skill:immunity|Immunity (Trait: Continuous Damage)]]" in immune
    assert "ordinary Saving Roll or the additional Critical Saving Roll" in immune
    assert "covered non-Comms Attack" in immune
    assert "[[skill:immunity|Immunity (Critical)]]" in immune
    assert "matching [[skill:immunity|Immunity]] printed" in immune
    assert "Trait's repeating-Saving-Roll effect" in immune
    assert "target's Unit Profile" in immune
    assert "?s" not in immune
    effects = " ".join(immunity["facts"]["effects"])
    assert "Immunity (Trait) ignores" in effects
    assert "Immunity (Critical) removes the additional Saving Roll" in effects
    cited = {(c["sourceId"], c.get("page")) for c in continuous["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 175),
        ("n5-core-v5.3-pdf", 95),
        ("n5-core-v5.3-es-pdf", 182),
        ("n5-core-v5.3-es-pdf", 99),
    }
    assert all(c["type"] != "causes-state" for c in continuous.get("relations", []))


def test_rea003_intuitive_attack_examples_keep_single_wip_and_deployable_branch() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    records = {r["id"]: r for r in load_curated_document(path)["records"]}
    record = records["skill:intuitive-attack"]
    facts = record["facts"]
    assert "one unmodified [[attribute:wip|WIP]] Roll" in " ".join(facts["effects"])
    assert "Burst for this Skill is always 1" in " ".join(facts["restrictions"])
    examples = facts["clarifications"]
    assert len(examples) == 3
    assert "not a preliminary check followed by a second" in examples[0]
    assert "[[rule:saving-rolls|Saving Roll]]" in examples[0]
    assert "next Active Turn" in examples[0]
    assert "[[rule:face-to-face-rolls|Face to Face Roll]]" in examples[1]
    assert "Another Trooper affected by the same Template" in examples[1]
    assert "Critical only against the declared Main Target" in examples[1]
    assert "non-Critical successful Roll" in examples[1]
    assert "[[skill:place-deployable|Place Deployable]]" in examples[2]
    assert "[[trait:disposable-x|Disposable]] loses one use" in examples[2]
    assert "specific [[skill:intuitive-attack|Intuitive Attack]] requirement" in examples[2]
    assert "other [[trait:deployable|Deployable]] placement restrictions" in examples[2]
    assert records["trait:intuitive-attack"]["relations"] == [
        {"type": "enables-use-of", "recordId": "skill:intuitive-attack"}
    ]
    assert {(c["sourceId"], c.get("page")) for c in record["citations"]} >= {
        ("n5-core-v5.3-pdf", 49),
        ("n5-core-v5.3-es-pdf", 48),
    }


def test_rea002_doctor_ordinary_gate_and_scoped_exceptions() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}
    doctor = records["skill:doctor"]
    facts = doctor["facts"]
    requirements = " ".join(facts["requirements"])
    effects = " ".join(facts["effects"])
    assert "Silhouette contact" in requirements
    assert "must have VITA" in requirements
    assert "[[state:unconscious|Unconscious State]]" in requirements
    assert "[[state:dead|Dead State]]" in effects
    assert "Doctor (2W)" in effects
    assert "Doctor (ReRoll WIP=X)" in effects
    assert "Command Token reroll" in effects
    assert "Null State" in " ".join(facts["restrictions"])
    assert len(facts["clarifications"]) >= 7
    examples = facts["clarifications"][-4:]
    assert "not in [[state:unconscious|Unconscious]] cannot" in examples[0]
    assert "failure puts the target in [[state:dead|Dead State]]" in examples[0]
    assert "in Silhouette contact" in examples[1]
    assert "[[state:stunned|Stunned]]" in examples[1]
    assert "[[skill:engineer|Engineer]]" in examples[1]
    assert "with both NWI and Doctor" in examples[2]
    assert "self" in examples[2]
    assert "removes one Wound and the NWI Token" in examples[2]
    assert "STR Trooper" in examples[3]
    assert "despite lacking VITA" in examples[3]
    assert "remaining STR Wounds" in examples[3]
    cited = {c["page"] for c in doctor["citations"] if c["sourceId"] == "n5-core-v5.3-pdf"}
    assert cited >= {90, 104, 116, 170}
    assert "blanket permission" in facts["sourceNotes"][0]
    assert "[[skill:doctor]]" in " ".join(
        records["skill:no-wound-incapacitation"]["facts"]["effects"]
    )
    assert "[[skill:doctor]]" in " ".join(records["skill:technorganic"]["facts"]["effects"])


def test_rea001_engineer_target_eligibility_and_repair_vs_cancel_examples() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    records = {r["id"]: r for r in load_curated_document(path)["records"]}
    engineer = records["skill:engineer"]
    facts = engineer["facts"]
    assert "STR is required to remove Wounds" in " ".join(facts["requirements"])
    assert "not to cancel conditions" in " ".join(facts["requirements"])
    assert "failed condition-cancellation Roll has no negative consequence" in (
        " ".join(facts["effects"])
    )
    assert "On failure, the target receives a Wound" in " ".join(facts["effects"])
    example = next(part for part in facts["clarifications"] if "VITA and STR example" in part)
    assert "allied VITA Trooper" in example
    assert "[[state:targeted|Targeted State]]" in example
    assert "no STR to repair" in example
    assert "failure does not inflict a Wound" in example
    exception = next(part for part in facts["clarifications"] if "Stunned]] exception" in part)
    assert "[[skill:doctor|Doctor]]" in exception
    assert "for a VITA target" in exception
    assert "Engineer for a STR target" in exception
    assert "[[state:immobilized-a|IMM-A]]" in exception
    assert all("Allied" not in item for item in facts["requirements"])
    pages = {
        c["page"] for c in engineer["citations"]
        if c["sourceId"] == "n5-core-v5.3-pdf"
    }
    assert pages >= {91, 170, 171}


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
        {"type": "prevents-state-entry", "recordId": "state:prone"},
    ]
    assert records["equipment:ai-motorcycle"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "equipment:motorcycle"},
        {"type": "uses-effects-of", "recordId": "rule:peripheral-type:synchronized"},
        {"type": "uses-effects-of", "recordId": "skill:transmutation"},
    ]
    assert records["equipment:escape-system"]["relations"] == [
        {"type": "uses-effects-of", "recordId": "skill:transmutation"}
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


def test_checked_in_n5_collection_models_fireteam_general_reference() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = load_curated_document(path)
    records = {record["id"]: record for record in document["records"]}

    general = records["rule:fireteam-general"]
    assert general["facts"]["memberLimits"] == {"min": 2, "max": 5}
    assert general["facts"]["types"] == [
        {"type": "DUO", "min": 2, "max": 2},
        {"type": "HARIS", "min": 3, "max": 3},
        {"type": "CORE", "min": 3, "max": 5},
    ]
    assert {item["term"]: item["provenance"] for item in general["facts"]["terminology"]} == {
        "Linkable": "historical-official",
        "Pure Fireteam": "community-historical",
    }

    levels = records["rule:fireteam-level-bonuses"]["facts"]
    assert levels["cumulative"] is True
    assert [item["level"] for item in levels["levels"]] == [1, 2, 3, 4, 5]
    assert levels["levels"][1]["bonuses"] == [
        "[[skill:bs-attack]] ([[rule:special-dice|+1 SD]])"
    ]
    assert levels["levels"][4]["bonuses"] == ["[[skill:sixth-sense]]"]


def test_rea041_curated_fireteam_and_special_dice_keep_source_conflict() -> None:
    source = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    records = {record["id"]: record for record in load_curated_document(source)["records"]}
    special_dice = records["rule:special-dice"]
    fireteam = records["rule:fireteam-level-bonuses"]
    assert "English N5.3 pp. 75/136" in special_dice["facts"]["sourceNotes"][0]
    assert "Spanish N5.3 p. 140" in special_dice["facts"]["sourceNotes"][1]
    assert "Unresolved Spanish Fireteam reminder" in fireteam["facts"]["sourceNotes"][0]
    assert "pending an official correction" in fireteam["facts"]["sourceNotes"][0]
    for record in (special_dice, fireteam):
        cited_pages = {
            citation["page"] for citation in record["citations"]
            if citation["sourceId"] == "n5-core-v5.3-es-pdf"
        }
        assert cited_pages >= {75, 140}


def test_rea034_level_three_morat_example_keeps_level_four_bonus_separate() -> None:
    source = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    records = {record["id"]: record for record in load_curated_document(source)["records"]}
    fireteam = records["rule:fireteam-level-bonuses"]
    facts = fireteam["facts"]
    assert "three Morat Vanguard" in facts["basis"]
    assert "one Kyosot and one Zabuk" in facts["basis"]
    assert "**Level 3**" in facts["basis"]
    assert "[[rule:special-dice|+1 SD]]" in facts["basis"]
    assert "Level 4 **+1 BS**" in facts["basis"]
    assert facts["levels"][2]["requirement"] == "At least 3 Troopers belong to the same Unit."
    assert facts["levels"][2]["bonuses"] == ["+3 [[skill:discover]]", "+1 [[skill:dodge]]"]
    assert facts["levels"][3]["requirement"] == "At least 4 Troopers belong to the same Unit."
    assert facts["levels"][3]["bonuses"] == ["+1 BS"]
    assert len(facts["sourceNotes"]) == 2
    note = facts["sourceNotes"][1]
    for phrase in ("English N5.3 p. 138", "Spanish N5.3 p. 142", "**Level 3**",
                   "**+1 BS/CD Attack**", "**Level 4**", "pending an official correction"):
        assert phrase in note
    cited = {(c["sourceId"], c.get("page")) for c in fireteam["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 135), ("n5-core-v5.3-pdf", 136),
        ("n5-core-v5.3-pdf", 138), ("n5-core-v5.3-es-pdf", 139),
        ("n5-core-v5.3-es-pdf", 140), ("n5-core-v5.3-es-pdf", 142),
    }


def test_scenario_collection_membership_must_cover_local_definitions(tmp_path: Path) -> None:
    source = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    document["scenarioCollection"]["members"].pop()
    path = tmp_path / "missing-scenario-membership.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="missing definitions"):
        load_curated_document(path)


@pytest.mark.parametrize(
    ("variant_refs", "message"),
    [
        ({"unlinked-weapon": ["ammunition:ap"]}, "requires linked weapon slugs"),
        ({"ap-mine": ["ammunition:ap", "ammunition:ap"]}, "duplicate variant"),
        ({"ap-mine": ["invalid"]}, "invalid variant rule target"),
    ],
)
def test_weapon_variant_rule_references_validate_membership_and_shape(
    tmp_path: Path, variant_refs: dict, message: str,
) -> None:
    document = json.loads(
        (Path(__file__).resolve().parents[1] / "data/curated/rules/n5-core-v5.3.json")
        .read_text(encoding="utf-8")
    )
    record = next(record for record in document["records"] if record["id"] == "weapon:mines")
    record["facts"]["variantRuleReferences"] = variant_refs
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_curated_document(path)


def test_source_mode_qualifier_is_weapon_only_and_excludes_source_variant(
    tmp_path: Path,
) -> None:
    document = valid_document()
    record = document["records"][0]
    record.update(
        id="weapon:kobra-pistol-cc-review",
        kind="weapon",
        armyLinks=[{"entity": "weapon", "id": 221}],
        variantSemantics={"inheritance": "source", "sourceMode": "CC Mode"},
    )
    path = tmp_path / "mode.json"

    def check() -> None:
        path.write_text(json.dumps(document), encoding="utf-8")
        load_curated_document(path)

    check()
    record["variantSemantics"]["sourceMode"] = "  "
    with pytest.raises(ValueError, match="sourceMode.*non-empty"):
        check()
    record["variantSemantics"]["sourceMode"] = "CC Mode"
    record["variantSemantics"]["sourceVariant"] = {"kind": "named", "label": "CC"}
    with pytest.raises(ValueError, match="mutually exclusive"):
        check()
    del record["variantSemantics"]["sourceVariant"]
    record["kind"] = "skill"
    record["id"] = "skill:kobra-pistol-cc-review"
    record["armyLinks"] = [{"entity": "skill", "id": 221}]
    with pytest.raises(ValueError, match="sourceMode requires source-specific Weapon"):
        check()
    record["kind"] = "weapon"
    record["id"] = "weapon:kobra-pistol-cc-review"
    record["armyLinks"] = [{"entity": "weapon", "id": 221}]
    record["variantSemantics"]["inheritance"] = "family"
    with pytest.raises(ValueError, match="sourceMode requires source-specific Weapon"):
        check()
    record["variantSemantics"]["inheritance"] = "source"
    record["armyLinks"] = [{"entity": "weapon", "id": "kobra-pistol"}]
    with pytest.raises(ValueError, match="numeric Army source id"):
        check()


def test_curated_long_rule_summaries_have_readable_paragraphs() -> None:
    """Prevent long, unbroken rules cards across all maintained collections."""
    root = Path(__file__).resolve().parents[1] / "data" / "curated"
    reviewed = 0
    for _, document in load_curated_directory(root):
        for record in document.get("records", []):
            summary = record.get("summary", "")
            if len(summary) < 350:
                continue
            reviewed += 1
            paragraphs = re.split(r"\n\s*\n", summary)
            assert len(paragraphs) >= 2, record["id"]
            assert max(map(len, paragraphs)) <= 350, record["id"]
    assert reviewed > 0


@pytest.mark.parametrize(
    "invalid",
    [
        {"defenseModifier": {"operation": "double", "attributes": ["ARM"]}},
        {"defenseModifier": {"operation": "halve", "attributes": ["WIP"]}},
        {"defenseModifier": {"operation": "halve", "attributes": ["ARM", "ARM"]}},
        {"defenseModifier": {"operation": "halve", "attributes": [{}]}},
        {"rollsPerHit": 0},
        {"rollsPerHit": True},
        {"criticalAdditionalSavingRolls": 0},
        {"criticalAdditionalSavingRolls": 2},
        {"criticalAdditionalSavingRolls": True},
        {"criticalAdditionalSavingRolls": "1"},
        {"savingRoll": {"attribute": "ARM", "modifier": -6, "missingAttribute": "no-effect"}},
        {"savingRoll": {"attribute": "PH", "modifier": True, "missingAttribute": "no-effect"}},
        {"savingRoll": {"attribute": "PH", "modifier": -6, "missingAttribute": "roll"}},
        {"savingRoll": {"attribute": "PH", "modifier": 0, "missingAttribute": "no-effect"}},
        {"woundsPerFailedSave": {"hit": 2}},
        {"woundsPerFailedSave": {"hit": 2, "criticalAdditionalRoll": True}},
        {"woundsPerFailedSave": {"hit": 0, "criticalAdditionalRoll": 1}},
        {"stateEffects": []},
        {"stateEffects": [{"stateId": "skill:reset", "condition": "failed-saving-roll"}]},
        {"stateEffects": [{"stateId": "state:isolated", "condition": "hit"}]},
        {
            "stateEffects": [
                {"stateId": "state:isolated", "condition": "failed-saving-roll"},
                {"stateId": "state:isolated", "condition": "failed-saving-roll"},
            ]
        },
        {
            "stateEffects": [
                {
                    "stateId": "state:immobilized-b",
                    "condition": "failed-saving-roll",
                    "targetTypes": ["HI", "WIP"],
                }
            ]
        },
        {"gutsEffect": {"condition": "hit", "result": "automatic-failure",
                        "exception": "courage-or-equivalent"}},
        {"gutsEffect": {"condition": "failed-saving-roll", "result": "no-guts-roll",
                        "exception": "courage-or-equivalent"}},
        {"stateEffects": [{"stateId": "state:dead", "condition": "failed-saving-roll",
                           "targetAttribute": {"name": "VITA", "equals": 2},
                           "application": "bypass-unconscious"}]},
        {"stateEffects": [{"stateId": "state:stunned", "condition": "failed-saving-roll",
                           "targetAttribute": {"name": "VITA", "equals": 1},
                           "application": "bypass-unconscious"}]},
        {"stateEffects": [{"stateId": "state:dead", "condition": "failed-saving-roll",
                           "targetAttribute": {"name": "VITA", "equals": True},
                           "application": "bypass-unconscious"}]},
        {"unreviewedOperation": "auto-resolve"},
    ],
)
def test_ammunition_resolution_rejects_invalid_typed_facts(
    tmp_path: Path, invalid: dict,
) -> None:
    document = valid_document()
    document["records"].append({
        "id": "ammunition:pilot",
        "kind": "ammunition",
        "name": "Pilot ammunition",
        "summary": "A typed fact validation fixture.",
        "facts": {"ammunitionResolution": invalid},
        "scope": {"game": "N5", "seasons": ["current"]},
        "citations": [{"sourceId": "n5-core-v5.3", "page": 64}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-10-09"},
    })
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="ammunitionResolution"):
        load_curated_document(path)


def test_ammunition_resolution_is_owned_only_by_ammunition(tmp_path: Path) -> None:
    document = valid_document()
    document["records"][0]["facts"]["ammunitionResolution"] = {"rollsPerHit": 2}
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="only Ammunition"):
        load_curated_document(path)


@pytest.mark.parametrize("invalid", [
    {},
    {"visibility": "low", "template": "circular", "height": "infinite",
     "expires": "start-of-states-phase", "multispectralVisor": "blocked"},
    {"visibility": "zero", "template": "circular", "height": "infinite",
     "expires": "start-of-states-phase", "multispectralVisor": "ignores-zone"},
    {"visibility": "zero", "template": "circular", "height": "infinite",
     "expires": "start-of-states-phase", "multispectralVisor": []},
    {"visibility": "zero", "template": "circular", "height": "infinite",
     "expires": "start-of-states-phase", "multispectralVisor": "blocked",
     "unreviewed": True},
])
def test_ammunition_visibility_zone_rejects_unreviewed_facts(
    tmp_path: Path, invalid: dict,
) -> None:
    document = valid_document()
    document["records"].append({
        "id": "ammunition:pilot", "kind": "ammunition", "name": "Pilot",
        "summary": "A visibility-zone fixture.",
        "facts": {"visibilityZone": invalid},
        "scope": {"game": "N5", "seasons": ["current"]},
        "citations": [{"sourceId": "n5-core-v5.3", "page": 64}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-10-09"},
    })
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="visibilityZone"):
        load_curated_document(path)


@pytest.mark.parametrize("kind", ["skill", "ammunition"])
def test_ammunition_visibility_zone_cannot_mix_domains_or_rolls(
    tmp_path: Path, kind: str,
) -> None:
    document = valid_document()
    record = {
        "id": f"{kind}:pilot", "kind": kind, "name": "Pilot",
        "summary": "A visibility-zone fixture.",
        "facts": {"visibilityZone": {
            "visibility": "zero", "template": "circular", "height": "infinite",
            "expires": "start-of-states-phase", "multispectralVisor": "blocked",
        }},
        "scope": {"game": "N5", "seasons": ["current"]},
        "citations": [{"sourceId": "n5-core-v5.3", "page": 64}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-10-09"},
    }
    if kind == "ammunition":
        record["facts"]["ammunitionResolution"] = {"rollsPerHit": 1}
    document["records"].append(record)
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="visibilityZone"):
        load_curated_document(path)


@pytest.mark.parametrize("case", ["missing", "extra", "wrong"])
def test_ammunition_state_graph_must_match_conditional_effect_facts(
    tmp_path: Path, case: str
) -> None:
    document = valid_document()
    record = {
        "id": "ammunition:pilot",
        "kind": "ammunition",
        "name": "Pilot ammunition",
        "summary": "A typed State-effect graph fixture.",
        "facts": {
            "ammunitionResolution": {
                "stateEffects": [
                    {"stateId": "state:isolated", "condition": "failed-saving-roll"}
                ]
            }
        },
        "relations": [{"type": "causes-state", "recordId": "state:isolated"}],
        "scope": {"game": "N5", "seasons": ["current"]},
        "citations": [{"sourceId": "n5-core-v5.3", "page": 64}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-10-09"},
    }
    document["records"].append(record)
    path = tmp_path / "state-graph.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert load_curated_document(path)
    if case == "missing":
        record["relations"] = []
    elif case == "extra":
        record["relations"].append(
            {"type": "causes-state", "recordId": "state:immobilized-b"}
        )
    else:
        record["relations"][0]["recordId"] = "state:stunned"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="causes-state relations must match"):
        load_curated_document(path)


def test_critical_roll_fact_is_single_and_only_on_saving_roll_ammunition() -> None:
    """One Critical adds one roll; it does not multiply with DA/EXP rolls."""
    path = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    records = {item["id"]: item for item in load_curated_document(path)["records"]}
    per_hit = {
        "normal": 1, "da": 2, "em": 2, "exp": 3,
        "para": 1, "shock": 1, "stun": 1,
    }
    for slug in ("normal", "ap", "da", "em", "exp", "para", "shock", "stun", "t2"):
        record = records[f"ammunition:{slug}"]
        facts = record["facts"]["ammunitionResolution"]
        assert facts["criticalAdditionalSavingRolls"] == 1
        if slug in per_hit:
            assert facts["rollsPerHit"] == per_hit[slug]
        assert record["citations"], slug
    for slug in ("smoke", "eclipse"):
        assert "ammunitionResolution" not in records[f"ammunition:{slug}"]["facts"]
    # T2's additional Critical roll inflicts 1 Wound, not its normal 2.
    assert records["ammunition:t2"]["facts"]["ammunitionResolution"][
        "woundsPerFailedSave"
    ] == {"hit": 2, "criticalAdditionalRoll": 1}


def test_current_ammunition_state_relations_preserve_conditional_effects() -> None:
    path = Path(__file__).parents[1] / "data/curated/rules/n5-core-v5.3.json"
    records = {item["id"]: item for item in load_curated_document(path)["records"]}
    expected = {
        "ammunition:em": {"state:isolated", "state:immobilized-b"},
        "ammunition:para": {"state:immobilized-a"},
        "ammunition:shock": {"state:dead"},
        "ammunition:stun": {"state:stunned"},
    }
    for record_id, state_ids in expected.items():
        record = records[record_id]
        assert {relation["recordId"] for relation in record["relations"]} == state_ids
        fact_states = record["facts"]["ammunitionResolution"]["stateEffects"]
        assert {effect["stateId"] for effect in fact_states} == state_ids
    for record_id in (
        "ammunition:normal",
        "ammunition:ap",
        "ammunition:da",
        "ammunition:exp",
        "ammunition:t2",
        "ammunition:smoke",
        "ammunition:eclipse",
    ):
        assert not any(
            relation["type"] == "causes-state"
            for relation in records[record_id].get("relations", [])
        )
    conditional = records["ammunition:em"]["facts"]["ammunitionResolution"][
        "stateEffects"
    ]
    assert conditional[1]["targetTypes"] == ["HI", "TAG", "REM", "VH"]
    shock = records["ammunition:shock"]["facts"]["ammunitionResolution"][
        "stateEffects"
    ]
    assert shock[0]["targetAttribute"] == {"name": "VITA", "equals": 1}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda f: f["coveredAmmunition"].update(treatAs="ammunition:ap"),
         "covered Ammunition"),
        (lambda f: f["coveredAmmunition"]["ignore"].pop(),
         "covered Ammunition"),
        (lambda f: f["criticalAgainstCoveredAmmunition"].update(
            additionalSavingRolls=2), "Critical exception"),
        (lambda f: f["criticalAgainstCoveredAmmunition"].update(
            unless="none"), "Critical exception"),
        (lambda f: f["exceptions"].update(commsAttacks="always-immune"),
         "Immunity exceptions"),
        (lambda f: f["exceptions"]["notNegatedByImmunity"].pop(),
         "Immunity exceptions"),
        (lambda f: f["reviewedSavingRollCases"][0]["when"].update(
            immunity="ARM"), "Plasma Combined Saving Roll example"),
        (lambda f: f["reviewedSavingRollCases"][0]["when"].update(
            ammunitionId="ammunition:ap"), "Plasma Combined Saving Roll example"),
        (lambda f: f["reviewedSavingRollCases"][0]["savingRolls"][1].update(
            attribute="ARM"), "Plasma Combined Saving Roll example"),
        (lambda f: f["reviewedSavingRollCases"][0].update(
            result="immunity-removes-bts"), "Plasma Combined Saving Roll example"),
        (lambda f: f["reviewedSavingRollCases"][0].update(
            evidence="derived-from-pinned-general-rules"),
            "Plasma Combined Saving Roll example"),
        (lambda f: f["reviewedSavingRollCases"].append(
            deepcopy(f["reviewedSavingRollCases"][0])),
            "Plasma Combined Saving Roll example"),
        (lambda f: f["reviewedCombinedCases"][3]["when"].update(
            weaponId="weapon:multi-pistol"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][3]["when"].update(
            attackClass="comms"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][3]["when"].update(
            savingAttribute="ARM"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][3].update(
            sourceAmmunitionId=10), "Silenced Pistol applicability"),
        (lambda f: f["reviewedCombinedCases"][3]["components"].reverse(),
            "Silenced Pistol applicability"),
        (lambda f: f["reviewedCombinedCases"][3]["withoutImmunity"].update(
            savingAttribute="ARM/2"), "Silenced Pistol applicability"),
        (lambda f: f["reviewedCombinedCases"][3]["withoutImmunity"].update(
            criticalRolls=3), "source hit/Critical Saving Roll counts"),
        (lambda f: f["reviewedCombinedCases"][3]["withImmunity"].update(
            savingAttribute="ARM"), "covered-attack result"),
        (lambda f: f["reviewedCombinedCases"][3]["withImmunity"].update(
            remainingComponents=["ammunition:normal"]), "covered-attack result"),
        (lambda f: f["reviewedCombinedCases"][4]["when"].update(
            weaponId="weapon:ap-t2-cc-weapon-sf"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][4]["when"].update(
            attackClass="comms"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][4]["when"].update(
            savingAttribute="BTS"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][4].update(
            sourceAmmunitionId=10), "CC applicability"),
        (lambda f: f["reviewedCombinedCases"][4]["components"].reverse(),
            "CC applicability"),
        (lambda f: f["reviewedCombinedCases"][4]["withoutImmunity"].update(
            savingAttribute="BTS/2"), "CC applicability"),
        (lambda f: f["reviewedCombinedCases"][4]["withoutImmunity"].update(
            criticalRolls=3), "source hit/Critical Saving Roll counts"),
        (lambda f: f["reviewedCombinedCases"][4]["withImmunity"].update(
            failedRollWounds={"hit": 1, "criticalAdditionalRoll": 2}),
            "covered-attack result"),
        (lambda f: f["reviewedCombinedCases"][4]["withImmunity"].update(
            savingAttribute="ARM/2"), "covered-attack result"),
        (lambda f: f["reviewedCombinedCases"][4]["withImmunity"].update(
            remainingComponents=["ammunition:normal"]), "covered-attack result"),
        (lambda f: f["reviewedCombinedCases"][5]["when"].update(
            weaponId="weapon:e-mitter"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][5]["when"].update(
            attackClass="comms"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][5]["when"].update(
            savingAttribute="ARM"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][5].update(
            sourceAmmunitionId=14), "BTS Weapon applicability"),
        (lambda f: f["reviewedCombinedCases"][5]["components"].reverse(),
            "BTS Weapon applicability"),
        (lambda f: f["reviewedCombinedCases"][5]["withoutImmunity"].update(
            hitRolls=1), "source hit/Critical Saving Roll counts"),
        (lambda f: f["reviewedCombinedCases"][5]["withImmunity"].update(
            criticalRolls=1), "covered-attack result"),
        (lambda f: f["reviewedCombinedCases"][0]["when"].update(immunity="DA"),
         "Immunity applicability"),
        (lambda f: f["reviewedWeaponCases"][1]["when"].update(
            sourceWeaponId=226), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][1]["when"].update(
            sourceAmmunitionId=5), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][1]["when"].update(
            weaponId="weapon:armed-turret"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][1]["when"].update(
            attackClass="comms"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][1]["survivingTraits"].clear(),
            "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][1]["withoutImmunity"].update(
            hitRolls=1), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][1]["withImmunity"].update(
            savingAttribute="ARM"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][1].update(
            evidence="explicit-pinned-wiki-example"),
            "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["when"].update(
            mode="Hit Mode"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["when"].update(
            immunity="BTS"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["sourceProfile"].update(
            ammunitionId="ammunition:ap"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["sourceProfile"].update(
            savingRoll="ARM/2"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["sourceProfile"].update(
            hitRolls=1), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["sourceProfile"]["traits"].pop(),
            "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["withImmunity"].update(
            hitRolls=2), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["withImmunity"].update(
            criticalRolls=1), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2]["withImmunity"].update(
            treatedAs="ammunition:exp"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][2].update(
            evidence="derived-from-pinned-general-rules"),
            "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3]["when"].update(
            weaponId="weapon:monofilament-mine"),
            "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3]["when"].update(
            immunity="BTS"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3]["sourceProfile"].update(
            ammunitionId="ammunition:ap"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3]["sourceProfile"].update(
            savingRoll="ARM"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3]["sourceProfile"]["traits"].pop(),
            "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3]["withImmunity"].update(
            savingAttribute="BTS"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3]["withImmunity"].update(
            criticalRolls=1), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3]["withImmunity"].update(
            stateAppliedOnFailedRoll=True), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][3].update(
            evidence="derived-from-pinned-general-rules"),
            "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][0]["when"].update(
            immunity="Enhanced"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][0]["stateEffect"].update(
            condition="any-hit"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][0].update(
            ammunitionTreatedAs="ammunition:stun"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedWeaponCases"][0]["when"].update(
            weaponId="weapon:stun-pistol"), "reviewed Weapon Immunity examples"),
        (lambda f: f["reviewedVulnerabilityCases"][0]["when"].update(
            weaponNameContains="AP"), "Vulnerability interaction example"),
        (lambda f: f["reviewedVulnerabilityCases"][0].update(
            evidence="rule-derived"), "Vulnerability interaction example"),
        (lambda f: f["reviewedVulnerabilityCases"][0].update(
            withImmunity={"hitRolls": 1}), "Vulnerability interaction example"),
        (lambda f: f["reviewedCombinedCases"][0]["when"].update(
            savingAttribute="BTS"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][0]["withoutImmunity"].update(
            criticalRolls=4), "source hit/Critical Saving Roll counts"),
        (lambda f: f["reviewedCombinedCases"][0]["withImmunity"].update(
            hitRolls=2), "covered-attack result"),
        (lambda f: f["reviewedCombinedCases"][2]["withImmunity"].update(
            remainingComponents=["ammunition:normal"]), "covered-attack result"),
        (lambda f: f["reviewedCombinedCases"][2]["when"].update(
            immunity="Shock"), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][2].update(
            sourceAmmunitionId=13), "Immunity applicability"),
        (lambda f: f["reviewedCombinedCases"][1].update(
            sourceAmmunitionId=10), "duplicate source Ammunition ID"),
        (lambda f: f["reviewedCombinedCases"][0].update(
            evidence="automatic"), "rule-derived conclusion"),
        (lambda f: f.update(automaticResolution=True),
         "Immunity interaction fields"),
    ],
)
def test_immunity_interaction_rejects_unreviewed_semantics(
    tmp_path: Path, change, message: str
) -> None:
    """Immunity facts must not become an inferred combined-attack evaluator."""
    root = Path(__file__).resolve().parents[1]
    source = json.loads(
        (root / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    record = deepcopy(next(r for r in source["records"] if r["id"] == "skill:immunity"))
    record["labelIds"] = ["example-label"]  # The standalone fixture uses its own Label.
    record["citations"] = [{"sourceId": "n5-core-v5.3", "page": 1}]
    doc = valid_document()
    doc["records"].append(record)
    path = tmp_path / "immunity.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert load_curated_document(path)

    change(record["facts"]["immunityInteraction"])
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_curated_document(path)


def test_immunity_interaction_is_not_accepted_on_other_skills(tmp_path: Path) -> None:
    doc = valid_document()
    root = Path(__file__).resolve().parents[1]
    source = json.loads(
        (root / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    immunity = next(r for r in source["records"] if r["id"] == "skill:immunity")
    doc["records"][0]["facts"]["immunityInteraction"] = immunity["facts"][
        "immunityInteraction"
    ]
    path = tmp_path / "invalid-owner.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="only the Immunity Skill"):
        load_curated_document(path)
