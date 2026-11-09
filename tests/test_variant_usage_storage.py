"""Relational source identity, reviewed meaning, API parity and fail-closed v11 reads."""

from __future__ import annotations

import copy
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from infinity_db.build_provenance import file_sha256
from infinity_db.curated import load_curated_directory
from infinity_db.database_set import EMBEDDED_VARIANT_RUNTIME_FILES, validate_database_set
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.variant_usage_reference import load_runtime_variant_usage
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"


def _export(path: Path, publication: dict[str, Any]) -> None:
    export_rules_database(
        load_curated_directory(ROOT / "data/curated/rules"), path,
        restrictions_manifest=json.loads(
            (ROOT / "config/validation/restrictions-source-chart.json").read_text(encoding="utf-8")
        ),
        deployed_objects=RulesDatabase(RELEASE / "rules.db").deployed_objects_payload(
            RELEASE / "infinity.db",
        ),
        variant_usage=publication,
    )


@pytest.fixture(scope="module")
def embedded(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, Any]]:
    directory = tmp_path_factory.mktemp("embedded-variants")
    publication = json.loads((RELEASE / "variant-usage.json").read_text(encoding="utf-8"))
    shutil.copyfile(RELEASE / "infinity.db", directory / "infinity.db")
    _export(directory / "rules.db", publication)
    weapons = json.loads((RELEASE / "weapon-profile-sources.json").read_text(encoding="utf-8"))
    weapons["sourceSnapshot"]["rulesDatabaseSha256"] = file_sha256(directory / "rules.db")
    (directory / "weapon-profile-sources.json").write_text(json.dumps(weapons), encoding="utf-8")
    expected = copy.deepcopy(publication)
    expected["sourceSnapshot"]["rulesDatabaseSha256"] = file_sha256(directory / "rules.db")
    return directory, expected


def test_all_committed_groups_and_source_rows_round_trip_without_a_sidecar(embedded) -> None:
    directory, expected = embedded
    rules = RulesDatabase(directory / "rules.db")
    rules.validate()
    assert rules.variant_usage_payload(directory / "infinity.db") == expected
    report = validate_database_set(directory)
    assert report["layout"] == "v11-three-file"
    assert set(report["sha256"]) == EMBEDDED_VARIANT_RUNTIME_FILES
    assert report["variantGroups"] == 151
    assert sum(len(group["sourceRows"]) for group in expected["variants"]) == 10923
    assert not (directory / "variant-usage.json").exists()
    with closing(sqlite3.connect(directory / "rules.db")) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 11
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        counts = connection.execute(
            "SELECT group_count,row_count FROM variant_usage_metadata"
        ).fetchone()
        assert counts == (
            151, 10923,
        )
        # Equivalent one-extra and two-extra TAGCom spellings keep distinct
        # reviewed source coordinates within the same semantic group.
        assert connection.execute(
            "SELECT r.group_id FROM variant_usage_source_rows r "
            "JOIN variant_usage_groups g ON g.id=r.group_id "
            "WHERE g.record_id='skill:tagcom' GROUP BY r.group_id "
            "HAVING count(DISTINCT r.combination_position)>1"
        ).fetchone() is not None


def test_runtime_api_preserves_exact_groups_and_ignores_obsolete_json(
    embedded, tmp_path: Path,
) -> None:
    directory, expected = embedded
    for name in EMBEDDED_VARIANT_RUNTIME_FILES:
        shutil.copyfile(directory / name, tmp_path / name)
    (tmp_path / "variant-usage.json").write_bytes(b"obsolete and invalid")
    app = create_app(tmp_path / "infinity.db", rules_database_path=tmp_path / "rules.db")
    assert app.variant_usage == expected
    record = "skill:doctor"
    url = f"http://variants.test/api/variant-usage?record_id={record}"
    status, headers, body = wsgi_response(app, url)
    assert status == 200
    payload = json.loads(body)
    assert payload["sourceSnapshot"] == expected["sourceSnapshot"]
    assert payload["items"] == [
        group for group in expected["variants"] if group["variant"]["recordId"] == record
    ]
    assert app.variant_usage_revision == file_sha256(tmp_path / "rules.db")
    etag = dict(headers)["ETag"]
    cached, _, content = wsgi_response(app, url, headers={"If-None-Match": etag})
    assert cached == 304 and content == b""


def test_shared_options_keep_unverified_context_and_zero_direct_counts(
    embedded, tmp_path: Path,
) -> None:
    _, expected = embedded
    publication = copy.deepcopy(expected)
    group = copy.deepcopy(next(
        group for group in expected["variants"] if group["variant"]["recordId"] == "skill:tagcom"
    ))
    row = group["sourceRows"][0]
    row.update(
        ownerKind="unit_option", armyId=None, groupId=None, parentId=7, optionId=7,
        ownerPathKey=[row["unitId"], 7],
        sourceKey=[row["catalog"], "unit_option", row["occurrenceId"]],
        sharedOption={"compatible": "[101]", "disabled": 0, "raw": None},
    )
    row["context"] = {
        "ownerKind": "unit_option", "sourceUnitId": row["unitId"], "optionId": 7,
        "applicationArmyId": None, "logicalUnitId": None, "payloadSha256": None,
        "compatibility": {
            "status": "source-only-unverified", "source": row["sharedOption"],
            "policy": "excluded from Army, Unit and profile/loadout totals",
        },
    }
    group["sourceRows"] = [row]
    for key in (
        "uniqueUnits", "uniqueArmyUnits", "distinctContexts", "distinctProfileContexts",
        "distinctLoadoutContexts",
    ):
        group[key] = 0
    group["sourceRelationshipRows"] = 1
    publication["variants"] = [group]
    path = tmp_path / "rules.db"
    _export(path, publication)
    result = RulesDatabase(path).variant_usage_payload(RELEASE / "infinity.db")
    assert result is not None and result["variants"] == [group]


@pytest.mark.parametrize(
    "damage", ["missing-table", "source-reference", "negative-reference", "counts", "extras"],
)
def test_damaged_relational_projection_fails_without_json_fallback(
    embedded, tmp_path: Path, damage: str,
) -> None:
    directory, _ = embedded
    path = tmp_path / "rules.db"
    shutil.copyfile(directory / "rules.db", path)
    with closing(sqlite3.connect(path)) as connection, connection:
        if damage == "missing-table":
            connection.execute("DROP TABLE variant_usage_extras")
        elif damage in {"source-reference", "negative-reference"}:
            connection.execute(
                "UPDATE variant_usage_source_rows SET combination_position=? "
                "WHERE combination_position IS NOT NULL",
                (-1 if damage == "negative-reference" else 999,),
            )
        elif damage == "counts":
            connection.execute(
                "UPDATE variant_usage_groups SET unique_units=unique_units+1 WHERE id=1"
            )
        else:
            connection.execute(
                "UPDATE variant_usage_extras SET raw_value='unreviewed' WHERE row_id=1"
            )
    with pytest.raises(ValueError):
        RulesDatabase(path).validate()
    (tmp_path / "variant-usage.json").write_bytes((RELEASE / "variant-usage.json").read_bytes())
    with pytest.raises((ValueError, sqlite3.Error)):
        load_runtime_variant_usage(directory / "infinity.db", path)


def test_source_occurrences_cannot_be_duplicated(embedded, tmp_path: Path) -> None:
    directory, _ = embedded
    path = tmp_path / "rules.db"
    shutil.copyfile(directory / "rules.db", path)
    with closing(sqlite3.connect(path)) as connection, connection:
        first = connection.execute(
            "SELECT catalog,owner_kind,occurrence_id FROM variant_usage_source_rows WHERE id=1"
        ).fetchone()
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE variant_usage_source_rows SET catalog=?,owner_kind=?,occurrence_id=? "
                "WHERE id=2",
                first,
            )


def test_wrong_army_bytes_are_rejected(embedded, tmp_path: Path) -> None:
    directory, _ = embedded
    army = tmp_path / "infinity.db"
    content = bytearray((directory / "infinity.db").read_bytes())
    content[96:100] = (int.from_bytes(content[96:100], "big") + 1).to_bytes(4, "big")
    army.write_bytes(content)
    with pytest.raises(ValueError, match="selected Army"):
        RulesDatabase(directory / "rules.db").variant_usage_payload(army)


def test_explicit_rules_selection_and_byte_revision_change_cache_validators(
    embedded, tmp_path: Path,
) -> None:
    directory, expected = embedded
    url = "http://variants.test/api/variant-usage?record_id=skill:doctor"
    original = create_app(directory / "infinity.db", rules_database_path=directory / "rules.db")
    _, original_headers, _ = wsgi_response(original, url)
    path = tmp_path / "rules.db"
    content = bytearray((directory / "rules.db").read_bytes())
    content[96:100] = (int.from_bytes(content[96:100], "big") + 1).to_bytes(4, "big")
    path.write_bytes(content)
    changed = create_app(directory / "infinity.db", rules_database_path=path)
    assert changed.variant_usage is not None
    assert changed.variant_usage["variants"] == expected["variants"]
    status, headers, _ = wsgi_response(
        changed, url, headers={"If-None-Match": dict(original_headers)["ETag"]},
    )
    assert status == 200 and dict(headers)["ETag"] != dict(original_headers)["ETag"]
    assert changed.variant_usage["sourceSnapshot"]["rulesDatabaseSha256"] == file_sha256(path)


def test_unknown_schema_does_not_attempt_a_legacy_json_fallback(
    embedded, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory, _ = embedded
    path = tmp_path / "rules.db"
    shutil.copyfile(directory / "rules.db", path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA user_version=999")

    def forbidden(*args: Any) -> None:
        pytest.fail("Unsupported schemas must not select a JSON publication")

    monkeypatch.setattr(
        "infinity_db.variant_usage_reference.load_variant_usage_publication", forbidden,
    )
    with pytest.raises(ValueError, match="Unsupported Rules schema"):
        load_runtime_variant_usage(directory / "infinity.db", path)


def test_unreviewed_rule_reference_cannot_replace_a_valid_export(embedded, tmp_path: Path) -> None:
    _, expected = embedded
    changed = copy.deepcopy(expected)
    changed["variants"][0]["variant"]["recordId"] = "skill:no-reviewed-definition"
    changed["variants"][0]["variantKey"] = json.dumps(
        changed["variants"][0]["variant"], sort_keys=True, separators=(",", ":"),
    )
    changed["variants"].sort(key=lambda group: group["variantKey"])
    path = tmp_path / "rules.db"
    path.write_bytes(b"previous output")
    with pytest.raises(ValueError, match="reviewed rule definition"):
        _export(path, changed)
    assert path.read_bytes() == b"previous output"
