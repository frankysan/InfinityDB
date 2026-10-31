"""Full reviewed Ammunition identity and cross-domain publication parity.

Source metadata IDs, Army profile labels, canonical rules, and published Weapon
profiles must agree. Composition is an ordered source fact, never an arithmetic
Saving Roll, Critical, immunity or weapon-name parsing rule.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.catalog_rules import CatalogRules
from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_ammunition_references import load_ammunition_reference_map
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
ARMY = ROOT / "data/generated/infinity.db"
RULES = ROOT / "data/generated/rules.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PDF_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
COMBINED = {
    5: ("N+E/M", ("ammunition:normal", "ammunition:em")),
    10: ("AP+DA", ("ammunition:ap", "ammunition:da")),
    13: ("AP+Exp", ("ammunition:ap", "ammunition:exp")),
    30: ("AP+Shock", ("ammunition:ap", "ammunition:shock")),
    40: ("AP+T2", ("ammunition:ap", "ammunition:t2")),
}
BASE = frozenset({
    "normal", "ap", "da", "eclipse", "em", "exp", "para",
    "shock", "smoke", "stun", "t2",
})


def test_pinned_combination_source_evidence_is_independent_of_army_map() -> None:
    """Page 67 describes three combined examples; two are Army metadata only."""
    fitz = pytest.importorskip("fitz")
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == PDF_SHA256
    with fitz.open(PDF) as document:
        page = " ".join(document[66].get_text("text").split()).casefold()
        assert "combined ammunition works as a single ammunition" in page
        assert "additional saving roll" in page
        for phrase in ("ap+da", "ap+exp", "n+e/m"):
            assert phrase in page
        assert "combined saving roll" in page
        assert "plasma carbine" in page

    reviewed = load_ammunition_reference_map()
    assert len(reviewed) == len(BASE) + len(COMBINED)
    assert {
        entry["segments"][0]["ruleId"].split(":", 1)[1]
        for entry in reviewed.values() if "components" not in entry
    } == BASE
    assert {
        source_id: (item["name"], tuple(item["components"]))
        for source_id, item in reviewed.items() if "components" in item
    } == COMBINED


def test_all_reviewed_ammunition_sources_reach_canonical_and_weapon_publication() -> None:
    """Walk actual metadata-backed Weapon references; never synthesize profiles."""
    mapping = load_ammunition_reference_map()
    rules = RulesDatabase(RULES)
    database = Database(ARMY)
    catalog = CatalogRules(rules)
    with sqlite3.connect(ARMY) as connection:
        sources = dict(connection.execute("SELECT id, name FROM metadata_ammunitions"))
        weapons = connection.execute(
            "SELECT id, ammunition, name, saving, savingNum, mode "
            "FROM metadata_weapons WHERE ammunition IS NOT NULL "
            "AND (type IS NULL OR type != 'EQUIPMENT') ORDER BY id, position"
        ).fetchall()
    assert {source_id: sources[source_id] for source_id in mapping} == {
        source_id: entry["name"] for source_id, entry in mapping.items()
    }
    reviewed_identities = {
        item["segments"][i]["ruleId"] for item in mapping.values()
        for i in range(len(item["segments"]))
        if "ruleId" in item["segments"][i]
    }
    assert reviewed_identities == {f"ammunition:{slug}" for slug in BASE}
    for rule_id in reviewed_identities:
        record = rules.composed_record(rule_id)
        assert record is not None and record["kind"] == "ammunition"
        assert record["citations"] and record["collection"]["id"] == "n5-core-v5.3"
        assert record["facts"]

    # One real source profile per reviewed source metadata identity; extra
    # occurrences and modes must retain their exact imported saving fields.
    visited: set[int] = set()
    for weapon_id, ammunition_id, _, _, _, _ in weapons:
        if ammunition_id not in mapping or ammunition_id in visited:
            continue
        raw = database.get_catalog_item("weapons", weapon_id)
        if raw is None:
            continue
        original_profiles = raw.get("profiles", []) + [
            profile for variant in raw.get("weapon_variants", [])
            for profile in variant.get("profiles", [])
        ]
        matched = [
            profile for profile in original_profiles
            if profile.get("ammunition_source_id") == ammunition_id
            and profile.get("ammunition") == mapping[ammunition_id]["name"]
        ]
        if not matched:
            continue
        enriched = catalog.enrich_catalog_item("weapons", raw)
        enriched_profiles = enriched.get("profiles", []) + [
            profile for variant in enriched.get("weapon_variants", [])
            for profile in variant.get("profiles", [])
        ]
        for source_profile in matched:
            published = [
                profile for profile in enriched_profiles
                if (profile.get("id"), profile.get("mode"),
                    profile.get("ammunition_source_id")) ==
                (source_profile.get("id"), source_profile.get("mode"), ammunition_id)
            ]
            assert published
            for occurrence in published:
                assert (occurrence["saving"], occurrence["saving_num"]) == (
                    source_profile["saving"], source_profile["saving_num"]
                )
            actual = published[0]
            parts = [
                segment["public_reference"]
                for segment in actual["ammunition_parts"]
                if segment.get("public_reference")
            ]
            expected_ids = mapping[ammunition_id].get("components") or [
                mapping[ammunition_id]["segments"][0]["ruleId"]
            ]
            assert parts == [
                {"catalog": "ammunition", "id": identity.split(":", 1)[1]}
                for identity in expected_ids
            ]
            effects = actual["ammunition_effects"]
            assert [effect["record_id"] for effect in effects] == expected_ids
            for identity, effect in zip(expected_ids, effects, strict=True):
                record = rules.composed_record(identity)
                assert record is not None
                assert effect["summary"] == record["summary"]
                assert effect["citations"] == record["citations"]
                assert "ammunitionResolution" not in effect
            composition = actual.get("ammunition_composition")
            if ammunition_id in COMBINED:
                assert composition is not None
                assert composition["kind"] == "combined"
                assert [item["record_id"] for item in composition["components"]] == expected_ids
                assert not (set(composition) & {
                    "rollsPerHit", "criticalAdditionalSavingRolls",
                    "defenseModifier", "savingRoll", "woundsPerFailedSave",
                })
            else:
                assert composition is None
        visited.add(ammunition_id)
    assert visited == set(mapping), {
        "missingWeaponProfileSourceIds": sorted(set(mapping) - visited)
    }


@pytest.mark.parametrize("source_id", sorted(COMBINED))
def test_combined_sources_publish_detail_without_reinterpreting_saving_roll(
    source_id: int,
) -> None:
    """HTTP Weapon details must use canonical mapping and leave roll notation raw."""
    with sqlite3.connect(ARMY) as connection:
        weapon_ids = [
            row[0] for row in connection.execute(
                "SELECT DISTINCT id FROM metadata_weapons "
                "WHERE ammunition = ? AND (type IS NULL OR type != 'EQUIPMENT') "
                "ORDER BY id", (source_id,),
            )
        ]
    database = Database(ARMY)
    app = create_app(ARMY, rules_database_path=RULES)
    for weapon_id in weapon_ids:
        slug = database.application_slug("weapons", weapon_id)
        if not slug:
            continue
        environ: dict[str, object] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=f"/api/weapons/{slug}", REQUEST_METHOD="GET")
        statuses: list[str] = []
        def respond(
            status: str, _headers: list, _exc: object = None,
            sink: list[str] = statuses,
        ) -> None:
            sink.append(status)

        data = b"".join(app(environ, respond))
        assert statuses == ["200 OK"]
        payload = json.loads(data)
        for profile in payload.get("profiles", []) + [
            p for v in payload.get("weapon_variants", []) for p in v.get("profiles", [])
        ]:
            if profile.get("ammunition_source_id") != source_id:
                continue
            assert profile["ammunition"] == COMBINED[source_id][0]
            assert [part["record_id"] for part in
                    profile["ammunition_composition"]["components"]] == list(
                COMBINED[source_id][1]
            )
            assert profile["saving"] is not None
            assert profile["saving_num"] is not None
            assert "rollsPerHit" not in profile["ammunition_composition"]
            return
    pytest.fail(f"No public Weapon profile for combined Ammunition source {source_id}")
