from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_unit_semantics import (
    EXPECTED_COLUMNS,
    UnitSemanticsAuditError,
    audit_database,
    main,
)

ROOT = Path(__file__).resolve().parents[1]


def _insert(connection: sqlite3.Connection, table: str, **values: object) -> None:
    columns = ", ".join(f'"{name}"' for name in values)
    placeholders = ", ".join("?" for _ in values)
    connection.execute(
        f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})',
        tuple(values.values()),
    )


def _unit(unit_id: int, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "id": unit_id,
        "id_army": unit_id,
        "canonical_faction_id": 101,
        "main_army_id": 101,
        "display_army_id": 101,
        "isc": f"Unit {unit_id}",
        "isc_abbr": None,
        "name": f"UNIT {unit_id}",
        "slug": f"unit-{unit_id}",
        "notes": None,
        "spectables": None,
        "source_defined": 1,
        "source_role": "standard",
        "relation_reference_count": 0,
    }
    row.update(overrides)
    return row


def _option(unit_id: int, *, points: int) -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "option_id": 1,
        "position": 1,
        "name": "TEAM",
        "points": points,
        "swc": "1",
        "minis": 2,
        "disabled": 0,
        "compatible": None,
        "habilities": "[]",
        "raw": None,
    }


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        for table, columns in EXPECTED_COLUMNS.items():
            definition = ", ".join(f'"{column}"' for column in columns)
            connection.execute(f'CREATE TABLE "{table}" ({definition})')

        connection.execute("PRAGMA user_version = 13")
        identity_document = json.loads(
            (ROOT / "config" / "identity" / "source-identities.json").read_text(
                encoding="utf-8"
            )
        )
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
        _insert(
            connection,
            "__infinity_metadata",
            key="identityConfig",
            value=json.dumps(identity_document, sort_keys=True),
        )

        for army_id, kind in ((101, "army"), (199, "reinforcement"), (901, "army")):
            _insert(
                connection,
                "army_lists",
                id=army_id,
                name=f"Army {army_id}",
                slug=f"army-{army_id}",
                kind=kind,
                version=None,
                reinforcement_id=None,
                source_file=None,
                source_sha256=None,
                resume=None,
                teamops=None,
                legacy_fireteams=None,
                filter_attrs=None,
                filter_points=None,
                filter_swc=None,
                fireteam_description=None,
                fireteam_spec=None,
            )

        source_rows = [
            _unit(1, name="BOLT", isc="Bolt", slug="bolt"),
            _unit(
                1001,
                id_army=1001,
                canonical_faction_id=199,
                main_army_id=None,
                display_army_id=None,
                name="REINF: BOLT",
                isc="Reinf. Bolt",
                slug="reinf-bolt",
            ),
            _unit(2, name="BOUNTY HUNTER", isc="Bounty Hunter", slug="bounty-hunter"),
            _unit(
                10002,
                id_army=10002,
                canonical_faction_id=1,
                main_army_id=None,
                display_army_id=901,
                name="BOUNTY HUNTER",
                isc="Bounty Hunter",
                slug="merc-bounty-hunter",
                source_role="mercenary_variant",
            ),
            _unit(3, name="NEEMA", isc="Neema", slug="neema"),
            _unit(
                1003,
                id_army=1003,
                canonical_faction_id=199,
                main_army_id=None,
                display_army_id=None,
                name="REINF: NEEMA",
                isc="Reinf. Neema",
                slug="reinf-neema",
                notes="Only one Neema may be included.",
            ),
            _unit(
                4,
                name="SPEC TABLE UNIT",
                isc="Spec Table Unit",
                slug="spec-table-unit",
                spectables='{"table":{"items":[]}}',
            ),
            _unit(5, name="SCARFACE", isc="Scarface", slug="scarface"),
            _unit(
                10005,
                id_army=10005,
                canonical_faction_id=1,
                main_army_id=None,
                display_army_id=901,
                name="SCARFACE",
                isc="Scarface",
                slug="merc-scarface",
                source_role="mercenary_variant",
            ),
            _unit(6, name="MIRAGE", isc="Mirage", slug="mirage"),
            _unit(
                1006,
                id_army=1006,
                canonical_faction_id=199,
                main_army_id=None,
                display_army_id=None,
                name="REINF: MIRAGE",
                isc="Reinf. Mirage",
                slug="reinf-mirage",
            ),
        ]
        for row in source_rows:
            _insert(connection, "units", **row)

        logical_groups = {
            1: (1, 1001),
            2: (2, 10002),
            3: (3, 1003),
            4: (4,),
            5: (5, 10005),
            6: (6, 1006),
        }
        for logical_id, source_ids in logical_groups.items():
            _insert(
                connection,
                "logical_units",
                id=logical_id,
                representative_unit_id=logical_id,
            )
            for source_id in source_ids:
                _insert(
                    connection,
                    "logical_unit_sources",
                    source_unit_id=source_id,
                    logical_unit_id=logical_id,
                )

        source_armies = {
            1: 101,
            1001: 199,
            2: 101,
            10002: 901,
            3: 101,
            1003: 199,
            4: 101,
            5: 101,
            10005: 901,
            6: 101,
            1006: 199,
        }
        for position, (source_id, army_id) in enumerate(source_armies.items(), start=1):
            _insert(
                connection,
                "army_units",
                army_id=army_id,
                unit_id=source_id,
                position=position,
                filters=None,
                availability_kind=("mercenary" if source_id in {10002, 10005} else "standard"),
            )
            if source_id not in {10002, 10005}:
                _insert(
                    connection,
                    "unit_factions",
                    unit_id=source_id,
                    faction_id=army_id,
                    position=1,
                )

        for source_id in (5, 10005):
            _insert(connection, "unit_options", **_option(source_id, points=80))
            _insert(
                connection,
                "unit_option_orders",
                unit_id=source_id,
                option_id=1,
                position=1,
                order_type="REGULAR",
                list_count=2,
                total_count=2,
                raw=None,
            )
            _insert(
                connection,
                "unit_option_includes",
                unit_id=source_id,
                option_id=1,
                position=1,
                target_group_id=1,
                target_option_id=1,
                quantity=1,
                raw=None,
            )

        for source_id, points in ((6, 60), (1006, 51)):
            _insert(connection, "unit_options", **_option(source_id, points=points))
            _insert(
                connection,
                "unit_option_orders",
                unit_id=source_id,
                option_id=1,
                position=1,
                order_type="REGULAR",
                list_count=1,
                total_count=1,
                raw=None,
            )
            _insert(
                connection,
                "unit_option_includes",
                unit_id=source_id,
                option_id=1,
                position=1,
                target_group_id=1,
                target_option_id=1,
                quantity=1,
                raw=None,
            )

        connection.commit()
    finally:
        connection.close()
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_unit_semantics_audit_classifies_representative_and_contextual_data(
    tmp_path: Path,
) -> None:
    report = audit_database(_fixture_database(tmp_path))

    assert report["summary"] == {
        "sourceUnitCount": 11,
        "logicalUnitCount": 6,
        "repeatedLogicalUnitCount": 5,
        "repeatedSourceUnitCount": 10,
        "singletonLogicalUnitCount": 1,
        "logicalUnitSourceCountDistribution": {"1": 1, "2": 5},
        "reinforcementOnlySourceUnitCount": 3,
        "mercenaryVariantSourceUnitCount": 2,
    }

    representative = report["representativeRule"]
    assert representative["representativeReinforcementOrNonStandardCount"] == 0
    assert representative["nonRepresentativeReinforcementCount"] == 3
    assert representative["nonRepresentativeMercenaryVariantCount"] == 2
    assert representative["repeatedLogicalUnitsWithAlternateGeneralLabels"] == 5
    assert representative["logicalUnitsWithNonRepresentativeNoteDeltas"] == 1
    assert representative["nonRepresentativeNoteDeltaSourceCount"] == 1

    assert report["fields"]["slug"]["variantLogicalUnitCount"] == 5
    assert report["fields"]["notes"]["variantLogicalUnitCount"] == 1
    assert report["fields"]["spectables"]["nonNullSourceUnitCount"] == 1
    assert report["fields"]["spectables"]["repeatedLogicalUnitSupportCount"] == 0

    normalized = report["diagnosticLabelNormalization"]["fields"]
    assert normalized["name"]["rawVariantLogicalUnitCount"] == 3
    assert normalized["name"]["afterIdentityNormalizationVariantLogicalUnitCount"] == 0
    assert normalized["isc"]["rawVariantLogicalUnitCount"] == 3
    assert normalized["isc"]["afterIdentityNormalizationVariantLogicalUnitCount"] == 0

    factions = report["relationships"]["unit_factions"]
    assert factions["variantRepeatedLogicalUnitCount"] == 5

    options = report["relationships"]["unit_options"]
    assert options["rowCount"] == 4
    assert options["sourceUnitCount"] == 4
    assert options["logicalUnitCount"] == 2
    assert options["repeatedLogicalUnitWithOptionsCount"] == 2
    assert options["variantRepeatedLogicalUnitCollectionCount"] == 1
    assert options["fields"]["points"]["variantRepeatedObservationalKeyCount"] == 1
    assert options["relationships"]["unit_option_orders"][
        "variantRepeatedObservationalKeyCount"
    ] == 0
    assert options["relationships"]["unit_option_includes"][
        "variantRepeatedObservationalKeyCount"
    ] == 0

    candidate = report["candidateModel"]
    assert candidate["canonicalLogicalUnit"]["rowCount"] == 6
    assert candidate["sourceLinks"]["rowCount"] == 11
    assert candidate["aliases"]["occurrenceCount"] == 11
    assert candidate["aliases"]["distinctLogicalValueCount"] == 11
    assert candidate["aliases"]["logicalUnitCount"] == 5
    assert candidate["notes"]["occurrenceCount"] == 1
    assert candidate["notes"]["logicalUnitCount"] == 1
    assert candidate["spectables"]["occurrenceCount"] == 1
    assert candidate["spectables"]["logicalUnitCount"] == 1
    assert candidate["unitOptions"]["rowCount"] == 4


def test_unit_semantics_audit_is_deterministic_and_read_only(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    before = _sha256(database)

    first = audit_database(database)
    second = audit_database(database)

    assert first == second
    assert _sha256(database) == before


def test_unit_semantics_audit_fails_when_classified_schema_drifts(tmp_path: Path) -> None:
    database = _fixture_database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute('ALTER TABLE "units" ADD COLUMN "new_field"')
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(UnitSemanticsAuditError, match="classification for units is stale"):
        audit_database(database)


def test_unit_semantics_audit_cli_writes_report(tmp_path: Path, capsys) -> None:
    database = _fixture_database(tmp_path)
    output = tmp_path / "unit-semantics.json"

    assert main([str(database), "--output", str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == "InfinityDB logical-unit semantics audit"
    assert report["formatVersion"] == 2
    assert "920 source" not in capsys.readouterr().out
