"""Source-bound variant usage projection regression and fail-closed contracts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from infinity_db import variant_usage
from infinity_db.database.schema import create_schema
from infinity_db.variant_usage import (
    _assert_complete_owner_rows,
    _include_peripheral_provenance,
    _published_extras_match,
    _resolve_effect,
    build_variant_usage_projection,
    validate_variant_usage_candidate,
)
from infinity_db.variant_usage_includes import build_include_provenance
from infinity_db.variant_usage_peripherals import build_peripheral_provenance
from infinity_db.variant_usage_reference import (
    load_variant_usage_publication,
    publication_from_candidate,
)

ROOT = Path(__file__).resolve().parents[1]


def _variant_usage_candidate(
    snapshot: dict[str, str], *, duplicate: bool = False,
) -> dict[str, Any]:
    rows = [{
        "catalog": "skills",
        "ownerKind": "profile",
        "sourceKey": ["skills", "profile", 1],
        "occurrenceId": 1,
        "sourceId": 47,
        "unitId": 185,
        "position": 1,
        "applicationItemId": 11,
        "context": {
            "ownerKind": "profile",
            "sourceUnitId": 185,
            "applicationArmyId": 70,
            "logicalUnitId": 18,
            "payloadSha256": "f" * 64,
        },
    }]
    variants = []
    for source_variant in (("level-1", "level-2") if duplicate else ("level-1",)):
        variant = {
            "recordId": "skill:stealth",
            "collectionId": "n5-core-v5.3",
            "effect": {"sourceVariant": source_variant},
        }
        variants.append({
            "variantKey": json.dumps(
                variant, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
            "variant": variant,
            "uniqueUnits": 1,
            "uniqueArmyUnits": 1,
            "distinctContexts": 1,
            "distinctProfileContexts": 1,
            "distinctLoadoutContexts": 0,
            "sourceRelationshipRows": 1,
            "sourceRows": rows,
        })
    variants.sort(key=lambda group: group["variantKey"])
    return {
        "format": "infinitydb-rule-variant-usage",
        "formatVersion": 2,
        "scope": "read-only-candidate-not-published",
        "sourceSnapshot": snapshot,
        "variants": variants,
        "diagnosticCounts": {"unreviewed-signature": 1},
        "unresolvedSourceRows": [{"rawValue": "not published"}],
    }


def _write_variant_usage_artifacts(
    tmp_path: Path, *, duplicate: bool = False,
) -> tuple[Path, Path, Path, Path]:
    army = tmp_path / "infinity.db"
    rules = tmp_path / "rules.db"
    objects = tmp_path / "deployed-objects.json"
    publication = tmp_path / "variant-usage.json"
    army.write_bytes(b"army")
    rules.write_bytes(b"rules")
    objects.write_bytes(b"deployed objects")
    snapshot = {
        "armyArchiveSha256": "a" * 64,
        "armyDatabaseSha256": hashlib.sha256(army.read_bytes()).hexdigest(),
        "rawDatabaseSha256": "b" * 64,
        "rulesDatabaseSha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
        "exportPairSha256": "c" * 64,
        "deployedObjectPublicationSha256": hashlib.sha256(objects.read_bytes()).hexdigest(),
    }
    candidate = _variant_usage_candidate(snapshot, duplicate=duplicate)
    if duplicate:
        document = {
            "format": "infinitydb-rule-variant-usage",
            "formatVersion": 1,
            "scope": "exact-reviewed-source-variants",
            "sourceSnapshot": snapshot,
            "variants": candidate["variants"],
        }
    else:
        document = publication_from_candidate(candidate)
    publication.write_text(json.dumps(document), encoding="utf-8")
    return army, rules, objects, publication


def test_variant_usage_publication_exposes_only_exact_source_variants(
    tmp_path: Path,
) -> None:
    army, rules, objects, publication = _write_variant_usage_artifacts(tmp_path)

    result = load_variant_usage_publication(publication, army, rules, objects)

    assert result is not None
    assert result["scope"] == "exact-reviewed-source-variants"
    assert len(result["variants"]) == 1
    assert "diagnosticCounts" not in result
    assert "unresolvedSourceRows" not in result


def test_variant_usage_publication_rejects_duplicate_source_rows(
    tmp_path: Path,
) -> None:
    army, rules, objects, publication = _write_variant_usage_artifacts(
        tmp_path, duplicate=True,
    )

    with pytest.raises(ValueError, match="duplicate variant usage source identity"):
        load_variant_usage_publication(publication, army, rules, objects)


@pytest.mark.parametrize("artifact", ["army", "rules", "objects"])
def test_variant_usage_publication_rejects_stale_release_artifacts(
    tmp_path: Path, artifact: str,
) -> None:
    army, rules, objects, publication = _write_variant_usage_artifacts(tmp_path)
    stale = {"army": army, "rules": rules, "objects": objects}[artifact]
    stale.write_bytes(f"changed {artifact}".encode())

    with pytest.raises(ValueError, match="does not match release artifacts"):
        load_variant_usage_publication(publication, army, rules, objects)


def _insert(connection: sqlite3.Connection, table: str, **values: Any) -> None:
    connection.execute(
        f"INSERT INTO {table} ({', '.join(values)}) "
        f"VALUES ({', '.join('?' for _ in values)})", tuple(values.values()),
    )


def _relax_keys(connection: sqlite3.Connection, table: str) -> None:
    """Deliberately malformed tables exercise rejection before schema validation."""
    connection.execute(f"CREATE TABLE bad_rows AS SELECT * FROM {table}")
    connection.execute(f"DROP TABLE {table}")
    connection.execute(f"ALTER TABLE bad_rows RENAME TO {table}")


@pytest.fixture
def usage_databases() -> Iterator[tuple[sqlite3.Connection, sqlite3.Connection]]:
    application = sqlite3.connect(":memory:")
    raw = sqlite3.connect(":memory:")
    for connection in (application, raw):
        connection.row_factory = sqlite3.Row
        create_schema(connection, {})
        _insert(connection, "__infinity_metadata", key="_meta",
                value=json.dumps({"snapshotArchiveSha256": "a" * 64}))
        _insert(connection, "__infinity_metadata", key="export_pair_sha256",
                value=json.dumps("b" * 64))
    _insert(raw, "unit_options", unit_id=185, option_id=9)
    _insert(application, "logical_unit_sources", source_unit_id=185, logical_unit_id=18)
    _insert(application, "profile_payloads", id=10, logical_unit_id=18, payload_sha256="profile")
    _insert(application, "loadout_payloads", id=20, logical_unit_id=18, payload_sha256="loadout")
    _insert(application, "unit_options", unit_id=185, option_id=9)
    for army, app_army in ((701, 70), (702, 71)):
        _insert(raw, "profiles", army_id=army, unit_id=185, group_id=1, profile_id=1)
        _insert(raw, "loadout_options", army_id=army, unit_id=185, group_id=1, option_id=1)
        _insert(application, "application_army_sources",
                source_army_id=army, application_army_id=app_army)
        _insert(application, "army_units", army_id=army, unit_id=185)
        _insert(application, "profile_payload_occurrences", army_id=army, unit_id=185,
                group_id=1, profile_id=1, profile_payload_id=10, position=1)
        _insert(application, "loadout_payload_occurrences", army_id=army, unit_id=185,
                group_id=1, option_id=1, loadout_payload_id=20, position=1)
    try:
        yield application, raw
    finally:
        application.close()
        raw.close()


def _add_direct(
    application: sqlite3.Connection, raw: sqlite3.Connection, catalog: str, owner: str,
    *, occurrence: int = 1, position: int = 1, army: int = 701,
) -> None:
    parents = {"unit_id": 185, "option_id": 9} if owner == "unit_option" else {
        "army_id": army, "unit_id": 185, "group_id": 1,
        "profile_id" if owner == "profile" else "option_id": 1,
    }
    common = {"item_id": 47, "position": position, "display_order": 2,
              "quantity": 1, "raw": None}
    _insert(raw, f"{owner}_{catalog}", occurrence_id=occurrence, **parents, **common)
    if owner == "unit_option":
        _insert(application, f"unit_option_{catalog}", occurrence_id=occurrence,
                **parents, **common)
    else:
        prefix, payload_id = ("profile", 10) if owner == "profile" else ("loadout", 20)
        table = f"{prefix}_payload_{catalog}"
        if application.execute(f"SELECT 1 FROM {table} WHERE position = ?",
                               (position,)).fetchone() is None:
            _insert(application, table, **{f"{prefix}_payload_id": payload_id}, **common)


def _extra(extra_id: int, raw: str, *, position: int = 1) -> dict[str, object]:
    return {"position": position, "extraId": extra_id,
            "extraType": "TEXT", "rawValue": raw}


def test_variant_usage_never_promotes_partial_or_unknown_extras() -> None:
    family = {
        "inheritance": "family",
        "occurrence_parameters": [{
            "source": "army-extra", "kind": "reviewed-extra",
            "extra_values": [{
                "extra_id": 250, "extra_type": "TEXT", "raw_value": "PH=12",
                "effect": {"kind": "infiltration-roll-ph-value",
                           "applies_to": "infiltration-ph-minus-three-roll",
                           "value": 12},
            }],
        }],
    }
    assert _resolve_effect(family, []) == ("family", None)
    state, typed = _resolve_effect(family, [_extra(250, "PH=12")])
    assert state == "exact" and typed is not None
    assert typed["parameter"]["effect"]["value"] == 12
    assert _resolve_effect(family, [_extra(277, "ReRoll")]) == ("unresolved", None)
    assert _resolve_effect(
        family, [_extra(250, "PH=12"), _extra(277, "ReRoll", position=2)]
    ) == ("unresolved", None)
    assert _resolve_effect(family, [_extra(250, "PH=13")]) == ("unresolved", None)


def test_variant_usage_exact_multi_extra_order_and_distinct_mods() -> None:
    variant = {
        "inheritance": "source",
        "source_variant": {"kind": "named", "value": "Example"},
        "occurrence_combinations": [{
            "extras": [
                {"extra_id": 6, "extra_type": "TEXT", "raw_value": "-3"},
                {"extra_id": 8, "extra_type": "TEXT", "raw_value": "+1B"},
            ],
            "effects": [
                {"kind": "target-roll-mod", "modifier": -3},
                {"kind": "burst-mod", "modifier": 1},
            ],
        }],
    }
    a, effect = _resolve_effect(
        variant, [_extra(6, "-3"), _extra(8, "+1B", position=2)]
    )
    assert a == "exact" and effect is not None
    assert len(effect["combinationEffects"]) == 2
    assert _resolve_effect(
        variant, [_extra(8, "+1B"), _extra(6, "-3", position=2)]
    ) == ("unresolved", None)
    assert _resolve_effect(variant, [_extra(6, "-3")]) == ("unresolved", None)


def test_variant_usage_published_extras_reject_drift_and_reordered_source() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE extras (id INTEGER, type TEXT, name TEXT)")
        connection.execute(
            "CREATE TABLE profile_payload_skill_extras "
            "(profile_payload_id INTEGER, occurrence_position INTEGER, "
            "position INTEGER, extra_id INTEGER)"
        )
        connection.executemany(
            "INSERT INTO extras VALUES (?, ?, ?)",
            [(6, "TEXT", "-3"), (8, "TEXT", "+1B")],
        )
        connection.executemany(
            "INSERT INTO profile_payload_skill_extras VALUES (1, 3, ?, ?)",
            [(1, 6), (2, 8)],
        )
        row = {
            "catalog": "skills", "position": 3,
            "extras": [_extra(6, "-3"), _extra(8, "+1B", position=2)],
        }
        assert _published_extras_match(connection, row, "profile", 1)
        assert not _published_extras_match(
            connection, {**row, "extras": list(reversed(row["extras"]))},
            "profile", 1,
        )
        connection.execute("UPDATE extras SET name = '+1 SD' WHERE id = 8")
        assert not _published_extras_match(connection, row, "profile", 1)


@pytest.mark.parametrize("catalog", ["skills", "equipment"])
@pytest.mark.parametrize("owner", ["profile", "option", "unit_option"])
def test_variant_usage_display_order_parity(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection], catalog: str, owner: str,
) -> None:
    application, raw = usage_databases
    _add_direct(application, raw, catalog, owner)
    row, = variant_usage._source_rows(raw, catalog, owner)
    assert variant_usage._direct_context(application, row, owner) is not None
    table = (f"unit_option_{catalog}" if owner == "unit_option" else
             f"{'profile' if owner == 'profile' else 'loadout'}_payload_{catalog}")
    application.execute(f"UPDATE {table} SET display_order = 3")
    assert variant_usage._direct_context(application, row, owner) is None


@pytest.mark.parametrize("owner", ["profile", "option", "unit_option"])
def test_variant_usage_ambiguous_published_owner_is_rejected(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection], owner: str,
) -> None:
    application, raw = usage_databases
    _add_direct(application, raw, "skills", owner)
    row, = variant_usage._source_rows(raw, "skills", owner)
    assert variant_usage._direct_context(application, row, owner) is not None
    table = {"profile": "profile_payload_occurrences", "option": "loadout_payload_occurrences",
             "unit_option": "unit_option_skills"}[owner]
    _relax_keys(application, table)
    application.execute(f"INSERT INTO {table} SELECT * FROM {table}")
    assert variant_usage._direct_context(application, row, owner) is None


@pytest.mark.parametrize("catalog", ["skills", "equipment"])
@pytest.mark.parametrize("owner", ["profile", "option", "unit_option"])
@pytest.mark.parametrize("corruption", ["duplicate", "missing-id", "missing-parent"])
def test_variant_usage_invalid_source_keys_fail_closed(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection],
    catalog: str, owner: str, corruption: str,
) -> None:
    application, raw = usage_databases
    _add_direct(application, raw, catalog, owner)
    table = f"{owner}_{catalog}"
    _relax_keys(raw, table)
    if corruption == "duplicate":
        raw.execute(f"INSERT INTO {table} SELECT * FROM {table}")
        message = "Duplicate variant source-row key"
    else:
        column = "occurrence_id" if corruption == "missing-id" else "unit_id"
        raw.execute(f"UPDATE {table} SET {column} = NULL")
        message = ("Missing variant source-row identity" if corruption == "missing-id"
                   else "Incomplete variant source owner path")
    with pytest.raises(ValueError, match=message):
        variant_usage._source_rows(raw, catalog, owner)


@pytest.mark.parametrize("ambiguity", ["source-catalog", "rules-link"])
def test_variant_usage_ambiguous_catalog_mapping_is_excluded(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection], ambiguity: str,
) -> None:
    application, _raw = usage_databases
    with sqlite3.connect(":memory:") as rules:
        rules.row_factory = sqlite3.Row
        rules.executescript(
            "CREATE TABLE collections (id TEXT, status TEXT);"
            "CREATE TABLE records (id TEXT, collection_id TEXT, variant_json TEXT, "
            "composition_role TEXT, kind TEXT);"
            "CREATE TABLE record_army_links "
            "(collection_id TEXT, record_id TEXT, entity TEXT, external_id TEXT);"
        )
        _insert(rules, "collections", id="core", status="current")
        _insert(rules, "records", id="skill:example", collection_id="core",
                variant_json=None, composition_role="definition", kind="skill")
        _insert(rules, "record_army_links", collection_id="core", record_id="skill:example",
                entity="skill", external_id="47")
        _insert(application, "application_catalog_sources", catalog="skills",
                application_item_id=47, source_item_id=47)
        assert variant_usage._source_mapping(application, rules)[("skills", 47)]["rules"]
        if ambiguity == "source-catalog":
            _insert(application, "application_catalog_sources", catalog="skills",
                    application_item_id=48, source_item_id=47)
        else:
            _insert(rules, "records", id="skill:other", collection_id="core",
                    variant_json=None, composition_role="definition", kind="skill")
            _insert(rules, "record_army_links", collection_id="core", record_id="skill:other",
                    entity="skill", external_id="47")
        mapping = variant_usage._source_mapping(application, rules)[("skills", 47)]
        assert mapping["rules"] is None
        assert mapping["ambiguous"] is True
        if ambiguity == "source-catalog":
            assert mapping["duplicateSourceMapping"] is True
            assert mapping["applicationItemId"] is None


def test_variant_usage_reused_payloads_preserve_all_source_paths_and_set_counts(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection],
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    application, raw = usage_databases
    for owner in ("profile", "option", "unit_option"):
        _add_direct(application, raw, "skills", owner)
        if owner != "unit_option":
            _add_direct(application, raw, "skills", owner, army=702, occurrence=2)
    for army, occurrence in ((701, 3), (702, 4)):
        _add_direct(application, raw, "skills", "profile", army=army,
                    occurrence=occurrence, position=2)
    paths = [tmp_path / name for name in ("application.db", "raw.db", "rules.db")]
    for source, path in zip((application, raw), paths, strict=False):
        source.commit()
        with sqlite3.connect(path) as destination:
            source.backup(destination)
    with sqlite3.connect(paths[2]) as rules:
        rules.execute("CREATE TABLE marker (id)")
    publication = tmp_path / "publication.json"
    publication.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(variant_usage, "load_deployed_object_publication", lambda *_args: {})
    monkeypatch.setattr(variant_usage, "_source_mapping", lambda *_args: {
        ("skills", 47): {"applicationItemId": 47, "rules": {
            "recordId": "skill:example-l1", "collectionId": "core",
            "variant": {"source_variant": {"kind": "level", "value": 1}},
        }},
    })
    projection = build_variant_usage_projection(
        paths[0], paths[1], paths[2], publication,
    )
    group, = projection["variants"]
    assert (group["uniqueUnits"], group["uniqueArmyUnits"], group["distinctContexts"],
            group["sourceRelationshipRows"]) == (1, 2, 4, 7)
    assert group["distinctProfileContexts"] == 2
    assert group["distinctLoadoutContexts"] == 2
    rows = group["sourceRows"]
    assert len({tuple(row["sourceKey"]) for row in rows}) == 7
    assert {(row["ownerKind"], tuple(row["ownerPathKey"]), row["position"])
            for row in rows} == {
        (owner, (army, 185, 1, 1), position)
        for owner, positions in (("profile", (1, 2)), ("option", (1,)))
        for army in (701, 702) for position in positions
    } | {("unit_option", (185, 9), 1)}
    shared, = [row for row in rows if row["ownerKind"] == "unit_option"]
    assert shared["context"]["applicationArmyId"] is None
    assert shared["context"]["logicalUnitId"] is None
    assert shared["context"]["compatibility"]["status"] == "source-only-unverified"
    assert [row["armyId"] for row in rows if row["ownerKind"] == "profile"] == [
        701, 701, 702, 702,
    ]


def _add_include(
    application: sqlite3.Connection, raw: sqlite3.Connection, owner: str,
    *, army: int = 701, parent: int = 1, target: int = 1, position: int = 1,
    quantity: int = 1,
) -> None:
    fields = {"unit_id": 185, "option_id": 9} if owner == "unit_option" else {
        "army_id": army, "unit_id": 185, "group_id": 1,
        "profile_id" if owner == "profile" else "option_id": parent,
    }
    _insert(raw, f"{owner}_includes", **fields, position=position,
            target_group_id=1, target_option_id=target, quantity=quantity, raw=None)
    armies = (701, 702) if owner == "unit_option" else (army,)
    table = {"profile": "profile_occurrence_includes", "option": "loadout_occurrence_includes",
             "unit_option": "unit_option_include_targets"}[owner]
    for target_army in armies:
        target_fields = {"target_army_id": target_army} if owner == "unit_option" else {}
        _insert(application, table, **fields, position=position, **target_fields,
                target_loadout_payload_id=19 + target, quantity=quantity, raw=None)


@pytest.fixture
def include_databases(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection],
) -> tuple[sqlite3.Connection, sqlite3.Connection]:
    application, raw = usage_databases
    for target in (2, 3):
        _insert(application, "loadout_payloads", id=19 + target, logical_unit_id=18,
                payload_sha256=f"target-{target}")
        for army in (701, 702):
            _insert(application, "loadout_payload_occurrences", army_id=army, unit_id=185,
                    group_id=1, option_id=target, loadout_payload_id=19 + target, position=target)
    for position, quantity in ((1, 2), (2, 1)):
        _add_include(application, raw, "profile", position=position, quantity=quantity)
    for army in (701, 702):
        _add_include(application, raw, "option", army=army, target=2)
    _add_include(application, raw, "unit_option")
    return application, raw


def test_variant_usage_include_paths_preserve_repetition_and_army_context(
    include_databases: tuple[sqlite3.Connection, sqlite3.Connection],
) -> None:
    application, raw = include_databases
    result = build_include_provenance(application, raw)
    assert len(result["includes"]) == 6
    assert len(result["includePaths"]) == 10
    profile_edges = [edge for edge in result["includes"] if edge["edgeKey"][0] == "profile"]
    assert {edge["owner"]["quantity"] for edge in profile_edges} == {1, 2}
    assert {edge["owner"]["position"] for edge in profile_edges} == {1, 2}
    for path in result["includePaths"]:
        assert path["relationshipKind"] == "include-context-only"
        assert len(path["edgeKeys"]) in (1, 2)
        if path["sourceOwnerKind"] == "unit_option":
            assert path["sourceOwnerPathKey"] == [185, 9]
            assert path["targetOwnerPathKey"][0] in (701, 702)
        else:
            assert path["targetOwnerPathKey"][0] == path["sourceOwnerPathKey"][0]
    profile_chains = [path for path in result["includePaths"]
                      if path["sourceOwnerKind"] == "profile" and len(path["edgeKeys"]) == 2]
    assert len(profile_chains) == 2
    assert profile_chains[0]["edgeKeys"] != profile_chains[1]["edgeKeys"]
    assert all(path["targetOwnerPathKey"] == [701, 185, 1, 2] for path in profile_chains)
    # Incidental SQLite row order cannot change edge keys, chains or ordering.
    for connection, table in ((raw, "profile_includes"), (raw, "option_includes"),
                              (application, "loadout_payload_occurrences")):
        connection.execute(
            f"CREATE TABLE reverse_rows AS SELECT * FROM {table} ORDER BY rowid DESC"
        )
        connection.execute(f"DROP TABLE {table}")
        connection.execute(f"ALTER TABLE reverse_rows RENAME TO {table}")
    assert build_include_provenance(application, raw) == result


@pytest.mark.parametrize(("statement", "message"), [
    ("DELETE FROM profile_payload_occurrences WHERE army_id = 701", "Missing Include parent"),
    ("DELETE FROM loadout_payload_occurrences WHERE army_id = 701 AND option_id = 1",
     "Missing Include target owner"),
    ("DELETE FROM loadout_payloads WHERE id = 20", "Missing Include target payload"),
    ("UPDATE profile_occurrence_includes SET quantity = 99", "source/published rows differ"),
    ("UPDATE profile_occurrence_includes SET raw = 'unreviewed'", "source/published rows differ"),
    ("UPDATE profile_occurrence_includes SET target_loadout_payload_id = 21",
     "source/published rows differ"),
])
def test_variant_usage_include_owner_target_and_parity_fail_closed(
    include_databases: tuple[sqlite3.Connection, sqlite3.Connection],
    statement: str, message: str,
) -> None:
    application, raw = include_databases
    assert build_include_provenance(application, raw)["includes"]
    application.execute(statement)
    with pytest.raises(ValueError, match=message):
        build_include_provenance(application, raw)


@pytest.mark.parametrize(("side", "table", "message"), [
    ("raw", "profile_includes", "duplicate Include source key"),
    ("published", "profile_occurrence_includes", "source/published rows differ"),
    ("published", "profile_payload_occurrences", "ambiguous Include owner"),
    ("published", "loadout_payload_occurrences", "ambiguous Include owner"),
    ("published", "unit_options", "ambiguous Include owner"),
    ("published", "loadout_payloads", "ambiguous Include owner"),
])
def test_variant_usage_duplicate_include_keys_fail_closed(
    include_databases: tuple[sqlite3.Connection, sqlite3.Connection],
    side: str, table: str, message: str,
) -> None:
    application, raw = include_databases
    connection = raw if side == "raw" else application
    _relax_keys(connection, table)
    connection.execute(f"INSERT INTO {table} SELECT * FROM {table} LIMIT 1")
    with pytest.raises(ValueError, match=message):
        build_include_provenance(application, raw)


@pytest.mark.parametrize(("statement", "message"), [
    ("DELETE FROM profile_includes WHERE position = 2", "source/published rows differ"),
    ("UPDATE profile_includes SET target_option_id = NULL", "Missing Include target key"),
    ("UPDATE profile_includes SET position = NULL", "Missing or duplicate Include source key"),
])
def test_variant_usage_incomplete_include_source_fails_closed(
    include_databases: tuple[sqlite3.Connection, sqlite3.Connection], statement: str, message: str,
) -> None:
    application, raw = include_databases
    _relax_keys(raw, "profile_includes")
    raw.execute(statement)
    with pytest.raises(ValueError, match=message):
        build_include_provenance(application, raw)


@pytest.mark.parametrize(("parent", "target"), [(1, 1), (2, 1), (3, 3)])
def test_variant_usage_include_cycles_fail_closed_even_when_disconnected(
    include_databases: tuple[sqlite3.Connection, sqlite3.Connection], parent: int, target: int,
) -> None:
    application, raw = include_databases
    assert build_include_provenance(application, raw)["includePaths"]
    _add_include(application, raw, "option", parent=parent, target=target, position=2)
    with pytest.raises(ValueError, match="Cyclic Include source path"):
        build_include_provenance(application, raw)


def test_variant_usage_include_and_peripheral_edges_are_context_only(
    include_databases: tuple[sqlite3.Connection, sqlite3.Connection],
) -> None:
    application, raw = include_databases
    result = _include_peripheral_provenance(application, raw)
    assert len(result["includes"]) == 6
    assert len(result["includePaths"]) == 10
    assert result["peripheralControllerEdges"] == []
    assert "never counted as direct" in result["policy"]


def test_variant_usage_truncated_raw_relationships_fail_closed() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE unit_option_skills (occurrence_id INTEGER)")
        connection.executemany(
            "INSERT INTO unit_option_skills VALUES (?)", [(1,), (2,)]
        )
        _assert_complete_owner_rows(connection, "skills", "unit_option", 2)
        with pytest.raises(ValueError, match="relationship count differs"):
            _assert_complete_owner_rows(connection, "skills", "unit_option", 1)


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_variant_usage_mismatched_raw_snapshot_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(("a" * 64, "b" * 64))
    monkeypatch.setattr(variant_usage, "_snapshot", lambda _db: next(values))
    with pytest.raises(ValueError, match="raw archive does not match"):
        build_variant_usage_projection(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            ROOT / "data/generated/rules.db",
            ROOT / "data/generated/deployed-objects.json",
        )


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_variant_usage_pinned_pair_has_source_ownership_not_inferred_includes() -> None:
    projection = build_variant_usage_projection(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db",
        ROOT / "data/generated/rules.db",
        ROOT / "data/generated/deployed-objects.json",
    )
    assert projection["scope"] == "read-only-candidate-not-published"
    assert projection["formatVersion"] == 2
    assert len(projection["sourceSnapshot"]["armyArchiveSha256"]) == 64
    assert projection["relationships"]["policy"].startswith("context-only")
    assert projection["relationships"]["includes"]
    assert len(projection["relationships"]["peripheralAttachments"]) == 818
    assert isinstance(projection["relationships"]["peripheralControllerEdges"], list)
    assert projection["variants"]
    assert {f"skill:martial-arts-l{level}" for level in range(1, 6)} <= {
        group["variant"]["recordId"] for group in projection["variants"]
    }
    assert all(
        group["uniqueUnits"] <= group["uniqueArmyUnits"]
        <= group["sourceRelationshipRows"]
        and group["sourceRows"]
        for group in projection["variants"]
    )
    for group in projection["variants"]:
        assert group["distinctContexts"] == (
            group["distinctProfileContexts"] + group["distinctLoadoutContexts"]
        )
        contexts = [
            row["context"] for row in group["sourceRows"]
            if row["context"]["applicationArmyId"] is not None
        ]
        assert group["uniqueUnits"] == len({
            context["logicalUnitId"] for context in contexts
        })
        assert group["uniqueArmyUnits"] == len({
            (context["applicationArmyId"], context["logicalUnitId"])
            for context in contexts
        })
    # Five bare Infiltration ReRolls and Doctor 2W are source-native
    # unresolved occurrence annotations, never fabricated typed effects.
    raw_unresolved = {
        (item["catalog"], item["sourceId"], item["occurrenceId"])
        for item in projection["unresolvedSourceRows"]
    }
    assert {("skills", 47, number) for number in
            (44546, 74177, 61511, 65105, 67248)} <= raw_unresolved
    assert {("skills", 53, number) for number in
            (33478, 34014, 34181, 35960)} <= raw_unresolved
    assert projection["diagnosticCounts"]["unreviewed-signature"] >= 9
    # No include or controller relationship can fabricate a direct owner.
    for group in projection["variants"]:
        for owner in group["sourceRows"]:
            assert owner["ownerKind"] in {"profile", "option", "unit_option"}
            assert owner["occurrenceId"] is not None
            assert not any(k in owner for k in ("includePosition", "peripheralId"))
    # Stable canonical output independent of incidental dict iteration.
    assert json.loads(json.dumps(projection, sort_keys=True)) == projection


@pytest.mark.parametrize("compatible", [None, "[]", "[1]", "unreviewed"])
@pytest.mark.parametrize("disabled", [0, 1])
def test_variant_usage_shared_option_never_infers_compatible_armies(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection],
    compatible: str | None, disabled: int,
) -> None:
    application, raw = usage_databases
    for database in (application, raw):
        database.execute("UPDATE unit_options SET compatible=?, disabled=?, raw=?",
                         (compatible, disabled, "opaque source data"))
    _add_direct(application, raw, "skills", "unit_option")
    row, = variant_usage._source_rows(raw, "skills", "unit_option")
    context = variant_usage._direct_context(application, row, "unit_option")
    assert context is not None
    assert context["applicationArmyId"] is None
    assert context["logicalUnitId"] is None
    assert context["payloadSha256"] is None
    assert context["compatibility"]["source"] == {
        "compatible": compatible, "disabled": disabled, "raw": "opaque source data",
    }
    assert context["compatibility"]["status"] == "source-only-unverified"


@pytest.mark.parametrize("mutation", [
    "UPDATE unit_options SET compatible='[701]'",
    "UPDATE unit_options SET disabled=1",
    "UPDATE unit_options SET raw='changed'",
    "DELETE FROM unit_options",
])
def test_variant_usage_shared_option_owner_drift_is_rejected(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection], mutation: str,
) -> None:
    application, raw = usage_databases
    _add_direct(application, raw, "skills", "unit_option")
    row, = variant_usage._source_rows(raw, "skills", "unit_option")
    application.execute(mutation)
    assert variant_usage._direct_context(application, row, "unit_option") is None


@pytest.mark.parametrize("mutation", [
    "DELETE FROM unit_options",
    "INSERT INTO unit_options SELECT * FROM unit_options",
])
def test_variant_usage_shared_option_source_owner_is_required(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection], mutation: str,
) -> None:
    application, raw = usage_databases
    _add_direct(application, raw, "skills", "unit_option")
    _relax_keys(raw, "unit_options")
    raw.execute(mutation)
    with pytest.raises(ValueError, match="Missing or ambiguous shared Unit option"):
        variant_usage._source_rows(raw, "skills", "unit_option")


@pytest.mark.parametrize("tamper", ["version", "count", "row", "hash", "typed", "unknown"])
def test_variant_usage_saved_candidate_rejects_stale_and_tampered_content(
    tmp_path: Path, tamper: str,
) -> None:
    expected = {
        "formatVersion": 2, "sourceSnapshot": {"armyDatabaseSha256": "a" * 64},
        "variants": [{"uniqueUnits": 1, "sourceRows": [{"occurrenceId": 7}]}],
    }
    candidate = tmp_path / "candidate.json"
    # Whitespace and JSON key ordering are presentation, not source identity.
    candidate.write_text(json.dumps(expected, sort_keys=True), encoding="utf-8")
    validate_variant_usage_candidate(candidate, expected)
    changed = json.loads(json.dumps(expected))
    if tamper == "version":
        changed["formatVersion"] = 1
    elif tamper == "count":
        changed["variants"][0]["uniqueUnits"] = 2
    elif tamper == "row":
        changed["variants"][0]["sourceRows"] = []
    elif tamper == "hash":
        changed["sourceSnapshot"]["armyDatabaseSha256"] = "b" * 64
    elif tamper == "typed":
        changed["variants"][0]["uniqueUnits"] = True
    else:
        changed["unverified"] = True
    candidate.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="stale or differs"):
        validate_variant_usage_candidate(candidate, expected)


@pytest.mark.parametrize("content", [None, "{", "NaN"])
def test_variant_usage_unreadable_candidate_fails_closed(
    tmp_path: Path, content: str | None,
) -> None:
    candidate = tmp_path / "candidate.json"
    if content is not None:
        candidate.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Unreadable or invalid"):
        validate_variant_usage_candidate(candidate, {})


def test_variant_usage_mismatched_export_generation_fails_before_reading_rows(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection],
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    application, raw = usage_databases
    raw.execute("UPDATE __infinity_metadata SET value=? WHERE key='export_pair_sha256'",
                (json.dumps("c" * 64),))
    paths = [tmp_path / name for name in ("application.db", "raw.db")]
    for connection, path in zip((application, raw), paths, strict=True):
        connection.commit()
        with sqlite3.connect(path) as destination:
            connection.backup(destination)
    monkeypatch.setattr(variant_usage, "load_deployed_object_publication", lambda *_args: {})
    with pytest.raises(ValueError, match="different exports"):
        build_variant_usage_projection(
            paths[0], paths[1], tmp_path / "rules.db", tmp_path / "pub.json",
        )


@pytest.mark.parametrize("owner", ["profile", "option"])
@pytest.mark.parametrize("mutation", [None, "quantity", "raw", "name", "owner"])
def test_variant_usage_source_only_peripheral_attachments_require_exact_parity(
    usage_databases: tuple[sqlite3.Connection, sqlite3.Connection],
    owner: str, mutation: str | None,
) -> None:
    application, raw = usage_databases
    identity = "profile_id" if owner == "profile" else "option_id"
    _insert(raw, "peripherals", army_id=701, id=7, name="Source-only bot")
    _insert(application, "application_peripheral_source_labels", army_id=701,
            peripheral_id=7, source_name="Source-only bot")
    for connection in (application, raw):
        _insert(connection, f"{owner}_peripherals", occurrence_id=9, army_id=701,
                unit_id=185, group_id=1, **{identity: 1}, position=1, item_id=7,
                quantity=2, raw=None)
    result = build_peripheral_provenance(application, raw)
    attachment, = result["peripheralAttachments"]
    assert attachment["source"]["quantity"] == 2
    assert attachment["source"]["occurrence_id"] == 9
    assert attachment["context"]["logicalUnitId"] == 18
    assert result["peripheralControllerEdges"] == []
    if mutation is None:
        return
    if mutation == "name":
        raw.execute("UPDATE peripherals SET name='Drifted'")
    elif mutation == "owner":
        table = "profiles" if owner == "profile" else "loadout_options"
        raw.execute(f"DELETE FROM {table}")
    else:
        value = "3" if mutation == "quantity" else "'changed'"
        application.execute(f"UPDATE {owner}_peripherals SET {mutation}={value}")
    with pytest.raises(ValueError):
        build_peripheral_provenance(application, raw)


def test_variant_usage_cli_check_never_writes_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tools import build_variant_usage as cli

    result = {
        "scope": "read-only-candidate-not-published", "variants": [],
        "familyOnlyUniqueUnitCounts": {}, "unresolvedSourceRows": [],
        "diagnosticCounts": {}, "sourceSnapshot": {},
        "relationships": {"includes": [], "includePaths": [],
                          "peripheralAttachments": [], "peripheralControllerEdges": []},
    }
    candidate = tmp_path / "candidate.json"
    original = json.dumps(result).encode("utf-8")
    candidate.write_bytes(original)
    monkeypatch.setattr(cli, "build_variant_usage_projection", lambda *_args: result)
    monkeypatch.setattr("sys.argv", ["build_variant_usage", "--check", str(candidate)])
    cli.main()
    assert candidate.read_bytes() == original
    result["scope"] = "changed"
    with pytest.raises(ValueError, match="stale or differs"):
        cli.main()
    assert candidate.read_bytes() == original
