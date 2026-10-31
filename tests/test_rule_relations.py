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
        assert outbound["relation_order"] == inbound["relation_order"]
        assert outbound["label"]
        assert inbound["label"]


def test_establishing_relations_sort_before_other_interactions() -> None:
    caused = relation_presentation("causes-state", "inbound")
    cancelled = relation_presentation("cancels-state", "inbound")

    assert caused is not None
    assert cancelled is not None
    assert caused["relation_order"] < cancelled["relation_order"]


def test_state_relation_sort_contract_matches_player_facing_order() -> None:
    items = [
        ("prevents-state-entry", "inbound", "Aerial"),
        ("cancels-state", "outbound", "Foxhole State"),
        ("cancels-state", "inbound", "Impetuous"),
        ("prevents-state-entry", "inbound", "Impetuous"),
        ("cancels-state", "inbound", "Jump"),
        ("prevents-state-entry", "inbound", "Motorcycle"),
        ("causes-state", "inbound", "Unconscious State"),
    ]
    presented = []
    for relation_type, direction, name in items:
        presentation = relation_presentation(relation_type, direction)
        assert presentation is not None
        presented.append((presentation, name))

    ordered = sorted(
        presented,
        key=lambda item: (
            item[0]["relation_order"],
            item[0]["label"],
            item[1],
        ),
    )
    assert [f"{presentation['label']}: {name}" for presentation, name in ordered] == [
        "Caused by: Unconscious State",
        "Cancelled by: Impetuous",
        "Cancelled by: Jump",
        "Cancels state: Foxhole State",
        "State entry prevented by: Aerial",
        "State entry prevented by: Impetuous",
        "State entry prevented by: Motorcycle",
    ]


def test_variant_relationship_is_structural_and_not_generically_presented() -> None:
    assert relation_presentation("variant-of", "outbound") is None
    assert relation_presentation("variant-of", "inbound") is None


def test_equips_with_preserves_equipment_provision_semantics() -> None:
    outbound = relation_presentation("equips-with", "outbound")
    inbound = relation_presentation("equips-with", "inbound")

    assert outbound is not None
    assert inbound is not None
    assert outbound["label"] == "Equips with"
    assert inbound["label"] == "Provided by"
    assert outbound["group_id"] == "creates-enables"
    assert inbound["group_id"] == "creates-enables"


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
        if record["composition"]["role"] == "definition" and not record["scope"].get("scenarios")
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
            outbound = relation["direction"] == "outbound"
            expected = relation_presentation(
                relation["type"],
                relation["direction"],
                source_record_id=record_id if outbound else relation["record_id"],
                target_record_id=relation["record_id"] if outbound else record_id,
            )
            if expected is None:
                assert "presentation" not in relation
            else:
                assert relation["presentation"] == expected


def test_two_source_scoped_legacy_edges_are_qualified_in_both_directions(
    tmp_path: Path,
) -> None:
    """Legacy relation IDs survive; only ambiguous display labels are tightened."""
    root = Path(__file__).resolve().parents[1]
    old_path = tmp_path / "v8-rules.db"
    export_rules_database(load_curated_directory(root / "data/curated"), old_path)

    cases = (
        (
            "equipment:motorcycle", "skill:jump",
            "Prohibits upward movement while mounted with",
            "Upward movement while mounted prohibited by",
        ),
        (
            "training:irregular", "skill:lieutenant",
            "Cannot be selected as",
            "Lieutenant selection excludes",
        ),
    )
    for db_path in (old_path, root / "data/generated/rules.db"):
        database = RulesDatabase(db_path)
        database.validate()
        records = {
            record["id"]: record
            for kind in ("training", "skill", "equipment")
            for record in database.composed_records_by_kind(kind)
        }
        for source_id, target_id, outward, inward in cases:
            source = records[source_id]
            target = records[target_id]
            # Existing structural and public API relation data remains untouched.
            assert {"type": "restricts-use-of", "record_id": target_id,
                    "collection_id": "n5-core-v5.3"} in source["relations"]
            outbound = next(
                relation for relation in source["display_relations"]
                if relation["type"] == "restricts-use-of"
                and relation["record_id"] == target_id
            )
            inbound = next(
                relation for relation in target["display_relations"]
                if relation["type"] == "restricts-use-of"
                and relation["record_id"] == source_id
                and relation["direction"] == "inbound"
            )
            assert outbound["presentation"]["label"] == outward
            assert inbound["presentation"]["label"] == inward
            assert outbound["record"]["id"] == target_id
            assert inbound["record"]["id"] == source_id

        # Other edges and generic relation-type metadata keep the old contract.
        climb = next(
            relation for relation in records["equipment:motorcycle"]["display_relations"]
            if relation["record_id"] == "skill:climb"
        )
        assert climb["presentation"]["label"] == "Restricts use of"
        generic = relation_presentation("restricts-use-of", "inbound")
        assert generic is not None and generic["label"] == "Use restricted by"


def test_scoped_legacy_labels_never_spill_to_other_relation_types() -> None:
    other = relation_presentation(
        "enables-use-of", "outbound",
        source_record_id="equipment:motorcycle", target_record_id="skill:jump",
    )
    assert other is not None and other["label"] == "Enables use of"
    unknown = relation_presentation(
        "restricts-use-of", "outbound",
        source_record_id="equipment:motorcycle", target_record_id="skill:climb",
    )
    assert unknown is not None and unknown["label"] == "Restricts use of"
