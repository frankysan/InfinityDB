from pathlib import Path

from infinity_db.curated import load_curated_directory
from infinity_db.rule_relations import (
    RELATION_GROUPS,
    RULE_RELATION_PRESENTATION,
    RULE_RELATION_TYPES,
    relation_presentation,
)
from infinity_db.rules_database import RulesDatabase, export_rules_database


def test_every_gameplay_relation_has_complete_bidirectional_presentation() -> None:
    assert RULE_RELATION_TYPES == frozenset(RULE_RELATION_PRESENTATION)
    assert set(RELATION_GROUPS) == {
        "creates-enables",
        "state-interactions",
        "mods-changes",
        "cancels-restricts",
    }

    assert RULE_RELATION_PRESENTATION["variant-of"] is None
    for relation_type in sorted(RULE_RELATION_TYPES - {"variant-of"}):
        outbound = relation_presentation(relation_type, "outbound")
        inbound = relation_presentation(relation_type, "inbound")
        assert outbound is not None
        assert inbound is not None
        assert outbound["group_id"] == inbound["group_id"]
        assert outbound["group_label"] == inbound["group_label"]
        assert outbound["group_order"] == inbound["group_order"]
        assert outbound["label"]
        assert inbound["label"]


def test_variant_relationship_is_structural_and_not_generically_presented() -> None:
    assert relation_presentation("variant-of", "outbound") is None
    assert relation_presentation("variant-of", "inbound") is None


def test_rules_database_projects_curated_summaries_labels_and_relation_semantics(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)
    database = RulesDatabase(output)

    definitions = {
        record["id"]: record
        for _, document in documents
        if document["collection"]["status"] == "current"
        for record in document["records"]
        if record["composition"]["role"] == "definition"
    }
    composed = {
        record["id"]: record
        for kind in sorted({record["kind"] for record in definitions.values()})
        for record in database.composed_records_by_kind(kind)
    }

    assert set(definitions) <= set(composed)
    for record_id, definition in definitions.items():
        record = composed[record_id]
        assert record["summary"] == definition["summary"]
        assert record["label_ids"] == definition.get("labelIds", [])
        assert {label["id"] for label in record.get("labels", [])} == set(
            definition.get("labelIds", [])
        )
        for relation in record.get("display_relations", []):
            expected = relation_presentation(relation["type"], relation["direction"])
            if expected is None:
                assert "presentation" not in relation
            else:
                assert relation["presentation"] == expected
