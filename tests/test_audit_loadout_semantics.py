from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_loadout_semantics import (
    EXPECTED_COLUMNS,
    LoadoutSemanticsAuditError,
    audit_database,
    main,
)


def _insert(connection: sqlite3.Connection, table: str, **values: object) -> None:
    columns = ", ".join(f'"{name}"' for name in values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    )


def _loadout(army_id: int, unit_id: int, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "army_id": army_id,
        "unit_id": unit_id,
        "group_id": 1,
        "option_id": 1,
        "position": 1,
        "name": f"Loadout {unit_id}",
        "points": 20,
        "swc": 0,
        "minis": 1,
        "disabled": 0,
    }
    row.update(overrides)
    return row


def _item_row(
    occurrence_id: int,
    loadout: dict[str, object],
    *,
    position: int = 1,
    item_id: int = 10,
    display_order: int | None = 1,
    quantity: int | None = None,
    raw: str | None = None,
) -> dict[str, object]:
    return {
        "occurrence_id": occurrence_id,
        "army_id": loadout["army_id"],
        "unit_id": loadout["unit_id"],
        "group_id": loadout["group_id"],
        "option_id": loadout["option_id"],
        "position": position,
        "item_id": item_id,
        "display_order": display_order,
        "quantity": quantity,
        "raw": raw,
    }


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        for table, columns in EXPECTED_COLUMNS.items():
            definition = ", ".join(f'"{column}"' for column in columns)
            connection.execute(f'CREATE TABLE "{table}" ({definition})')

        connection.execute("PRAGMA user_version = 12")
        _insert(
            connection,
            "__infinity_metadata",
            key="_meta",
            value=json.dumps(
                {
                    "snapshotArchiveSha256": "a" * 64,
                    "snapshotDownloadedOn": "2026-09-18",
                },
                sort_keys=True,
            ),
        )

        loadouts: dict[tuple[int, int], dict[str, object]] = {}
        for unit_id in range(1, 9):
            for army_id in (101, 102):
                overrides: dict[str, object] = {}
                if unit_id == 1 and army_id == 102:
                    overrides["points"] = 21
                if unit_id == 2 and army_id == 102:
                    overrides["swc"] = 1
                row = _loadout(army_id, unit_id, **overrides)
                loadouts[(army_id, unit_id)] = row
                _insert(connection, "loadout_options", **row)

        # Unit 3 differs only by equipment representation.
        _insert(
            connection,
            "option_equipment",
            **_item_row(1, loadouts[(101, 3)], display_order=1, quantity=None),
        )
        _insert(
            connection,
            "option_equipment",
            **_item_row(2, loadouts[(102, 3)], display_order=7, quantity=1),
        )

        # Unit 4 has a genuine skill-extra difference.
        for occurrence_id, army_id in ((3, 101), (4, 102)):
            _insert(
                connection,
                "option_skills",
                **_item_row(occurrence_id, loadouts[(army_id, 4)]),
            )
        _insert(
            connection,
            "option_skill_extras",
            occurrence_id=4,
            position=1,
            extra_id=50,
        )

        # Unit 5 has different army-local peripheral IDs for the same definition.
        # Unit 6 has the same name but a real contextual mercs difference.
        for army_id, peripheral_id in ((101, 1001), (102, 2001)):
            _insert(
                connection,
                "peripherals",
                army_id=army_id,
                id=peripheral_id,
                position=1,
                name="BOT",
                mercs=0,
            )
            _insert(
                connection,
                "option_peripherals",
                **_item_row(
                    10 + army_id,
                    loadouts[(army_id, 5)],
                    item_id=peripheral_id,
                    display_order=None,
                ),
            )

        for army_id, peripheral_id, mercs in ((101, 1002, 0), (102, 2002, 1)):
            _insert(
                connection,
                "peripherals",
                army_id=army_id,
                id=peripheral_id,
                position=2,
                name="TURTLEMEK",
                mercs=mercs,
            )
            _insert(
                connection,
                "option_peripherals",
                **_item_row(
                    20 + army_id,
                    loadouts[(army_id, 6)],
                    item_id=peripheral_id,
                    display_order=None,
                ),
            )

        # Unit 7 has the same weapon content with different display_order only.
        for template_id, display_order in ((1, 1), (2, 9)):
            _insert(
                connection,
                "option_weapon_templates",
                id=template_id,
                item_id=70,
                display_order=display_order,
                quantity=None,
                raw=None,
            )
        for occurrence_id, army_id, template_id in ((31, 101, 1), (32, 102, 2)):
            row = loadouts[(army_id, 7)]
            _insert(
                connection,
                "option_weapons",
                occurrence_id=occurrence_id,
                army_id=army_id,
                unit_id=7,
                group_id=1,
                option_id=1,
                position=1,
                template_id=template_id,
            )

        # Unit 8 genuinely changes the generated order type.
        for army_id, order_type in ((101, "REGULAR"), (102, "IRREGULAR")):
            _insert(
                connection,
                "option_orders",
                army_id=army_id,
                unit_id=8,
                group_id=1,
                option_id=1,
                position=1,
                order_type=order_type,
                list_count=1,
                total_count=1,
                raw=None,
            )

        connection.commit()
    finally:
        connection.close()
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_loadout_semantics_stages_representation_and_peripheral_identity(
    tmp_path: Path,
) -> None:
    report = audit_database(_fixture_database(tmp_path))

    assert report["summary"] == {
        "loadoutOccurrenceCount": 16,
        "sourceLoadoutIdentityCount": 8,
        "repeatedSourceLoadoutIdentityCount": 8,
        "repeatedSourceLoadoutOccurrenceCount": 16,
        "baselineVariantIdentityCount": 8,
        "normalizedRepresentationVariantIdentityCount": 6,
        "resolvedPeripheralIdentityVariantIdentityCount": 7,
        "resolvedPeripheralIdentityAndNormalizedRepresentationVariantIdentityCount": 5,
    }

    equipment = report["relationships"]["equipment"]
    assert equipment["sameSourceRawVariantIdentityCount"] == 1
    assert equipment["sameSourceNormalizedVariantIdentityCount"] == 0

    weapons = report["relationships"]["weapons"]
    assert weapons["sameSourceRawVariantIdentityCount"] == 1
    assert weapons["sameSourceNormalizedVariantIdentityCount"] == 0

    peripherals = report["relationships"]["peripherals"]
    assert peripherals["sameSourceRawVariantIdentityCount"] == 2
    assert peripherals["sameSourceResolvedIdentityVariantIdentityCount"] == 1
    assert peripherals["armyLocalIdOnlyVariantIdentityCount"] == 1


def test_loadout_semantics_records_field_and_relationship_classification(
    tmp_path: Path,
) -> None:
    report = audit_database(_fixture_database(tmp_path))

    assert report["fields"]["army_id"]["classification"] == "source_provenance"
    assert report["fields"]["position"]["classification"] == "normalization_only"
    assert report["fields"]["name"]["classification"] == "canonical_fact"
    assert report["fields"]["points"]["classification"] == "contextual_delta"
    assert report["fields"]["swc"]["sameSourceVariantIdentityCount"] == 1
    assert report["fields"]["minis"]["sameSourceVariantIdentityCount"] == 0
    assert report["relationships"]["orders"]["sameSourceRawVariantIdentityCount"] == 1
    assert report["nestedFieldClassification"]["raw"]["classification"] == (
        "source_provenance"
    )


def test_loadout_semantics_rejects_unclassified_schema_drift(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("ALTER TABLE loadout_options ADD COLUMN future_field")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        LoadoutSemanticsAuditError,
        match=r"loadout_options.*unclassified future_field",
    ):
        audit_database(database)


def test_loadout_semantics_is_read_only_and_json_is_deterministic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = _fixture_database(tmp_path)
    before = _sha256(database)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    assert main([str(database), "--output", str(first)]) == 0
    assert main([str(database), "--output", str(second)]) == 0
    assert _sha256(database) == before
    assert first.read_bytes() == second.read_bytes()

    report = json.loads(first.read_text(encoding="utf-8"))
    assert report["formatVersion"] == 1
    assert report["sourceLoadoutKey"] == ["unit_id", "group_id", "option_id"]
    assert "not a proposed canonical" in report["sourceLoadoutKeyCaveat"]
    output = capsys.readouterr().out
    assert "Loadouts: 16 occurrences" in output
    assert "8 baseline" in output
