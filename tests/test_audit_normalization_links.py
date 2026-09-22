from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db.database.schema import create_schema
from tools.audit_normalization_links import (
    FILTER_CATALOG_LINKS,
    NormalizationLinkAuditError,
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


def _fixture_database(tmp_path: Path) -> Path:
    path = tmp_path / "infinity.db"
    connection = sqlite3.connect(path)
    try:
        create_schema(connection, {})
        _insert(
            connection,
            "__infinity_metadata",
            key="_meta",
            value=json.dumps(
                {
                    "snapshotArchiveSha256": "a" * 64,
                    "snapshotDownloadedOn": "2026-09-18",
                }
            ),
        )
        _insert(connection, "factions", id=101)
        _insert(connection, "army_lists", id=101)
        for _source_name, (_link_table, catalog_table) in FILTER_CATALOG_LINKS.items():
            _insert(connection, catalog_table, id=1)
        for index, (_source_name, (link_table, _catalog_table)) in enumerate(
            FILTER_CATALOG_LINKS.items(), start=1
        ):
            _insert(
                connection,
                link_table,
                army_id=101,
                item_id=1,
                position=1,
                mercs=1 if index == 1 else None,
                specops=None,
                teamops=None,
            )

        _insert(connection, "units", id=1)
        _insert(connection, "army_units", army_id=101, unit_id=1)
        _insert(connection, "profile_groups", army_id=101, unit_id=1, group_id=1)
        _insert(
            connection,
            "loadout_options",
            army_id=101,
            unit_id=1,
            group_id=1,
            option_id=1,
        )
        _insert(connection, "option_weapon_templates", id=1, item_id=1, quantity=1)
        _insert(
            connection,
            "option_weapons",
            occurrence_id=1,
            army_id=101,
            unit_id=1,
            group_id=1,
            option_id=1,
            position=1,
            template_id=1,
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_normalization_link_audit_classifies_structural_links(tmp_path: Path) -> None:
    report = audit_database(_fixture_database(tmp_path))

    filters = report["sourceFilterCatalogLinks"]
    assert filters["classification"] == "normalization_only_source_filter_index"
    assert filters["tableCount"] == 8
    assert filters["rowCount"] == 8
    assert filters["tables"][0]["contextFlagTrueCounts"]["mercs"] == 1

    templates = report["optionWeaponTemplateIndirection"]
    assert templates["classification"] == "normalization_only_storage_indirection"
    assert templates["occurrenceRowCount"] == 1
    assert templates["templateRowCount"] == 1
    assert templates["danglingOccurrenceCount"] == 0
    assert templates["unreferencedTemplateCount"] == 0

    canonical = report["canonicalizationLinks"]
    assert canonical["classification"] == "canonicalization_or_provenance_infrastructure"
    assert canonical["linkCount"] == 7


def test_normalization_link_audit_rejects_missing_schema(tmp_path: Path) -> None:
    path = tmp_path / "broken.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE __infinity_metadata (key, value)")
    connection.commit()
    connection.close()

    with pytest.raises(NormalizationLinkAuditError, match="missing required table"):
        audit_database(path)


def test_normalization_link_audit_cli_writes_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database = _fixture_database(tmp_path)
    output = tmp_path / "report.json"

    assert main([str(database), "--output", str(output)]) == 0
    captured = capsys.readouterr().out
    assert "InfinityDB normalization link semantics audit" in captured
    assert "Source filter joins: 8 tables | 8 rows" in captured
    assert json.loads(output.read_text(encoding="utf-8"))["formatVersion"] == 1
