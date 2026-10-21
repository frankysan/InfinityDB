from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

from infinity_army_data.merge import load_sources
from tools.report_reference_baseline import (
    _NESTED_SOURCE_FIELDS,
    ReferenceBaselineError,
    _artifact_evidence,
    _revision_oldid,
    _route_hint,
    _source_location,
    _verify_army_archive_sources,
    _verify_published_characteristics_orders,
    _verify_published_peripherals_includes,
    _verify_published_profile_extras,
    _verify_published_profile_references,
    build_baseline,
    main,
    render_markdown,
    verify_served_revision,
)

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"


def test_baseline_reports_pinned_publication_without_claiming_completeness() -> None:
    report = build_baseline(ARMY_DB, RULES_DB)

    assert report["status"] == "initial-evidence-only-not-a-completeness-verdict"
    assert report["armySnapshot"]["archiveVerification"] == "not-supplied"
    assert len(report["armySnapshot"]["archiveSha256"]) == 64
    assert len(report["rulesPublication"]["publishedDatabaseSha256"]) == 64
    combined = (
        report["armySnapshot"]["publishedDatabaseSha256"] + ":"
        + report["rulesPublication"]["publishedDatabaseSha256"]
    )
    assert report["runtimeSnapshotRevision"] == hashlib.sha256(
        combined.encode()
    ).hexdigest()
    # The published rules database includes four core missions and one
    # separately scoped ITS Season 18 Battleground pilot.
    assert report["scenarioMembershipCount"] == 5
    assert report["scenarioMemberships"] == [
        {
            "collectionId": "its-18",
            "collectionRevision": "2026.09.01",
            "position": 0,
            "scenarioId": "scenario:battleground",
            "publicationCollectionId": "its-season-18-2026.09.01",
        },
        *[
            {
                "collectionId": "n5-core",
                "collectionRevision": "5.3",
                "position": position,
                "scenarioId": f"scenario:{slug}",
                "publicationCollectionId": "n5-core-v5.3",
            }
            for position, slug in enumerate((
                "annihilation", "domination", "supplies", "firefight"
            ))
        ],
    ]
    with sqlite3.connect(RULES_DB) as db:
        assert db.execute(
            "SELECT collection_id, COUNT(*) FROM scenario_memberships "
            "GROUP BY collection_id ORDER BY collection_id"
        ).fetchall() == [("its-18", 1), ("n5-core", 4)]
    assert "rules:scenario" in {item["id"] for item in report["inventory"]}
    assert "army:profiles" in {item["id"] for item in report["inventory"]}
    assert all(item["scopeDecision"] == "pending" for item in report["inventory"])
    assert all(item["browserEntryPoint"] is None for item in report["inventory"])
    assert all(item["apiReadPath"] is None for item in report["inventory"])
    assert all(item["factCoverage"] == "not-reviewed-against-source"
               for item in report["inventory"])
    assert len(report["sourceInventory"]) >= len(report["sourceGroups"])
    # URL-backed Wiki revisions cannot be collapsed into one generic source.
    revisions = [source for source in report["sourceGroups"]
                 if source["verificationStatus"] == "revision-url-pinned"]
    assert len(revisions) > 1
    assert len({source["url"] for source in revisions}) == len(revisions)
    assert all(source["revisionOldid"] for source in revisions)
    assert sum(report["sourceVerificationCounts"].values()) == len(report["sourceGroups"])
    assert all(item["rowsWithCitations"] <= item["publishedRows"]
               for item in report["inventory"] if item["rowsWithCitations"] is not None)


def test_route_hints_reuse_published_surfaces_without_claiming_coverage() -> None:
    from infinity_db.web.presentation import PresentationHandler
    from infinity_db.web.routes import metric_route

    report = build_baseline(ARMY_DB, RULES_DB)
    entries = {item["id"]: item for item in report["inventory"]}
    assert entries["army:armies"]["routeHint"] == {
        "mode": "overview", "browser": "/armies", "api": "/api/armies",
    }
    assert entries["army:profiles"]["routeHint"] == {
        "mode": "nested-unit", "browser": "/units/:id", "api": "/api/units/:id",
    }
    assert entries["rules:weapon"]["routeHint"] == {
        "mode": "catalog", "browser": "/weapons", "api": "/api/weapons",
    }
    assert entries["rules:attribute"]["routeHint"] == {
        "mode": "embedded-glossary", "browser": "/glossary", "api": "/api/glossary",
    }
    assert entries["rules:rule"]["routeHint"] is None
    assert _route_hint("army:catalog:unknown") is None

    presentation = PresentationHandler(
        source_data_changed_on=None,
        snapshot_downloaded_on=None,
        snapshot_revision="audit-test",
    )
    for entry in entries.values():
        hint = entry["routeHint"]
        if hint is None:
            continue
        browser = hint["browser"].replace(":id", "test-identity")
        api = hint["api"].replace(":id", "test-identity")
        assert metric_route(browser, ()) != "/other", (entry["id"], browser)
        assert metric_route(api, ()) != "/other", (entry["id"], api)
        assert presentation.handle(browser, "") is not None, (entry["id"], browser)
        # Discovery is not proof that each published source fact is presented.
        assert entry["browserEntryPoint"] is None
        assert entry["apiReadPath"] is None
        assert entry["presentationCoverage"] == "not-reviewed"
        assert entry["scopeDecision"] == "pending"


def test_unavailable_sources_and_pinned_url_revisions_are_not_conflated(
    tmp_path: Path,
) -> None:
    report = build_baseline(ARMY_DB, RULES_DB, root=tmp_path)
    assert any(item["localStatus"] == "missing-local-artifact"
               for item in report["sourceGroups"])
    assert any(item["localStatus"] == "url-backed/no-local-artifact"
               for item in report["sourceGroups"])
    assert _source_location(tmp_path, "../outside.pdf") == "unsafe-declared-path"
    assert _source_location(tmp_path, r"..\outside.pdf") == "unsafe-declared-path"
    assert _source_location(tmp_path, r"C:\outside.pdf") == "unsafe-declared-path"
    assert _source_location(tmp_path, None) == "url-backed/no-local-artifact"
    assert "not a completeness verdict" in render_markdown(report)


def test_local_source_hash_evidence_and_unpinned_pdf(tmp_path: Path) -> None:
    path = tmp_path / "rules.pdf"
    path.write_bytes(b"pinned bytes")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()

    matched = _artifact_evidence(tmp_path, "rules.pdf", None, {checksum})
    assert matched["verificationStatus"] == "hash-matched"
    assert matched["artifactSha256"] == checksum
    assert matched["declaredHashMatches"] is True

    unpinned = _artifact_evidence(tmp_path, "rules.pdf", None, set())
    assert unpinned["verificationStatus"] == "local-file-no-hash-pin"
    assert unpinned["artifactSha256"] == checksum

    wrong = _artifact_evidence(tmp_path, "rules.pdf", None, {"0" * 64})
    assert wrong["verificationStatus"] == "hash-mismatch-needs-review"
    assert wrong["declaredHashMatches"] is False
    conflict = _artifact_evidence(tmp_path, "rules.pdf", None, {checksum, "0" * 64})
    assert conflict["verificationStatus"] == "conflicting-source-hashes"


def test_url_pin_is_not_offline_content_verification(tmp_path: Path) -> None:
    exact = "https://infinitythewiki.com/index.php?title=Reset&oldid=3056"
    assert _revision_oldid(exact) == "3056"
    assert _revision_oldid("https://infinitythewiki.com/wiki/Reset") is None
    assert _revision_oldid(exact + "&oldid=3057") is None
    pinned = _artifact_evidence(tmp_path, None, exact, set())
    assert pinned["verificationStatus"] == "revision-url-pinned"
    assert pinned["artifactSha256"] is None
    assert pinned["declaredHashMatches"] is None
    assert _artifact_evidence(tmp_path, None, "https://example.org", set())[
        "verificationStatus"] == "url-without-revision-pin"


def _synthetic_army_archive(tmp_path: Path) -> Path:
    archive = tmp_path / "army.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("metadata.json", '{"source":"fixture"}')
        output.writestr(
            "101-first.json", json.dumps({
                "version": "7.26246.158",
                "units": [
                    {
                        "id": 10,
                        "profileGroups": [{
                            "id": 7, "category": 5, "isc": "Main",
                            "profiles": [{
                                "id": 1, "name": "Test Unit", "type": 2,
                                "move": [15, 10], "cc": 16, "w": 1,
                                "str": False,
                                "chars": [51, 52],
                                "peripheral": [{"id": 74, "order": 2, "q": 3}],
                                "includes": [{"group": 7, "option": 9, "q": 2}],
                                "skills": [
                                    {"id": 11, "q": 1, "order": 2, "extra": [41, 42]},
                                    {"id": 12, "q": 2, "order": 1},
                                ],
                                "equip": [{"id": 21, "extra": [43]}],
                                "weapons": [{"id": 31, "order": 3, "extra": [44]}],
                            }],
                            "options": [{
                                "id": 9, "name": "Test Loadout",
                                "points": 17, "swc": "0.5",
                                "minis": 1, "disabled": False,
                                "chars": [53],
                                "peripheral": [{"id": 75, "q": 1}],
                                "includes": [{"group": 7, "option": 9, "q": 1}],
                                "orders": [
                                    {"type": "regular", "list": 1, "total": 2},
                                    {"type": "irregular", "list": 0, "total": 1},
                                ],
                                "skills": [{"id": 11, "q": 1, "extra": [45]}],
                                "equip": [{"id": 22, "order": 2, "extra": [46]}],
                                "weapons": [{"id": 32, "extra": [47, 48]}],
                            }],
                        }],
                    },
                    {"id": 11},
                ],
                "reinforcements": 201,
            })
        )
        output.writestr(
            "201-second.json", json.dumps({
                "version": "7.26246.159",
                "units": [{"id": 11}],
            })
        )
    return archive


def test_published_peripherals_and_includes_reject_drift(tmp_path: Path) -> None:
    sources, _ = load_sources(_synthetic_army_archive(tmp_path))
    with sqlite3.connect(":memory:") as db:
        db.execute(
            "CREATE TABLE loadout_payload_occurrences "
            "(army_id, unit_id, group_id, option_id, loadout_payload_id)"
        )
        db.execute(
            "INSERT INTO loadout_payload_occurrences VALUES (101, 10, 7, 9, 50)"
        )
        db.execute(
            "CREATE TABLE profile_peripherals "
            "(army_id, unit_id, group_id, profile_id, position, item_id, "
            "display_order, quantity)"
        )
        db.execute(
            "CREATE TABLE option_peripherals "
            "(army_id, unit_id, group_id, option_id, position, item_id, "
            "display_order, quantity)"
        )
        for kind, identity in (("profile", "profile_id"), ("loadout", "option_id")):
            db.execute(
                f"CREATE TABLE {kind}_occurrence_includes "
                f"(army_id, unit_id, group_id, {identity}, position, "
                "target_loadout_payload_id, quantity)"
            )
        db.execute(
            "INSERT INTO profile_peripherals VALUES (101, 10, 7, 1, 1, 74, 2, 3)"
        )
        db.execute(
            "INSERT INTO option_peripherals VALUES (101, 10, 7, 9, 1, 75, NULL, 1)"
        )
        db.execute(
            "INSERT INTO profile_occurrence_includes VALUES (101, 10, 7, 1, 1, 50, 2)"
        )
        db.execute(
            "INSERT INTO loadout_occurrence_includes VALUES (101, 10, 7, 9, 1, 50, 1)"
        )
        expected = {
            "profile.peripherals": 1, "loadout.peripherals": 1,
            "profile.includes": 1, "loadout.includes": 1,
        }
        assert _verify_published_peripherals_includes(db, sources) == expected

        db.execute("UPDATE profile_peripherals SET item_id = 999")
        with pytest.raises(ReferenceBaselineError, match="relationship differs"):
            _verify_published_peripherals_includes(db, sources)
        db.execute("UPDATE profile_peripherals SET item_id = 74")
        db.execute("UPDATE option_peripherals SET quantity = 5")
        with pytest.raises(ReferenceBaselineError, match="relationship differs"):
            _verify_published_peripherals_includes(db, sources)
        db.execute("UPDATE option_peripherals SET quantity = 1")
        db.execute("UPDATE profile_occurrence_includes SET target_loadout_payload_id = 99")
        with pytest.raises(ReferenceBaselineError, match="relationship differs"):
            _verify_published_peripherals_includes(db, sources)
        db.execute("UPDATE profile_occurrence_includes SET target_loadout_payload_id = 50")
        db.execute("UPDATE loadout_occurrence_includes SET position = 2")
        with pytest.raises(ReferenceBaselineError, match="occurrence positions differ"):
            _verify_published_peripherals_includes(db, sources)
        db.execute("UPDATE loadout_occurrence_includes SET position = 1")
        db.execute("DELETE FROM profile_peripherals")
        with pytest.raises(ReferenceBaselineError, match="occurrence positions differ"):
            _verify_published_peripherals_includes(db, sources)
        db.execute("INSERT INTO profile_peripherals VALUES (101, 10, 7, 1, 1, 74, 2, 3)")
        db.execute("INSERT INTO profile_peripherals VALUES (101, 10, 7, 1, 1, 74, 2, 3)")
        with pytest.raises(ReferenceBaselineError, match="duplicate"):
            _verify_published_peripherals_includes(db, sources)


def test_published_characteristics_and_orders_reject_drift(tmp_path: Path) -> None:
    sources, _ = load_sources(_synthetic_army_archive(tmp_path))
    with sqlite3.connect(":memory:") as db:
        for kind, identity in (("profile", "profile_id"), ("loadout", "option_id")):
            db.execute(
                f"CREATE TABLE {kind}_payload_occurrences "
                f"(army_id, unit_id, group_id, {identity}, {kind}_payload_id)"
            )
            db.execute(
                f"INSERT INTO {kind}_payload_occurrences VALUES (101, 10, 7, "
                f"{1 if kind == 'profile' else 9}, 1)"
            )
            db.execute(
                f"CREATE TABLE {kind}_payload_characteristics "
                f"({kind}_payload_id, position, characteristic_id)"
            )
        db.execute(
            "CREATE TABLE loadout_payload_orders "
            "(loadout_payload_id, position, order_type, list_count, total_count)"
        )
        db.executemany(
            "INSERT INTO profile_payload_characteristics VALUES (?, ?, ?)",
            [(1, 1, 51), (1, 2, 52)],
        )
        db.execute("INSERT INTO loadout_payload_characteristics VALUES (1, 1, 53)")
        db.executemany(
            "INSERT INTO loadout_payload_orders VALUES (?, ?, ?, ?, ?)",
            [(1, 1, "regular", 1, 2), (1, 2, "irregular", 0, 1)],
        )
        expected = {
            "profile.characteristics": 2,
            "loadout.characteristics": 1,
            "loadout.orders": 2,
        }
        assert _verify_published_characteristics_orders(db, sources) == expected

        db.execute(
            "UPDATE profile_payload_characteristics SET characteristic_id = 99 "
            "WHERE position = 2"
        )
        with pytest.raises(ReferenceBaselineError, match="source/published facts differ"):
            _verify_published_characteristics_orders(db, sources)
        db.execute(
            "UPDATE profile_payload_characteristics SET characteristic_id = 52 "
            "WHERE position = 2"
        )
        db.execute("UPDATE loadout_payload_orders SET total_count = 9 WHERE position = 1")
        with pytest.raises(ReferenceBaselineError, match="source/published facts differ"):
            _verify_published_characteristics_orders(db, sources)
        db.execute("UPDATE loadout_payload_orders SET total_count = 2 WHERE position = 1")
        db.execute("UPDATE loadout_payload_orders SET position = 3 WHERE position = 2")
        with pytest.raises(ReferenceBaselineError, match="occurrence positions differ"):
            _verify_published_characteristics_orders(db, sources)
        db.execute("UPDATE loadout_payload_orders SET position = 2 WHERE position = 3")
        db.execute("DELETE FROM loadout_payload_characteristics")
        with pytest.raises(ReferenceBaselineError, match="occurrence positions differ"):
            _verify_published_characteristics_orders(db, sources)
        db.execute("INSERT INTO loadout_payload_characteristics VALUES (1, 1, 53)")
        db.execute("INSERT INTO loadout_payload_characteristics VALUES (1, 1, 53)")
        with pytest.raises(ReferenceBaselineError, match="duplicate"):
            _verify_published_characteristics_orders(db, sources)


def test_published_nested_reference_occurrences_reject_source_drift(
    tmp_path: Path,
) -> None:
    sources, _ = load_sources(_synthetic_army_archive(tmp_path))
    with sqlite3.connect(":memory:") as db:
        for kind, reference_name in (
            ("profile", "profile_id"),
            ("loadout", "option_id"),
        ):
            db.execute(
                f"CREATE TABLE {kind}_payload_occurrences "
                f"(army_id, unit_id, group_id, {reference_name}, {kind}_payload_id)"
            )
            db.execute(
                f"INSERT INTO {kind}_payload_occurrences VALUES (101, 10, 7, "
                f"{1 if kind == 'profile' else 9}, 1)"
            )
            for field in ("skills", "equipment", "weapons"):
                db.execute(
                    f"CREATE TABLE {kind}_payload_{field} "
                    f"({kind}_payload_id, position, item_id, display_order, quantity)"
                )
                suffix = "skill_extras" if field == "skills" else (
                    "weapon_extras" if field == "weapons" else "equipment_extras"
                )
                db.execute(
                    f"CREATE TABLE {kind}_payload_{suffix} "
                    f"({kind}_payload_id, occurrence_position, position, extra_id)"
                )
        values = {
            "profile_payload_skills": [(1, 1, 11, 2, 1), (1, 2, 12, 1, 2)],
            "profile_payload_equipment": [(1, 1, 21, None, None)],
            "profile_payload_weapons": [(1, 1, 31, 3, None)],
            "loadout_payload_skills": [(1, 1, 11, None, 1)],
            "loadout_payload_equipment": [(1, 1, 22, 2, None)],
            "loadout_payload_weapons": [(1, 1, 32, None, None)],
        }
        for table, rows in values.items():
            db.executemany(f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?)", rows)
        extras = {
            "profile_payload_skill_extras": [(1, 1, 1, 41), (1, 1, 2, 42)],
            "profile_payload_equipment_extras": [(1, 1, 1, 43)],
            "profile_payload_weapon_extras": [(1, 1, 1, 44)],
            "loadout_payload_skill_extras": [(1, 1, 1, 45)],
            "loadout_payload_equipment_extras": [(1, 1, 1, 46)],
            "loadout_payload_weapon_extras": [(1, 1, 1, 47), (1, 1, 2, 48)],
        }
        for table, rows in extras.items():
            db.executemany(f"INSERT INTO {table} VALUES (?, ?, ?, ?)", rows)
        assert _verify_published_profile_extras(db, sources) == {
            "profile.skills": 2, "profile.equipment": 1, "profile.weapons": 1,
            "loadout.skills": 1, "loadout.equipment": 1, "loadout.weapons": 2,
        }
        db.execute("UPDATE profile_payload_skill_extras SET extra_id = 99 WHERE position = 2")
        with pytest.raises(ReferenceBaselineError, match="published extra differs"):
            _verify_published_profile_extras(db, sources)
        db.execute("UPDATE profile_payload_skill_extras SET extra_id = 42 WHERE position = 2")
        db.execute("UPDATE loadout_payload_weapon_extras SET position = 3 WHERE position = 2")
        with pytest.raises(ReferenceBaselineError, match="extra positions differ"):
            _verify_published_profile_extras(db, sources)
        db.execute("UPDATE loadout_payload_weapon_extras SET position = 2 WHERE position = 3")
        db.execute("DELETE FROM profile_payload_equipment_extras")
        with pytest.raises(ReferenceBaselineError, match="extra positions differ"):
            _verify_published_profile_extras(db, sources)
        db.execute("INSERT INTO profile_payload_equipment_extras VALUES (1, 1, 1, 43)")
        db.execute("INSERT INTO profile_payload_equipment_extras VALUES (1, 1, 1, 43)")
        with pytest.raises(ReferenceBaselineError, match="duplicate"):
            _verify_published_profile_extras(db, sources)
        db.execute("DELETE FROM profile_payload_equipment_extras WHERE rowid = "
                   "(SELECT MAX(rowid) FROM profile_payload_equipment_extras)")
        assert _verify_published_profile_references(db, sources) == {
            "profile.skills": 2, "profile.equipment": 1, "profile.weapons": 1,
            "loadout.skills": 1, "loadout.equipment": 1, "loadout.weapons": 1,
        }
        db.execute("UPDATE profile_payload_skills SET quantity = 9 WHERE position = 2")
        with pytest.raises(ReferenceBaselineError, match="published reference differs"):
            _verify_published_profile_references(db, sources)
        db.execute("UPDATE profile_payload_skills SET quantity = 2 WHERE position = 2")
        db.execute("DELETE FROM loadout_payload_weapons")
        with pytest.raises(
            ReferenceBaselineError, match="source/published reference identities differ"
        ):
            _verify_published_profile_references(db, sources)


def test_pinned_army_archive_source_identity_matches_publication(tmp_path: Path) -> None:
    archive = _synthetic_army_archive(tmp_path)
    metadata = {
        "sourceFileCount": 2,
        "sourceVersions": {"7.26246.158": 1, "7.26246.159": 1},
    }
    with sqlite3.connect(":memory:") as db, sqlite3.connect(":memory:") as raw_db:
        db.execute(
            "CREATE TABLE army_lists (id INTEGER PRIMARY KEY, version TEXT, "
            "kind TEXT, source_file TEXT, source_sha256 TEXT)"
        )
        db.execute(
            "CREATE TABLE army_units (army_id INTEGER, unit_id INTEGER, position INTEGER)"
        )
        for table, (identities, values) in _NESTED_SOURCE_FIELDS.items():
            target = db if table == "profile_groups" else raw_db
            target.execute(f"CREATE TABLE {table} ({', '.join((*identities, *values))})")
        sources, _ = load_sources(archive)
        db.executemany(
            "INSERT INTO army_lists VALUES (?, ?, ?, ?, ?)",
            [
                (
                    source.faction_id, source.data["version"],
                    "army" if "reinforcements" in source.data else "reinforcement",
                    source.filename, source.sha256,
                )
                for source in sources
            ],
        )
        db.executemany(
            "INSERT INTO army_units VALUES (?, ?, ?)",
            [(101, 10, 1), (101, 11, 2), (201, 11, 1)],
        )
        profile_values = {
            "army_id": 101, "unit_id": 10, "group_id": 7,
            "profile_id": 1, "position": 1, "name": "Test Unit",
            "type_id": 2, "move_1": 15, "move_2": 10,
            "cc": 16, "vitality": 1, "is_structure": 0,
        }
        rows = {
            "profile_groups": {
                "army_id": 101, "unit_id": 10, "group_id": 7,
                "position": 1, "category_id": 5, "isc": "Main",
            },
            "profiles": profile_values,
            "loadout_options": {
                "army_id": 101, "unit_id": 10, "group_id": 7,
                "option_id": 9, "position": 1,
                "name": "Test Loadout", "points": 17, "swc": "0.5",
                "minis": 1, "disabled": 0,
            },
        }
        for table, row in rows.items():
            identities, values = _NESTED_SOURCE_FIELDS[table]
            target = db if table == "profile_groups" else raw_db
            target.execute(
                f"INSERT INTO {table} VALUES ({', '.join('?' for _ in (*identities, *values))})",
                tuple(row.get(field) for field in (*identities, *values)),
            )
        evidence = _verify_army_archive_sources(archive, metadata, db, raw_db)
        assert evidence == {
            "status": "source-identities-match-published-army-lists",
            "archiveJsonDocuments": 3,
            "sourceFileCount": 2,
            "sourceVersions": metadata["sourceVersions"],
            "matchedArmyListIds": 2,
            "matchedSourceProvenanceRows": 2,
            "matchedUnitMembershipOccurrences": 3,
            "matchedNestedSourceRows": {
                "profile_groups": 1, "profiles": 1, "loadout_options": 1,
            },
            "nestedStorage": {
                "profile_groups": "published-infinity.db",
                "profiles": "paired-infinity.raw.db",
                "loadout_options": "paired-infinity.raw.db",
            },
        }
        raw_db.execute("UPDATE profiles SET cc = 99 WHERE army_id = 101")
        with pytest.raises(ReferenceBaselineError, match="profiles source facts differ"):
            _verify_army_archive_sources(archive, metadata, db, raw_db)
        raw_db.execute("UPDATE profiles SET cc = 16 WHERE army_id = 101")
        raw_db.execute("UPDATE loadout_options SET points = 99 WHERE army_id = 101")
        with pytest.raises(
            ReferenceBaselineError, match="loadout_options source facts differ"
        ):
            _verify_army_archive_sources(archive, metadata, db, raw_db)
        raw_db.execute("UPDATE loadout_options SET points = 17 WHERE army_id = 101")
        db.execute("UPDATE profile_groups SET position = 2 WHERE army_id = 101")
        with pytest.raises(
            ReferenceBaselineError, match="profile_groups source facts differ"
        ):
            _verify_army_archive_sources(archive, metadata, db, raw_db)
        db.execute("UPDATE profile_groups SET position = 1 WHERE army_id = 101")
        with pytest.raises(ReferenceBaselineError, match="source count differs"):
            _verify_army_archive_sources(
                archive, {**metadata, "sourceFileCount": 3}, db
            )
        with pytest.raises(ReferenceBaselineError, match="source versions differ"):
            _verify_army_archive_sources(
                archive, {**metadata, "sourceVersions": {"unknown": 2}}, db
            )
        db.execute("UPDATE army_lists SET source_sha256 = ? WHERE id = 201", ("bad",))
        with pytest.raises(ReferenceBaselineError, match="source provenance differs"):
            _verify_army_archive_sources(archive, metadata, db)
        db.execute(
            "UPDATE army_lists SET source_sha256 = ? WHERE id = 201",
            (next(source.sha256 for source in sources if source.faction_id == 201),),
        )
        db.execute("UPDATE army_units SET position = 3 WHERE army_id = 101 AND unit_id = 11")
        with pytest.raises(ReferenceBaselineError, match="memberships/positions differ"):
            _verify_army_archive_sources(archive, metadata, db)
        db.execute("UPDATE army_units SET position = 2 WHERE army_id = 101 AND unit_id = 11")
        db.execute("DELETE FROM army_lists WHERE id = 201")
        db.execute("INSERT INTO army_lists (id) VALUES (999)")
        with pytest.raises(ReferenceBaselineError, match="list identities differ"):
            _verify_army_archive_sources(archive, metadata, db)


def test_army_archive_source_identity_rejects_unexpected_json(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "army.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("other.json", "{}")
        output.writestr("101-first.json", '{"version":"v1","units":[]}')
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE army_lists (id INTEGER PRIMARY KEY)")
        db.execute("INSERT INTO army_lists (id) VALUES (101)")
        with pytest.raises(ReferenceBaselineError, match="metadata.json"):
            _verify_army_archive_sources(
                archive, {"sourceFileCount": 1, "sourceVersions": {"v1": 1}}, db
            )


@pytest.mark.parametrize(
    "units",
    [
        [{"id": 10}, {"id": 10}],
        [{"id": "10"}],
        [{"id": True}],
    ],
)
def test_army_archive_rejects_invalid_or_duplicate_unit_ids(
    tmp_path: Path, units: list[dict[str, object]],
) -> None:
    archive = tmp_path / "army.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("metadata.json", "{}")
        output.writestr(
            "101-first.json", json.dumps({"version": "v1", "units": units})
        )
    sources, _ = load_sources(archive)
    source = sources[0]
    with sqlite3.connect(":memory:") as db:
        db.execute(
            "CREATE TABLE army_lists (id INTEGER PRIMARY KEY, version TEXT, "
            "kind TEXT, source_file TEXT, source_sha256 TEXT)"
        )
        db.execute(
            "INSERT INTO army_lists VALUES (?, ?, ?, ?, ?)",
            (101, "v1", "reinforcement", source.filename, source.sha256),
        )
        with pytest.raises(ReferenceBaselineError, match="invalid or duplicate"):
            _verify_army_archive_sources(
                archive, {"sourceFileCount": 1, "sourceVersions": {"v1": 1}}, db
            )


def test_pinned_army_archive_nested_publication_when_available() -> None:
    archive = ROOT / "data/raw/JSON 20260929-114335.zip"
    if not archive.is_file():
        pytest.skip("Optional pinned Army source archive is not available")
    report = build_baseline(ARMY_DB, RULES_DB, army_archive=archive)
    evidence = report["armySnapshot"]["sourceIdentityEvidence"]
    assert evidence["matchedArmyListIds"] == 58
    assert evidence["matchedUnitMembershipOccurrences"] > 0
    assert evidence["matchedNestedSourceRows"]["profile_groups"] > 0
    assert evidence["matchedNestedSourceRows"]["profiles"] > 0
    assert evidence["matchedNestedSourceRows"]["loadout_options"] > 0
    published = evidence["matchedPublishedReferences"]
    assert set(published) == {
        "profile.skills", "profile.equipment", "profile.weapons",
        "loadout.skills", "loadout.equipment", "loadout.weapons",
    }
    assert all(count > 0 for count in published.values()), published
    extras = evidence["matchedPublishedExtras"]
    assert set(extras) == set(published)
    assert sum(extras.values()) > 0, extras
    characteristics_orders = evidence["matchedPublishedCharacteristicsOrders"]
    assert set(characteristics_orders) == {
        "profile.characteristics",
        "loadout.characteristics",
        "loadout.orders",
    }
    assert characteristics_orders["profile.characteristics"] == 15011
    assert characteristics_orders["loadout.orders"] == 15195
    # No loadout Characteristics exist in this pinned source. The parity
    # check still rejects unexpectedly published rows for this category.
    assert characteristics_orders["loadout.characteristics"] == 0
    peripherals_includes = evidence["matchedPublishedPeripheralsIncludes"]
    assert set(peripherals_includes) == {
        "profile.peripherals", "loadout.peripherals",
        "profile.includes", "loadout.includes",
    }
    assert sum(peripherals_includes.values()) > 0, peripherals_includes


def test_army_archive_identity_evidence_is_visible_in_markdown() -> None:
    report = build_baseline(ARMY_DB, RULES_DB)
    report["armySnapshot"]["sourceIdentityEvidence"] = {
        "archiveJsonDocuments": 59,
        "matchedArmyListIds": 58,
        "matchedSourceProvenanceRows": 58,
        "matchedUnitMembershipOccurrences": 12345,
        "matchedNestedSourceRows": {
            "profile_groups": 4748, "profiles": 5020, "loadout_options": 9000,
        },
        "matchedPublishedReferences": {
            "profile.skills": 20, "loadout.weapons": 30,
        },
        "matchedPublishedExtras": {
            "profile.skills": 12, "loadout.weapons": 17,
        },
        "matchedPublishedCharacteristicsOrders": {
            "profile.characteristics": 41,
            "loadout.characteristics": 37,
            "loadout.orders": 26,
        },
        "matchedPublishedPeripheralsIncludes": {
            "profile.peripherals": 13, "loadout.includes": 27,
        },
    }
    markdown = render_markdown(report)
    assert "59 archive JSON documents (including metadata.json)" in markdown
    assert "58 matched published Army-list IDs" in markdown
    assert "58 matched per-file provenance records" in markdown
    assert "12345 ordered Unit membership occurrences" in markdown
    assert "4748 profile groups in published infinity.db" in markdown
    assert "5020 profiles and 9000 loadouts" in markdown
    assert "export-paired infinity.raw.db" in markdown
    assert "loadout.weapons=30, profile.skills=20" in markdown
    assert "loadout.weapons=17, profile.skills=12" in markdown
    assert "loadout.characteristics=37, loadout.orders=26" in markdown
    assert "profile.characteristics=41" in markdown
    assert "loadout.includes=27, profile.peripherals=13" in markdown


def test_baseline_requires_published_databases_and_verified_supplied_army_zip(
    tmp_path: Path,
) -> None:
    with pytest.raises(ReferenceBaselineError, match="database is unavailable"):
        build_baseline(tmp_path / "missing.db", RULES_DB)
    archive = tmp_path / "unmatched.zip"
    archive.write_bytes(b"incorrect source bytes")
    with pytest.raises(ReferenceBaselineError, match="differs from published metadata"):
        build_baseline(ARMY_DB, RULES_DB, army_archive=archive)


class _VersionResponse(BytesIO):
    status = 200


def test_served_revision_matches_exact_inventoried_database_pair() -> None:
    from infinity_db.web import create_app

    report = build_baseline(ARMY_DB, RULES_DB)
    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    assert report["runtimeSnapshotRevision"] == app.snapshot_revision

    payload = {
        "snapshot_revision": report["runtimeSnapshotRevision"],
        "version": "1.0.0",
        "static_revision": "abc",
    }
    with patch(
        "tools.report_reference_baseline.urlopen",
        return_value=_VersionResponse(json.dumps(payload).encode()),
    ) as opened:
        observed = verify_served_revision(report, "http://127.0.0.1:8000")
    assert observed["status"] == "exact-database-pair-match-not-source-completeness"
    assert observed["snapshotRevision"] == app.snapshot_revision
    assert opened.call_args.args[0].full_url == "http://127.0.0.1:8000/api/version"
    assert opened.call_args.kwargs == {"timeout": 10}


def test_served_revision_rejects_stale_and_invalid_runtime() -> None:
    report = {"runtimeSnapshotRevision": "a" * 64}
    stale = {"snapshot_revision": "b" * 64}
    with patch(
        "tools.report_reference_baseline.urlopen",
        return_value=_VersionResponse(json.dumps(stale).encode()),
    ):
        with pytest.raises(ReferenceBaselineError, match="does not match"):
            verify_served_revision(report, "http://localhost:8000/")
    for base in (
        "file:///data/generated/infinity.db",
        "http://user:pass@localhost:8000",
        "http://localhost:8000/api",
        "http://localhost:8000?skip=1",
    ):
        with pytest.raises(ReferenceBaselineError, match="Server base URL"):
            verify_served_revision(report, base)
    with patch(
        "tools.report_reference_baseline.urlopen",
        return_value=_VersionResponse(b"[]"),
    ):
        with pytest.raises(ReferenceBaselineError, match="did not return an object"):
            verify_served_revision(report, "http://localhost:8000")


def test_baseline_cli_rejects_stale_server_before_writing_outputs(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.json"
    payload = {"snapshot_revision": "0" * 64}
    with patch(
        "tools.report_reference_baseline.urlopen",
        return_value=_VersionResponse(json.dumps(payload).encode()),
    ):
        assert main([
            "--verify-server", "http://127.0.0.1:8000",
            "--json-output", str(path),
        ]) == 1
    assert not path.exists()


def test_baseline_cli_records_served_pair_in_json_and_markdown(tmp_path: Path) -> None:
    report = build_baseline(ARMY_DB, RULES_DB)
    payload = {
        "snapshot_revision": report["runtimeSnapshotRevision"],
        "version": "1.0.0",
        "static_revision": "static-test",
    }
    json_path = tmp_path / "baseline.json"
    markdown_path = tmp_path / "baseline.md"
    with patch(
        "tools.report_reference_baseline.urlopen",
        return_value=_VersionResponse(json.dumps(payload).encode()),
    ):
        assert main([
            "--verify-server", "http://localhost:8000",
            "--json-output", str(json_path),
            "--markdown-output", str(markdown_path),
        ]) == 0
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["servedSnapshot"]["status"] == (
        "exact-database-pair-match-not-source-completeness"
    )
    assert saved["servedSnapshot"]["snapshotRevision"] == report[
        "runtimeSnapshotRevision"
    ]
    assert "Served runtime: exact-database-pair-match" in markdown_path.read_text(
        encoding="utf-8"
    )


def test_baseline_cli_writes_stable_local_reports(tmp_path: Path) -> None:
    json_output = tmp_path / "baseline.json"
    markdown_output = tmp_path / "baseline.md"
    args = [
        "--army-db", str(ARMY_DB), "--rules-db", str(RULES_DB),
        "--json-output", str(json_output),
        "--markdown-output", str(markdown_output),
    ]
    assert main(args) == 0
    first = json_output.read_bytes()
    assert main(args) == 0
    assert json_output.read_bytes() == first
    saved = json.loads(first)
    assert saved["formatVersion"] == 2
    assert len(saved["scenarioMemberships"]) == saved["scenarioMembershipCount"] == 5
    markdown = markdown_output.read_text(encoding="utf-8")
    assert "## Published scenario memberships by collection" in markdown
    assert "| `its-18` | `2026.09.01` | 0 | `scenario:battleground` |" in markdown
    assert "| `n5-core` | `5.3` | 0 | `scenario:annihilation` |" in markdown
    assert "not a core-only scenario count" in markdown
    assert "Candidate browser / API" in markdown
    assert "pending source/API/browser review" in markdown
    assert "## Outstanding 1.0 evidence" in markdown
