"""Disposable v9 conditional-restriction storage/API contract and v8 parity tests."""
from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.restriction_conditions import compile_restriction_conditions
from infinity_db.restriction_storage import (
    CANDIDATE_COMPATIBILITY_VERSION,
    CANDIDATE_SCHEMA_VERSION,
    candidate_restrictions_payload,
    stage_candidate_restrictions,
)
from infinity_db.rules_database import (
    RULES_COMPATIBILITY_VERSION,
    RULES_SCHEMA_VERSION,
    RulesDatabase,
    export_rules_database,
)

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/generated/rules.db"
CHART = ROOT / "config/validation/restrictions-source-chart.json"
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"


def test_english_core_pdf_pin_survives_curated_export(tmp_path: Path) -> None:
    documents = load_curated_directory(ROOT / "data/curated/rules")
    chart = json.loads(CHART.read_text(encoding="utf-8"))
    pins = {
        document["collection"]["id"]: source["sha256"]
        for _, document in documents for source in document["sources"]
        if source["id"] == chart["sourceId"]
    }
    assert pins == {
        "n5-core-v5.3": chart["sourcePdfSha256"],
        "n5-hacking-programs-v5.3": chart["sourcePdfSha256"],
    }
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)
    with sqlite3.connect(output) as db:
        stored = dict(db.execute(
            "SELECT collection_id, sha256 FROM sources WHERE id = ?", (chart["sourceId"],),
        ))
    assert stored == pins
    pdf = ROOT / "data/pdf/rules/n5-rules-v5.3-en.pdf"
    if pdf.exists():
        assert hashlib.sha256(pdf.read_bytes()).hexdigest() == chart["sourcePdfSha256"]


@pytest.mark.parametrize(
    "defect", (None, "rules", "source-url", "source-hash", "missing", "extra", "schema", "version",
               "previous-pin", "index"),
)
def test_source_pin_guard_rejects_every_unrelated_database_change(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import _check_source_pin_delta

    old_path, new_path = tmp_path / "old.db", tmp_path / "new.db"
    digest = "a" * 64
    with sqlite3.connect(old_path) as old, sqlite3.connect(new_path) as new:
        old.executescript("""
            PRAGMA application_id=123;
            PRAGMA user_version=9;
            CREATE TABLE sources(collection_id TEXT, id TEXT, sha256 TEXT, url TEXT);
            CREATE TABLE records(id TEXT, summary TEXT);
            INSERT INTO records VALUES ('unchanged', 'reviewed meaning');
            INSERT INTO sources VALUES ('core', 'pdf', NULL, 'https://example.invalid/core');
            INSERT INTO sources VALUES ('hacking', 'pdf', NULL, 'https://example.invalid/core');
        """)
        if defect == "previous-pin":
            old.execute("UPDATE sources SET sha256 = ?", ("b" * 64,))
        old.commit()
        old.backup(new)
        new.execute("UPDATE sources SET sha256 = ?", (digest,))
        if defect == "rules":
            new.execute("UPDATE records SET summary = 'unreviewed meaning'")
        elif defect == "source-url":
            new.execute("UPDATE sources SET url = 'https://example.invalid/other'")
        elif defect == "source-hash":
            new.execute("UPDATE sources SET sha256 = ?", ("c" * 64,))
        elif defect == "missing":
            new.execute("DELETE FROM sources WHERE collection_id = 'hacking'")
        elif defect == "extra":
            new.execute("INSERT INTO sources VALUES ('extra', 'pdf', NULL, 'unknown')")
        elif defect == "schema":
            new.execute("ALTER TABLE records ADD COLUMN unexpected TEXT")
        elif defect == "version":
            new.execute("PRAGMA user_version=8")
        elif defect == "index":
            new.execute("CREATE INDEX unreviewed ON records(id)")
    if defect is None:
        _check_source_pin_delta(old_path, new_path, "pdf", digest, {"core", "hacking"})
    else:
        with pytest.raises(ValueError, match="Source pin refresh"):
            _check_source_pin_delta(old_path, new_path, "pdf", digest, {"core", "hacking"})


def test_multiple_pdf_pin_guard_preserves_existing_pins(tmp_path: Path) -> None:
    from tools.restrictions_v9_release import _check_source_pins_delta

    old_path, new_path = tmp_path / "old.db", tmp_path / "new.db"
    with sqlite3.connect(old_path) as old, sqlite3.connect(new_path) as new:
        old.execute("CREATE TABLE sources(collection_id TEXT, id TEXT, sha256 TEXT)")
        old.executemany("INSERT INTO sources VALUES (?, ?, ?)", (
            ("core", "core-pdf", "a" * 64), ("core", "faq-en", None),
            ("faq", "faq-es", None),
        ))
        old.commit()
        old.backup(new)
        new.execute("UPDATE sources SET sha256 = ? WHERE id = 'faq-en'", ("b" * 64,))
        new.execute("UPDATE sources SET sha256 = ? WHERE id = 'faq-es'", ("c" * 64,))
    pins = {("core", "faq-en"): "b" * 64, ("faq", "faq-es"): "c" * 64}
    _check_source_pins_delta(old_path, new_path, pins)
    with sqlite3.connect(new_path) as new:
        new.execute("UPDATE sources SET sha256 = ? WHERE id = 'core-pdf'", ("d" * 64,))
    with pytest.raises(ValueError, match="unrelated rows"):
        _check_source_pins_delta(old_path, new_path, pins)


def test_all_selected_pdf_sources_have_consistent_pins_and_exports(tmp_path: Path) -> None:
    documents = load_curated_directory(ROOT / "data/curated/rules")
    pdfs = [(doc["collection"]["id"], source)
            for _, doc in documents for source in doc["sources"] if source["kind"] == "pdf"]
    assert len(pdfs) == 14
    assert {
        (collection, source["id"])
        for collection, source in pdfs
        if collection == "reinforcements-extra-n4-reference"
    } == {
        ("reinforcements-extra-n4-reference", "reinforcements-its-season-18"),
        ("reinforcements-extra-n4-reference", "reinforcements-n5-core"),
    }
    source_pins: dict[str, str] = {}
    for _, source in pdfs:
        assert len(source["sha256"]) == 64
        assert source_pins.setdefault(source["id"], source["sha256"]) == source["sha256"]
        path = ROOT / source["localPath"]
        if path.exists():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
    assert len(source_pins) == 8
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)
    with sqlite3.connect(output) as db:
        actual = db.execute(
            "SELECT collection_id, id, sha256 FROM sources WHERE kind='pdf' "
            "ORDER BY collection_id,id",
        ).fetchall()
    assert actual == sorted((collection, source["id"], source["sha256"])
                            for collection, source in pdfs)


@pytest.mark.parametrize(
    "defect", (None, "facts", "other-record", "index", "inheritance", "replace", "missing"),
)
def test_variant_metadata_refresh_preserves_other_rows_and_prior_parameters(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import _check_variant_semantics_delta

    before = {"inheritance": "family", "occurrenceParameters": [{"kind": "existing"}]}
    after = copy.deepcopy(before)
    after["occurrenceParameters"].append({"kind": "reviewed-addition"})
    if defect == "inheritance":
        after["inheritance"] = "source"
    elif defect == "replace":
        after["occurrenceParameters"][0]["kind"] = "replacement"
    old_path, new_path = tmp_path / "old.db", tmp_path / "new.db"
    payload = json.dumps(after)
    with sqlite3.connect(old_path) as old, sqlite3.connect(new_path) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", (
            ("core", "skill", json.dumps(before), "preserved"),
            ("core", "other", json.dumps(before), "preserved"),
        ))
        old.commit()
        old.backup(new)
        new.execute("UPDATE records SET variant_json=? WHERE id='skill'", (payload,))
        if defect == "facts":
            new.execute("UPDATE records SET facts='changed' WHERE id='skill'")
        elif defect == "other-record":
            new.execute("UPDATE records SET variant_json=? WHERE id='other'", (payload,))
        elif defect == "index":
            new.execute("CREATE INDEX changed ON records(id)")
    variants = {("core", "absent" if defect == "missing" else "skill"): payload}
    if defect is None:
        _check_variant_semantics_delta(old_path, new_path, variants)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(old_path, new_path, variants)


@pytest.mark.parametrize(
    "defect", (None, "missing-link", "extra-link", "wrong-source",
               "other-record", "unexpected-variant", "schema", "other-stats"),
)
def test_initial_jump_climb_distance_refresh_rejects_unrelated_changes(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        INITIAL_MOVEMENT_DISTANCE,
        MOVEMENT_DISTANCE_VARIANT,
        _check_variant_semantics_delta,
    )

    old_path, new_path = tmp_path / "old.db", tmp_path / "new.db"
    variants = {
        key: json.dumps(MOVEMENT_DISTANCE_VARIANT)
        for key in INITIAL_MOVEMENT_DISTANCE
    }
    with sqlite3.connect(old_path) as old, sqlite3.connect(new_path) as new:
        old.execute(
            "CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)"
        )
        old.execute(
            "CREATE TABLE record_army_links("
            "collection_id TEXT,record_id TEXT,position INT,entity TEXT,"
            "external_id TEXT,external_name TEXT)"
        )
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            ("n5-core-v5.3", "skill:climb", None, "unchanged"),
            ("n5-core-v5.3", "skill:jump", None, "unchanged"),
            ("n5-core-v5.3", "skill:other", None, "unchanged"),
        ])
        old.execute(
            "INSERT INTO record_army_links VALUES (?,?,?,?,?,?)",
            ("n5-core-v5.3", "skill:other", 0, "skill", "1", None),
        )
        old.execute("CREATE INDEX idx_links ON record_army_links(record_id)")
        old.execute("CREATE INDEX idx_records ON records(id)")
        old.execute("ANALYZE")
        old.commit()
        old.backup(new)
        for _, record_id in INITIAL_MOVEMENT_DISTANCE:
            new.execute(
                "UPDATE records SET variant_json=? WHERE id=?",
                (json.dumps(MOVEMENT_DISTANCE_VARIANT), record_id),
            )
        for (collection, record_id), source_id in INITIAL_MOVEMENT_DISTANCE.items():
            new.execute(
                "INSERT INTO record_army_links VALUES (?,?,?,?,?,?)",
                (collection, record_id, 0, "skill", str(source_id), None),
            )
        if defect == "missing-link":
            new.execute("DELETE FROM record_army_links WHERE record_id='skill:climb'")
        elif defect == "extra-link":
            new.execute(
                "INSERT INTO record_army_links VALUES (?,?,?,?,?,?)",
                ("n5-core-v5.3", "skill:jump", 1, "skill", "999", None),
            )
        elif defect == "wrong-source":
            new.execute(
                "UPDATE record_army_links SET external_id='999' "
                "WHERE record_id='skill:climb'"
            )
        elif defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='skill:other'")
        elif defect == "unexpected-variant":
            new.execute(
                "UPDATE records SET variant_json=? WHERE id='skill:jump'",
                (json.dumps({"inheritance": "family", "occurrenceParameters": []}),),
            )
        elif defect == "schema":
            new.execute("CREATE INDEX unrelated_index ON records(id)")
        new.execute("ANALYZE")
        if defect == "other-stats":
            new.execute("UPDATE sqlite_stat1 SET stat='999' WHERE tbl='records'")
    if defect is None:
        _check_variant_semantics_delta(
            old_path, new_path, variants, initialize_movement_distance=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                old_path, new_path, variants, initialize_movement_distance=True,
            )
    # The older append-only refresh never permits a new Army link.
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(old_path, new_path, variants)


@pytest.mark.parametrize(
    "defect", (None, "name", "application", "count", "extra", "status", "raw"),
)
def test_jump_climb_migration_requires_exact_pinned_army_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as source_audit
    from tools import restrictions_v9_release as release

    items = [
        {
            "id": source_id, "name": name, "applicationId": source_id,
            "occurrences": count, "status": "unresolved-occurrence-parameter",
            "extraSignatures": [{
                "extras": [[372, "DISTANCE", "7.5"]],
                "reviewed": False, "count": count,
            }],
            "rawValues": [],
        }
        for source_id, name, count in ((263, "Jump", 26), (271, "Climb", 6))
    ]
    if defect == "name":
        items[0]["name"] = "Not Jump"
    elif defect == "application":
        items[0]["applicationId"] = 999
    elif defect == "count":
        items[0]["occurrences"] = 27
    elif defect == "extra":
        items[0]["extraSignatures"][0]["extras"][0][0] = 999
    elif defect == "status":
        items[0]["status"] = "reviewed-distance-parameter"
    elif defect == "raw":
        items[0]["rawValues"] = ["unreviewed"]
    monkeypatch.setattr(
        source_audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": items}}},
    )
    calls: list[dict] = []

    def migration(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migration)
    if defect:
        with pytest.raises(ValueError, match="source drift"):
            release.refresh_movement_distance_v9_release(root=tmp_path)
        assert not calls
    else:
        assert release.refresh_movement_distance_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls[0]["variant_records"] == {"skill:jump", "skill:climb"}
        assert calls[0]["initialize_movement_distance"] is True


@pytest.mark.parametrize(
    "defect", (None, "modified-name", "modified-scope", "modified-modifier",
               "other-record", "schema", "missing-record"),
)
def test_tinbot_firewall_variant_refresh_preserves_named_source(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        TINBOT_FIREWALL,
        TINBOT_FIREWALL_BASE,
        TINBOT_FIREWALL_VARIANT,
        _check_variant_semantics_delta,
    )

    old_path, new_path = tmp_path / "old.db", tmp_path / "new.db"
    after = copy.deepcopy(TINBOT_FIREWALL_VARIANT)
    if defect == "modified-name":
        after["sourceVariant"]["label"] = "Guided"
    elif defect == "modified-scope":
        after["occurrenceParameters"][0]["extraValues"][0]["effect"]["appliesTo"] = (
            "all-enemy-rolls"
        )
    elif defect == "modified-modifier":
        after["occurrenceParameters"][0]["extraValues"][1]["effect"]["modifier"] = 3
    with sqlite3.connect(old_path) as old, sqlite3.connect(new_path) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*TINBOT_FIREWALL, json.dumps(TINBOT_FIREWALL_BASE), "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        if defect != "missing-record":
            new.execute(
                "UPDATE records SET variant_json=? WHERE id=?",
                (json.dumps(after), TINBOT_FIREWALL[1]),
            )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
    variants: dict[tuple[str, str], str] = {TINBOT_FIREWALL: json.dumps(after)}
    if defect is None:
        _check_variant_semantics_delta(
            old_path, new_path, variants, tinbot_firewall=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                old_path, new_path, variants, tinbot_firewall=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(old_path, new_path, variants)


@pytest.mark.parametrize(
    "defect", (None, "name", "application", "count", "extra", "status",
               "variant", "raw"),
)
def test_tinbot_firewall_refresh_requires_exact_pinned_occurrences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as source_audit
    from tools import restrictions_v9_release as release

    item = {
        "id": 169, "name": "TinBot: Firewall", "applicationId": 235,
        "occurrences": 147, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": {"kind": "named", "label": "Firewall"},
        "reviewedExtra": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[6, "TEXT", "-3"]], "reviewed": False, "count": 92},
            {"extras": [[7, "TEXT", "-6"]], "reviewed": False, "count": 55},
        ],
    }
    if defect == "name":
        item["name"] = "TinBot: Guided"
    elif defect == "application":
        item["applicationId"] = 999
    elif defect == "count":
        item["occurrences"] = 148
    elif defect == "extra":
        item["extraSignatures"][1]["extras"][0][0] = 999
    elif defect == "status":
        item["status"] = "reviewed-extra-parameter"
    elif defect == "variant":
        item["reviewedVariant"]["label"] = "Guided"
    elif defect == "raw":
        item["rawValues"] = ["unreviewed"]
    monkeypatch.setattr(
        source_audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": [item]}}},
    )
    calls: list[dict] = []

    def migration(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migration)
    if defect:
        with pytest.raises(ValueError, match="source signature drift"):
            release.refresh_tinbot_firewall_v9_release(root=tmp_path)
        assert not calls
    else:
        assert release.refresh_tinbot_firewall_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls[0]["variant_records"] == {"equipment:tinbot-firewall"}
        assert calls[0]["tinbot_firewall"] is True


@pytest.mark.parametrize(
    "defect", (None, "source", "modifier", "scope", "other-record", "schema", "missing"),
)
def test_tinbot_other_refresh_rejects_unrelated_database_changes(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        TINBOT_OTHER_SOURCES,
        TINBOT_OTHER_VARIANTS,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "old.db", tmp_path / "next.db"
    variants: dict[tuple[str, str], str] = {
        key: json.dumps(value) for key, value in TINBOT_OTHER_VARIANTS.items()
    }
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (
                key[0], key[1],
                json.dumps({
                    "inheritance": "source",
                    "sourceVariant": {"kind": "named", "label": source["label"]},
                }),
                "unchanged",
            )
            for key, source in TINBOT_OTHER_SOURCES.items()
        ] + [("n5-core-v5.3", "equipment:other", None, "unchanged")])
        old.commit()
        old.backup(new)
        for key, payload in variants.items():
            new.execute(
                "UPDATE records SET variant_json=? WHERE collection_id=? AND id=?",
                (payload, *key),
            )
        if defect == "source":
            changed = json.loads(variants[("n5-core-v5.3", "equipment:tinbot-discover")])
            changed["sourceVariant"]["label"] = "Firewall"
            new.execute(
                "UPDATE records SET variant_json=? WHERE id='equipment:tinbot-discover'",
                (json.dumps(changed),),
            )
        elif defect in {"modifier", "scope"}:
            key = ("n5-core-v5.3", "equipment:tinbot-ecm-guided")
            changed = json.loads(variants[key])
            effect = changed["occurrenceParameters"][0]["extraValues"][1]["effect"]
            if defect == "modifier":
                effect["modifier"] = -3
            else:
                effect["appliesTo"] = "all-attacks"
            new.execute(
                "UPDATE records SET variant_json=? WHERE id='equipment:tinbot-ecm-guided'",
                (json.dumps(changed),),
            )
        elif defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:tinbot-discover'")
    if defect is None:
        _check_variant_semantics_delta(
            previous, proposed, variants, tinbot_other=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                previous, proposed, variants, tinbot_other=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, variants)


@pytest.mark.parametrize(
    "defect", (None, "name", "application", "count", "extra", "status", "variant", "raw"),
)
def test_tinbot_other_refresh_checks_exact_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as source_audit
    from tools import restrictions_v9_release as release

    items = [
        {
            "id": source["sourceId"], "name": source["name"], "applicationId": 235,
            "occurrences": source["count"], "status": "unresolved-occurrence-parameter",
            "reviewedVariant": {"kind": "named", "label": source["label"]},
            "reviewedExtra": None, "rawValues": [],
            "extraSignatures": copy.deepcopy(source["signatures"]),
        }
        for source in release.TINBOT_OTHER_SOURCES.values()
    ]
    item = items[0]
    if defect == "name":
        item["name"] = "Different"
    elif defect == "application":
        item["applicationId"] = 999
    elif defect == "count":
        item["occurrences"] += 1
    elif defect == "extra":
        item["extraSignatures"][0]["extras"][0][0] = 999
    elif defect == "status":
        item["status"] = "reviewed-extra-parameter"
    elif defect == "variant":
        item["reviewedVariant"]["label"] = "Firewall"
    elif defect == "raw":
        item["rawValues"] = ["unreviewed"]
    monkeypatch.setattr(
        source_audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": items}}},
    )
    calls: list[dict] = []

    def migration(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migration)
    if defect:
        with pytest.raises(ValueError, match="source drift"):
            release.refresh_tinbot_other_v9_release(root=tmp_path)
        assert not calls
    else:
        assert release.refresh_tinbot_other_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls[0]["variant_records"] == {
            "equipment:tinbot-discover", "equipment:tinbot-ecm-guided",
        }
        assert calls[0]["tinbot_other"] is True


@pytest.mark.parametrize(
    "defect", (None, "name", "count", "grant-text", "grant-count",
               "combined", "reviewed", "raw", "device"),
)
def test_hacking_program_grant_refresh_requires_exact_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    items = []
    for source_id, source in release.HACKING_GRANT_SOURCES.items():
        signatures = [
            {
                "extras": [[extra_id, "TEXT", raw]],
                "reviewed": False, "count": count,
            }
            for extra_id, (raw, count) in source["singles"].items()
        ]
        signatures.extend(copy.deepcopy(source["combined"]))
        items.append({
            "id": source_id,
            "name": source["name"],
            "applicationId": source_id,
            "occurrences": source["occurrences"],
            "status": "unresolved-occurrence-parameter",
            "reviewedExtra": None,
            "rawValues": [],
            "extraSignatures": signatures,
        })
    first = items[0]
    if defect == "name":
        first["name"] = "Unexpected device"
    elif defect == "count":
        first["occurrences"] += 1
    elif defect == "grant-text":
        first["extraSignatures"][0]["extras"][0][2] = "UPGRADE: Wrong"
    elif defect == "grant-count":
        first["extraSignatures"][0]["count"] += 1
    elif defect == "combined":
        first["extraSignatures"][-1]["reviewed"] = True
    elif defect == "reviewed":
        first["reviewedExtra"] = {"kind": "reviewed-extra"}
    elif defect == "raw":
        first["rawValues"] = ["unreviewed"]
    elif defect == "device":
        first["applicationId"] = 999

    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": items}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is not None:
        with pytest.raises(ValueError, match="source drift|signature drift"):
            release.refresh_hacking_program_grants_v9_release(root=tmp_path)
        assert not calls
    else:
        assert release.refresh_hacking_program_grants_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path,
            "variant_records": {"equipment:hacking-device",
                                "equipment:hacking-device-plus"},
        }]


@pytest.mark.parametrize(
    "defect", (None, "wrong-kind", "wrong-target", "reorder", "remove-grant",
               "other-record", "schema", "missing-record"),
)
def test_hacking_program_mods_delta_is_exactly_append_only(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        HACKING_GRANT_SOURCES,
        _check_variant_semantics_delta,
        _hacking_mod_values,
    )

    old_path, new_path = tmp_path / "old.db", tmp_path / "new.db"
    variants: dict[tuple[str, str], str] = {}
    old_rows = []
    for source_id, source in HACKING_GRANT_SOURCES.items():
        grants = [
            {
                "extraId": extra_id, "extraType": "TEXT", "rawValue": raw,
                "effect": {"kind": "hacking-program-grant", "program": "hacking-program:trinity"},
            }
            for extra_id, (raw, _count) in source["singles"].items()
        ]
        old_variant = {
            "inheritance": "family",
            "occurrenceParameters": [{
                "source": "army-extra", "kind": "reviewed-extra",
                "extraValues": grants,
            }],
        }
        after_variant = copy.deepcopy(old_variant)
        after_variant["occurrenceParameters"][0]["extraValues"].extend(
            _hacking_mod_values(source_id)
        )
        key = ("n5-core-v5.3", source["record"])
        variants[key] = json.dumps(after_variant)
        old_rows.append((*key, json.dumps(old_variant), "untouched"))
    key = ("n5-core-v5.3", "equipment:hacking-device")
    if defect in {"wrong-kind", "wrong-target", "reorder", "remove-grant"}:
        changed = json.loads(variants[key])
        values = changed["occurrenceParameters"][0]["extraValues"]
        if defect == "wrong-kind":
            values[-1]["effect"]["kind"] = "program-burst-mod"
        elif defect == "wrong-target":
            values[-1]["effect"]["program"] = "hacking-program:spotlight"
        elif defect == "reorder":
            values[0], values[1] = values[1], values[0]
        else:
            values.pop(0)
        variants[key] = json.dumps(changed)
    with sqlite3.connect(old_path) as old, sqlite3.connect(new_path) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", old_rows + [
            ("n5-core-v5.3", "equipment:other", None, "untouched"),
        ])
        old.commit()
        old.backup(new)
        for key, payload in variants.items():
            new.execute(
                "UPDATE records SET variant_json=? WHERE collection_id=? AND id=?",
                (payload, *key),
            )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX unexpected ON records(id)")
        elif defect == "missing-record":
            new.execute("DELETE FROM records WHERE id='equipment:hacking-device-plus'")
    if defect is None:
        _check_variant_semantics_delta(
            old_path, new_path, variants, hacking_mods=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                old_path, new_path, variants, hacking_mods=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(old_path, new_path, variants)


@pytest.mark.parametrize(
    "defect", (None, "id", "raw", "count", "combined", "reviewed", "old-grant"),
)
def test_hacking_program_mods_refresh_checks_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    items = []
    for source_id, specs in release.HACKING_MOD_SOURCES.items():
        old = release.HACKING_GRANT_SOURCES[source_id]
        items.append({
            "id": source_id, "name": old["name"], "applicationId": source_id,
            "occurrences": old["occurrences"],
            "status": "unresolved-occurrence-parameter",
            "reviewedVariant": None, "reviewedDistance": None,
            "reviewedNumericMod": None, "rawValues": [],
            "reviewedExtra": {
                "extra_values": [
                    {"extra_id": extra_id, "raw_value": raw}
                    for extra_id, (raw, _count) in old["singles"].items()
                ],
            },
            "extraSignatures": [
                {
                    "extras": [[extra_id, "TEXT", raw]],
                    "count": count, "reviewed": False,
                }
                for extra_id, raw, _program, _kind, _field, _value, count in specs
            ],
        })
    item = items[0]
    if defect == "id":
        item["applicationId"] = 999
    elif defect == "raw":
        item["extraSignatures"][0]["extras"][0][2] = "unknown"
    elif defect == "count":
        item["extraSignatures"][0]["count"] += 1
    elif defect == "combined":
        item["extraSignatures"].append({
            "extras": [[269, "TEXT", "UPGRADE: Oblivion (+1B)"],
                       [12, "TEXT", "UPGRADE:\u00a0Trinity"]],
            "count": 1, "reviewed": False,
        })
    elif defect == "reviewed":
        item["extraSignatures"][0]["reviewed"] = True
    elif defect == "old-grant":
        item["reviewedExtra"]["extra_values"][0]["extra_id"] = 999
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": items}}},
    )
    calls: list[dict] = []
    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"
    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is not None:
        with pytest.raises(ValueError, match="drift|changed"):
            release.refresh_hacking_program_mods_v9_release(root=tmp_path)
        assert not calls
    else:
        assert release.refresh_hacking_program_mods_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path,
            "variant_records": {"equipment:hacking-device", "equipment:hacking-device-plus"},
            "hacking_mods": True,
        }]


@pytest.mark.parametrize(
    "defect", (None, "value", "scope", "removed-prior", "other-record", "schema"),
)
def test_hacking_sr_delta_preserves_existing_modifiers(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        HACKING_GRANT_SOURCES,
        _check_variant_semantics_delta,
        _hacking_mod_values,
        _hacking_sr_values,
    )

    old_db, new_db = tmp_path / "old.db", tmp_path / "new.db"
    existing = []
    proposed: dict[tuple[str, str], str] = {}
    for source_id, source in HACKING_GRANT_SOURCES.items():
        grants = [
            {
                "extraId": extra_id, "extraType": "TEXT", "rawValue": raw,
                "effect": {
                    "kind": "hacking-program-grant",
                    "program": "hacking-program:trinity",
                },
            }
            for extra_id, (raw, _count) in source["singles"].items()
        ]
        old_param = {
            "source": "army-extra", "kind": "reviewed-extra",
            "extraValues": grants + _hacking_mod_values(source_id),
        }
        before = {"inheritance": "family", "occurrenceParameters": [old_param]}
        after = copy.deepcopy(before)
        after["occurrenceParameters"][0]["extraValues"].extend(
            _hacking_sr_values(source_id)
        )
        key = ("n5-core-v5.3", source["record"])
        existing.append((*key, json.dumps(before), "untouched"))
        proposed[key] = json.dumps(after)
    key = ("n5-core-v5.3", "equipment:hacking-device")
    if defect in {"value", "scope", "removed-prior"}:
        changed = json.loads(proposed[key])
        values = changed["occurrenceParameters"][0]["extraValues"]
        if defect == "value":
            values[-1]["effect"]["modifier"] = 2
        elif defect == "scope":
            values[-1]["effect"]["appliesTo"] = "all-rolls"
        else:
            values.pop(len(HACKING_GRANT_SOURCES[100]["singles"]))
        proposed[key] = json.dumps(changed)
    with sqlite3.connect(old_db) as old, sqlite3.connect(new_db) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", existing + [
            ("n5-core-v5.3", "equipment:other", None, "untouched"),
        ])
        old.commit()
        old.backup(new)
        for key, variant in proposed.items():
            new.execute(
                "UPDATE records SET variant_json=? WHERE collection_id=? AND id=?",
                (variant, *key),
            )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX unexpected ON records(id)")
    if defect is None:
        _check_variant_semantics_delta(old_db, new_db, proposed, hacking_srs=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(old_db, new_db, proposed, hacking_srs=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(old_db, new_db, proposed)


@pytest.mark.parametrize(
    "defect", (None, "source", "raw", "count", "compound", "prior", "already-reviewed"),
)
def test_hacking_sr_source_gate_rejects_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    items = []
    for source_id, specs in release.HACKING_SR_SOURCES.items():
        source = release.HACKING_GRANT_SOURCES[source_id]
        previous = [
            {"extra_id": extra_id, "raw_value": raw}
            for extra_id, (raw, _count) in source["singles"].items()
        ] + [
            {"extra_id": extra_id, "raw_value": raw}
            for extra_id, raw, _program, _kind, _field, _value, _count
            in release.HACKING_MOD_SOURCES[source_id]
        ]
        items.append({
            "id": source_id, "name": source["name"], "applicationId": source_id,
            "occurrences": source["occurrences"],
            "status": "unresolved-occurrence-parameter",
            "reviewedVariant": None, "rawValues": [],
            "reviewedExtra": {"extra_values": previous},
            "extraSignatures": [
                {"extras": [[extra_id, "TEXT", raw]], "count": count, "reviewed": False}
                for extra_id, raw, _program, _modifier, count in specs
            ],
        })
    row = items[0]
    if defect == "source":
        row["applicationId"] = 999
    elif defect == "raw":
        row["extraSignatures"][0]["extras"][0][2] = "WRONG"
    elif defect == "count":
        row["extraSignatures"][0]["count"] += 1
    elif defect == "compound":
        row["extraSignatures"].append({
            "extras": [[331, "TEXT", "UPGRADE: Carbonite (SR-2)"],
                       [12, "TEXT", "UPGRADE:\u00a0Trinity"]],
            "count": 1, "reviewed": False,
        })
    elif defect == "prior":
        row["reviewedExtra"]["extra_values"][0]["extra_id"] = 999
    elif defect == "already-reviewed":
        row["extraSignatures"][0]["reviewed"] = True
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": items}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_hacking_saving_rolls_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls[0]["hacking_srs"] is True
        assert calls[0]["variant_records"] == {
            "equipment:hacking-device", "equipment:hacking-device-plus",
        }
    else:
        with pytest.raises(ValueError, match="drift|changed"):
            release.refresh_hacking_saving_rolls_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wip", "saving-roll", "scope", "prior", "other-record", "schema"),
)
def test_hacking_firewall_delta_preserves_previous_reviewed_effects(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        HACKING_GRANT_SOURCES,
        _check_variant_semantics_delta,
        _hacking_firewall_values,
        _hacking_mod_values,
        _hacking_sr_values,
    )

    old_db, new_db = tmp_path / "old.db", tmp_path / "new.db"
    old_values = [
        {
            "extraId": extra_id, "extraType": "TEXT", "rawValue": raw,
            "effect": {"kind": "hacking-program-grant", "program": "hacking-program:trinity"},
        }
        for extra_id, (raw, _count) in HACKING_GRANT_SOURCES[100]["singles"].items()
    ]
    old_values += _hacking_mod_values(100) + _hacking_sr_values(100)
    old_variant = {
        "inheritance": "family",
        "occurrenceParameters": [{
            "source": "army-extra", "kind": "reviewed-extra",
            "extraValues": old_values,
        }],
    }
    after = copy.deepcopy(old_variant)
    after_values = after["occurrenceParameters"][0]["extraValues"]
    after_values.extend(_hacking_firewall_values(100))
    if defect in {"wip", "saving-roll", "scope", "prior"}:
        if defect == "wip":
            after_values[-1]["effect"]["attackerWipMod"] = -3
        elif defect == "saving-roll":
            after_values[-1]["effect"]["defenderSavingRollMod"] = 6
        elif defect == "scope":
            after_values[-1]["effect"]["appliesTo"] = "all-attacks"
        else:
            after_values.pop(len(HACKING_GRANT_SOURCES[100]["singles"]))
    key = ("n5-core-v5.3", "equipment:hacking-device")
    with sqlite3.connect(old_db) as old, sqlite3.connect(new_db) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*key, json.dumps(old_variant), "untouched"),
            ("n5-core-v5.3", "equipment:other", None, "untouched"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(after), key[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX unexpected ON records(id)")
    changes: dict[tuple[str, str], str] = {key: json.dumps(after)}
    if defect is None:
        _check_variant_semantics_delta(old_db, new_db, changes, hacking_firewall=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(old_db, new_db, changes, hacking_firewall=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(old_db, new_db, changes)


@pytest.mark.parametrize(
    "defect", (None, "id", "name", "count", "value", "type", "compound", "prior"),
)
def test_hacking_firewall_source_gate_rejects_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    old = release.HACKING_GRANT_SOURCES[100]
    prior = [
        {"extra_id": extra_id, "raw_value": raw}
        for extra_id, (raw, _count) in old["singles"].items()
    ] + [
        {"extra_id": extra_id, "raw_value": raw}
        for extra_id, raw, _program, _kind, _field, _value, _count
        in release.HACKING_MOD_SOURCES[100]
    ] + [
        {"extra_id": extra_id, "raw_value": raw}
        for extra_id, raw, _program, _modifier, _count
        in release.HACKING_SR_SOURCES[100]
    ]
    item = {
        "id": 100, "name": old["name"], "applicationId": 100,
        "occurrences": old["occurrences"],
        "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "rawValues": [],
        "reviewedExtra": {"extra_values": prior},
        "extraSignatures": [
            {"extras": [[extra_id, "TEXT", raw]], "count": count, "reviewed": False}
            for extra_id, raw, _modifier, count in release.HACKING_FIREWALL_SOURCES[100]
        ],
    }
    if defect == "id":
        item["applicationId"] = 999
    elif defect == "name":
        item["name"] = "wrong"
    elif defect == "count":
        item["extraSignatures"][0]["count"] += 1
    elif defect == "value":
        item["extraSignatures"][0]["extras"][0][2] = "wrong"
    elif defect == "type":
        item["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "compound":
        item["extraSignatures"].append({
            "extras": [[326, "TEXT", "Firewall -6"],
                       [12, "TEXT", "UPGRADE:\u00a0Trinity"]],
            "reviewed": False, "count": 1,
        })
    elif defect == "prior":
        item["reviewedExtra"]["extra_values"][0]["extra_id"] = 999
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": [item]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_hacking_firewall_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls[0]["hacking_firewall"] is True
        assert calls[0]["variant_records"] == {"equipment:hacking-device"}
    else:
        with pytest.raises(ValueError, match="drift|changed"):
            release.refresh_hacking_firewall_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "missing-combination", "reordered-extras", "wrong-program",
               "prior-grant", "other-record", "schema", "missing-record"),
)
def test_hacking_combination_delta_only_adds_exact_full_signatures(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import _check_variant_semantics_delta

    source = json.loads(
        (ROOT / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    ids = ("equipment:hacking-device", "equipment:hacking-device-plus")
    records = {row["id"]: row for row in source["records"] if row["id"] in ids}
    before_rows = []
    variants: dict[tuple[str, str], str] = {}
    for record_id in ids:
        after = copy.deepcopy(records[record_id]["variantSemantics"])
        previous = copy.deepcopy(after)
        previous.pop("occurrenceCombinations")
        key = ("n5-core-v5.3", record_id)
        before_rows.append((*key, json.dumps(previous), "preserved"))
        variants[key] = json.dumps(after)
    key = ("n5-core-v5.3", ids[0])
    if defect in {"missing-combination", "reordered-extras", "wrong-program", "prior-grant"}:
        after = json.loads(variants[key])
        if defect == "missing-combination":
            after["occurrenceCombinations"].pop()
        elif defect == "reordered-extras":
            after["occurrenceCombinations"][0]["extras"].reverse()
        elif defect == "wrong-program":
            after["occurrenceCombinations"][1]["effects"][0]["program"] = (
                "hacking-program:spotlight"
            )
        else:
            after["occurrenceParameters"][0]["extraValues"].pop(0)
        variants[key] = json.dumps(after)
    before_db, next_db = tmp_path / "before.db", tmp_path / "next.db"
    with sqlite3.connect(before_db) as old, sqlite3.connect(next_db) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", before_rows + [
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        for key, value in variants.items():
            new.execute(
                "UPDATE records SET variant_json=? WHERE collection_id=? AND id=?",
                (value, *key),
            )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX unwanted ON records(id)")
        elif defect == "missing-record":
            new.execute("DELETE FROM records WHERE id='equipment:hacking-device-plus'")
    if defect is None:
        _check_variant_semantics_delta(
            before_db, next_db, variants, hacking_combinations=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                before_db, next_db, variants, hacking_combinations=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(before_db, next_db, variants)


@pytest.mark.parametrize(
    "defect", (None, "name", "count", "extra-id", "raw-value", "reviewed",
               "unqualified", "missing", "previous-combinations"),
)
def test_hacking_combination_source_gate_checks_entire_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    items = []
    for source_id, specs in ((100, (
        ((25, "UPGRADE: Cybermask"), (12, "UPGRADE:\u00a0Trinity"), 1),
        ((373, "UPGRADE: Total Control (PS=3)"),
         (343, "UPGRADE: Trinity (PS=5)"), 2),
    )), (101, (
        ((343, "UPGRADE: Trinity (PS=5)"), (287, "UPGRADE: Zero Pain"), 2),
    ))):
        source = release.HACKING_GRANT_SOURCES[source_id]
        unreviewed = [
            {
                "extras": [[first[0], "TEXT", first[1]],
                           [second[0], "TEXT", second[1]]],
                "reviewed": False, "count": count,
            }
            for first, second, count in specs
        ]
        if source_id == 101:
            unreviewed.append({
                "extras": [[344, "TEXT", "UPGRADE: SR-1"]],
                "reviewed": False, "count": 2,
            })
        items.append({
            "id": source_id, "name": source["name"], "applicationId": source_id,
            "occurrences": source["occurrences"],
            "status": "unresolved-occurrence-parameter",
            "reviewedCombinations": None, "reviewedExtra": {"kind": "reviewed-extra"},
            "rawValues": [], "extraSignatures": unreviewed,
        })
    item = items[0]
    if defect == "name":
        item["name"] = "unexpected"
    elif defect == "count":
        item["extraSignatures"][0]["count"] += 1
    elif defect == "extra-id":
        item["extraSignatures"][0]["extras"][0][0] = 999
    elif defect == "raw-value":
        item["extraSignatures"][0]["extras"][0][2] = "unknown"
    elif defect == "reviewed":
        item["extraSignatures"][0]["reviewed"] = True
    elif defect == "unqualified":
        items[1]["extraSignatures"][-1]["reviewed"] = True
    elif defect == "missing":
        item["extraSignatures"].pop(0)
    elif defect == "previous-combinations":
        item["reviewedCombinations"] = []
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": items}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_hacking_combinations_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {
                "equipment:hacking-device", "equipment:hacking-device-plus",
            }, "hacking_combinations": True,
        }]
    else:
        with pytest.raises(ValueError, match="drift|changed"):
            release.refresh_hacking_combinations_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "modifier", "scope", "raw", "other-record", "schema", "missing"),
)
def test_bangbomb_v9_refresh_guards_exact_parameter_delta(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        BANGBOMB,
        BANGBOMB_VARIANT,
        _check_variant_semantics_delta,
    )

    original, next_db = tmp_path / "original.db", tmp_path / "next.db"
    variant = copy.deepcopy(BANGBOMB_VARIANT)
    if defect in {"modifier", "scope", "raw"}:
        extra = variant["occurrenceParameters"][0]["extraValues"][0]
        if defect == "modifier":
            extra["effect"]["modifier"] = 3
        elif defect == "scope":
            extra["effect"]["appliesTo"] = "all-dodge"
        else:
            extra["rawValue"] = "+3"
    with sqlite3.connect(original) as old, sqlite3.connect(next_db) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*BANGBOMB, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), BANGBOMB[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:bangbomb'")
    variants: dict[tuple[str, str], str] = {BANGBOMB: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(original, next_db, variants, bangbomb=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(original, next_db, variants, bangbomb=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(original, next_db, variants)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id", "extra-type",
               "raw", "status", "previous", "compound"),
)
def test_bangbomb_v9_refresh_checks_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 246, "name": "Bangbomb", "applicationId": 246,
        "occurrences": 125, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [{
            "extras": [[310, "TEXT", "+4"]], "reviewed": False, "count": 125,
        }],
    }
    if defect == "name":
        source["name"] = "different"
    elif defect == "app-id":
        source["applicationId"] = 245
    elif defect == "count":
        source["occurrences"] = 124
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 999
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][0]["extras"][0][2] = "+3"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([310, "TEXT", "+4"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_bangbomb_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:bangbomb"},
            "bangbomb": True,
        }]
    else:
        with pytest.raises(ValueError, match="Bangbomb source signature drift"):
            release.refresh_bangbomb_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "variant", "name", "existing", "extra-row",
               "source-link", "relation", "schema"),
)
def test_ecm_v9_additions_preserve_all_existing_database_rows(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        ECM_SOURCES,
        _check_ecm_source_additions,
        _ecm_variant,
    )

    before_path, after_path = tmp_path / "before.db", tmp_path / "after.db"
    statements = (
        "CREATE TABLE records("
        "collection_id TEXT,id TEXT,name TEXT,kind TEXT,"
        "composition_role TEXT,variant_json TEXT)",
        "CREATE TABLE record_army_links("
        "collection_id TEXT,record_id TEXT,entity TEXT,external_id TEXT)",
        "CREATE TABLE record_citations("
        "collection_id TEXT,record_id TEXT,source_id TEXT)",
        "CREATE TABLE record_relations("
        "collection_id TEXT,record_id TEXT,relation_type TEXT,related_record_id TEXT)",
    )
    with sqlite3.connect(before_path) as old, sqlite3.connect(after_path) as new:
        for statement in statements:
            old.execute(statement)
        old.execute("INSERT INTO records VALUES (?,?,?,?,?,?)", (
            "n5-core-v5.3", "equipment:ecm", "ECM", "equipment",
            "definition", '{"inheritance":"family"}',
        ))
        old.commit()
        old.backup(new)
        variants: dict[tuple[str, str], str] = {}
        for key, spec in ECM_SOURCES.items():
            value = _ecm_variant(key)
            variants[key] = json.dumps(value)
            new.execute("INSERT INTO records VALUES (?,?,?,?,?,?)", (
                *key, spec["recordName"], "equipment", "definition",
                json.dumps(value),
            ))
            new.execute("INSERT INTO record_army_links VALUES (?,?,?,?)", (
                *key, "equipment", str(spec["sourceId"]),
            ))
            new.execute("INSERT INTO record_citations VALUES (?,?,?)", (
                *key, "n5-core-v5.3-pdf",
            ))
            new.execute("INSERT INTO record_relations VALUES (?,?,?,?)", (
                *key, "variant-of", "equipment:ecm",
            ))
        first = next(iter(ECM_SOURCES))
        if defect == "variant":
            value = json.loads(variants[first])
            value["sourceVariant"]["label"] = "Hacker"
            variants[first] = json.dumps(value)
            new.execute("UPDATE records SET variant_json=? WHERE id=?", (
                variants[first], first[1],
            ))
        elif defect == "name":
            new.execute("UPDATE records SET name='wrong' WHERE id=?", (first[1],))
        elif defect == "existing":
            new.execute("UPDATE records SET name='wrong' WHERE id='equipment:ecm'")
        elif defect == "extra-row":
            new.execute("INSERT INTO record_citations VALUES (?,?,?)", (
                "n5-core-v5.3", "equipment:ecm", "bad",
            ))
        elif defect == "source-link":
            new.execute("UPDATE record_army_links SET external_id='999' WHERE record_id=?",
                        (first[1],))
        elif defect == "relation":
            new.execute("UPDATE record_relations SET related_record_id='equipment:firewall'")
        elif defect == "schema":
            new.execute("CREATE INDEX unexpected ON records(id)")
    if defect is None:
        _check_ecm_source_additions(before_path, after_path, variants)
    else:
        with pytest.raises(ValueError):
            _check_ecm_source_additions(before_path, after_path, variants)


@pytest.mark.parametrize(
    "defect", (None, "id", "name", "count", "extra-id", "raw",
               "type", "reviewed", "compound"),
)
def test_ecm_v9_preflight_pins_distinct_guided_extra_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    items = []
    for spec in release.ECM_SOURCES.values():
        items.append({
            "id": spec["sourceId"], "name": spec["name"],
            "applicationId": 239, "occurrences": spec["count"],
            "status": "unresolved-occurrence-parameter",
            "reviewedExtra": None, "reviewedVariant": None,
            "reviewedCombinations": None, "rawValues": [],
            "extraSignatures": [
                {"extras": [[extra_id, "TEXT", str(modifier)]],
                 "reviewed": False, "count": count}
                for extra_id, modifier, count in spec["signatures"]
            ],
        })
    item = items[0]
    if defect == "id":
        item["applicationId"] = 241
    elif defect == "name":
        item["name"] = "wrong"
    elif defect == "count":
        item["extraSignatures"][-1]["count"] += 1
    elif defect == "extra-id":
        item["extraSignatures"][-1]["extras"][0][0] = 51
    elif defect == "raw":
        item["extraSignatures"][-1]["extras"][0][2] = "-6"
    elif defect == "type":
        item["extraSignatures"][-1]["extras"][0][1] = "DISTANCE"
    elif defect == "reviewed":
        item["status"] = "reviewed-extra-parameter"
    elif defect == "compound":
        item["extraSignatures"][-1]["extras"].append([7, "TEXT", "-6"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": items}}},
    )
    calls: list[dict] = []

    def promote(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", promote)
    if defect is None:
        assert release.refresh_ecm_source_variants_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path,
            "variant_records": {"equipment:ecm-guided", "equipment:ecm-hacker"},
            "ecm_sources": True,
        }]
    else:
        with pytest.raises(ValueError, match="ECM source signature drift"):
            release.refresh_ecm_source_variants_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "count", "name", "app-id", "extra-id",
               "raw", "frequency", "status", "previous", "new-extra"),
)
def test_regeneration_v9_source_gate_pins_four_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 62, "name": "Regeneration", "applicationId": 62,
        "occurrences": 82, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None,
        "reviewedNumericMod": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[eid, "TEXT", f"PH={value}"]],
             "reviewed": False, "count": count}
            for eid, value, count in (
                (52, 13, 3), (244, 14, 3), (250, 12, 2), (353, 15, 8)
            )
        ],
    }
    if defect == "count":
        source["occurrences"] = 81
    elif defect == "name":
        source["name"] = "Regenerations"
    elif defect == "app-id":
        source["applicationId"] = 99
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 53
    elif defect == "raw":
        source["extraSignatures"][1]["extras"][0][2] = "PH=15"
    elif defect == "frequency":
        source["extraSignatures"][3]["count"] = 9
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "new-extra":
        source["extraSignatures"].append({
            "extras": [[400, "TEXT", "PH=16"]],
            "reviewed": False, "count": 1,
        })
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "backup"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_regeneration_v9_release(root=tmp_path) == (
            tmp_path / "backup"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"skill:regeneration"},
            "regeneration": True,
        }]
    else:
        with pytest.raises(ValueError, match="Regeneration source-62 signature drift"):
            release.refresh_regeneration_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wrong-scope", "wrong-value", "float-value",
               "wrong-id", "reordered", "other-record", "schema", "missing"),
)
def test_regeneration_v9_delta_only_adds_exact_ph_roll_values(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        REGENERATION,
        REGENERATION_VARIANT,
        _check_variant_semantics_delta,
    )

    before, after = tmp_path / "before.db", tmp_path / "after.db"
    variant = copy.deepcopy(REGENERATION_VARIANT)
    values = variant["occurrenceParameters"][0]["extraValues"]
    if defect == "wrong-scope":
        values[0]["effect"]["appliesTo"] = "all-ph-rolls"
    elif defect == "wrong-value":
        values[1]["effect"]["value"] = 15
    elif defect == "float-value":
        values[2]["effect"]["value"] = 12.0
    elif defect == "wrong-id":
        values[0]["extraId"] = 53
    elif defect == "reordered":
        values.reverse()
    with sqlite3.connect(before) as old, sqlite3.connect(after) as new:
        old.execute(
            "CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)"
        )
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*REGENERATION, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), REGENERATION[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX altered ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:regeneration'")
    changed: dict[tuple[str, str], str] = {REGENERATION: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(before, after, changed, regeneration=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(before, after, changed, regeneration=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(before, after, changed)


@pytest.mark.parametrize(
    "defect", (None, "missing", "wrong-scope", "wrong-id",
               "float-id", "other-record", "schema", "only-one"),
)
def test_chart_rerolls_v9_delta_is_exact_and_pairwise(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        CHART_REROLLS,
        _check_variant_semantics_delta,
    )

    before, after = tmp_path / "before.db", tmp_path / "after.db"
    versions = copy.deepcopy(CHART_REROLLS)
    keys = list(versions)
    if defect == "wrong-scope":
        versions[keys[0]]["occurrenceParameters"][0][
            "extraValues"
        ][0]["effect"]["appliesTo"] = "all-rolls"
    elif defect == "wrong-id":
        versions[keys[0]]["occurrenceParameters"][0][
            "extraValues"
        ][0]["extraId"] = 278
    elif defect == "float-id":
        versions[keys[1]]["occurrenceParameters"][0][
            "extraValues"
        ][0]["extraId"] = 277.0
    with sqlite3.connect(before) as old, sqlite3.connect(after) as new:
        old.execute(
            "CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)"
        )
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*key, '{"inheritance":"family"}', "preserved") for key in keys
        ] + [("n5-core-v5.3", "skill:other", None, "preserved")])
        old.commit()
        old.backup(new)
        for key, variant in versions.items():
            new.execute(
                "UPDATE records SET variant_json=? WHERE collection_id=? AND id=?",
                (json.dumps(variant), *key),
            )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:metachemistry'")
    changes: dict[tuple[str, str], str] = {
        key: json.dumps(value) for key, value in versions.items()
    }
    if defect == "only-one":
        changes.pop(keys[0])
    if defect is None:
        _check_variant_semantics_delta(before, after, changes, chart_rerolls=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                before, after, changes, chart_rerolls=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(before, after, changes)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count",
               "extra-id", "raw", "status", "previous", "count-per-extra"),
)
def test_chart_rerolls_v9_requires_both_exact_pinned_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = [
        {
            "id": source_id, "name": name, "applicationId": source_id,
            "occurrences": count, "status": "unresolved-occurrence-parameter",
            "reviewedVariant": None, "reviewedDistance": None,
            "reviewedNumericMod": None, "reviewedExtra": None,
            "reviewedCombinations": None, "rawValues": [],
            "extraSignatures": [{
                "extras": [[277, "TEXT", "ReRoll"]],
                "reviewed": False, "count": signatures,
            }],
        }
        for source_id, name, count, signatures in (
            (25, "Booty", 482, 108), (55, "MetaChemistry", 117, 60),
        )
    ]
    if defect == "name":
        source[0]["name"] = "Booties"
    elif defect == "app-id":
        source[1]["applicationId"] = 54
    elif defect == "count":
        source[0]["occurrences"] = 481
    elif defect == "extra-id":
        source[1]["extraSignatures"][0]["extras"][0][0] = 278
    elif defect == "raw":
        source[0]["extraSignatures"][0]["extras"][0][2] = "Reroll"
    elif defect == "status":
        source[1]["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source[0]["reviewedExtra"] = {"unexpected": True}
    elif defect == "count-per-extra":
        source[1]["extraSignatures"][0]["count"] = 59
    elif defect == "missing":
        source.pop()
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_a: {"catalogs": {"skills": {"items": source}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_chart_rerolls_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path,
            "variant_records": {"skill:booty", "skill:metachemistry"},
            "chart_rerolls": True,
        }]
    else:
        with pytest.raises(ValueError, match="Chart ReRoll source"):
            release.refresh_chart_rerolls_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id",
               "extra-type", "raw", "pair-order", "status", "previous",
               "extra-combination"),
)
def test_hacker_skill_v9_source_gate_pins_all_four_exact_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 1000, "name": "Hacker", "applicationId": 1000,
        "occurrences": 1094, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None,
        "reviewedNumericMod": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[265, "TEXT", "Zero Pain"]], "reviewed": False, "count": 4},
            {"extras": [[314, "TEXT", "UPGRADE: Total Control (SR-2)"]],
             "reviewed": False, "count": 3},
            {"extras": [[334, "TEXT", "UPGRADE: Firewall (-3)"]],
             "reviewed": False, "count": 2},
            {"extras": [[386, "TEXT", "Carbonite"], [387, "TEXT", "Spotlight"]],
             "reviewed": False, "count": 12},
        ],
    }
    if defect == "name":
        source["name"] = "Hackers"
    elif defect == "app-id":
        source["applicationId"] = 100
    elif defect == "count":
        source["occurrences"] = 1093
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 266
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][1]["extras"][0][2] = "Total Control"
    elif defect == "pair-order":
        source["extraSignatures"][3]["extras"].reverse()
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "extra-combination":
        source["extraSignatures"].append({
            "extras": [[386, "TEXT", "Carbonite"]],
            "reviewed": False, "count": 1,
        })
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_hacker_skill_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"skill:hacker"},
            "hacker_skill": True,
        }]
    else:
        with pytest.raises(ValueError, match="Hacker Skill source-1000 signature drift"):
            release.refresh_hacker_skill_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wrong-owner", "wrong-sr", "float-sr", "wrong-firewall",
               "wrong-grant", "wrong-program", "reordered", "other-record",
               "schema", "missing"),
)
def test_hacker_skill_v9_delta_only_certifies_direct_source_programs(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        HACKER_SKILL,
        HACKER_SOURCE_VARIANT,
        _check_variant_semantics_delta,
    )

    before, after = tmp_path / "before.db", tmp_path / "after.db"
    variant = copy.deepcopy(HACKER_SOURCE_VARIANT)
    values = variant["occurrenceParameters"][0]["extraValues"]
    pair = variant["occurrenceCombinations"][0]
    if defect == "wrong-owner":
        values[0]["effect"]["owner"] = "hacking-device"
    elif defect == "wrong-sr":
        values[1]["effect"]["modifier"] = -1
    elif defect == "float-sr":
        values[1]["effect"]["modifier"] = -2.0
    elif defect == "wrong-firewall":
        values[2]["effect"]["appliesTo"] = "comms-attack-targeting-device-owner"
    elif defect == "wrong-grant":
        values[1]["effect"]["grantsProgram"] = False
    elif defect == "wrong-program":
        pair["effects"][0]["program"] = "hacking-program:trinity"
    elif defect == "reordered":
        pair["extras"].reverse()
    with sqlite3.connect(before) as old, sqlite3.connect(after) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*HACKER_SKILL, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute("UPDATE records SET variant_json=? WHERE id=?",
                    (json.dumps(variant), HACKER_SKILL[1]))
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:hacker'")
    changed: dict[tuple[str, str], str] = {HACKER_SKILL: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(before, after, changed, hacker_skill=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                before, after, changed, hacker_skill=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(before, after, changed)


@pytest.mark.parametrize(
    "defect", (None, "wrong-name", "ammunition-component", "wrong-immunity",
               "wrong-extra", "float-id", "other-record", "schema", "missing"),
)
def test_vulnerability_viral_v9_delta_is_weapon_name_scoped(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        VULNERABILITY,
        VULNERABILITY_VIRAL_VARIANT,
        _check_variant_semantics_delta,
    )

    before, after = tmp_path / "before.db", tmp_path / "after.db"
    variant = copy.deepcopy(VULNERABILITY_VIRAL_VARIANT)
    entry = variant["occurrenceParameters"][0]["extraValues"][0]
    effect = entry["effect"]
    if defect == "wrong-name":
        effect["weaponNameContains"] = "Shock"
    elif defect == "ammunition-component":
        effect["appliesTo"] = "attack-with-ammunition-component-viral"
    elif defect == "wrong-immunity":
        effect["immunity"] = "skill:immunity-enhanced"
    elif defect == "wrong-extra":
        entry["extraId"] = 40
    elif defect == "float-id":
        entry["extraId"] = 39.0
    with sqlite3.connect(before) as old, sqlite3.connect(after) as new:
        old.execute(
            "CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)"
        )
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*VULNERABILITY, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), VULNERABILITY[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:vulnerability'")
    changed: dict[tuple[str, str], str] = {VULNERABILITY: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(
            before, after, changed, vulnerability=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                before, after, changed, vulnerability=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(before, after, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id", "raw",
               "count-per-extra", "status", "previous", "compound"),
)
def test_vulnerability_viral_v9_source_gate_is_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 220, "name": "Vulnerability", "applicationId": 220,
        "occurrences": 2, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None,
        "reviewedNumericMod": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [{
            "extras": [[39, "TEXT", "Viral"]],
            "reviewed": False, "count": 2,
        }],
    }
    if defect == "name":
        source["name"] = "Viral Vulnerability"
    elif defect == "app-id":
        source["applicationId"] = 221
    elif defect == "count":
        source["occurrences"] = 3
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 40
    elif defect == "raw":
        source["extraSignatures"][0]["extras"][0][2] = "VIRAL"
    elif defect == "count-per-extra":
        source["extraSignatures"][0]["count"] = 3
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([1, "TEXT", "+3"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_vulnerability_viral_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"skill:vulnerability"},
            "vulnerability": True,
        }]
    else:
        with pytest.raises(ValueError, match="Vulnerability source-220 signature drift"):
            release.refresh_vulnerability_viral_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wrong-count", "wrong-scope", "wrong-extra-id",
               "float-count", "reordered", "other-record", "schema", "missing"),
)
def test_decoy_v9_refresh_only_adds_exact_replica_counts(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        DECOY,
        DECOY_VARIANT,
        _check_variant_semantics_delta,
    )

    before, after = tmp_path / "before.db", tmp_path / "after.db"
    variant = copy.deepcopy(DECOY_VARIANT)
    extras = variant["occurrenceParameters"][0]["extraValues"]
    if defect == "wrong-count":
        extras[0]["effect"]["count"] = 2
    elif defect == "wrong-scope":
        extras[1]["effect"]["appliesTo"] = "all-deployment"
    elif defect == "wrong-extra-id":
        extras[0]["extraId"] = 267
    elif defect == "float-count":
        extras[1]["effect"]["count"] = 2.0
    elif defect == "reordered":
        extras.reverse()
    with sqlite3.connect(before) as old, sqlite3.connect(after) as new:
        old.execute(
            "CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)"
        )
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*DECOY, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), DECOY[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:decoy'")
    changed: dict[tuple[str, str], str] = {DECOY: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(before, after, changed, decoy=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(before, after, changed, decoy=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(before, after, changed)


@pytest.mark.parametrize(
    "defect", (None, "count", "name", "app-id", "extra-id",
               "raw", "count-per-extra", "status", "previous", "additional"),
)
def test_decoy_v9_refresh_checks_pinned_source_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 215, "name": "Decoy", "applicationId": 215,
        "occurrences": 162, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None,
        "reviewedNumericMod": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[44, "TEXT", "1"]], "reviewed": False, "count": 132},
            {"extras": [[267, "TEXT", "2"]], "reviewed": False, "count": 24},
        ],
    }
    if defect == "count":
        source["occurrences"] = 161
    elif defect == "name":
        source["name"] = "Decoys"
    elif defect == "app-id":
        source["applicationId"] = 220
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 45
    elif defect == "raw":
        source["extraSignatures"][1]["extras"][0][2] = "1"
    elif defect == "count-per-extra":
        source["extraSignatures"][0]["count"] = 131
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "additional":
        source["extraSignatures"].append({
            "extras": [[99, "TEXT", "3"]], "reviewed": False, "count": 1,
        })
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_decoy_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"skill:decoy"},
            "decoy": True,
        }]
    else:
        with pytest.raises(ValueError, match="Decoy source-215 signature drift"):
            release.refresh_decoy_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "other-record", "schema", "missing", "no-op",
               "wrong-base", "other-variant"),
)
def test_commlink_v9_guard_preserves_other_records_and_schema(
    tmp_path: Path, defect: str | None,
) -> None:
    """The optional annex variant may be appended, not broadly republished."""
    from tools.restrictions_v9_release import _check_variant_semantics_delta

    source = Path(__file__).resolve().parents[1] / (
        "data/curated/rules/reinforcements-extra-n4-reference.json"
    )
    document = json.loads(source.read_text(encoding="utf-8"))
    record = next(row for row in document["records"] if row["id"] == "skill:commlink")
    variant = copy.deepcopy(record["variantSemantics"])
    key = ("reinforcements-extra-n4-reference", "skill:commlink")
    before, after = tmp_path / "before.db", tmp_path / "after.db"
    baseline = '{"inheritance":"family"}'
    with sqlite3.connect(before) as old, sqlite3.connect(after) as new:
        old.execute(
            "CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)"
        )
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*key, baseline, "preserved"),
            ("reinforcements-extra-n4-reference", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        if defect == "wrong-base":
            old.execute(
                "UPDATE records SET variant_json=? WHERE id='skill:commlink'",
                ('{"inheritance":"source"}',),
            )
            old.commit()
        if defect != "no-op":
            new.execute(
                "UPDATE records SET variant_json=? WHERE id='skill:commlink'",
                (json.dumps(variant),),
            )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:commlink'")
        elif defect == "other-variant":
            new.execute(
                "UPDATE records SET variant_json=? WHERE id='skill:other'",
                ('{"inheritance":"family"}',),
            )
    changed: dict[tuple[str, str], str] = {key: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(before, after, changed)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(before, after, changed)


@pytest.mark.parametrize(
    "defect", (None, "wrong-unit", "wrong-scope", "wrong-raw",
               "wrong-extra-id", "other-record", "schema", "missing"),
)
def test_ft_master_v9_refresh_only_changes_exact_source_metadata(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        FT_MASTER,
        FT_MASTER_VARIANT,
        _check_variant_semantics_delta,
    )

    before, after = tmp_path / "before.db", tmp_path / "after.db"
    variant = copy.deepcopy(FT_MASTER_VARIANT)
    extras = variant["occurrenceParameters"][0]["extraValues"]
    if defect == "wrong-unit":
        extras[3]["effect"]["unitNames"] = ["Morlocks"]
    elif defect == "wrong-scope":
        extras[0]["effect"]["appliesTo"] = "all-fireteams"
    elif defect == "wrong-raw":
        extras[1]["rawValue"] = "Shaolin Monks"
    elif defect == "wrong-extra-id":
        extras[1]["extraId"] = 330
    with sqlite3.connect(before) as old, sqlite3.connect(after) as new:
        old.execute(
            "CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)"
        )
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*FT_MASTER, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), FT_MASTER[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:ft-master'")
    changed: dict[tuple[str, str], str] = {FT_MASTER: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(before, after, changed, ft_master=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(before, after, changed, ft_master=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(before, after, changed)


@pytest.mark.parametrize(
    "defect", (None, "count", "name", "app-id", "extra-id",
               "raw", "count-per-extra", "status", "previous", "additional"),
)
def test_ft_master_v9_refresh_checks_pinned_source_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from infinity_db.curated import FT_MASTER_UNIT_SIGNATURES
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    raw_counts = (2, 47, 1, 2, 2, 2, 2, 1)
    source = {
        "id": 261, "name": "FT Master", "applicationId": 261,
        "occurrences": 61, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None,
        "reviewedNumericMod": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[extra_id, "TEXT", raw]], "reviewed": False,
             "count": count}
            for (extra_id, raw, _names), count in zip(
                FT_MASTER_UNIT_SIGNATURES, raw_counts, strict=True,
            )
        ],
    }
    if defect == "count":
        source["occurrences"] = 60
    elif defect == "name":
        source["name"] = "FT-Master"
    elif defect == "app-id":
        source["applicationId"] = 999
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 321
    elif defect == "raw":
        source["extraSignatures"][3]["extras"][0][2] = "Morlocks"
    elif defect == "count-per-extra":
        source["extraSignatures"][1]["count"] = 46
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "additional":
        source["extraSignatures"].append({
            "extras": [[999, "TEXT", "Unknown"]], "reviewed": False, "count": 1,
        })
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_ft_master_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"skill:ft-master"},
            "ft_master": True,
        }]
    else:
        with pytest.raises(ValueError, match="FT Master source-261 signature drift"):
            release.refresh_ft_master_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wrong-recipient", "wrong-condition", "wrong-dodge-scope",
               "wrong-gizmokit-scope", "changed-mod", "wrong-stacking",
               "incomplete", "reordered", "other-record", "schema", "missing"),
)
def test_tagcom_v9_refresh_only_promotes_exact_combat_group_modifiers(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        TAGCOM,
        TAGCOM_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(TAGCOM_VARIANT)
    combos = variant["occurrenceCombinations"]
    if defect == "wrong-recipient":
        combos[0]["effects"][0]["recipient"] = "tagcom-user"
    elif defect == "wrong-condition":
        combos[0]["effects"][1]["sourceCondition"] = "tagcom-user-null"
    elif defect == "wrong-dodge-scope":
        combos[1]["effects"][0]["appliesTo"] = "all-dodge-rolls"
    elif defect == "wrong-gizmokit-scope":
        combos[1]["effects"][1]["appliesTo"] = "gizmokit-user-bs-attack"
    elif defect == "changed-mod":
        combos[2]["effects"][0]["modifier"] = 3
    elif defect == "wrong-stacking":
        combos[0]["effects"][0]["stacking"] = "cumulative"
    elif defect == "incomplete":
        combos[0]["extras"].pop()
    elif defect == "reordered":
        combos[0]["extras"].reverse()
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*TAGCOM, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), TAGCOM[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:tagcom'")
    changed: dict[tuple[str, str], str] = {TAGCOM: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, tagcom=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(previous, proposed, changed, tagcom=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id", "extra-type",
               "raw", "order", "status", "previous", "compound"),
)
def test_tagcom_v9_refresh_requires_exact_pinned_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 270, "name": "TAGCom", "applicationId": 270,
        "occurrences": 28, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None,
        "reviewedNumericMod": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[312, "TEXT", "Dodge (PH+3)"],
                        [313, "TEXT", "GizmoKit (PH+1)"]],
             "reviewed": False, "count": 2},
            {"extras": [[369, "TEXT", "Dodge (PH+3), GizmoKit (PH+1)"]],
             "reviewed": False, "count": 24},
            {"extras": [[370, "TEXT", "Dodge (PH+1), GizmoKit (PH+1)"]],
             "reviewed": False, "count": 2},
        ],
    }
    if defect == "name":
        source["name"] = "TagCom"
    elif defect == "app-id":
        source["applicationId"] = 999
    elif defect == "count":
        source["occurrences"] = 27
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 313
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][1]["extras"][0][2] = "Dodge (PH+1)"
    elif defect == "order":
        source["extraSignatures"][0]["extras"].reverse()
    elif defect == "status":
        source["status"] = "reviewed-combination-parameter"
    elif defect == "previous":
        source["reviewedCombinations"] = [{"unexpected": True}]
    elif defect == "compound":
        source["extraSignatures"].append(
            {"extras": [[312, "TEXT", "Dodge (PH+3)"]],
             "reviewed": False, "count": 1}
        )
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_tagcom_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"skill:tagcom"},
            "tagcom": True,
        }]
    else:
        with pytest.raises(ValueError, match="TAGCom source-270 signature drift"):
            release.refresh_tagcom_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wrong-recipient", "wrong-attribute", "changed-mod",
               "incomplete", "reordered", "other-record", "schema", "missing"),
)
def test_remdriver_v9_refresh_only_promotes_exact_compound_metadata(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        REMDRIVER,
        REMDRIVER_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(REMDRIVER_VARIANT)
    combos = variant["occurrenceCombinations"]
    if defect == "wrong-recipient":
        combos[0]["effects"][0]["recipient"] = "remdriver-user"
    elif defect == "wrong-attribute":
        combos[1]["effects"][1]["attribute"] = "WIP"
    elif defect == "changed-mod":
        combos[0]["effects"][0]["modifier"] = 2
    elif defect == "incomplete":
        combos[2]["extras"].pop()
    elif defect == "reordered":
        combos[1]["extras"].reverse()
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*REMDRIVER, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), REMDRIVER[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:remdriver'")
    changed: dict[tuple[str, str], str] = {REMDRIVER: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, remdriver=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(previous, proposed, changed, remdriver=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "signature-id", "raw",
               "order", "status", "previous", "extra-combo"),
)
def test_remdriver_v9_refresh_requires_exact_pinned_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 255, "name": "RemDriver", "applicationId": 255,
        "occurrences": 12, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None,
        "reviewedNumericMod": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[271, "TEXT", "+1 BS"], [300, "TEXT", "+5 CC"]],
             "reviewed": False, "count": 3},
            {"extras": [[280, "TEXT", "CC=15"], [281, "TEXT", "BS=13"],
                        [282, "TEXT", "WIP=14"]],
             "reviewed": False, "count": 5},
            {"extras": [[281, "TEXT", "BS=13"], [52, "TEXT", "PH=13"],
                        [384, "TEXT", "BTS=6"]],
             "reviewed": False, "count": 4},
        ],
    }
    if defect == "name":
        source["name"] = "Other"
    elif defect == "app-id":
        source["applicationId"] = 250
    elif defect == "count":
        source["occurrences"] = 11
    elif defect == "signature-id":
        source["extraSignatures"][0]["extras"][0][0] = 280
    elif defect == "raw":
        source["extraSignatures"][1]["extras"][1][2] = "BS=14"
    elif defect == "order":
        source["extraSignatures"][2]["extras"].reverse()
    elif defect == "status":
        source["status"] = "reviewed-combination-parameter"
    elif defect == "previous":
        source["reviewedCombinations"] = [{"unexpected": True}]
    elif defect == "extra-combo":
        source["extraSignatures"].append(
            {"extras": [[271, "TEXT", "+1 BS"]], "reviewed": False, "count": 1}
        )
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_remdriver_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"skill:remdriver"},
            "remdriver": True,
        }]
    else:
        with pytest.raises(ValueError, match="RemDriver source signature drift"):
            release.refresh_remdriver_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wrong-state", "wrong-scope", "not-only", "raw",
               "other-record", "schema", "missing"),
)
def test_impersonation_v9_refresh_only_changes_exact_imp2_semantics(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        IMPERSONATION,
        IMPERSONATION_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(IMPERSONATION_VARIANT)
    extra = variant["occurrenceParameters"][0]["extraValues"][0]
    if defect == "wrong-state":
        extra["effect"]["state"] = "state:impersonation-1"
    elif defect == "wrong-scope":
        extra["effect"]["appliesTo"] = "deployment-only"
    elif defect == "not-only":
        extra["effect"]["only"] = False
    elif defect == "raw":
        extra["rawValue"] = "IMP-1"
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*IMPERSONATION, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "skill:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), IMPERSONATION[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='skill:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='skill:impersonation'")
    changed: dict[tuple[str, str], str] = {IMPERSONATION: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, impersonation=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(previous, proposed, changed, impersonation=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id", "extra-type",
               "raw", "status", "previous", "compound"),
)
def test_impersonation_v9_refresh_checks_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 249, "name": "Impersonation", "applicationId": 249,
        "occurrences": 14, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None, "reviewedNumericMod": None,
        "reviewedExtra": None, "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [{
            "extras": [[268, "TEXT", "IMP-2"]], "reviewed": False, "count": 9,
        }],
    }
    if defect == "name":
        source["name"] = "other"
    elif defect == "app-id":
        source["applicationId"] = 248
    elif defect == "count":
        source["occurrences"] = 13
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 99
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][0]["extras"][0][2] = "IMP-1"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([268, "TEXT", "IMP-2"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_impersonation_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"skill:impersonation"},
            "impersonation": True,
        }]
    else:
        with pytest.raises(ValueError, match="Impersonation source signature drift"):
            release.refresh_impersonation_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "missing-grant", "ap", "opponent-scope", "firewall",
               "compound", "other-record", "schema", "missing"),
)
def test_khd_v9_refresh_only_changes_exact_reviewed_extras(
    tmp_path: Path, defect: str | None,
) -> None:
    from infinity_db.curated import KILLER_HACKING_VARIANT
    from tools.restrictions_v9_release import (
        KILLER_HACKING_DEVICE,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(KILLER_HACKING_VARIANT)
    entries = variant["occurrenceParameters"][0]["extraValues"]
    if defect == "missing-grant":
        entries.pop(0)
    elif defect == "ap":
        entries[4]["effect"]["ammunition"] = "ammunition:normal"
    elif defect == "opponent-scope":
        entries[5]["effect"]["appliesTo"] = "all-enemy-rolls"
    elif defect == "firewall":
        entries[6]["effect"]["defenderSavingRollMod"] = 0
    elif defect == "compound":
        entries[7]["effect"]["grantsProgram"] = False
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*KILLER_HACKING_DEVICE, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), KILLER_HACKING_DEVICE[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:killer-hacking-device'")
    changed: dict[tuple[str, str], str] = {
        KILLER_HACKING_DEVICE: json.dumps(variant),
    }
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, killer_hacking=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                previous, proposed, changed, killer_hacking=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id", "extra-type",
               "raw", "status", "previous", "compound"),
)
def test_khd_v9_refresh_requires_exact_pinned_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 145, "name": "Killer Hacking Device", "applicationId": 145,
        "occurrences": 229, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[extra_id, "TEXT", raw]], "reviewed": False, "count": count}
            for extra_id, raw, count in (
                (13, "UPGRADE: Carbonite", 10),
                (14, "UPGRADE: Spotlight", 6),
                (20, "UPGRADE:\u00a0White Noise", 1),
                (21, "UPGRADE: Oblivion", 2),
                (270, "UPGRADE: Trinity (AP)", 2),
                (286, "UPGRADE: Trinity (-3)", 4),
                (334, "UPGRADE: Firewall (-3)", 14),
                (335, "UPGRADES: Carbonite, Firewall (-3)", 4),
                (339, "UPGRADE: Trinity (SR-1)", 1),
                (343, "UPGRADE: Trinity (PS=5)", 1),
            )
        ],
    }
    if defect == "name":
        source["name"] = "other"
    elif defect == "app-id":
        source["applicationId"] = 144
    elif defect == "count":
        source["occurrences"] = 228
    elif defect == "extra-id":
        source["extraSignatures"][7]["extras"][0][0] = 99
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][2]["extras"][0][2] = "UPGRADE: White Noise"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][7]["extras"].append([334, "TEXT", "Firewall"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_killer_hacking_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:killer-hacking-device"},
            "killer_hacking": True,
        }]
    else:
        with pytest.raises(ValueError, match="Killer Hacking source signature drift"):
            release.refresh_killer_hacking_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "generic-scope", "template-scope", "wrong-mod",
               "wrong-source", "equipment-change", "other-record",
               "schema", "missing"),
)
def test_bangbomb_skill_266_delta_preserves_equipment_dodge_scope(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        BANGBOMB,
        BANGBOMB_SKILL_VARIANT,
        BANGBOMB_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(BANGBOMB_SKILL_VARIANT)
    extra = variant["sourceCatalogParameters"][0]["extraValues"][0]
    if defect == "generic-scope":
        extra["effect"]["appliesTo"] = "all-dodge-rolls"
    elif defect == "template-scope":
        extra["effect"]["appliesTo"] = "dodge-vs-all-enemy-attacks"
    elif defect == "wrong-mod":
        extra["effect"]["modifier"] = 5
    elif defect == "wrong-source":
        variant["sourceCatalogParameters"][0]["sourceId"] = 246
    elif defect == "equipment-change":
        variant["occurrenceParameters"][0]["extraValues"][0]["effect"][
            "modifier"
        ] = 3
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*BANGBOMB, json.dumps(BANGBOMB_VARIANT), "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), BANGBOMB[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:bangbomb'")
    changed: dict[tuple[str, str], str] = {BANGBOMB: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, bangbomb_skill=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                previous, proposed, changed, bangbomb_skill=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id",
               "extra-type", "raw", "status", "previous", "compound"),
)
def test_bangbomb_skill_266_source_gate_checks_exact_raw_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 266, "name": "Bangbomb", "applicationId": 266,
        "occurrences": 4, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None,
        "reviewedNumericMod": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [{
            "extras": [[310, "TEXT", "+4"]], "reviewed": False, "count": 4,
        }],
    }
    if defect == "name":
        source["name"] = "BangBomb"
    elif defect == "app-id":
        source["applicationId"] = 246
    elif defect == "count":
        source["occurrences"] = 5
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 8
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][0]["extras"][0][2] = "+3"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([310, "TEXT", "+4"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_bangbomb_skill_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:bangbomb"},
            "bangbomb_skill": True,
        }]
    else:
        with pytest.raises(ValueError, match="Bangbomb Skill source-266 signature drift"):
            release.refresh_bangbomb_skill_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wrong-scope", "wrong-value", "wrong-source",
               "burst-change", "other-record", "schema", "missing"),
)
def test_medikit_target_ph_cross_catalog_delta_is_exact(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        MEDIKIT,
        MEDIKIT_TARGET_PH_VARIANT,
        MEDIKIT_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(MEDIKIT_TARGET_PH_VARIANT)
    if defect == "wrong-scope":
        variant["sourceCatalogParameters"][0]["extraValues"][0]["effect"][
            "appliesTo"
        ] = "medikit-user-bs-attack"
    elif defect == "wrong-value":
        variant["sourceCatalogParameters"][0]["extraValues"][0]["effect"]["value"] = 14
    elif defect == "wrong-source":
        variant["sourceCatalogParameters"][0]["sourceId"] = 106
    elif defect == "burst-change":
        variant["occurrenceParameters"][0]["extraValues"][0]["effect"]["modifier"] = 2
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*MEDIKIT, json.dumps(MEDIKIT_VARIANT), "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), MEDIKIT[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:medikit'")
    changed: dict[tuple[str, str], str] = {MEDIKIT: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(
            previous, proposed, changed, medikit_target_ph=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                previous, proposed, changed, medikit_target_ph=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id",
               "raw", "status", "previous", "compound"),
)
def test_medikit_target_ph_source_gate_checks_exact_skill_273_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 273, "name": "MediKit", "applicationId": 273,
        "occurrences": 31, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None, "reviewedNumericMod": None,
        "reviewedExtra": None, "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[extra_id, "TEXT", f"PH={value}"]],
             "reviewed": False, "count": count}
            for extra_id, value, count in (
                (52, 13, 2), (244, 14, 12), (250, 12, 1),
                (340, 16, 4), (353, 15, 6), (382, 17, 6),
            )
        ],
    }
    if defect == "name":
        source["name"] = "Medikit"
    elif defect == "app-id":
        source["applicationId"] = 106
    elif defect == "count":
        source["occurrences"] = 30
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 8
    elif defect == "raw":
        source["extraSignatures"][1]["extras"][0][2] = "PH=13"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([244, "TEXT", "PH=14"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_medikit_target_ph_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:medikit"},
            "medikit_target_ph": True,
        }]
    else:
        with pytest.raises(ValueError, match="MediKit target PH source signature drift"):
            release.refresh_medikit_target_ph_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "wrong-scope", "wrong-value", "wrong-source",
               "burst-change", "other-record", "schema", "missing"),
)
def test_gizmokit_target_ph_cross_catalog_delta_is_exact(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        GIZMOKIT,
        GIZMOKIT_TARGET_PH_VARIANT,
        GIZMOKIT_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(GIZMOKIT_TARGET_PH_VARIANT)
    if defect == "wrong-scope":
        variant["sourceCatalogParameters"][0]["extraValues"][0]["effect"][
            "appliesTo"
        ] = "gizmokit-user-bs-attack"
    elif defect == "wrong-value":
        variant["sourceCatalogParameters"][0]["extraValues"][0]["effect"]["value"] = 10
    elif defect == "wrong-source":
        variant["sourceCatalogParameters"][0]["sourceId"] = 237
    elif defect == "burst-change":
        variant["occurrenceParameters"][0]["extraValues"][0]["effect"]["modifier"] = 2
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*GIZMOKIT, json.dumps(GIZMOKIT_VARIANT), "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), GIZMOKIT[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:gizmokit'")
    changed: dict[tuple[str, str], str] = {GIZMOKIT: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(
            previous, proposed, changed, gizmokit_target_ph=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                previous, proposed, changed, gizmokit_target_ph=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id",
               "raw", "status", "previous", "compound"),
)
def test_gizmokit_target_ph_source_gate_checks_exact_skill_254_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 254, "name": "Gizmokit", "applicationId": 254,
        "occurrences": 288, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedDistance": None, "reviewedNumericMod": None,
        "reviewedExtra": None, "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[extra_id, "TEXT", f"PH={value}"]],
             "reviewed": False, "count": count}
            for extra_id, value, count in (
                (27, 11, 131), (32, 10, 53), (46, 9, 57),
                (52, 13, 33), (244, 14, 4), (250, 12, 10),
            )
        ],
    }
    if defect == "name":
        source["name"] = "GizmoKit"
    elif defect == "app-id":
        source["applicationId"] = 237
    elif defect == "count":
        source["occurrences"] = 287
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 8
    elif defect == "raw":
        source["extraSignatures"][1]["extras"][0][2] = "PH=11"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([32, "TEXT", "PH=10"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"skills": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_gizmokit_target_ph_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:gizmokit"},
            "gizmokit_target_ph": True,
        }]
    else:
        with pytest.raises(ValueError, match="GizmoKit target PH source signature drift"):
            release.refresh_gizmokit_target_ph_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "burst-scope", "burst-value", "reroll-scope",
               "reroll-kind", "raw", "other-record", "schema", "missing"),
)
def test_deactivator_v9_refresh_only_changes_exact_wip_metadata(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        DEACTIVATOR,
        DEACTIVATOR_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(DEACTIVATOR_VARIANT)
    burst, reroll = variant["occurrenceParameters"][0]["extraValues"]
    if defect == "burst-scope":
        burst["effect"]["appliesTo"] = "all-wip-rolls"
    elif defect == "burst-value":
        burst["effect"]["modifier"] = 2
    elif defect == "reroll-scope":
        reroll["effect"]["appliesTo"] = "all-wip-rolls"
    elif defect == "reroll-kind":
        reroll["effect"]["kind"] = "equipment-burst-mod"
    elif defect == "raw":
        reroll["rawValue"] = "ReRoll WIP"
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*DEACTIVATOR, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), DEACTIVATOR[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:deactivator'")
    changed: dict[tuple[str, str], str] = {DEACTIVATOR: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, deactivator=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(previous, proposed, changed, deactivator=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "burst-id", "reroll-id",
               "burst-raw", "reroll-raw", "status", "previous", "compound"),
)
def test_deactivator_v9_refresh_checks_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 238, "name": "Deactivator", "applicationId": 238,
        "occurrences": 416, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [
            {"extras": [[8, "TEXT", "+1B"]], "reviewed": False, "count": 1},
            {"extras": [[277, "TEXT", "ReRoll"]], "reviewed": False, "count": 9},
        ],
    }
    if defect == "name":
        source["name"] = "different"
    elif defect == "app-id":
        source["applicationId"] = 237
    elif defect == "count":
        source["occurrences"] = 415
    elif defect == "burst-id":
        source["extraSignatures"][0]["extras"][0][0] = 99
    elif defect == "reroll-id":
        source["extraSignatures"][1]["extras"][0][0] = 99
    elif defect == "burst-raw":
        source["extraSignatures"][0]["extras"][0][2] = "+1SD"
    elif defect == "reroll-raw":
        source["extraSignatures"][1]["extras"][0][2] = "ReRoll WIP"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][1]["extras"].append([8, "TEXT", "+1B"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_deactivator_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:deactivator"},
            "deactivator": True,
        }]
    else:
        with pytest.raises(ValueError, match="Deactivator source signature drift"):
            release.refresh_deactivator_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "modifier", "scope", "raw", "other-record", "schema", "missing"),
)
def test_gizmokit_v9_refresh_only_changes_exact_ranged_burst_metadata(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        GIZMOKIT,
        GIZMOKIT_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(GIZMOKIT_VARIANT)
    if defect in {"modifier", "scope", "raw"}:
        extra = variant["occurrenceParameters"][0]["extraValues"][0]
        if defect == "modifier":
            extra["effect"]["modifier"] = 2
        elif defect == "scope":
            extra["effect"]["appliesTo"] = "all-gizmokit-uses"
        else:
            extra["rawValue"] = "+1SD"
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*GIZMOKIT, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), GIZMOKIT[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:gizmokit'")
    changed: dict[tuple[str, str], str] = {GIZMOKIT: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, gizmokit=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(previous, proposed, changed, gizmokit=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "modifier", "scope", "raw", "other-record", "schema", "missing"),
)
def test_medikit_v9_refresh_only_changes_exact_ranged_burst_metadata(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        MEDIKIT,
        MEDIKIT_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(MEDIKIT_VARIANT)
    if defect in {"modifier", "scope", "raw"}:
        extra = variant["occurrenceParameters"][0]["extraValues"][0]
        if defect == "modifier":
            extra["effect"]["modifier"] = 2
        elif defect == "scope":
            extra["effect"]["appliesTo"] = "all-medikit-uses"
        else:
            extra["rawValue"] = "+1SD"
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*MEDIKIT, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), MEDIKIT[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:medikit'")
    changed: dict[tuple[str, str], str] = {MEDIKIT: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, medikit=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(previous, proposed, changed, medikit=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id", "extra-type",
               "raw", "status", "previous", "compound"),
)
def test_gizmokit_v9_refresh_checks_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 237, "name": "GizmoKit", "applicationId": 237,
        "occurrences": 544, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [{
            "extras": [[8, "TEXT", "+1B"]], "reviewed": False, "count": 16,
        }],
    }
    if defect == "name":
        source["name"] = "different"
    elif defect == "app-id":
        source["applicationId"] = 236
    elif defect == "count":
        source["occurrences"] = 543
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 999
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][0]["extras"][0][2] = "+1SD"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([8, "TEXT", "+1B"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_gizmokit_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:gizmokit"},
            "gizmokit": True,
        }]
    else:
        with pytest.raises(ValueError, match="GizmoKit source signature drift"):
            release.refresh_gizmokit_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id", "extra-type",
               "raw", "status", "previous", "compound"),
)
def test_medikit_v9_refresh_checks_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 106, "name": "MediKit", "applicationId": 106,
        "occurrences": 573, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [{
            "extras": [[8, "TEXT", "+1B"]], "reviewed": False, "count": 38,
        }],
    }
    if defect == "name":
        source["name"] = "different"
    elif defect == "app-id":
        source["applicationId"] = 105
    elif defect == "count":
        source["occurrences"] = 572
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 999
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][0]["extras"][0][2] = "+1SD"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([8, "TEXT", "+1B"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_medikit_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:medikit"},
            "medikit": True,
        }]
    else:
        with pytest.raises(ValueError, match="MediKit source signature drift"):
            release.refresh_medikit_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (None, "grant", "modifier", "scope", "program", "raw",
               "other-record", "schema", "missing"),
)
def test_evo_trinity_v9_refresh_requires_coupled_exact_metadata(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        EVO_HACKING_DEVICE,
        EVO_TRINITY_VARIANT,
        _check_variant_semantics_delta,
    )

    previous, proposed = tmp_path / "previous.db", tmp_path / "proposed.db"
    variant = copy.deepcopy(EVO_TRINITY_VARIANT)
    if defect in {"grant", "modifier", "scope", "program", "raw"}:
        extra = variant["occurrenceParameters"][0]["extraValues"][0]
        if defect == "grant":
            extra["effect"]["grantsProgram"] = False
        elif defect == "modifier":
            extra["effect"]["modifier"] = -1
        elif defect == "scope":
            extra["effect"]["appliesTo"] = "all-programs"
        elif defect == "program":
            extra["effect"]["program"] = "hacking-program:carbonite"
        else:
            extra["rawValue"] = "UPGRADE: Trinity (SR-1)"
    with sqlite3.connect(previous) as old, sqlite3.connect(proposed) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*EVO_HACKING_DEVICE, '{"inheritance":"family"}', "preserved"),
            ("n5-core-v5.3", "equipment:other", None, "preserved"),
        ])
        old.commit()
        old.backup(new)
        new.execute(
            "UPDATE records SET variant_json=? WHERE id=?",
            (json.dumps(variant), EVO_HACKING_DEVICE[1]),
        )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='altered' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX changed ON records(id)")
        elif defect == "missing":
            new.execute("DELETE FROM records WHERE id='equipment:evo-hacking-device'")
    changed: dict[tuple[str, str], str] = {EVO_HACKING_DEVICE: json.dumps(variant)}
    if defect is None:
        _check_variant_semantics_delta(previous, proposed, changed, evo_trinity=True)
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(previous, proposed, changed, evo_trinity=True)
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(previous, proposed, changed)


@pytest.mark.parametrize(
    "defect", (None, "name", "app-id", "count", "extra-id", "extra-type",
               "raw", "status", "previous", "compound"),
)
def test_evo_trinity_v9_refresh_checks_pinned_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    source = {
        "id": 182, "name": "EVO Hacking Device", "applicationId": 182,
        "occurrences": 40, "status": "unresolved-occurrence-parameter",
        "reviewedVariant": None, "reviewedExtra": None,
        "reviewedCombinations": None, "rawValues": [],
        "extraSignatures": [{
            "extras": [[352, "TEXT", "UPGRADE: Trinity (SR-2)"]],
            "reviewed": False, "count": 2,
        }],
    }
    if defect == "name":
        source["name"] = "different"
    elif defect == "app-id":
        source["applicationId"] = 101
    elif defect == "count":
        source["occurrences"] = 39
    elif defect == "extra-id":
        source["extraSignatures"][0]["extras"][0][0] = 339
    elif defect == "extra-type":
        source["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "raw":
        source["extraSignatures"][0]["extras"][0][2] = "UPGRADE: Trinity (SR-1)"
    elif defect == "status":
        source["status"] = "reviewed-extra-parameter"
    elif defect == "previous":
        source["reviewedExtra"] = {"unexpected": True}
    elif defect == "compound":
        source["extraSignatures"][0]["extras"].append([352, "TEXT", "UPGRADE: Trinity (SR-2)"])
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": [source]}}},
    )
    calls: list[dict] = []

    def migrate(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", migrate)
    if defect is None:
        assert release.refresh_evo_trinity_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path, "variant_records": {"equipment:evo-hacking-device"},
            "evo_trinity": True,
        }]
    else:
        with pytest.raises(ValueError, match="EVO Trinity source signature drift"):
            release.refresh_evo_trinity_v9_release(root=tmp_path)
        assert not calls


@pytest.mark.parametrize(
    "defect", (
        None, "missing-grant", "false-grant", "baseline-grant",
        "wrong-program", "wrong-modifier", "wrong-combo",
        "other-record", "schema", "missing-device",
    ),
)
def test_hacking_trinity_access_v9_delta_is_additive_and_exact(
    tmp_path: Path, defect: str | None,
) -> None:
    from tools.restrictions_v9_release import (
        _check_variant_semantics_delta,
        _with_exact_trinity_access,
    )

    curated = json.loads(
        (ROOT / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    keys = [(100, "hacking-device"), (101, "hacking-device-plus")]
    before: dict[tuple[str, str], dict] = {}
    after: dict[tuple[str, str], dict] = {}
    for source_id, name in keys:
        key = ("n5-core-v5.3", f"equipment:{name}")
        variant = copy.deepcopy(next(
            r["variantSemantics"] for r in curated["records"] if r["id"] == key[1]
        ))
        previous = copy.deepcopy(variant)
        for entry in previous["occurrenceParameters"][0]["extraValues"]:
            if entry["effect"].get("grantsProgram") is True:
                entry["effect"].pop("grantsProgram")
        for pair in previous["occurrenceCombinations"]:
            for effect in pair["effects"]:
                effect.pop("grantsProgram", None)
        assert _with_exact_trinity_access(previous, source_id) == variant
        before[key], after[key] = previous, variant
    first = next(iter(after))
    if defect in {"missing-grant", "false-grant", "baseline-grant",
                  "wrong-program", "wrong-modifier", "wrong-combo"}:
        changed = after[first]
        entries = changed["occurrenceParameters"][0]["extraValues"]
        trinity = next(entry["effect"] for entry in entries if entry["extraId"] == 290)
        if defect == "missing-grant":
            del trinity["grantsProgram"]
        elif defect == "false-grant":
            trinity["grantsProgram"] = False
        elif defect == "baseline-grant":
            next(entry for entry in entries if entry["extraId"] == 269
                 )["effect"]["grantsProgram"] = True
        elif defect == "wrong-program":
            trinity["program"] = "hacking-program:carbonite"
        elif defect == "wrong-modifier":
            trinity["modifier"] = 2
        else:
            changed["occurrenceCombinations"][1]["effects"][1]["grantsProgram"] = False
    prior_db, next_db = tmp_path / "prior.db", tmp_path / "next.db"
    with sqlite3.connect(prior_db) as old, sqlite3.connect(next_db) as new:
        old.execute("CREATE TABLE records(collection_id TEXT,id TEXT,variant_json TEXT,facts TEXT)")
        old.executemany("INSERT INTO records VALUES (?,?,?,?)", [
            (*key, json.dumps(variant), "unchanged") for key, variant in before.items()
        ] + [("n5-core-v5.3", "equipment:other", None, "unchanged")])
        old.commit()
        old.backup(new)
        for key, value in after.items():
            new.execute(
                "UPDATE records SET variant_json=? WHERE collection_id=? AND id=?",
                (json.dumps(value), *key),
            )
        if defect == "other-record":
            new.execute("UPDATE records SET facts='changed' WHERE id='equipment:other'")
        elif defect == "schema":
            new.execute("CREATE INDEX unwanted ON records(id)")
        elif defect == "missing-device":
            new.execute("DELETE FROM records WHERE id='equipment:hacking-device-plus'")
    variants = {key: json.dumps(value) for key, value in after.items()}
    if defect is None:
        _check_variant_semantics_delta(
            prior_db, next_db, variants, hacking_trinity_access=True,
        )
    else:
        with pytest.raises(ValueError):
            _check_variant_semantics_delta(
                prior_db, next_db, variants, hacking_trinity_access=True,
            )
    with pytest.raises(ValueError):
        _check_variant_semantics_delta(prior_db, next_db, variants)


@pytest.mark.parametrize(
    "defect", (None, "count", "extra-id", "raw", "type", "compound",
               "status", "bare-sr", "name", "missing"),
)
def test_hacking_trinity_access_v9_source_gate_pins_signatures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str | None,
) -> None:
    from tools import audit_source_variant_inputs as audit
    from tools import restrictions_v9_release as release

    raw_names = {
        290: "UPGRADE: Trinity (+1B)", 378: "UPGRADE: Trinity (+1SD)",
        339: "UPGRADE: Trinity (SR-1)", 352: "UPGRADE: Trinity (SR-2)",
    }
    items = []
    for source_id, source in release.HACKING_GRANT_SOURCES.items():
        combination = (
            [[373, "TEXT", "UPGRADE: Total Control (PS=3)"],
             [343, "TEXT", "UPGRADE: Trinity (PS=5)"]]
            if source_id == 100 else
            [[343, "TEXT", "UPGRADE: Trinity (PS=5)"],
             [287, "TEXT", "UPGRADE: Zero Pain"]]
        )
        signatures = [
            {"extras": [[extra_id, "TEXT", raw_names[extra_id]]],
             "reviewed": True, "count": count}
            for extra_id, count in release.TRINITY_ACCESS_SIGNATURES[source_id]
        ] + [{"extras": combination, "reviewed": True, "count": 2}]
        if source_id == 101:
            signatures.append({
                "extras": [[344, "TEXT", "UPGRADE: SR-1"]],
                "reviewed": False, "count": 2,
            })
        items.append({
            "id": source_id, "name": source["name"],
            "applicationId": source_id, "occurrences": source["occurrences"],
            "status": ("reviewed-extra-parameter" if source_id == 100
                       else "unresolved-occurrence-parameter"),
            "reviewedVariant": None, "reviewedExtra": {"source": "army-extra"},
            "reviewedCombinations": [{"extras": combination}],
            "rawValues": [], "extraSignatures": signatures,
        })
    target = items[0]
    if defect == "count":
        target["extraSignatures"][0]["count"] += 1
    elif defect == "extra-id":
        target["extraSignatures"][0]["extras"][0][0] = 999
    elif defect == "raw":
        target["extraSignatures"][0]["extras"][0][2] = "UPGRADE: Trinity (+2B)"
    elif defect == "type":
        target["extraSignatures"][0]["extras"][0][1] = "DISTANCE"
    elif defect == "compound":
        target["extraSignatures"][-1]["extras"].reverse()
    elif defect == "status":
        target["status"] = "unresolved-occurrence-parameter"
    elif defect == "bare-sr":
        items[1]["extraSignatures"][-1]["reviewed"] = True
    elif defect == "name":
        target["name"] = "wrong device"
    elif defect == "missing":
        items.pop()
    monkeypatch.setattr(
        audit, "inventory_source_variants",
        lambda *_args: {"catalogs": {"equipment": {"items": items}}},
    )
    calls: list[dict] = []

    def promote(**kwargs: object) -> Path:
        calls.append(kwargs)
        return tmp_path / "recovery"

    monkeypatch.setattr(release, "_refresh_metadata_v9_release", promote)
    if defect is None:
        assert release.refresh_hacking_trinity_access_v9_release(root=tmp_path) == (
            tmp_path / "recovery"
        )
        assert calls == [{
            "root": tmp_path,
            "variant_records": {"equipment:hacking-device", "equipment:hacking-device-plus"},
            "hacking_trinity_access": True,
        }]
    else:
        with pytest.raises(ValueError, match="Trinity|Charontid"):
            release.refresh_hacking_trinity_access_v9_release(root=tmp_path)
        assert not calls


def source_data() -> tuple[dict, dict]:
    chart = json.loads(CHART.read_text(encoding="utf-8"))
    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    return chart, {row["id"]: row for row in curated["records"]}


@pytest.fixture(scope="module")
def legacy_v8_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Keep v8 rollback acceptance testable after the tracked v9 promotion."""
    assert DB.is_file()
    RulesDatabase(DB).validate()
    with sqlite3.connect(DB) as current:
        if current.execute("PRAGMA user_version").fetchone()[0] == RULES_SCHEMA_VERSION:
            return DB
    output = tmp_path_factory.mktemp("restrictions-legacy-v8") / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated"), output)
    RulesDatabase(output).validate()
    return output


@pytest.fixture
def candidate(
    tmp_path: Path, legacy_v8_db: Path,
) -> Iterator[tuple[sqlite3.Connection, dict, dict, Path]]:
    target = tmp_path / "candidate.db"
    with sqlite3.connect(
        f"file:{legacy_v8_db.as_posix()}?mode=ro", uri=True,
    ) as current:
        with sqlite3.connect(target) as staging:
            current.backup(staging)
    connection = sqlite3.connect(target)
    chart, records = source_data()
    try:
        yield connection, chart, records, target
    finally:
        connection.close()


def test_shared_staging_preserves_active_v9_restrictions(tmp_path: Path) -> None:
    from tools.stage_hacking_device_chart_citations import export_release_rules

    current = RulesDatabase(DB)
    current.validate()
    assert len(current.restrictions_payload()["items"]) == 14
    staged = tmp_path / "staged-rules.db"
    export_release_rules(load_curated_directory(ROOT / "data/curated/rules"), staged)
    copied = RulesDatabase(staged)
    copied.validate()
    assert copied.restrictions_payload() == current.restrictions_payload()
    with sqlite3.connect(staged) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 9


def test_shared_promotion_refuses_v9_to_v8_downgrade(
    tmp_path: Path, legacy_v8_db: Path,
) -> None:
    from tools.stage_hacking_device_chart_citations import STAGED_PATHS, _replace_staged_batch

    root = tmp_path / "workspace"
    (root / "local").mkdir(parents=True)
    originals = {path: (ROOT / path).read_bytes() for path in STAGED_PATHS}
    for path, data in originals.items():
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    proposed = dict(originals)
    proposed[STAGED_PATHS[1]] = legacy_v8_db.read_bytes()
    with pytest.raises(ValueError, match="schema differs"):
        _replace_staged_batch(root, proposed, lambda: None)
    assert all((root / path).read_bytes() == original for path, original in originals.items())


def test_disposable_v8_rollback_pair_preserves_v9_reviewed_objects(
    legacy_v8_db: Path, tmp_path: Path,
) -> None:
    """Rollback image must differ only in the rules DB and its pinned SHA-256."""
    import hashlib

    from infinity_db.deployed_object_publication import load_deployed_object_publication
    from tools.build_deployed_object_publication import build_publication, publication_bytes

    army = ROOT / "data/generated/infinity.db"
    arguments = (
        ROOT / "data/curated/rules/n5-core-v5.3.json",
        ROOT / "config/validation/deployed-object-delivery-reviews.json",
        ROOT / "config/validation/deployed-object-candidate-reviews.json",
    )
    current = RulesDatabase(DB)
    rollback = RulesDatabase(legacy_v8_db)
    current.validate()
    rollback.validate()
    assert len(current.restrictions_payload()["items"]) == 14
    assert rollback.restrictions_payload() == {
        "formatVersion": 1,
        "available": False,
        "source": None,
        "polarity": "prohibition",
        "items": [],
        "evaluationSupported": False,
    }
    current_publication = build_publication(army, DB, *arguments)
    v8_publication = build_publication(army, legacy_v8_db, *arguments)
    expected = copy.deepcopy(v8_publication)
    expected["sourceSnapshot"]["rulesDatabaseSha256"] = (
        current_publication["sourceSnapshot"]["rulesDatabaseSha256"]
    )
    assert expected == current_publication
    assert v8_publication["sourceSnapshot"]["rulesDatabaseSha256"] == (
        hashlib.sha256(legacy_v8_db.read_bytes()).hexdigest()
    )

    staged_publication = tmp_path / "deployed-objects.json"
    staged_publication.write_bytes(publication_bytes(v8_publication))
    assert load_deployed_object_publication(
        staged_publication, army, legacy_v8_db,
    ) == v8_publication
    with sqlite3.connect(legacy_v8_db) as old, sqlite3.connect(DB) as new:
        assert old.execute("PRAGMA user_version").fetchone()[0] == 8
        assert new.execute("PRAGMA user_version").fetchone()[0] == 9
        assert legacy_relation_snapshot(old) == legacy_relation_snapshot(new)


def legacy_relation_snapshot(connection: sqlite3.Connection) -> list[tuple]:
    return connection.execute(
        "SELECT collection_id, record_id, position, relation_type, related_record_id "
        "FROM record_relations ORDER BY collection_id, record_id, position"
    ).fetchall()


def test_candidate_additive_table_preserves_legacy_db_and_composed_api(
    candidate: tuple[sqlite3.Connection, dict, dict, Path],
) -> None:
    connection, chart, records, target = candidate
    before_relations = legacy_relation_snapshot(connection)
    previous = RulesDatabase(target)
    before_motorcycle = previous.composed_record("equipment:motorcycle")
    before_lieutenant = previous.composed_record("skill:lieutenant")
    assert before_motorcycle and before_lieutenant
    assert connection.execute("PRAGMA user_version").fetchone()[0] == RULES_SCHEMA_VERSION
    assert stage_candidate_restrictions(connection, chart, records) == 14
    connection.commit()
    assert connection.execute("PRAGMA user_version").fetchone()[0] == RULES_SCHEMA_VERSION
    compatibility = connection.execute(
        "SELECT value FROM __rules_metadata WHERE key = 'databaseCompatibilityVersion'"
    ).fetchone()[0]
    assert json.loads(compatibility) == RULES_COMPATIBILITY_VERSION
    assert legacy_relation_snapshot(connection) == before_relations
    previous.validate()
    assert previous.composed_record("equipment:motorcycle") == before_motorcycle
    assert previous.composed_record("skill:lieutenant") == before_lieutenant
    assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    compiled = compile_restriction_conditions(chart, records)
    result = candidate_restrictions_payload(connection)
    assert result["formatVersion"] == 1
    assert result["source"] == {
        "id": chart["sourceId"],
        "page": chart["sourcePage"],
        "pdfSha256": chart["sourcePdfSha256"],
    }
    assert result["polarity"] == "prohibition"
    assert result["evaluationSupported"] is False
    assert len(result["items"]) == 14
    assert [row["subject"] for row in result["items"]] == [
        item.subject for item in compiled
    ]
    assert [
        (row["subjectKind"], row["ownerRecordId"], row["action"], row["operation"],
         row["targetRecordId"], row["scope"])
        for row in result["items"]
    ] == [
        (item.subject_kind, item.owner_record_id, item.action,
         item.publication_operation(), item.target_record_id, item.scope)
        for item in compiled
    ]


def test_candidate_api_filters_preserve_negative_only_and_provenance(
    candidate: tuple[sqlite3.Connection, dict, dict, Path],
) -> None:
    connection, chart, records, _ = candidate
    stage_candidate_restrictions(connection, chart, records)
    motorcycle = candidate_restrictions_payload(connection, subject="Motorcycle")
    assert len(motorcycle["items"]) == 5
    jump = next(row for row in motorcycle["items"] if row["action"] == "upward-jump")
    assert jump["scope"] == "while-mounted-upwards-only"
    assert jump["operation"] == {
        "kind": "directional-skill-movement",
        "qualifier": {"direction": "upward"},
    }
    assert jump["ownerRecordId"] == "equipment:motorcycle"
    assert jump["targetRecordId"] == "skill:jump"

    ladders = next(row for row in motorcycle["items"] if row["action"] == "use-ladders")
    assert ladders["operation"] == {
        "kind": "terrain-traversal", "qualifier": {"terrain": "ladders"},
    }
    assert ladders["targetRecordId"] is None

    lieutenant = candidate_restrictions_payload(connection, record_id="skill:lieutenant")
    assert len(lieutenant["items"]) == 2
    assert {row["subject"] for row in lieutenant["items"]} == {"REM", "Irregular"}
    assert all(
        row["scope"] == "army-selection-only"
        and row["operation"] == {
            "kind": "army-role-selection", "qualifier": {"role": "lieutenant"},
        }
        for row in lieutenant["items"]
    )
    source_only = candidate_restrictions_payload(connection, subject="TAG")
    assert len(source_only["items"]) == 2
    assert all(row["ownerRecordId"] is None for row in source_only["items"])
    empty = candidate_restrictions_payload(connection, record_id="skill:dodge")
    assert empty["items"] == []
    assert empty["evaluationSupported"] is False
    assert empty["source"] == lieutenant["source"]
    assert len(candidate_restrictions_payload(
        connection, subject="Motorcycle", record_id="skill:jump"
    )["items"]) == 1

    for kwargs in ({"subject": "HI"}, {"record_id": "skill:jump' OR TRUE --"}):
        with pytest.raises(ValueError):
            candidate_restrictions_payload(connection, **kwargs)


def test_candidate_fails_closed_without_mutating_legacy_rows(
    candidate: tuple[sqlite3.Connection, dict, dict, Path],
) -> None:
    connection, chart, records, _ = candidate
    baseline = legacy_relation_snapshot(connection)
    bad = copy.deepcopy(chart)
    bad["rows"][1]["restrictions"][4]["scope"] = "all"
    with pytest.raises(ValueError, match="scope drift"):
        stage_candidate_restrictions(connection, bad, records)
    assert connection.execute(
        "SELECT name FROM sqlite_master WHERE name = 'restriction_constraints'"
    ).fetchone() is None
    assert legacy_relation_snapshot(connection) == baseline

    bad = copy.deepcopy(chart)
    bad["sourcePdfSha256"] = "invalid"
    with pytest.raises(ValueError, match="fingerprint"):
        stage_candidate_restrictions(connection, bad, records)
    assert legacy_relation_snapshot(connection) == baseline

    connection.execute(
        "UPDATE __rules_metadata SET value = '12' "
        "WHERE key = 'databaseCompatibilityVersion'"
    )
    with pytest.raises(ValueError, match="compatibility revision 10"):
        stage_candidate_restrictions(connection, chart, records)
    connection.execute(
        "UPDATE __rules_metadata SET value = '10' "
        "WHERE key = 'databaseCompatibilityVersion'"
    )

    stage_candidate_restrictions(connection, chart, records)
    with pytest.raises(ValueError, match="already staged"):
        stage_candidate_restrictions(connection, chart, records)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        connection.execute(
            "UPDATE restriction_constraints SET polarity = 'permission' "
            "WHERE subject = 'TAG'"
        )
    assert legacy_relation_snapshot(connection) == baseline
    assert connection.execute(
        "SELECT COUNT(*) FROM restriction_constraints WHERE polarity = 'prohibition'"
    ).fetchone()[0] == 14


def test_candidate_version_rollout_requires_application_transition(
    candidate: tuple[sqlite3.Connection, dict, dict, Path], legacy_v8_db: Path,
) -> None:
    connection, chart, records, target = candidate
    stage_candidate_restrictions(connection, chart, records)
    connection.execute(f"PRAGMA user_version = {CANDIDATE_SCHEMA_VERSION}")
    connection.execute(
        "UPDATE __rules_metadata SET value = ? "
        "WHERE key = 'databaseCompatibilityVersion'",
        (json.dumps(CANDIDATE_COMPATIBILITY_VERSION),),
    )
    connection.execute(
        "UPDATE __rules_metadata SET value = ? WHERE key = 'formatVersion'",
        (json.dumps(CANDIDATE_SCHEMA_VERSION),),
    )
    connection.commit()
    assert len(candidate_restrictions_payload(connection)["items"]) == 14
    assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    RulesDatabase(target).validate()
    assert RulesDatabase(target).restrictions_payload()["available"] is True
    assert RulesDatabase(legacy_v8_db).restrictions_payload()["available"] is False

    connection.execute(
        "UPDATE __rules_metadata SET value = '10' "
        "WHERE key = 'databaseCompatibilityVersion'"
    )
    connection.commit()
    with pytest.raises(ValueError, match="compatibility revision"):
        RulesDatabase(target).validate()
    connection.execute(
        "UPDATE __rules_metadata SET value = '11' "
        "WHERE key = 'databaseCompatibilityVersion'"
    )
    connection.execute("PRAGMA user_version = 10")
    connection.commit()
    with pytest.raises(ValueError, match="Unsupported rules database schema"):
        RulesDatabase(target).validate()


def test_explicit_v9_export_is_deterministic_and_legacy_relations_unchanged(
    tmp_path: Path, legacy_v8_db: Path,
) -> None:
    documents = load_curated_directory(ROOT / "data/curated")
    chart, _ = source_data()
    first = tmp_path / "v9-first.db"
    second = tmp_path / "v9-second.db"
    export_rules_database(documents, first, restrictions_manifest=chart)
    export_rules_database(documents, second, restrictions_manifest=chart)
    assert first.read_bytes() == second.read_bytes()
    v9 = RulesDatabase(first)
    v9.validate()
    assert len(v9.restrictions_payload()["items"]) == 14
    assert v9.restrictions_payload(record_id="skill:lieutenant")["available"]
    assert len(v9.restrictions_payload(record_id="skill:lieutenant")["items"]) == 2
    with sqlite3.connect(legacy_v8_db) as original, sqlite3.connect(first) as generated:
        assert legacy_relation_snapshot(original) == legacy_relation_snapshot(generated)
        assert generated.execute("PRAGMA user_version").fetchone()[0] == 9
        assert generated.execute("PRAGMA foreign_key_check").fetchall() == []
    assert RulesDatabase(legacy_v8_db).restrictions_payload() == {
        "formatVersion": 1, "available": False, "source": None,
        "polarity": "prohibition", "items": [], "evaluationSupported": False,
    }


def test_restrictions_http_v8_and_v9_are_additive(
    candidate: tuple[sqlite3.Connection, dict, dict, Path], legacy_v8_db: Path,
) -> None:
    from urllib.parse import urlsplit
    from wsgiref.util import setup_testing_defaults

    from infinity_db.web import create_app

    connection, chart, records, target = candidate

    def get(app, path: str) -> tuple[int, dict]:
        parsed = urlsplit(path)
        environ: dict = {}
        setup_testing_defaults(environ)
        environ["PATH_INFO"] = parsed.path
        environ["QUERY_STRING"] = parsed.query
        result: dict = {}

        def respond(status: str, headers: list[tuple[str, str]], exc_info=None) -> None:
            result["status"] = int(status.split()[0])

        response = app(environ, respond)
        try:
            body = b"".join(response)
        finally:
            if close := getattr(response, "close", None):
                close()
        return result["status"], json.loads(body)

    v8 = create_app(ROOT / "data/generated/infinity.db", rules_database_path=legacy_v8_db)
    status, payload = get(v8, "/api/restrictions")
    assert status == 200
    assert payload["available"] is False
    assert payload["items"] == []
    assert payload["evaluationSupported"] is False
    assert get(v8, "/api/restrictions?subject=TAG")[1]["available"] is False
    assert get(v8, "/api/restrictions?subject=UNKNOWN")[0] == 400

    stage_candidate_restrictions(connection, chart, records)
    connection.execute("PRAGMA user_version = 9")
    connection.execute(
        "UPDATE __rules_metadata SET value = '9' WHERE key = 'formatVersion'"
    )
    connection.execute(
        "UPDATE __rules_metadata SET value = '11' "
        "WHERE key = 'databaseCompatibilityVersion'"
    )
    connection.commit()
    v9 = create_app(ROOT / "data/generated/infinity.db", rules_database_path=target)
    status, payload = get(v9, "/api/restrictions")
    assert status == 200
    assert payload["available"] is True
    assert payload["polarity"] == "prohibition"
    assert len(payload["items"]) == 14
    assert get(v9, "/api/restrictions?subject=Motorcycle")[1]["items"][4][
        "operation"
    ] == {"kind": "directional-skill-movement", "qualifier": {"direction": "upward"}}
    assert len(get(v9, "/api/restrictions?record_id=skill:lieutenant")[1]["items"]) == 2
    assert get(v9, "/api/restrictions?record_id=skill:dodge")[1]["items"] == []
    assert get(v9, "/api/restrictions?subject=REM&record_id=skill:lieutenant")[
        1
    ]["items"][0]["action"] == "lieutenant-selection"
    for query in (
        "?subject=UNKNOWN", "?record_id=not-an-id",
        "?subject=TAG&subject=REM", "?extra=true",
    ):
        assert get(v9, "/api/restrictions" + query)[0] == 400
    # No changes to existing API schemas or record relation semantics.
    for path in ("/api/skills/lieutenant", "/api/equipment/motorcycle"):
        assert get(v8, path) == get(v9, path)


def test_v9_validator_rejects_missing_table_and_broadened_constraint(
    candidate: tuple[sqlite3.Connection, dict, dict, Path],
) -> None:
    connection, chart, records, target = candidate
    connection.execute("PRAGMA user_version = 9")
    connection.execute(
        "UPDATE __rules_metadata SET value = '9' WHERE key = 'formatVersion'"
    )
    connection.execute(
        "UPDATE __rules_metadata SET value = '11' "
        "WHERE key = 'databaseCompatibilityVersion'"
    )
    connection.commit()
    with pytest.raises(ValueError, match="missing or damaged table"):
        RulesDatabase(target).validate()

    # Stage on a valid base version; only then mark the snapshot as v9.
    connection.execute("PRAGMA user_version = 8")
    connection.execute(
        "UPDATE __rules_metadata SET value = '8' WHERE key = 'formatVersion'"
    )
    connection.execute(
        "UPDATE __rules_metadata SET value = '10' "
        "WHERE key = 'databaseCompatibilityVersion'"
    )
    stage_candidate_restrictions(connection, chart, records)
    connection.execute("PRAGMA user_version = 9")
    connection.execute(
        "UPDATE __rules_metadata SET value = '9' WHERE key = 'formatVersion'"
    )
    connection.execute(
        "UPDATE __rules_metadata SET value = '11' "
        "WHERE key = 'databaseCompatibilityVersion'"
    )
    connection.commit()
    RulesDatabase(target).validate()
    connection.execute(
        "UPDATE restriction_constraints SET scope = 'while-mounted' "
        "WHERE subject = 'Motorcycle' AND action = 'upward-jump'"
    )
    connection.commit()
    with pytest.raises(ValueError, match="source condition drift"):
        RulesDatabase(target).validate()


def test_default_build_rules_writes_standalone_v10_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from infinity_db import cli

    output = tmp_path / "rules-standalone.db"
    monkeypatch.setattr(cli, "DEFAULT_STANDALONE_RULES_DATABASE", output)
    args = cli.build_parser().parse_args([
        "build-rules", str(ROOT / "data/curated/rules"),
    ])
    assert args.output is None
    assert cli.cmd_build_rules(args) == 0
    with sqlite3.connect(output) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 10
    RulesDatabase(output).validate()
    assert len(RulesDatabase(output).restrictions_payload()["items"]) == 14
    deployed = RulesDatabase(output).deployed_objects_payload(
        ROOT / "data/generated/infinity.db"
    )
    assert deployed is not None
    assert len(deployed["objects"]) == 17


def test_v9_cli_rejects_tracked_release_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from infinity_db import cli

    path = tmp_path / "rules.db"
    monkeypatch.setattr(cli, "DEFAULT_RULES_DATABASE", path)
    args = cli.build_parser().parse_args(["build-rules", "--output", str(path)])
    with pytest.raises(ValueError, match="cannot write the tracked release"):
        cli.cmd_build_rules(args)
    assert not path.exists()


def test_v8_manifest_conflict_fails_closed() -> None:
    from infinity_db.cli import build_parser, cmd_build_rules

    args = build_parser().parse_args([
        "build-rules", "--legacy-v8", "--restrictions-manifest",
        "config/validation/restrictions-source-chart.json",
    ])
    with pytest.raises(ValueError, match="cannot be combined"):
        cmd_build_rules(args)


def test_explicit_v8_build_rules_cannot_replace_tracked_v9_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from infinity_db import cli

    output = tmp_path / "rules.db"
    documents = load_curated_directory(ROOT / "data/curated")
    chart = json.loads(CHART.read_text(encoding="utf-8"))
    export_rules_database(documents, output, restrictions_manifest=chart)
    RulesDatabase(output).validate()
    assert len(RulesDatabase(output).restrictions_payload()["items"]) == 14
    original = output.read_bytes()

    monkeypatch.setattr(cli, "DEFAULT_RULES_DATABASE", output)
    args = cli.build_parser().parse_args([
        "build-rules", str(ROOT / "data/curated/rules"),
        "--legacy-v8", "--output", str(output),
    ])
    assert args.output.resolve() == output.resolve()
    with pytest.raises(ValueError, match="cannot write the tracked release"):
        cli.cmd_build_rules(args)

    assert output.read_bytes() == original


def test_legacy_v8_opt_in_can_rebuild_existing_v8_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from infinity_db import cli

    output = tmp_path / "rules.db"
    documents = load_curated_directory(ROOT / "data/curated/rules")
    export_rules_database(documents, output)

    args = cli.build_parser().parse_args([
        "build-rules", str(ROOT / "data/curated/rules"),
        "--legacy-v8", "--output", str(output),
    ])
    assert args.output.resolve() == output.resolve()
    assert cli.cmd_build_rules(args) == 0

    database = RulesDatabase(output)
    database.validate()
    assert database.restrictions_payload()["available"] is False


def test_v8_reader_preserves_preexisting_metadata_contract(
    candidate: tuple[sqlite3.Connection, dict, dict, Path],
) -> None:
    connection, _, _, target = candidate
    # Older v8 validation checked compatibility, not the formatVersion key.
    connection.execute(
        "DELETE FROM __rules_metadata WHERE key = 'formatVersion'"
    )
    connection.commit()
    RulesDatabase(target).validate()
    assert RulesDatabase(target).restrictions_payload()["available"] is False


def test_explicit_build_rules_cli_exports_v9_to_separate_path(tmp_path: Path) -> None:
    from infinity_db.cli import build_parser, cmd_build_rules

    output = tmp_path / "restrictions-v9.db"
    args = build_parser().parse_args([
        "build-rules", "--legacy-v9", "--restrictions-manifest",
        "config/validation/restrictions-source-chart.json",
        "--output", str(output),
    ])
    assert cmd_build_rules(args) == 0
    RulesDatabase(output).validate()
    assert len(RulesDatabase(output).restrictions_payload()["items"]) == 14


@pytest.mark.parametrize("inject_failure", [False, True])
def test_restrictions_paired_replacement_retains_v8_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, inject_failure: bool,
) -> None:
    from tools import restrictions_v9_release as release

    (tmp_path / "local").mkdir()
    original = {}
    replacement = {}
    for index, relative in enumerate(release.ARTIFACTS):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        original[relative] = f"v8-original-{index}".encode()
        replacement[relative] = f"v9-staged-{index}".encode()
        path.write_bytes(original[relative])

    if inject_failure:
        write = release._atomic_write
        calls = 0

        def failure_on_second(path: Path, raw: bytes) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected second-artifact write failure")
            write(path, raw)

        monkeypatch.setattr(release, "_atomic_write", failure_on_second)
        with pytest.raises(RuntimeError, match="rolled back"):
            release._replace_with_rollback(tmp_path, replacement, lambda: None)
    else:
        recovery = release._replace_with_rollback(
            tmp_path, replacement, lambda: None,
        )
        assert recovery.is_dir()

    expected = original if inject_failure else replacement
    assert all((tmp_path / relative).read_bytes() == data
               for relative, data in expected.items())
    backups = list((tmp_path / "local").glob("restrictions-v8-recovery-*"))
    assert len(backups) == 1
    for relative, old in original.items():
        assert (backups[0] / relative).read_bytes() == old


def test_restrictions_promotion_rejects_unreviewed_publication_changes() -> None:
    from tools.restrictions_v9_release import _expected_publication_delta

    previous = {
        "sourceSnapshot": {"rulesDatabaseSha256": "a" * 64, "armyDatabaseSha256": "b" * 64},
        "objects": [{"id": "example"}],
        "unresolvedDeliveries": [],
    }
    reviewed = copy.deepcopy(previous)
    reviewed["sourceSnapshot"]["rulesDatabaseSha256"] = "c" * 64
    _expected_publication_delta(previous, reviewed, "c" * 64)
    reviewed["objects"][0]["id"] = "unsupported-change"
    with pytest.raises(ValueError, match="unexpectedly changed"):
        _expected_publication_delta(previous, reviewed, "c" * 64)
