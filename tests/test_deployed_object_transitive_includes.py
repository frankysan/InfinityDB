"""Audit whether reviewed delivery sources occur past one contextual Include edge.

The read-only audit resolves intermediate loadout payloads inside the same
source Army and Unit. Shared payload identities are not enough to assign a
particular group/option or infer a Unit-wide option's Army ownership.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

from infinity_db.deployed_object_usage import _source_ids

ROOT = Path(__file__).resolve().parents[1]


class IncludeAudit(TypedDict):
    roots: int
    ambiguous: list[tuple[object, ...]]
    cycles: list[tuple[object, ...]]
    transitiveCandidates: list[tuple[object, ...]]


def _reviewed_origins() -> tuple[str, ...]:
    reviews = json.loads(
        (ROOT / "config/validation/deployed-object-delivery-reviews.json").read_text(
            encoding="utf-8"
        )
    )
    return tuple(sorted({
        delivery["originRecordId"]
        for delivery in reviews["reviewedDeliveryPaths"]
        if delivery["sourceProfile"] is not None
    }))


def _report(
    army_db: Path, *, origins: tuple[str, ...] | None = None,
) -> IncludeAudit:
    db = sqlite3.connect(f"{army_db.resolve().as_uri()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        identifiers = {
            ("weapons" if record_id.startswith("weapon:") else "equipment", item)
            for record_id in (origins if origins is not None else _reviewed_origins())
            for item in _source_ids(db, record_id)
        }
        occurrences: dict[tuple[int, int, int], list[tuple[int, int]]] = defaultdict(list)
        for row in db.execute(
            "SELECT army_id, unit_id, group_id, option_id, loadout_payload_id "
            "FROM loadout_payload_occurrences"
        ):
            occurrences[(row["army_id"], row["unit_id"], row["loadout_payload_id"])].append(
                (row["group_id"], row["option_id"])
            )
        edges: dict[tuple[int, int, int, int], list[tuple[int, int]]] = defaultdict(list)
        for row in db.execute(
            "SELECT army_id, unit_id, group_id, option_id, position, "
            "target_loadout_payload_id FROM loadout_occurrence_includes"
        ):
            edges[(row["army_id"], row["unit_id"], row["group_id"], row["option_id"])].append(
                (row["position"], row["target_loadout_payload_id"])
            )
        items: dict[int, list[tuple[str, int, int]]] = defaultdict(list)
        for catalog in ("weapons", "equipment"):
            for row in db.execute(
                f"SELECT loadout_payload_id, item_id, position "
                f"FROM loadout_payload_{catalog}"
            ):
                if (catalog, row["item_id"]) in identifiers:
                    items[row["loadout_payload_id"]].append(
                        (catalog, row["item_id"], row["position"])
                    )
        roots: list[tuple[str, int, int, int | None, int, int, int]] = []
        for kind in ("profile", "loadout"):
            for row in db.execute(
                f"SELECT army_id, unit_id, group_id, "
                f"{'profile_id' if kind == 'profile' else 'option_id'} AS identity_id, "
                f"position, target_loadout_payload_id FROM {kind}_occurrence_includes"
            ):
                roots.append((
                    kind, row["army_id"], row["unit_id"], row["group_id"],
                    row["identity_id"], row["position"], row["target_loadout_payload_id"],
                ))
        for row in db.execute(
            "SELECT unit_id, option_id, position, target_army_id, "
            "target_loadout_payload_id FROM unit_option_include_targets"
        ):
            roots.append((
                "unit-option", row["target_army_id"], row["unit_id"], None,
                row["option_id"], row["position"], row["target_loadout_payload_id"],
            ))
        ambiguous: list[tuple[object, ...]] = []
        cycles: list[tuple[object, ...]] = []
        candidates: list[tuple[object, ...]] = []
        for kind, army, unit, group, parent_id, root_position, target in roots:
            # Distinct contextual routes are not merged: a root is a particular
            # source Include, and each step needs exactly one Army/Unit occurrence.
            root = (kind, army, unit, group, parent_id, root_position, target)
            stack: list[tuple[int, tuple[int, ...], int]] = [(target, (target,), 1)]
            while stack:
                payload, path, depth = stack.pop()
                contexts = occurrences.get((army, unit, payload), [])
                if len(contexts) != 1:
                    ambiguous.append((*root, path, len(contexts)))
                    continue
                child_group, child_option = contexts[0]
                for edge_position, next_target in edges.get(
                    (army, unit, child_group, child_option), []
                ):
                    trail = (*path, next_target)
                    for catalog, source_id, position in items.get(next_target, []):
                        candidates.append((
                            *root, depth + 1, child_group, child_option,
                            edge_position, trail, catalog, source_id, position,
                        ))
                    if next_target in path:
                        cycles.append((*root, trail))
                    else:
                        stack.append((next_target, trail, depth + 1))
        return {
            "roots": len(roots),
            "ambiguous": ambiguous,
            "cycles": cycles,
            "transitiveCandidates": candidates,
        }
    finally:
        db.close()



def test_audit_detects_nested_delivery_and_respects_contextual_target_identity(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "synthetic-includes.db"
    with sqlite3.connect(database_path) as db:
        db.executescript(
            """
            CREATE TABLE application_domain_slugs (
                domain TEXT, application_id INTEGER, slug TEXT
            );
            CREATE TABLE application_catalog_sources (
                catalog TEXT, application_item_id INTEGER, source_item_id INTEGER
            );
            CREATE TABLE loadout_payload_occurrences (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER,
                option_id INTEGER, loadout_payload_id INTEGER
            );
            CREATE TABLE profile_occurrence_includes (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER,
                profile_id INTEGER, position INTEGER, target_loadout_payload_id INTEGER
            );
            CREATE TABLE loadout_occurrence_includes (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER,
                option_id INTEGER, position INTEGER, target_loadout_payload_id INTEGER
            );
            CREATE TABLE unit_option_include_targets (
                unit_id INTEGER, option_id INTEGER, position INTEGER,
                target_army_id INTEGER, target_loadout_payload_id INTEGER
            );
            CREATE TABLE loadout_payload_weapons (
                loadout_payload_id INTEGER, item_id INTEGER, position INTEGER
            );
            CREATE TABLE loadout_payload_equipment (
                loadout_payload_id INTEGER, item_id INTEGER, position INTEGER
            );
            INSERT INTO application_domain_slugs VALUES
                ('weapons', 12, 'pitcher'),
                ('equipment', 13, 'deployable-repeater'),
                ('weapons', 14, 'disco-baller'),
                ('weapons', 15, 'drop-bears');
            INSERT INTO application_catalog_sources VALUES
                ('weapons', 12, 3), ('equipment', 13, 4),
                ('weapons', 14, 5), ('weapons', 15, 6);
            INSERT INTO profile_occurrence_includes VALUES (101, 7, 1, 2, 1, 10);
            INSERT INTO loadout_payload_occurrences VALUES
                (101, 7, 2, 3, 10), (101, 7, 3, 4, 20);
            INSERT INTO loadout_occurrence_includes VALUES (101, 7, 2, 3, 2, 20);
            INSERT INTO loadout_payload_weapons VALUES (20, 3, 1);
            """
        )
    report = _report(database_path, origins=("weapon:pitcher",))
    assert len(report["transitiveCandidates"]) == 1
    candidate = report["transitiveCandidates"][0]
    assert candidate[0] == "profile"
    assert candidate[7] == 2  # second Include hop, not the direct root
    assert candidate[11] == (10, 20)  # exact payload path
    assert report["ambiguous"] == []
    assert report["cycles"] == []

    # Sharing payload identifiers across Armies/Units cannot add parent uses.
    with sqlite3.connect(database_path) as db:
        db.execute("INSERT INTO loadout_payload_occurrences VALUES (201, 7, 2, 3, 10)")
        db.execute("INSERT INTO loadout_payload_occurrences VALUES (101, 8, 2, 3, 10)")
    assert (
        _report(database_path, origins=("weapon:pitcher",))["transitiveCandidates"]
        == report["transitiveCandidates"]
    )

    # Re-entering a visited payload is a cycle, never unbounded traversal.
    with sqlite3.connect(database_path) as db:
        db.execute(
            "INSERT INTO loadout_occurrence_includes VALUES (101, 7, 3, 4, 3, 10)"
        )
    assert _report(database_path, origins=("weapon:pitcher",))["cycles"]

    # Two candidate loadout occurrences in the same Army/Unit make the
    # intermediate context ambiguous, even if their payload IDs match.
    with sqlite3.connect(database_path) as db:
        db.execute("INSERT INTO loadout_payload_occurrences VALUES (101, 7, 4, 5, 10)")
    assert _report(database_path, origins=("weapon:pitcher",))["ambiguous"]

def test_pinned_reviewed_delivery_includes_have_no_unsupported_transitive_paths() -> None:
    path = ROOT / "data/generated/infinity.db"
    if not path.is_file():
        import pytest
        pytest.skip("Pinned Army release database missing")
    report = _report(path)
    assert report["roots"] > 0
    # This audit intentionally fails if the pinned snapshot adds a relevant
    # two-hop path; review its context before extending published reverse uses.
    assert not report["transitiveCandidates"], report["transitiveCandidates"][:20]
    assert not report["ambiguous"], report["ambiguous"][:20]
    assert not report["cycles"], report["cycles"][:20]
