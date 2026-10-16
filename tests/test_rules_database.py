import copy
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import pytest

import infinity_db.rules_database as rules_database_module
from infinity_db.curated import load_curated_directory
from infinity_db.database import Database
from infinity_db.rules_database import (
    RULES_APPLICATION_ID,
    RULES_SCHEMA_VERSION,
    RulesDatabase,
)
from infinity_db.rules_database import (
    export_rules_database as export_release_rules_database,
)
from infinity_db.skill_catalog import SkillCatalog

FINALIZE_TEST_DATABASES = os.environ.get("INFINITYDB_TEST_FINALIZE_SQLITE") == "1"


def export_rules_database(*args, **kwargs) -> None:
    """Build semantic test fixtures without canonical SQLite finalization by default."""
    kwargs.setdefault("finalize", FINALIZE_TEST_DATABASES)
    export_release_rules_database(*args, **kwargs)


def test_rules_export_creates_schema_inside_transaction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    schema_transactions: list[bool] = []
    original_connect = sqlite3.connect

    def traced_connect(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        connection = original_connect(*args, **kwargs)

        def trace(statement: str) -> None:
            if statement.lstrip().upper().startswith("CREATE "):
                schema_transactions.append(connection.in_transaction)

        connection.set_trace_callback(trace)
        return connection

    monkeypatch.setattr(sqlite3, "connect", traced_connect)
    root = Path(__file__).parents[1]
    path = tmp_path / "rules.db"
    export_release_rules_database(load_curated_directory(root / "data/curated"), path)

    assert schema_transactions
    assert all(schema_transactions)
    RulesDatabase(path).validate()


@pytest.fixture(scope="module")
def current_rules_database(tmp_path_factory: pytest.TempPathFactory) -> RulesDatabase:
    """Build the unchanged current rules corpus once for read-only query tests."""
    root = Path(__file__).parents[1]
    output = tmp_path_factory.mktemp("rules-database-current") / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    database = RulesDatabase(output)
    database.validate()
    return database


def _current_core_with_hacking_programs(
    root: Path,
) -> tuple[Path, dict, tuple[Path, dict]]:
    documents = load_curated_directory(root / "data" / "curated")
    current_path, current = next(
        item for item in documents if item[1]["collection"]["id"] == "n5-core-v5.3"
    )
    hacking_programs = next(
        item
        for item in documents
        if item[1]["collection"]["id"] == "n5-hacking-programs-v5.3"
    )
    return current_path, current, hacking_programs


@pytest.mark.parametrize(
    ("record_id", "expected"),
    [
        *[(f"skill:martial-arts-l{level}", f"Level {level}") for level in range(1, 6)],
        *[(f"skill:strategos-l{level}", f"Level {level}") for level in range(1, 3)],
        ("skill:bs-attack", "some variants"),
        ("skill:cc-attack", "some variants"),
        ("skill:bs-12", "with 12"),
        ("skill:bs-11", "with 11"),
        ("skill:cc-21", "with 21"),
        ("equipment:tinbot", "listed"),
        *[
            (f"equipment:tinbot-{variant}", "Unit Profile")
            for variant in (
                "firewall", "neurocinetics", "albedo", "discover", "ecm-guided", "repeater"
            )
        ],
    ],
)
def test_published_variant_descriptions_use_game_language(
    current_rules_database: RulesDatabase, record_id: str, expected: str,
) -> None:
    record = current_rules_database.composed_record(record_id)
    assert record is not None
    assert expected in record["summary"]
    assert record["citations"]
    for internal_copy in ("source variant", "source identity", "occurrence", "modifier values"):
        assert internal_copy not in record["summary"]
    if "-l" in record_id:
        assert "discrete rather than cumulative" in record["summary"]


def test_shared_hacking_area_firewall_and_supportware_mechanics_are_composed(
    current_rules_database: RulesDatabase,
) -> None:
    hacking_area = current_rules_database.composed_record("rule:hacking-area")
    firewall = current_rules_database.composed_record("equipment:firewall")
    supportware = current_rules_database.composed_record("rule:supportware")
    assert hacking_area is not None
    assert firewall is not None
    assert supportware is not None

    assert "[[distance:8:inch]]" in " ".join(
        hacking_area["facts"]["clarifications"]
    )
    assert "non-[[skill:hacker]]" in hacking_area["summary"]
    assert "only one [[equipment:firewall]]" in firewall["summary"]
    assert "+3 to Saving Rolls" in " ".join(firewall["facts"]["effects"])
    assert "[[state:isolated|Isolated]]" in " ".join(
        firewall["facts"]["restrictions"]
    )
    assert "entirely canceled" in " ".join(
        supportware["facts"]["clarifications"]
    )
    assert {citation["source_id"] for citation in hacking_area["citations"]} >= {
        "wiki-hacking-area-oldid-3974", "n5-core-v5.3-pdf"
    }
    assert {citation["source_id"] for citation in firewall["citations"]} >= {
        "wiki-firewall-oldid-4097", "n5-faq-v0.1-en-pdf"
    }

    fairy_dust = current_rules_database.composed_record("hacking-program:fairy-dust")
    assert fairy_dust is not None
    assert "entire chosen Troop Type" in " ".join(
        fairy_dust["facts"]["restrictions"]
    )

    hacking_restrictions = " ".join(hacking_area["facts"]["restrictions"])
    hacking_clarifications = " ".join(hacking_area["facts"]["clarifications"])
    assert "fails its Requirements" in hacking_restrictions
    assert "[[skill:idle]]" in hacking_restrictions
    assert "along the Active Trooper's path" in hacking_clarifications
    assert "from that Trooper's [[equipment:repeater:plural]]" in (
        hacking_clarifications
    )
    assert "must still satisfy" in hacking_clarifications

    firewall_effects = " ".join(firewall["facts"]["effects"])
    firewall_restrictions = " ".join(firewall["facts"]["restrictions"])
    assert "-3 or -6" in firewall_effects
    assert "regardless of whether" in firewall_effects
    assert "MODs do not stack" in firewall_effects
    assert "Device is disabled" in firewall_restrictions
    assert "[[term:null-state|Null State]]" in firewall_restrictions

    supportware_effects = " ".join(supportware["facts"]["effects"])
    supportware_restrictions = " ".join(supportware["facts"]["restrictions"])
    supportware_examples = " ".join(supportware["facts"]["clarifications"])
    assert "only one Supportware Program" in supportware_effects
    assert "only one active Supportware Program" in supportware_effects
    assert "earlier Program protected a whole Troop Type" in (
        supportware_restrictions
    )
    assert "[[state:isolated|Isolated]]" in supportware_restrictions
    assert "[[term:null-state|Null State]]" in supportware_restrictions
    assert "other REMs lose" in supportware_examples
    assert "[[hacking-program:enhanced-reaction]]" in supportware_examples


def test_special_dice_reference_and_source_exceptions_are_composed(
    current_rules_database: RulesDatabase,
) -> None:
    special_dice = current_rules_database.composed_record("rule:special-dice")
    assert special_dice is not None
    assert special_dice["facts"]["category"] == "basic-rule"
    text = " ".join(
        clause
        for field in ("effects", "restrictions", "clarifications")
        for clause in special_dice["facts"][field]
    )
    for required in (
        "do not spend [[trait:disposable-x|Disposable]] uses",
        "the Active Player selects first",
        "assigned to a different target",
        "[[skill:berserk]]",
        "[[equipment:medikit|MediKit]]",
        "[[equipment:gizmokit|GizmoKit]]",
        "[[trait:bs-weapon-ph|PH]]",
        "[[trait:bs-weapon-wip|WIP]]",
        "[[skill:martial-arts]]",
        "Coordinated Orders",
    ):
        assert required in text
    assert {
        (source["source_id"], source.get("page"))
        for source in special_dice["citations"]
    } >= {
        ("n5-core-v5.3-pdf", 75),
        ("n5-core-v5.3-pdf", 100),
        ("n5-core-v5.3-pdf", 136),
        ("n5-faq-v0.1-en-pdf", 3),
    }

    assert sum(
        "N5 v0.1 FAQ confirms" in clause
        for clause in special_dice["facts"]["clarifications"]
    ) == 1

    for record_id in (
        "rule:fireteam-level-bonuses",
        "skill:martial-arts",
        "skill:martial-arts-l3",
        "skill:martial-arts-l5",
        "skill:berserk",
        "skill:bs-attack",
        "trait:disposable-x",
        "equipment:medikit",
        "equipment:gizmokit",
    ):
        record = current_rules_database.composed_record(record_id)
        assert record is not None, record_id
        authored_text = json.dumps(record)
        assert any(
            reference in authored_text
            for reference in (
                "[[rule:special-dice|Special Dice]]",
                "[[rule:special-dice|Special Die]]",
            )
        ), record_id


def test_rea041_spanish_fireteam_dice_conflict_is_visible_without_changing_b6(
    current_rules_database: RulesDatabase,
) -> None:
    special_dice = current_rules_database.composed_record("rule:special-dice")
    fireteam = current_rules_database.composed_record("rule:fireteam-level-bonuses")
    assert special_dice is not None and fireteam is not None

    notes = special_dice["facts"]["sourceNotes"]
    assert len(notes) == 2
    assert "English N5.3 pp. 75/136" in notes[0]
    assert "Spanish N5.3 p. 75" in notes[0]
    assert "B6 Attack with one +1 SD" in notes[0]
    assert "roll seven dice, discard one" in notes[0]
    assert "Spanish N5.3 p. 140" in notes[1]
    assert "conflicts with its own p. 75" in notes[1]
    assert "pending a scoped official ruling" in notes[1]
    assert "a separate Fireteam dice cap" in notes[1]

    restrictions = " ".join(special_dice["facts"]["restrictions"])
    assert "maximum Attack Burst remains B6" in restrictions
    assert "extra SD dice do not count as Burst" in restrictions
    source_note = fireteam["facts"]["sourceNotes"][0]
    assert "**Unresolved Spanish Fireteam reminder:**" in source_note
    assert "[[rule:special-dice|Special Dice (+1 SD)]]" in source_note
    assert "unverified pending an official correction" in source_note
    assert fireteam["facts"]["levels"][1]["bonuses"] == [
        "[[skill:bs-attack]] ([[rule:special-dice|+1 SD]])"
    ]
    for record in (special_dice, fireteam):
        assert {
            (citation["source_id"], citation.get("page"))
            for citation in record["citations"]
            if citation["source_id"] == "n5-core-v5.3-es-pdf"
        } >= {
            ("n5-core-v5.3-es-pdf", 75),
            ("n5-core-v5.3-es-pdf", 140),
        }


def test_rea034_published_morat_example_and_conflict_notice(
    current_rules_database: RulesDatabase,
) -> None:
    record = current_rules_database.composed_record("rule:fireteam-level-bonuses")
    assert record is not None
    facts = record["facts"]
    basis = facts["basis"]
    assert "five-member CORE" in basis
    assert "three Morat Vanguard" in basis
    assert "**Level 3**" in basis
    assert "[[rule:special-dice|+1 SD]]" in basis
    assert "Level 4 **+1 BS**" in basis
    assert facts["levels"][2]["bonuses"] == ["+3 [[skill:discover]]", "+1 [[skill:dodge]]"]
    assert facts["levels"][3]["bonuses"] == ["+1 BS"]
    assert "Unresolved Spanish Fireteam reminder" in facts["sourceNotes"][0]
    note = facts["sourceNotes"][1]
    assert "Unresolved printed Fireteam example" in note
    assert "English N5.3 p. 138" in note
    assert "Spanish N5.3 p. 142" in note
    assert "**+1 BS/CD Attack**" in note
    assert "table-based rule pending an official correction" in note
    cited = {(ref["source_id"], ref.get("page")) for ref in record["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 138),
        ("n5-core-v5.3-es-pdf", 139),
        ("n5-core-v5.3-es-pdf", 142),
    }


def test_shared_face_to_face_and_saving_roll_baselines_are_composed(
    current_rules_database: RulesDatabase,
) -> None:
    face_to_face = current_rules_database.composed_record("rule:face-to-face-rolls")
    saving = current_rules_database.composed_record("rule:saving-rolls")
    assert face_to_face is not None
    assert saving is not None
    assert face_to_face["facts"]["category"] == "basic-rule"
    assert saving["facts"]["category"] == "basic-rule"
    assert "affect one another directly" in " ".join(face_to_face["facts"]["restrictions"])
    assert "both players roll Criticals" in " ".join(face_to_face["facts"]["effects"])
    assert "Order is still spent" in " ".join(face_to_face["facts"]["effects"])
    assert "[[skill:dodge|Dodge]]" in " ".join(face_to_face["facts"]["clarifications"])
    assert "PH-6" in " ".join(saving["facts"]["restrictions"])
    assert "rolling 13 passes, while 14 fails" in " ".join(saving["facts"]["clarifications"])
    assert "additional Saving Roll" in " ".join(saving["facts"]["effects"])
    for rule in (face_to_face, saving):
        assert {citation["source_id"] for citation in rule["citations"]} >= {
            "n5-core-v5.3-pdf"
        }
    for skill_id in ("skill:bs-attack", "skill:cc-attack"):
        skill = current_rules_database.composed_record(skill_id)
        assert skill is not None
        rendered = json.dumps(skill)
        assert "[[rule:face-to-face-rolls|Face to Face Rolls]]" in rendered
        assert "[[rule:saving-rolls|Saving Rolls]]" in rendered


def test_guts_roll_reference_and_source_exceptions_are_composed(
    current_rules_database: RulesDatabase,
) -> None:
    guts = current_rules_database.composed_record("rule:guts-roll")
    assert guts is not None
    assert guts["facts"]["category"] == "basic-rule"
    text = " ".join(
        clause
        for field in ("requirements", "effects", "restrictions", "clarifications")
        for clause in guts["facts"][field]
    )
    for phrase in (
        "single unopposed [[attribute:wip|WIP]] Roll",
        "[[distance:2:inch]]",
        "positions where they actually attacked",
        "[[state:prone|Prone]]",
        "[[skill:courage|Courage]]",
        "[[skill:religious-troop|Religious Troop]]",
        "[[ammunition:stun|Stun Ammunition]]",
        "Operational Command Token during their Active Turn",
    ):
        assert phrase in text
    assert ("n5-core-v5.3-pdf", 38) in {
        (citation["source_id"], citation.get("page"))
        for citation in guts["citations"]
    }
    assert {citation["source_id"] for citation in guts["citations"]} >= {
        "wiki-guts-roll-oldid-4122",
    }
    for entity_id in (
        "skill:courage", "skill:religious-troop", "skill:journalist",
        "skill:climbing-plus", "state:prone", "state:suppressive-fire",
        "ammunition:stun",
    ):
        record = current_rules_database.composed_record(entity_id)
        assert record is not None, entity_id
        assert "[[rule:guts-roll|Guts Roll]]" in json.dumps(record), entity_id


def test_rea010_published_immunity_protection_and_source_examples(
    current_rules_database: RulesDatabase,
) -> None:
    immunity = current_rules_database.composed_record("skill:immunity")
    flash = current_rules_database.composed_record("weapon:flash-pulse")
    continuous = current_rules_database.composed_record("trait:continuous-damage")
    arm_zero = current_rules_database.composed_record("trait:arm-0")
    bts_zero = current_rules_database.composed_record("trait:bts-0")
    assert immunity is not None and flash is not None
    assert continuous is not None and arm_zero is not None and bts_zero is not None
    baseline = next(x for x in immunity["facts"]["effects"] if "non-Comms" in x)
    for ref in (
        "[[trait:continuous-damage|Continuous Damage]]", "[[trait:arm-0|ARM = 0]]",
        "[[trait:bts-0|BTS = 0]]", "[[ammunition:normal|Normal]]",
    ):
        assert ref in baseline
    assert "neither protection removes the ordinary Saving Roll" in baseline
    mono, pulse = immunity["facts"]["clarifications"][:2]
    assert "two ARM Saving Rolls" in mono
    assert "[[skill:immunity|Immunity (Critical)]]" in mono
    assert "[[weapon:flash-pulse|Flash Pulse]]" in pulse
    assert "Saving Roll stays BTS, not ARM" in pulse
    assert "[[state:stunned|Stunned]] only on a failed BTS roll" in pulse
    assert "one BTS Saving Roll per hit" in flash["summary"]
    assert "Non-Lethal" in flash["summary"]
    assert "Stunned" in flash["summary"]
    assert "[[skill:immunity]]" in continuous["summary"]
    assert len(immunity["facts"]["immunityInteraction"]["reviewedCombinedCases"]) == 3
    cited = {(c["source_id"], c.get("page")) for c in immunity["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 95), ("n5-core-v5.3-pdf", 96),
        ("n5-core-v5.3-es-pdf", 99),
    }


def test_rea009_shared_timing_example_and_recovery_links_are_published(
    current_rules_database: RulesDatabase,
) -> None:
    ids = (
        "rule:order-expenditure-sequence", "skill:engineer", "skill:doctor",
        "state:immobilized-a", "ammunition:para",
    )
    records = {rid: current_rules_database.composed_record(rid) for rid in ids}
    assert all(record is not None for record in records.values())
    order = records["rule:order-expenditure-sequence"]
    assert order is not None
    snippets = " ".join(order["facts"]["clarifications"])
    assert "**Positive-before-negative resolution:**" in snippets
    assert "**new** [[state:immobilized-a|IMM-A]]" in snippets
    assert "original [[state:immobilized-a|IMM-A]] is not removed" in snippets
    assert "passed Saving Roll leaves the Trooper free" in snippets
    for rid in ids[1:4]:
        rec = records[rid]
        assert rec is not None
        text = " ".join(
            rec["facts"].get("restrictions", []) + rec["facts"].get("clarifications", [])
        )
        assert "[[rule:order-expenditure-sequence|Order Expenditure Sequence]]" in text
    engineer = records["skill:engineer"]
    doctor = records["skill:doctor"]
    imm_a = records["state:immobilized-a"]
    assert engineer and doctor and imm_a
    assert any(c["source_id"] == "n5-core-v5.3-pdf" and c.get("page") == 15
               for c in engineer["citations"])
    assert any(c["source_id"] == "n5-core-v5.3-pdf" and c.get("page") == 15
               for c in doctor["citations"])
    for rid in ("rule:order-expenditure-sequence", "state:immobilized-a"):
        rec = records[rid]
        assert rec is not None
        cited = {(c["source_id"], c.get("page")) for c in rec["citations"]}
        assert cited >= {("n5-core-v5.3-pdf", 15), ("n5-core-v5.3-es-pdf", 15)}
    para = records["ammunition:para"]
    assert para is not None
    assert para["facts"]["ammunitionResolution"]["stateEffects"] == [
        {"stateId": "state:immobilized-a", "condition": "failed-saving-roll"}
    ]


def test_order_expenditure_sequence_mechanics_are_composed(
    current_rules_database: RulesDatabase,
) -> None:
    order = current_rules_database.composed_record("rule:order-expenditure-sequence")
    assert order is not None
    assert order["facts"]["category"] == "basic-rule"
    text = " ".join(
        clause
        for field in ("effects", "restrictions", "clarifications")
        for clause in order["facts"][field]
    )
    for fragment in (
        "First [[trait:aro|ARO]] check",
        "not eligible at the first check",
        "full movement route",
        "all Basic Short Skills",
        "Long [[skill:jump|Jump]] or [[skill:climb|Climb]]",
        "Declared [[trait:disposable-x|Disposable]] uses are still spent",
        "[[skill:discover|Discover]]",
        "[[skill:engineer|Engineer]]",
        "[[state:immobilized-a|IMM-A]]",
    ):
        assert fragment in text
    assert {
        (citation["source_id"], citation.get("page"))
        for citation in order["citations"]
    } >= {("n5-core-v5.3-pdf", 14), ("n5-core-v5.3-pdf", 15)}

    for identifier in (
        "skill:idle", "skill:move", "skill:bs-attack", "skill:alert",
        "rule:guts-roll", "trait:disposable-x",
    ):
        entry = current_rules_database.composed_record(identifier)
        assert entry is not None, identifier
        assert "[[rule:order-expenditure-sequence|Order Expenditure Sequence]]" in json.dumps(entry)


def test_coordinated_orders_baseline_and_cross_references(
    current_rules_database: RulesDatabase,
) -> None:
    record = current_rules_database.composed_record("rule:coordinated-orders")
    assert record is not None
    assert record["facts"]["category"] == "basic-rule"
    prose = " ".join(
        fragment
        for section in ("requirements", "effects", "restrictions", "clarifications")
        for fragment in record["facts"][section]
    )
    for expected in (
        "one Command Token and one Regular Order",
        "same Training (Regular or Irregular)",
        "Spearhead uses half",
        "Every other participating Trooper has Burst 1",
        "different reactive Troopers may choose different targets",
        "[[skill:idle|Idle]]",
        "[[skill:cc-attack|CC Attack]]",
        "[[skill:doctor|Doctor]]",
        "[[equipment:medikit|MediKit]]",
        "[[skill:engineer|Engineer]]",
        "[[trait:targetless|Targetless]]",
        "[[rule:special-dice|Special Dice (+1 SD)]]",
        "[[state:hidden-deployment|Hidden Deployment]]",
    ):
        assert expected in prose
    assert {
        (citation["source_id"], citation.get("page"))
        for citation in record["citations"]
    } >= {
        ("n5-core-v5.3-pdf", 129),
        ("n5-core-v5.3-pdf", 130),
        ("n5-faq-v0.1-en-pdf", 3),
    }
    for linked in (
        "rule:order-expenditure-sequence", "rule:special-dice",
        "skill:bs-attack", "skill:cc-attack", "skill:doctor",
        "skill:engineer", "equipment:medikit", "equipment:gizmokit",
        "skill:hacker", "rule:fireteam-general",
    ):
        source = current_rules_database.composed_record(linked)
        assert source is not None, linked
        assert "[[rule:coordinated-orders|Coordinated Orders]]" in json.dumps(source), linked


def test_escape_system_threshold_help_refers_to_the_unit_profile(
    current_rules_database: RulesDatabase,
) -> None:
    record = current_rules_database.composed_record("equipment:escape-system")
    assert record is not None
    restrictions = " ".join(record["facts"]["restrictions"])
    assert "listed after [[equipment:escape-system]] in the Unit Profile" in restrictions
    assert "source profile" not in restrictions


def test_rules_export_finalization_is_default_and_can_be_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    calls: list[str] = []

    monkeypatch.setattr(
        rules_database_module,
        "vacuum_deterministic_sqlite",
        lambda connection: calls.append("vacuum"),
    )
    monkeypatch.setattr(
        rules_database_module,
        "normalize_sqlite_header",
        lambda path: calls.append("header"),
    )

    export_release_rules_database(documents, tmp_path / "canonical.db")
    assert calls == ["vacuum", "header"]

    calls.clear()
    export_release_rules_database(documents, tmp_path / "semantic.db", finalize=False)
    assert calls == []


@pytest.mark.parametrize(
    "record_id",
    (
        "weapon:drop-bears", "weapon:sepsitor-plus", "weapon:pt",
        "weapon:pt-endgame", "weapon:kobra-pistol-cc",
        "weapon:wildparrot", "weapon:para-mine",
    ),
)
def test_weapon_source_notes_remain_distinct_from_gameplay_summary(
    current_rules_database: RulesDatabase, record_id: str,
) -> None:
    record = current_rules_database.composed_record(record_id)
    assert record is not None
    notes = record["facts"]["sourceNotes"]
    assert len(notes) == (2 if record_id == "weapon:kobra-pistol-cc" else 1)
    for note in notes:
        assert "Army" in note
        assert note not in record["summary"]
    assert record["citations"]


def test_export_rules_database_ignores_example_and_preserves_provenance(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"

    export_rules_database(documents, output)

    with sqlite3.connect(output) as connection:
        assert connection.execute("PRAGMA application_id").fetchone()[0] == RULES_APPLICATION_ID
        assert connection.execute("PRAGMA user_version").fetchone()[0] == RULES_SCHEMA_VERSION
        assert connection.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 465
        assert connection.execute(
            "SELECT id, title FROM scenario_collections ORDER BY id"
        ).fetchall() == [
            ("its-18", "ITS Season 18: Overheat"),
            ("n5-core", "N5 Core Scenarios"),
        ]
        assert connection.execute(
            "SELECT collection_id, revision, source_collection_id "
            "FROM scenario_collection_revisions ORDER BY collection_id"
        ).fetchall() == [
            ("its-18", "2026.09.01", "its-season-18-2026.09.01"),
            ("n5-core", "5.3", "n5-core-v5.3"),
        ]
        assert connection.execute(
            "SELECT scenario_id, position FROM scenario_memberships "
            "WHERE collection_id = 'n5-core' ORDER BY position"
        ).fetchall() == [
            ("scenario:annihilation", 0),
            ("scenario:domination", 1),
            ("scenario:supplies", 2),
            ("scenario:firefight", 3),
        ]
        publication_rows = connection.execute(
            "SELECT scenario_id, content_sha256 FROM scenario_publications "
            "ORDER BY scenario_id"
        ).fetchall()
        assert [row[0] for row in publication_rows] == [
            "scenario:annihilation",
            "scenario:battleground",
            "scenario:domination",
            "scenario:firefight",
            "scenario:supplies",
        ]
        assert all(len(row[1]) == 64 for row in publication_rows)
        example_count = connection.execute(
            "SELECT COUNT(*) FROM records WHERE id LIKE '%example%'"
        ).fetchone()[0]
        assert example_count == 0
        assert connection.execute(
            "SELECT member, page FROM vocabulary_sources WHERE vocabulary = 'skillTypes'"
        ).fetchone() == ("Skills_and_Equipment_Module", None)
        assert connection.execute(
            "SELECT member, page FROM vocabulary_sources WHERE vocabulary = 'labels'"
        ).fetchone() == ("Labels", None)
        assert connection.execute(
            "SELECT local_path, sha256, acquired_at, language, document_count, url "
            "FROM sources WHERE id = 'wiki-en-20260926-200832'"
        ).fetchone() == (
            "data/wiki/WIKI-en 20260926-200832.zip",
            "c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987",
            "2026-09-26T20:08:32+02:00",
            "en",
            812,
            "https://infinitythewiki.com/",
        )
        assert connection.execute(
            "SELECT url FROM sources WHERE id = 'n5-core-v5.3-pdf'"
        ).fetchone()[0] == "https://experience.corvusbelli.com/en/infinity/resources"
        annihilation_row = connection.execute(
            "SELECT kind, facts_json FROM records WHERE id = 'scenario:annihilation'"
        ).fetchone()
        assert annihilation_row is not None
        assert annihilation_row[0] == "scenario"
        annihilation_facts = json.loads(annihilation_row[1])
        assert [
            configuration["armyPoints"]
            for configuration in annihilation_facts["configurations"]
        ] == [[150], [200, 250], [300, 350, 400]]
        assert {
            (annotation["kind"], annotation["target"])
            for annotation in annihilation_facts["configurations"][0]["geometry"][
                "annotations"
            ]
        } == {
            ("dimension", "deployment-a"),
            ("dimension", "deployment-b"),
        }
        scenario_row = connection.execute(
            "SELECT kind, facts_json FROM records WHERE id = 'scenario:domination'"
        ).fetchone()
        assert scenario_row is not None
        assert scenario_row[0] == "scenario"
        scenario_facts = json.loads(scenario_row[1])
        assert scenario_facts["definitionVersion"] == 1
        assert [
            configuration["armyPoints"]
            for configuration in scenario_facts["configurations"]
        ] == [[150], [200, 250], [300, 350, 400]]
        first_annotations = scenario_facts["configurations"][0]["geometry"][
            "annotations"
        ]
        assert {annotation["target"] for annotation in first_annotations} == {
            "deployment-a",
            "deployment-b",
            "quadrant-1",
            "quadrant-2",
            "quadrant-3",
            "quadrant-4",
        }
        supplies_row = connection.execute(
            "SELECT kind, facts_json FROM records WHERE id = 'scenario:supplies'"
        ).fetchone()
        assert supplies_row is not None
        assert supplies_row[0] == "scenario"
        supplies_facts = json.loads(supplies_row[1])
        assert [
            configuration["armyPoints"]
            for configuration in supplies_facts["configurations"]
        ] == [[150], [200, 250], [300, 350, 400]]
        supplies_annotations = supplies_facts["configurations"][0]["geometry"][
            "annotations"
        ]
        assert {
            (annotation["kind"], annotation["target"])
            for annotation in supplies_annotations
        } == {
            ("dimension", "deployment-a"),
            ("dimension", "deployment-b"),
            ("element-edge-distance", "supply-box-left"),
            ("element-edge-distance", "supply-box-right"),
        }
        firefight_row = connection.execute(
            "SELECT kind, facts_json FROM records WHERE id = 'scenario:firefight'"
        ).fetchone()
        assert firefight_row is not None
        assert firefight_row[0] == "scenario"
        firefight_facts = json.loads(firefight_row[1])
        assert [
            configuration["armyPoints"]
            for configuration in firefight_facts["configurations"]
        ] == [[150], [200, 250], [300, 350, 400]]
        assert {
            (annotation["kind"], annotation["target"])
            for annotation in firefight_facts["configurations"][0]["geometry"][
                "annotations"
            ]
        } == {
            ("dimension", "deployment-a"),
            ("dimension", "deployment-b"),
        }
        assert connection.execute(
            "SELECT relation_type, related_record_id FROM record_relations "
            "WHERE record_id = 'skill:camouflage' ORDER BY position LIMIT 1"
        ).fetchone() == ("enters-state", "state:camouflaged")
        assert connection.execute(
            "SELECT relation_type, related_record_id FROM record_relations "
            "WHERE record_id = 'equipment:baggage' ORDER BY position"
        ).fetchall() == [
            ("enables-use-of", "skill:reload"),
            ("cancels-state", "state:unloaded"),
        ]
        assert connection.execute(
            "SELECT source_id, page FROM record_citations "
            "WHERE record_id = 'state:camouflaged' AND page IS NOT NULL "
            "ORDER BY page LIMIT 1"
        ).fetchone() == ("n5-core-v5.3-pdf", 87)


def test_composed_record_can_attach_current_army_links(
    current_rules_database: RulesDatabase,
) -> None:
    ordinary = current_rules_database.composed_record("equipment:multispectral-visor")
    assert ordinary is not None
    assert "army_links" not in ordinary

    routed = current_rules_database.composed_record(
        "equipment:multispectral-visor", include_army_links=True
    )
    assert routed is not None
    assert routed["army_links"] == [
        {"entity": "equipment", "id": "multispectral-visor"}
    ]


def test_rules_database_returns_records_using_current_label(
    current_rules_database: RulesDatabase,
) -> None:
    cc_attack = current_rules_database.composed_records_using_label("cc-attack")
    assert [record["id"] for record in cc_attack] == ["skill:berserk"]
    assert cc_attack[0]["army_links"] == [
        {"entity": "skill", "id": "berserk"}
    ]

    comms_equipment = {
        record["id"]: record
        for record in current_rules_database.composed_records_using_label("comms-equipment")
    }
    assert set(comms_equipment) == {
        "equipment:deployable-repeater",
        "equipment:evo-hacking-device",
        "equipment:hacking-device",
        "equipment:hacking-device-plus",
        "equipment:killer-hacking-device",
        "equipment:repeater",
    }
    assert comms_equipment["equipment:hacking-device"]["army_links"] == [
        {"entity": "equipment", "id": "hacking-device"}
    ]


def test_hacking_programs_reuse_canonical_current_labels(
    current_rules_database: RulesDatabase,
) -> None:
    programs = {
        record["id"]: record
        for record in current_rules_database.records_by_kind("hacking-program")
    }

    assert [label["name"] for label in programs["hacking-program:assisted-fire"]["labels"]] == [
        "Supportware",
        "No Roll",
    ]
    assert [label["name"] for label in programs["hacking-program:carbonite"]["labels"]] == [
        "Comms Attack"
    ]
    assert [label["name"] for label in programs["hacking-program:cybermask"]["labels"]] == [
        "Negative Feedback (NFB)",
        "No Roll",
    ]
    assert [label["name"] for label in programs["hacking-program:white-noise"]["labels"]] == [
        "Negative Feedback (NFB)"
    ]


def test_negative_feedback_has_owner_scoped_effect_and_program_lifetimes(
    current_rules_database: RulesDatabase,
) -> None:
    """NFB is per Trooper; Programs retain their distinct cancellation conditions."""
    label = next(
        label
        for label in current_rules_database.current_labels()
        if label["id"] == "negative-feedback"
    )
    description = label["description"]
    assert "cancels and overrides" in description
    assert "same Trooper" in description
    assert "Only one NFB effect" in description
    assert "canceled or voluntarily deactivated" in description
    assert "other Troopers are not affected" in description

    cybermask = current_rules_database.composed_record("hacking-program:cybermask")
    assert cybermask is not None
    assert any(item["id"] == "negative-feedback" for item in cybermask["labels"])
    cybermask_effects = " ".join(cybermask["facts"]["effects"])
    assert "[[state:impersonation-2]]" in cybermask_effects
    assert "NFB Label" in cybermask_effects
    assert "while" in cybermask_effects.lower()
    assert "other NFB" in cybermask_effects
    assert "not to allied Troopers" in cybermask_effects

    white_noise = current_rules_database.composed_record("hacking-program:white-noise")
    assert white_noise is not None
    assert any(item["id"] == "negative-feedback" for item in white_noise["labels"])
    white_noise_effects = " ".join(white_noise["facts"]["effects"])
    assert "successful Normal WIP Roll" in white_noise_effects
    assert "until the start of the States Phase" in white_noise_effects
    assert "While this Template remains on the table" in white_noise_effects
    assert "This restriction ends when the Template is removed" in white_noise_effects
    assert "does not extend to other Troopers" in white_noise_effects
    assert "[[term:white-noise-zone|White Noise Zone]]" in white_noise_effects


def test_controlled_jump_immediate_aro_and_opposing_effects_are_published(
    current_rules_database: RulesDatabase,
) -> None:
    program = current_rules_database.composed_record("hacking-program:controlled-jump")
    assert program is not None
    assert "immediately" in program["summary"]

    effects = " ".join(program["facts"]["effects"])
    restrictions = " ".join(program["facts"]["restrictions"])
    assert "as soon as it is declared" in effects
    assert "before the Resolution step" in effects
    assert "Supportware Token" in effects
    assert "allied Troopers receive +3" in effects
    assert "enemy Troopers receive -3" in effects
    assert "even if the Troopers are not Hackable" in effects
    assert "[[skill:combat-jump]]" in effects
    assert "ARO" in effects and "anywhere on the table" in effects
    assert "immediately applies to the same [[skill:combat-jump]] PH Roll" in effects
    assert "ARO is optional" in restrictions
    assert "their Programs' effects cancel" in restrictions
    assert "This does not cancel independent MODs" in restrictions
    assert "Firefight's Designated Landing Area +3" in restrictions
    assert "one Controlled Jump Program active" in restrictions
    assert {
        citation["page"]
        for citation in program["citations"]
        if citation["source_id"] == "n5-core-v5.3-pdf"
    } == {56, 59, 155}
    assert any(
        relation["type"] == "modifies-rolls-for"
        and relation["record_id"] == "skill:combat-jump"
        for relation in program["relations"]
    )


def test_rea006_controlled_jump_worked_examples_are_published(
    current_rules_database: RulesDatabase,
) -> None:
    program = current_rules_database.composed_record("hacking-program:controlled-jump")
    speedball = current_rules_database.composed_record("skill:request-speedball")
    assert program is not None and speedball is not None
    aro, opposing, tokens = program["facts"]["clarifications"]
    assert "same PH landing Roll" in aro
    assert "before Resolution" in aro
    assert "another eligible [[trait:aro|ARO]]" in aro
    assert "neither Program gives +3 or -3" in opposing
    assert "not a general rule that opposite MODs always cancel" in opposing
    assert "Designated Landing Area" in opposing
    assert "that scenario MOD is not canceled" in opposing
    assert "[[skill:request-speedball|Speedball]]" in tokens
    assert "FAQ expressly excludes these Tokens" in tokens
    assert "[[hacking-program:controlled-jump]] does not affect Speedballs" in speedball["summary"]
    cited = {(c["source_id"], c.get("page")) for c in program["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 59),
        ("n5-core-v5.3-pdf", 155),
        ("n5-core-v5.3-es-pdf", 61),
        ("n5-faq-v0.1-en-pdf", 1),
    }


def test_protheion_overkill_and_opponent_mod_are_published(
    current_rules_database: RulesDatabase,
) -> None:
    record = current_rules_database.composed_record("skill:protheion")
    assert record is not None
    assert "[[skill:cc-attack]]" in record["summary"]
    assert "[[state:dead]]" in record["summary"]
    assert "temporary VITA" not in record["summary"]

    requirements = " ".join(record["facts"]["requirements"])
    effects = " ".join(record["facts"]["effects"])
    assert "reach or already be in Silhouette contact" in requirements
    assert "Power-Up 1 or Power-Up 2 Token" in effects
    assert "first remove the user's Wounds, then increase VITA" in effects
    assert "finally apply Wounds received by the user" in effects
    assert "applies to the enemy's Attribute in a Face to Face Roll" in effects
    assert "not the user's Attribute" in effects
    assert "additional failed Saving Rolls against it have no effect" in effects
    assert "the second gives no benefit" in effects
    assert "[[state:unconscious|Unconscious]]" in effects
    assert "+2" in record["summary"]
    assert {
        (citation["source_id"], citation.get("page"))
        for citation in record["citations"]
    } >= {
        ("n5-core-v5.3-pdf", 109),
        ("n5-faq-v0.1-en-pdf", 2),
    }
    assert any(
        relation["type"] == "applies-effects-to"
        and relation["record_id"] == "skill:cc-attack"
        for relation in record["relations"]
    )


def test_request_specball_is_published_and_linked_without_replacing_speedball(
    current_rules_database: RulesDatabase,
) -> None:
    spec_ops = current_rules_database.composed_record("skill:infinity-spec-ops")
    request = current_rules_database.composed_record("skill:request-specball")
    speedball = current_rules_database.composed_record("skill:request-speedball")
    assert spec_ops is not None and request is not None and speedball is not None
    assert "[[skill:request-specball|Request SpecBall]]" in " ".join(
        spec_ops["facts"]["effects"]
    )
    assert "Game Round 2 or 3" in request["summary"]
    assert "[[skill:combat-jump|Combat Jump]]" in request["summary"]
    assert "[[term:null-state|Null State]]" in " ".join(
        request["facts"]["requirements"]
    )
    assert "[[term:state-token|State Tokens]]" in " ".join(
        request["facts"]["effects"]
    )
    assert "do not block enemy Movement" in " ".join(
        request["facts"]["effects"]
    )
    assert "At the end of the collecting Order" in " ".join(
        request["facts"]["effects"]
    )
    assert any("TEAM-OPS" in note for note in request["facts"]["sourceNotes"])
    assert any("Spanish N5.3" in note for note in request["facts"]["sourceNotes"])
    assert ("uses-effects-of", "outbound", "Combat Jump") in {
        (edge["type"], edge["direction"], edge["record"]["name"])
        for edge in request["display_relations"]
    }
    assert ("enables-use-of", "outbound", "Request SpecBall") in {
        (edge["type"], edge["direction"], edge["record"]["name"])
        for edge in spec_ops["display_relations"]
    }
    assert "two Speedball Tokens" in speedball["summary"]


def test_speedball_faq_exclusion_is_published_on_both_rule_cards(
    current_rules_database: RulesDatabase,
) -> None:
    speedball = current_rules_database.composed_record("skill:request-speedball")
    program = current_rules_database.composed_record("hacking-program:controlled-jump")
    assert speedball is not None and program is not None

    assert "PH 15" in speedball["summary"]
    assert "[[skill:combat-jump]]" in speedball["summary"]
    assert "[[hacking-program:controlled-jump]]" in speedball["summary"]
    assert "Troopers" in " ".join(speedball["facts"]["effects"])
    assert "Speedballs are Tokens" in " ".join(speedball["facts"]["effects"])
    assert "does not affect Speedball Tokens" in " ".join(
        program["facts"]["restrictions"]
    )
    assert "[[skill:request-speedball]]" in " ".join(
        program["facts"]["restrictions"]
    )
    assert "FAQ limits this Program to Troopers" in " ".join(
        program["facts"]["restrictions"]
    )
    for record in (speedball, program):
        assert any(
            citation["source_id"] == "n5-faq-v0.1-en-pdf"
            and citation["page"] == 1
            for citation in record["citations"]
        )
    assert any(
        relation["type"] == "uses-effects-of"
        and relation["record_id"] == "skill:combat-jump"
        for relation in speedball["relations"]
    )


def test_rea007_speedball_ph15_worked_example_is_published(
    current_rules_database: RulesDatabase,
) -> None:
    speedball = current_rules_database.composed_record("skill:request-speedball")
    program = current_rules_database.composed_record("hacking-program:controlled-jump")
    assert speedball is not None and program is not None
    assert len(speedball["facts"]["clarifications"]) == 1
    example = speedball["facts"]["clarifications"][0]
    assert "Each Token still uses its own PH 15 Roll" in example
    assert "PH 18" in example and "PH 12" in example
    assert "not every other possible modifier to placement" in example
    assert "[[skill:combat-jump|Combat Jump]]" in example
    assert "[[hacking-program:controlled-jump|Controlled Jump]]" in example
    assert "**Troopers versus Speedball Tokens:**" in " ".join(
        program["facts"]["clarifications"]
    )
    assert "does not affect Speedball Tokens" in " ".join(program["facts"]["restrictions"])
    for record in (speedball, program):
        assert any(
            c["source_id"] == "n5-faq-v0.1-en-pdf" and c["page"] == 1
            for c in record["citations"]
        )


def test_rea005_wip_attack_prohibitions_are_visible_without_new_variant_edges(
    current_rules_database: RulesDatabase,
) -> None:
    trait = current_rules_database.composed_record("trait:bs-weapon-wip")
    flash_pulse = current_rules_database.composed_record("weapon:flash-pulse")
    assert trait is not None and flash_pulse is not None
    ordinary, shock, guided = trait["facts"]["clarifications"]
    assert "[[weapon:flash-pulse|Flash Pulse]]" in ordinary
    assert "[[skill:bs-attack|BS Attack]] MODs to WIP" in ordinary
    assert "cannot use the named [[skill:bs-attack|BS Attack (Shock)]]" in shock
    assert "[[ammunition:shock|Shock Ammunition]] in general" in shock
    assert "[[state:targeted|Targeted]]" in guided
    assert "Guided's permission" in guided
    assert "cannot be used" in guided
    assert "[[trait:bs-weapon-wip|BS Weapon (WIP)]]" in flash_pulse["summary"]
    assert [(r["type"], r["record_id"]) for r in trait["relations"]] == [
        ("modifies-rolls-for", "skill:bs-attack")
    ]
    cited = {(c["source_id"], c.get("page")) for c in trait["citations"]}
    assert cited >= {
        ("n5-core-v5.3-pdf", 175),
        ("n5-core-v5.3-pdf", 39),
        ("n5-core-v5.3-es-pdf", 39),
    }


def test_rea004_continuous_damage_critical_and_immunity_examples_are_published(
    current_rules_database: RulesDatabase,
) -> None:
    trait = current_rules_database.composed_record("trait:continuous-damage")
    immunity = current_rules_database.composed_record("skill:immunity")
    saving_rolls = current_rules_database.composed_record("rule:saving-rolls")
    assert trait is not None and immunity is not None and saving_rolls is not None
    assert "additional roll does not apply Continuous Damage" in trait["summary"]
    hit, immune = trait["facts"]["clarifications"]
    assert "[[rule:saving-rolls|Saving Roll]]" in hit
    assert "**does not start a Continuous Damage chain**" in hit
    assert "only the failed ordinary-hit branch triggers repetition" in hit
    assert "[[skill:immunity|Immunity (Trait: Continuous Damage)]]" in immune
    assert "[[skill:immunity|Immunity (Critical)]]" in immune
    assert "covered non-Comms Attack" in immune
    assert "Immunity (Trait) ignores the special effects" in " ".join(
        immunity["facts"]["effects"]
    )
    assert "a Critical adds one additional Saving Roll" in " ".join(
        saving_rolls["facts"]["effects"]
    )
    assert {(c["source_id"], c.get("page")) for c in trait["citations"]} >= {
        ("n5-core-v5.3-pdf", 175),
        ("n5-core-v5.3-pdf", 95),
        ("n5-core-v5.3-es-pdf", 182),
        ("n5-core-v5.3-es-pdf", 99),
    }


def test_reviewed_trait_critical_and_wip_restrictions_are_published(
    current_rules_database: RulesDatabase,
) -> None:
    continuous = current_rules_database.composed_record("trait:continuous-damage")
    assert continuous is not None
    assert "Each failed Saving Roll required by a hit" in continuous["summary"]
    assert "inflicts a Wound" in continuous["summary"]
    assert "additional roll does not apply Continuous Damage" in continuous["summary"]
    assert "failing it does not start another chain" in continuous["summary"]
    assert "[[skill:immunity]]" in continuous["summary"]
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == 175
        for citation in continuous["citations"]
    )

    wip = current_rules_database.composed_record("trait:bs-weapon-wip")
    assert wip is not None
    assert "using WIP instead of BS" in wip["summary"]
    assert "BS Attack (Shock)" in wip["summary"]
    assert "BS Attack (Guided)" in wip["summary"]
    assert "not [[ammunition:shock|Shock Ammunition]] in general" in wip["summary"]
    assert {
        citation["page"]
        for citation in wip["citations"]
        if citation["source_id"] == "n5-core-v5.3-pdf"
    } == {39, 175}


def test_rules_database_returns_current_trait_records(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    database.validate()
    traits = {record["id"]: record for record in database.records_by_kind("trait")}

    assert len(traits) == 33
    assert traits["trait:suppressive-fire"]["aliases"] == ["Suppressive Fire"]
    assert traits["trait:bs-weapon-ph"]["aliases"] == ["Throwing Weapon"]
    assert traits["trait:bs-weapon-wip"]["aliases"] == ["Technical Weapon"]
    labels = {label["id"]: label for label in database.current_labels()}
    assert labels["comms-attack"]["name"] == "Comms Attack"
    assert labels["no-lof"]["name"] == "No LoF"
    assert traits["trait:disposable-x"]["facts"]["sourceIdentity"]["prefixes"] == [
        "Disposable ("
    ]
    assert traits["trait:continuous-damage"]["citations"][0]["heading"] == (
        "Continuous Damage"
    )
    assert traits["trait:continuous-damage"]["citations"][0]["source_url"] == (
        "https://infinitythewiki.com/index.php?title=Traits&oldid=4110"
    )
    assert traits["trait:continuous-damage"]["collection"] == {
        "id": "n5-core-v5.3",
        "title": "N5 Core Rules v5.3",
        "domain": "core-rules",
        "status": "current",
        "effective_from": "2026-08-10",
        "authority": "primary",
    }
    camouflaged = database.records_by_kind("state")[0]
    archived = next(
        citation
        for citation in camouflaged["citations"]
        if citation["source_id"] == "wiki-en-20260926-200832"
    )
    assert archived["member"] == "Camouflaged_State"
    assert archived["source_url"] == "https://infinitythewiki.com/"


def test_unit_profile_help_returns_reviewed_profile_notation_entries(
    current_rules_database: RulesDatabase,
) -> None:

    items = current_rules_database.unit_profile_help()

    assert [item["key"] for item in items] == [
        "unit-profile",
        "attributes",
        "training-orders",
        "troop-type",
        "classification",
        "isc",
        "hackable",
        "peripheral",
        "skills",
        "equipment",
        "weapons",
        "profile-options",
    ]
    assert items[2]["name"] == "Training and Orders"
    assert "Regular and Irregular" in items[2]["summary"]
    assert [item["name"] for item in items[8:11]] == [
        "Skills",
        "Equipment",
        "Weapons",
    ]
    assert items[-1]["order"] == 100


def test_training_classifies_normal_order_types_without_conflating_tactical_orders(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    database = RulesDatabase(output)
    training = database.training_by_order_type()
    assert set(training) == {"regular", "irregular"}
    assert {item["id"] for item in training.values()} == {
        "training:regular",
        "training:irregular",
    }
    assert all(item["kind"] == "training" for item in training.values())
    assert all(item["citations"][0]["page"] == 11 for item in training.values())
    assert all(item["collection"]["status"] == "current" for item in training.values())

    with sqlite3.connect(output) as connection:
        connection.execute("UPDATE collections SET status = 'superseded'")
    assert database.training_by_order_type() == {}


def test_training_enrichment_preserves_all_other_orders(
    tmp_path: Path,
    current_rules_database: RulesDatabase,
) -> None:
    catalog = SkillCatalog(Database(tmp_path / "unused.db"), current_rules_database)
    unit = {
        "armies": [
            {
                "loadouts": [
                    {
                        "orders": [
                            {"type": "regular", "list": 1},
                            {"type": "irregular", "list": 1},
                            {"type": "tactical", "list": 1},
                            {"type": "lieutenant", "list": 1},
                        ]
                    }
                ]
            }
        ]
    }
    enriched = catalog.enrich_unit(unit)
    orders = enriched["armies"][0]["loadouts"][0]["orders"]
    assert [order.get("training_reference", {}).get("id") for order in orders] == [
        "training:regular", "training:irregular", None, None
    ]
    assert all(
        "training_reference" not in order
        for order in unit["armies"][0]["loadouts"][0]["orders"]
    )


def test_rules_database_returns_armed_turret_special_profile(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    records = database.records_for_army_link("weapon", "armed-turret")

    assert [record["id"] for record in records] == ["weapon:armed-turret"]
    assert records[0]["variant_semantics"] == {"inheritance": "family"}
    assert records[0]["facts"]["specialProfile"] == {
        "stats": [
            ["MOV", "--"],
            ["CC", "5"],
            ["BS", "10"],
            ["PH", "--"],
            ["WIP", "--"],
            ["ARM", "2"],
            ["BTS", "3"],
            ["STR", "1"],
            ["S", "2"],
        ],
        "equipment": ["360º Visor"],
        "skills": ["Total Reaction"],
        "ccWeapon": "PARA CC Weapon (-3)",
    }
    citation = records[0]["citations"][0]
    assert citation["source_id"] == "n5-core-v5.3-pdf"
    assert citation["source_version"] == "5.3"
    assert citation["page"] == 70
    assert citation["section"] == "Armed Turret Profile"


def test_rea037_published_turret_profile_preserves_s2_and_source_conflict(
    current_rules_database: RulesDatabase,
) -> None:
    turret = current_rules_database.composed_record("weapon:armed-turret")
    assert turret is not None
    assert turret["facts"]["specialProfile"]["stats"][-1] == ["S", "2"]
    note = turret["facts"]["sourceNotes"][0]
    assert "**Unresolved Silhouette conflict:**" in note
    assert "**S1**" in note and "**S2**" in note
    assert "25 mm high versus 40 mm" in note
    assert "official correction has not been established" in note
    assert "[[trait:deployable|Deployable]] Weapon" in turret["summary"]
    assert "one-roll Turret mode" in turret["facts"]["sourceNotes"][1]
    assert "Unresolved Silhouette conflict" in turret["facts"]["sourceNotes"][0]
    pages = {(ref["source_id"], ref.get("page")) for ref in turret["citations"]}
    assert pages >= {
        ("n5-core-v5.3-pdf", 18),
        ("n5-core-v5.3-pdf", 70),
        ("n5-core-v5.3-pdf", 74),
        ("n5-core-v5.3-pdf", 195),
        ("n5-core-v5.3-es-pdf", 74),
        ("n5-core-v5.3-es-pdf", 203),
    }


def test_rules_database_returns_skill_parameter_semantics(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    assert RulesDatabase(output).skill_parameter_semantics() == {
        "super-jump": {"kind": "distance", "positive_sign": "omit"},
        "forward-deployment": {"kind": "distance", "positive_sign": "force"},
    }


def test_rules_database_returns_reviewed_source_variant_semantics(
    current_rules_database: RulesDatabase,
) -> None:

    variants = current_rules_database.catalog_source_variant_semantics("skill")

    assert variants[19] == {"kind": "level", "value": 1}
    assert variants[23] == {"kind": "level", "value": 5}
    assert variants[69] == {"kind": "level", "value": 1}
    assert variants[70] == {"kind": "level", "value": 2}
    assert variants[278] == {
        "kind": "attribute-replacement",
        "attribute": "BS",
        "value": 12,
    }
    assert variants[279] == {
        "kind": "attribute-replacement",
        "attribute": "BS",
        "value": 11,
    }
    assert variants[274] == {
        "kind": "attribute-replacement",
        "attribute": "CC",
        "value": 21,
    }

    equipment_variants = current_rules_database.catalog_source_variant_semantics(
        "equipment"
    )
    assert equipment_variants[169] == {"kind": "named", "label": "Firewall"}
    assert equipment_variants[188] == {"kind": "named", "label": "Neurocinetics"}
    assert equipment_variants[193] == {"kind": "named", "label": "Albedo"}
    assert equipment_variants[244] == {"kind": "named", "label": "Discover"}
    assert equipment_variants[247] == {"kind": "named", "label": "ECM Guided"}
    assert equipment_variants[248] == {"kind": "named", "label": "Repeater"}


def test_rules_database_returns_skill_declaration_categories(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    categories = [
        category
        for category in database.skill_declaration_categories()
        if category["skill_ref"] == "sapper"
    ]

    assert categories == [
        {
            "skill_ref": "sapper",
            "name": "Deployment",
            "order": 20,
            "source_title": "N5 Core Rules",
            "source_version": "5.3",
            "page": 111,
        },
        {
            "skill_ref": "sapper",
            "name": "Long Skill",
            "order": 50,
            "source_title": "N5 Core Rules",
            "source_version": "5.3",
            "page": 111,
        },
    ]



def test_rules_database_returns_equipment_declaration_categories(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    categories = RulesDatabase(output).declaration_categories("equipment")

    assert [
        {
            "army_ref": category["army_ref"],
            "type_id": category["type_id"],
            "name": category["name"],
            "order": category["order"],
            "page": category["page"],
        }
        for category in categories
    ] == [
        {
            "army_ref": "deactivator",
            "type_id": "short-skill",
            "name": "Short Skill",
            "order": 40,
            "page": 121,
        },
        {
            "army_ref": "gizmokit",
            "type_id": "short-skill",
            "name": "Short Skill",
            "order": 40,
            "page": 123,
        },
        {
            "army_ref": "medikit",
            "type_id": "short-skill",
            "name": "Short Skill",
            "order": 40,
            "page": 124,
        },
    ]

    with pytest.raises(ValueError, match="skill or equipment"):
        RulesDatabase(output).declaration_categories("weapon")


def test_current_declaration_categories_match_reviewed_n5_3_semantics(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    skill_categories: dict[object, list[str]] = {}
    for category in database.declaration_categories("skill"):
        skill_categories.setdefault(category["army_ref"], []).append(category["name"])

    assert skill_categories["bs-attack"] == ["Short Skill", "ARO"]
    assert skill_categories["cc-attack"] == ["Short Skill", "ARO"]
    assert skill_categories["dodge"] == ["Short Skill", "ARO"]
    assert skill_categories["forward-observer"] == ["Short Skill", "ARO"]
    assert skill_categories["doctor"] == ["Short Skill"]
    assert skill_categories["engineer"] == ["Short Skill"]
    assert skill_categories["cyberplug"] == ["Automatic"]
    assert skill_categories["paramedic"] == ["Automatic"]
    assert skill_categories["parachutist"] == ["Long Skill"]
    assert skill_categories["triangulated-fire"] == ["Long Skill"]
    assert skill_categories["berserk"] == ["Long Skill"]

    reload = next(
        record
        for record in database.composed_records_by_kind("skill")
        if record["id"] == "skill:reload"
    )
    assert [skill_type["id"] for skill_type in reload["skill_types"]] == [
        "short-skill",
        "aro",
    ]
    assert reload["skill_type"]["id"] == "short-skill"


def test_army_link_records_use_current_collections_by_default(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    current_path, current, hacking_programs = _current_core_with_hacking_programs(root)
    superseded = copy.deepcopy(current)
    superseded["collection"] = {
        **superseded["collection"],
        "id": "n5-core-v5.2",
        "title": "N5 Core Rules v5.2",
        "status": "superseded",
        "effectiveFrom": "2026-01-01",
    }
    superseded["scenarioCollection"]["revision"] = "5.2"
    output = tmp_path / "rules.db"
    export_rules_database(
        [
            (current_path, current),
            hacking_programs,
            (root / "n5-core-v5.2.json", superseded),
        ],
        output,
    )

    database = RulesDatabase(output)
    current_records = database.records_for_army_link("skill", "camouflage")
    all_records = database.records_for_army_link(
        "skill", "camouflage", current_only=False
    )

    assert current_records
    assert {record["collection"]["status"] for record in current_records} == {"current"}
    assert len(all_records) == len(current_records) * 2
    assert {record["collection"]["status"] for record in all_records} == {
        "current",
        "superseded",
    }


def test_composed_records_attach_current_supplements_without_field_merging(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    current_path, current, hacking_programs = _current_core_with_hacking_programs(root)
    supplement = copy.deepcopy(current)
    supplement["collection"] = {
        **supplement["collection"],
        "id": "n5-faq-v0.1",
        "title": "N5 FAQ v0.1",
        "domain": "faq",
        "effectiveFrom": "2026-09-01",
    }
    supplement.pop("scenarioComponents", None)
    supplement.pop("scenarioCollection", None)
    supplement["records"] = [
        {
            "id": "skill:camouflage",
            "kind": "skill",
            "name": "Camouflage",
            "summary": "A scoped FAQ clarification for Camouflage.",
            "composition": {"role": "supplement"},
            "scope": {"game": "N5", "seasons": ["current"]},
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 87}],
            "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
        }
    ]
    output = tmp_path / "rules.db"
    export_rules_database(
        [
            (current_path, current),
            hacking_programs,
            (root / "n5-faq-v0.1.json", supplement),
        ],
        output,
    )

    raw = RulesDatabase(output).records_for_army_link("skill", "camouflage")
    composed = RulesDatabase(output).composed_records_for_army_link(
        "skill", "camouflage"
    )

    raw_camouflage = [record for record in raw if record["id"] == "skill:camouflage"]
    composed_camouflage = next(
        record for record in composed if record["id"] == "skill:camouflage"
    )
    assert len(raw_camouflage) == 1
    assert composed_camouflage["summary"] == next(
        record["summary"]
        for record in current["records"]
        if record["id"] == "skill:camouflage"
    )
    assert [item["summary"] for item in composed_camouflage["supplements"]] == [
        "A scoped FAQ clarification for Camouflage."
    ]
    assert composed_camouflage["supplements"][0]["collection"]["id"] == "n5-faq-v0.1"


def test_export_rejects_ambiguous_current_definitions(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    current_path, current = load_curated_directory(root / "data" / "curated")[0]
    duplicate = copy.deepcopy(current)
    duplicate["collection"] = {
        **duplicate["collection"],
        "id": "n5-annex-current",
        "title": "N5 Annex",
        "domain": "annex",
    }
    duplicate.pop("scenarioCollection", None)
    duplicate["records"] = [
        next(record for record in duplicate["records"] if record["id"] == "skill:camouflage")
    ]

    with pytest.raises(ValueError, match="exactly one definition contribution"):
        export_rules_database(
            [(current_path, current), (root / "annex.json", duplicate)],
            tmp_path / "rules.db",
        )


def test_export_rejects_unresolved_current_label_reference(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    current_path, current, (hacking_path, hacking_programs) = (
        _current_core_with_hacking_programs(root)
    )
    document = copy.deepcopy(hacking_programs)
    document["records"][0]["labelIds"] = ["missing-label"]

    with pytest.raises(ValueError, match="does not resolve to a current canonical Label"):
        export_rules_database(
            [(current_path, current), (hacking_path, document)],
            tmp_path / "rules.db",
        )


def test_export_rejects_conflicting_current_label_definition(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    current_path, current, (hacking_path, hacking_programs) = (
        _current_core_with_hacking_programs(root)
    )
    document = copy.deepcopy(hacking_programs)
    supportware = copy.deepcopy(
        next(label for label in current["labels"] if label["id"] == "supportware")
    )
    supportware["description"] = "Conflicting test definition."
    document["labels"] = [supportware]

    with pytest.raises(ValueError, match="conflicting canonical definitions"):
        export_rules_database(
            [(current_path, current), (hacking_path, document)],
            tmp_path / "rules.db",
        )


def test_rules_database_exposes_reverse_typed_relations(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    relations = database.relations_for_record("state:camouflaged")

    assert {
        (item["type"], item["direction"], item["record_id"])
        for item in relations
    } == {
        ("enables-use-of", "outbound", "skill:surprise-attack"),
        ("restricts-use-of", "outbound", "skill:place-deployable"),
        ("enters-state", "inbound", "skill:camouflage"),
        ("reveals-state", "inbound", "skill:discover"),
        ("reveals-state", "inbound", "skill:sensor"),
        ("uses-effects-of", "inbound", "trait:concealed"),
        ("uses-effects-of", "inbound", "weapon:mines"),
        ("cancels-state", "inbound", "skill:frenzy"),
        ("cancels-state", "inbound", "state:retreat"),
    }

    camouflage = next(
        record
        for record in database.composed_records_for_army_link("skill", "camouflage")
        if record["id"] == "skill:camouflage"
    )
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in camouflage["display_relations"]
    } == {
        ("enters-state", "outbound", "Camouflaged State"),
        ("restricts-use-of", "inbound", "Sensor"),
    }

    camouflaged = next(
        record
        for record in database.composed_records_by_kind("state")
        if record["id"] == "state:camouflaged"
    )
    assert {
        (
            relation["type"],
            relation["direction"],
            relation["record"]["name"],
            tuple(
                (link["entity"], link.get("id"))
                for link in relation["record"]["army_links"]
            ),
        )
        for relation in camouflaged["display_relations"]
    } == {
        ("enables-use-of", "outbound", "Surprise Attack", (("skill", "surprise-attack"),)),
        ("restricts-use-of", "outbound", "Place Deployable", ()),
        ("enters-state", "inbound", "Camouflage", (("skill", "camouflage"),)),
        ("reveals-state", "inbound", "Discover", (("skill", "discover"),)),
        ("reveals-state", "inbound", "Sensor", (("skill", "sensor"),)),
        ("uses-effects-of", "inbound", "Concealed", ()),
        (
            "uses-effects-of", "inbound", "Mines",
            (
                ("weapon", "ap-mine"),
                ("weapon", "e-m-mine"),
                ("weapon", "monofilament-mine"),
                ("weapon", "para-mine"),
                ("weapon", "shock-mine"),
                ("weapon", "viral-mine"),
                ("weapon", "cybermine"),
            ),
        ),
        ("cancels-state", "inbound", "Frenzy", (("skill", "frenzy"),)),
        ("cancels-state", "inbound", "Retreat! State", ()),
    }



def test_reviewed_trait_skill_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    records = {
        record["id"]: record
        for kind in ("trait", "skill")
        for record in database.composed_records_by_kind(kind)
    }
    expected = {
        ("trait:bs-weapon-ph", "modifies-rolls-for", "skill:bs-attack"),
        ("trait:bs-weapon-wip", "modifies-rolls-for", "skill:bs-attack"),
        ("trait:cc", "enables-use-of", "skill:cc-attack"),
        ("trait:non-reloadable", "restricts-use-of", "skill:reload"),
    }

    for source_id, relation_type, target_id in expected:
        source = records[source_id]
        target = records[target_id]
        source_name = source["name"]
        target_name = target["name"]

        assert (relation_type, "outbound", target_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in source["display_relations"]
        }
        assert (relation_type, "inbound", source_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in target["display_relations"]
        }


def test_weapon_trait_skill_prerequisites_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def record(kind: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_by_kind(kind)
            if item["id"] == record_id
        )

    expected_pairs = {
        "trait:intuitive-attack": "skill:intuitive-attack",
        "trait:speculative-attack": "skill:speculative-attack",
        "trait:suppressive-fire": "skill:suppressive-fire",
    }

    for trait_id, skill_id in expected_pairs.items():
        trait = record("trait", trait_id)
        skill = record("skill", skill_id)
        skill_name = skill["name"]
        trait_name = trait["name"]

        assert ("enables-use-of", "outbound", skill_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in trait["display_relations"]
        }
        assert ("enables-use-of", "inbound", trait_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in skill["display_relations"]
        }


def test_skill_roll_modifier_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    records = {
        record["id"]: record for record in database.composed_records_by_kind("skill")
    }
    expected_pairs = {
        ("skill:martial-arts", "skill:cc-attack"),
        ("skill:marksmanship", "skill:bs-attack"),
        ("skill:sixth-sense", "skill:dodge"),
        ("skill:sixth-sense", "skill:reset"),
    }

    for source_id, target_id in expected_pairs:
        source = records[source_id]
        target = records[target_id]
        source_name = source["name"]
        target_name = target["name"]

        assert ("modifies-rolls-for", "outbound", target_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in source["display_relations"]
        }
        assert ("modifies-rolls-for", "inbound", source_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in target["display_relations"]
        }


def test_peripheral_subtypes_explain_shared_and_distinct_operation(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database
    skill = database.composed_record("skill:peripheral")
    assert skill is not None
    baseline = " ".join(skill["facts"]["effects"] + skill["facts"]["restrictions"])
    assert "count as one Trooper" in baseline
    assert "same Short Skills or Long Skill" in baseline
    assert "[[skill:idle|Idle]]" in baseline
    assert "[[state:disconnected|Disconnected]]" in baseline
    assert "[[rule:peripheral-type:ancillary|Ancillary Peripherals]]" in baseline

    expected = {
        "servant": ("Controller—not the Servant—makes the Roll", "one Model per Order"),
        "synchronized": ("before any declared movement is measured", "Controller"),
        "control": ("only the Controller and Spearhead perform it", "Spearhead"),
        "ancillary": ("using [[skill:place-deployable|Place Deployable]]", "Fireteam membership"),
        "cyberplug": ("Connected or Autonomous", "rather than becoming"),
    }
    for subtype, (effect, detail) in expected.items():
        rule = database.composed_record(f"rule:peripheral-type:{subtype}")
        assert rule is not None, subtype
        assert rule["facts"]["category"] == "peripheral-type"
        facts = rule["facts"]
        assert facts["effects"], subtype
        prose = " ".join(
            item
            for field in ("effects", "restrictions", "clarifications")
            for item in facts.get(field, [])
        )
        assert effect in prose, subtype
        assert detail in prose, subtype
        assert any(
            citation["source_id"] == "n5-core-v5.3-pdf"
            and citation.get("page") in (106, 107, 108)
            for citation in rule["citations"]
        ), subtype

    cyberplug = database.composed_record("rule:peripheral-type:cyberplug")
    assert cyberplug is not None
    cyberplug_facts = " ".join(
        cyberplug["facts"][field][0]
        for field in ("effects", "clarifications")
    )
    assert "[[skill:idle|Idle]]" in cyberplug_facts
    assert "[[skill:doctor|Doctor]]" in cyberplug_facts
    assert "[[skill:engineer|Engineer]]" in cyberplug_facts

    for source in ("skill:doctor", "skill:engineer", "state:disconnected", "skill:cyberplug"):
        record = database.composed_record(source)
        assert record is not None, source
        assert "[[rule:peripheral-type:cyberplug|Cyberplug" in str(record["facts"])


def test_place_deployable_prerequisites_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    records = {
        record["id"]: record
        for kind in ("trait", "rule", "skill")
        for record in database.composed_records_by_kind(kind)
    }
    place_deployable = records["skill:place-deployable"]
    expected_sources = {
        "trait:deployable": "Deployable",
        "rule:peripheral-type:ancillary": "Peripheral (Ancillary)",
    }

    for source_id, source_name in expected_sources.items():
        source = records[source_id]
        assert ("enables-use-of", "outbound", "Place Deployable") in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in source["display_relations"]
        }
        assert ("enables-use-of", "inbound", source_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in place_deployable["display_relations"]
        }


def test_common_skill_interactions_are_bidirectional(current_rules_database: RulesDatabase) -> None:
    database = current_rules_database

    records = {
        record["id"]: record for record in database.composed_records_by_kind("skill")
    }
    expected_pairs = {
        ("skill:look-out", "modifies-rolls-for", "skill:dodge"),
        ("skill:speculative-attack", "ignores-modifiers-from", "skill:mimetism"),
    }

    for source_id, relation_type, target_id in expected_pairs:
        source = records[source_id]
        target = records[target_id]
        source_name = source["name"]
        target_name = target["name"]

        assert (relation_type, "outbound", target_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in source["display_relations"]
        }
        assert (relation_type, "inbound", source_name) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in target["display_relations"]
        }


def test_mimetism_modifier_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def skill_rule(slug: str, record_id: str) -> dict:
        return next(
            record
            for record in database.composed_records_for_army_link("skill", slug)
            if record["id"] == record_id
        )

    msv = next(
        record
        for record in database.composed_records_for_army_link(
            "equipment", "multispectral-visor"
        )
        if record["id"] == "equipment:multispectral-visor"
    )
    mimetism = skill_rule("mimetism", "skill:mimetism")
    bs_attack = skill_rule("bs-attack", "skill:bs-attack")
    discover = skill_rule("discover", "skill:discover")

    assert (
        "reduces-modifiers-from",
        "outbound",
        "Mimetism",
    ) in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in msv["display_relations"]
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in mimetism["display_relations"]
    } == {
        ("imposes-modifiers-on", "outbound", "BS Attack"),
        ("imposes-modifiers-on", "outbound", "Discover"),
        ("reduces-modifiers-from", "inbound", "Multispectral Visor"),
        ("uses-effects-of", "inbound", "Foxhole State"),
        ("uses-effects-of", "inbound", "Mines"),
        ("ignores-modifiers-from", "inbound", "Deactivator"),
        ("ignores-modifiers-from", "inbound", "Sensor"),
        ("ignores-modifiers-from", "inbound", "Speculative Attack"),
        ("ignores-modifiers-from", "inbound", "Triangulated Fire"),
    }
    for target in (bs_attack, discover):
        assert (
            "imposes-modifiers-on",
            "inbound",
            "Mimetism",
        ) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in target["display_relations"]
        }


def test_mobility_environment_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def record(record_id: str) -> dict:
        kind = record_id.split(":", 1)[0]
        return next(
            candidate
            for candidate in database.composed_records_by_kind(kind)
            if candidate["id"] == record_id
        )

    aerial = record("skill:aerial")
    assert {
        (relation["type"], relation["direction"], relation["record"]["id"])
        for relation in aerial["display_relations"]
    } == {
        ("restricts-use-of", "outbound", "skill:cautious-movement"),
        ("restricts-use-of", "outbound", "skill:guard"),
        ("negates-effects-of", "outbound", "trait:boost"),
        ("prevents-state-entry", "outbound", "state:prone"),
        ("prevents-state-entry", "outbound", "state:engaged"),
    }
    assert ("restricts-use-of", "inbound", "skill:aerial") in {
        (relation["type"], relation["direction"], relation["record"]["id"])
        for relation in record("skill:guard")["display_relations"]
    }

    climbing = record("skill:climbing-plus")
    assert {
        (relation["type"], relation["direction"], relation["record"]["id"])
        for relation in climbing["display_relations"]
    } == {
        ("uses-effects-of", "outbound", "skill:climb"),
        ("applies-effects-to", "outbound", "skill:move"),
        ("applies-effects-to", "outbound", "skill:dodge"),
    }


def test_morale_behavior_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def record(record_id: str) -> dict:
        kind = record_id.split(":", 1)[0]
        return next(
            candidate
            for candidate in database.composed_records_by_kind(kind)
            if candidate["id"] == record_id
        )

    frenzy = record("skill:frenzy")
    assert {
        (relation["type"], relation["direction"], relation["record"]["id"])
        for relation in frenzy["display_relations"]
    } == {
        ("uses-effects-of", "outbound", "skill:impetuous"),
        ("uses-effects-of", "outbound", "skill:limited-cover"),
        ("cancels-state", "outbound", "state:camouflaged"),
        ("cancels-state", "outbound", "state:decoy"),
        ("cancels-state", "outbound", "state:impersonation-1"),
        ("cancels-state", "outbound", "state:impersonation-2"),
        ("cancels-state", "outbound", "state:holoecho"),
    }
    foxhole = record("state:foxhole")
    assert ("uses-effects-of", "outbound", "skill:courage") in {
        (relation["type"], relation["direction"], relation["record"]["id"])
        for relation in foxhole["display_relations"]
    }
    assert ("uses-effects-of", "inbound", "state:foxhole") in {
        (relation["type"], relation["direction"], relation["record"]["id"])
        for relation in record("skill:courage")["display_relations"]
    }


def test_rea042_published_dodge_arm_modifier_is_not_dodge_ph_bonus(
    current_rules_database: RulesDatabase,
) -> None:
    dodge = current_rules_database.composed_record("skill:dodge")
    assert dodge is not None
    effects = " ".join(dodge["facts"]["effects"])
    clarifications = " ".join(dodge["facts"]["clarifications"])
    notes = dodge["facts"]["sourceNotes"]
    assert "Dodge (ARM+3)" in effects
    assert "Unit Profile lists this modifier" in effects
    assert "[[attribute:arm|ARM]]" in effects
    assert "[[rule:saving-rolls|ARM Saving Roll]]" in effects
    assert "not conditional on failing" in effects
    assert "does not add +3 to Dodge PH" in clarifications
    assert "without the printed modifier" in clarifications
    assert "still fail to evade one" in clarifications
    assert "failed Dodge PH Roll" in notes[1]
    assert "English p. 75" in notes[0]
    assert "Spanish p. 75" in notes[0]
    assert "PDF-based wording pending official clarification" in notes[1]
    sources = {
        (ref["source_id"], ref.get("page"), ref.get("member"))
        for ref in dodge["citations"]
    }
    assert ("n5-core-v5.3-pdf", 75, None) in sources
    assert ("n5-core-v5.3-es-pdf", 75, None) in sources
    assert ("wiki-en-20260926-200832", None, "Template_Modifiers-explained") in sources
    assert ("wiki-es-20261009-211304", None, "es/Plantilla_Modifiers-explained") in sources
    assert "[[state:immobilized-a]]" in effects or "[[state:immobilized-a]]" in clarifications


def test_silent_dodge_modifier_interaction_is_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    silent = next(
        item
        for item in database.composed_records_by_kind("trait")
        if item["id"] == "trait:silent-x"
    )
    dodge = next(
        item
        for item in database.composed_records_for_army_link("skill", "dodge")
        if item["id"] == "skill:dodge"
    )

    assert ("imposes-modifiers-on", "outbound", "Dodge") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in silent["display_relations"]
    }
    assert ("imposes-modifiers-on", "inbound", "Silent (X)") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in dodge["display_relations"]
    }


def test_disposable_causes_item_specific_unloaded_state(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    disposable = next(
        item
        for item in database.composed_records_by_kind("trait")
        if item["id"] == "trait:disposable-x"
    )
    unloaded = next(
        item
        for item in database.composed_records_by_kind("state")
        if item["id"] == "state:unloaded"
    )

    assert ("causes-state", "outbound", "Unloaded State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in disposable["display_relations"]
    }
    assert ("causes-state", "inbound", "Disposable (X)") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in unloaded["display_relations"]
    }


def test_rea016_stealth_examples_and_citations_are_published(
    current_rules_database: RulesDatabase,
) -> None:
    stealth = current_rules_database.composed_record("skill:stealth")
    mines = current_rules_database.composed_record("weapon:mines")
    boost = current_rules_database.composed_record("trait:boost")
    sixth_sense = current_rules_database.composed_record("skill:sixth-sense")
    combat_instinct = current_rules_database.composed_record("skill:combat-instinct")
    peripheral = current_rules_database.composed_record("skill:peripheral")
    assert all(x is not None for x in (
        stealth, mines, boost, sixth_sense, combat_instinct, peripheral,
    ))
    assert stealth is not None and mines is not None and boost is not None
    assert sixth_sense is not None and combat_instinct is not None
    assert peripheral is not None
    mine_case, mixed, marker = stealth["facts"]["clarifications"]
    assert "Mine" in mine_case
    assert "does **not** switch off [[trait:deployable|Deployable]]" in mine_case
    assert "Trigger Area" in mines["summary"]
    assert "cannot activate other [[trait:deployable|Deployable]]" in boost["summary"]
    assert "[[skill:peripheral|Peripheral]]" in mixed
    assert "other activated Trooper independently generates" in mixed
    assert "reaction becomes [[skill:idle|Idle]]" in mixed
    assert "An ARO generated" not in mixed
    assert "must announce" in marker
    assert "Marker form" in marker
    assert "[[skill:stealth]] is not effective against the user." in " ".join(
        sixth_sense["facts"]["effects"]
    )
    assert "[[skill:stealth]] is not effective against the user." in " ".join(
        combat_instinct["facts"]["effects"]
    )
    assert "same Order" in " ".join(peripheral["facts"]["effects"])
    citations = {(c["source_id"], c.get("page")) for c in stealth["citations"]}
    assert citations >= {
        ("n5-core-v5.3-pdf", 112),
        ("n5-core-v5.3-es-pdf", 114),
        ("n5-faq-v0.1-en-pdf", 2),
        ("n5-faq-v0.1-es-pdf", 2),
    }
    assert [(r["type"], r["record_id"]) for r in stealth["relations"]] == [
        ("enables-use-of", "skill:cautious-movement")
    ]


def test_stealth_counter_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def skill_rule(slug: str, record_id: str) -> dict:
        return next(
            record
            for record in database.composed_records_for_army_link("skill", slug)
            if record["id"] == record_id
        )

    combat_instinct = skill_rule("combat-instinct", "skill:combat-instinct")
    sixth_sense = skill_rule("sixth-sense", "skill:sixth-sense")
    stealth = skill_rule("stealth", "skill:stealth")
    cautious_movement = skill_rule("cautious-movement", "skill:cautious-movement")
    surprise_attack = skill_rule("surprise-attack", "skill:surprise-attack")

    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in combat_instinct["display_relations"]
    } == {
        ("ignores-modifiers-from", "outbound", "Surprise Attack"),
        ("negates-effects-of", "outbound", "Stealth"),
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in sixth_sense["display_relations"]
    } == {
        ("modifies-rolls-for", "outbound", "Dodge"),
        ("modifies-rolls-for", "outbound", "Reset"),
        ("negates-effects-of", "outbound", "Stealth"),
    }
    stealth_relations = {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in stealth["display_relations"]
    }
    assert ("negates-effects-of", "inbound", "Combat Instinct") in stealth_relations
    assert ("negates-effects-of", "inbound", "Sixth Sense") in stealth_relations
    assert ("enables-use-of", "outbound", "Cautious Movement") in stealth_relations
    assert ("enables-use-of", "inbound", "Stealth") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in cautious_movement["display_relations"]
    }
    surprise_relations = {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in surprise_attack["display_relations"]
    }
    assert (
        "ignores-modifiers-from",
        "inbound",
        "Combat Instinct",
    ) in surprise_relations
    assert ("enables-use-of", "inbound", "Camouflaged State") in surprise_relations
    assert ("enables-use-of", "inbound", "Hidden Deployment State") in surprise_relations


def test_sensor_interactions_are_bidirectional(current_rules_database: RulesDatabase) -> None:
    database = current_rules_database

    def record(kind: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_by_kind(kind)
            if item["id"] == record_id
        )

    sensor = next(
        item
        for item in database.composed_records_for_army_link("skill", "sensor")
        if item["id"] == "skill:sensor"
    )
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in sensor["display_relations"]
    } == {
        ("ignores-modifiers-from", "outbound", "Mimetism"),
        ("modifies-rolls-for", "outbound", "Discover"),
        ("restricts-use-of", "outbound", "Camouflage"),
        ("reveals-state", "outbound", "Camouflaged State"),
        ("reveals-state", "outbound", "Hidden Deployment State"),
    }

    discover = next(
        item
        for item in database.composed_records_for_army_link("skill", "discover")
        if item["id"] == "skill:discover"
    )
    assert ("modifies-rolls-for", "inbound", "Sensor") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in discover["display_relations"]
    }

    camouflage = next(
        item
        for item in database.composed_records_for_army_link("skill", "camouflage")
        if item["id"] == "skill:camouflage"
    )
    assert ("restricts-use-of", "inbound", "Sensor") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in camouflage["display_relations"]
    }

    hidden_deployment = next(
        item
        for item in database.composed_records_for_army_link("skill", "hidden-deployment")
        if item["id"] == "skill:hidden-deployment"
    )
    assert ("enters-state", "outbound", "Hidden Deployment State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in hidden_deployment["display_relations"]
    }

    hidden_state = record("state", "state:hidden-deployment")
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in hidden_state["display_relations"]
    } == {
        ("enables-use-of", "outbound", "Surprise Attack"),
        ("enters-state", "inbound", "Hidden Deployment"),
        ("reveals-state", "inbound", "Sensor"),
    }


def test_marksmanship_counter_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    marksmanship = next(
        item
        for item in database.composed_records_for_army_link("skill", "marksmanship")
        if item["id"] == "skill:marksmanship"
    )
    msv = next(
        item
        for item in database.composed_records_for_army_link(
            "equipment", "multispectral-visor"
        )
        if item["id"] == "equipment:multispectral-visor"
    )
    albedo = next(
        item
        for item in database.composed_records_for_army_link("equipment", "albedo")
        if item["id"] == "equipment:albedo"
    )
    reflective = next(
        item
        for item in database.composed_records_by_kind("trait")
        if item["id"] == "trait:reflective"
    )

    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in albedo["display_relations"]
    } == {
        ("imposes-modifiers-on", "outbound", "Marksmanship"),
        ("imposes-modifiers-on", "outbound", "Multispectral Visor"),
        ("uses-effects-of", "inbound", "TinBot: Albedo"),
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in reflective["display_relations"]
    } == {
        ("applies-effects-to", "outbound", "Marksmanship"),
        ("applies-effects-to", "outbound", "Multispectral Visor"),
    }
    for target in (marksmanship, msv):
        assert {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in target["display_relations"]
            if relation["record"]["name"] in {"Albedo", "Reflective"}
        } == {
            ("applies-effects-to", "inbound", "Reflective"),
            ("imposes-modifiers-on", "inbound", "Albedo"),
        }

def test_natural_born_warrior_counter_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def skill_rule(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )

    natural_born_warrior = skill_rule(
        "natural-born-warrior", "skill:natural-born-warrior"
    )
    martial_arts = skill_rule("martial-arts", "skill:martial-arts")
    surprise_attack = skill_rule("surprise-attack", "skill:surprise-attack")

    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in natural_born_warrior["display_relations"]
    } == {
        ("ignores-modifiers-from", "outbound", "Martial Arts"),
        ("ignores-modifiers-from", "outbound", "Surprise Attack"),
    }
    for target in (martial_arts, surprise_attack):
        assert (
            "ignores-modifiers-from",
            "inbound",
            "Natural Born Warrior",
        ) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in target["display_relations"]
        }



def test_no_cover_override_interaction_is_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def skill_rule(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )

    no_cover = skill_rule("no-cover", "skill:no-cover")
    limited_cover = skill_rule("limited-cover", "skill:limited-cover")

    assert ("overrides-effects-of", "outbound", "Limited Cover") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in no_cover["display_relations"]
    }
    assert ("overrides-effects-of", "inbound", "No Cover") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in limited_cover["display_relations"]
    }

def test_state_recovery_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    doctor = next(
        item
        for item in database.composed_records_for_army_link("skill", "doctor")
        if item["id"] == "skill:doctor"
    )
    engineer = next(
        item
        for item in database.composed_records_for_army_link("skill", "engineer")
        if item["id"] == "skill:engineer"
    )
    paramedic = next(
        item
        for item in database.composed_records_for_army_link("skill", "paramedic")
        if item["id"] == "skill:paramedic"
    )
    tech_recovery = next(
        item
        for item in database.composed_records_for_army_link("skill", "tech-recovery")
        if item["id"] == "skill:tech-recovery"
    )
    technorganic = next(
        item
        for item in database.composed_records_for_army_link("skill", "technorganic")
        if item["id"] == "skill:technorganic"
    )
    gizmokit = next(
        item
        for item in database.composed_records_for_army_link("equipment", "gizmokit")
        if item["id"] == "equipment:gizmokit"
    )
    medikit = next(
        item
        for item in database.composed_records_for_army_link("equipment", "medikit")
        if item["id"] == "equipment:medikit"
    )
    states = {item["id"]: item for item in database.composed_records_by_kind("state")}

    assert ("cancels-state", "outbound", "Unconscious State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in doctor["display_relations"]
    }
    assert ("cancels-state", "outbound", "Targeted State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in engineer["display_relations"]
    }
    assert ("cancels-state", "inbound", "Doctor") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in states["state:unconscious"]["display_relations"]
    }
    assert ("cancels-state", "inbound", "Engineer") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in states["state:targeted"]["display_relations"]
    }
    assert ("equips-with", "outbound", "MediKit") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in paramedic["display_relations"]
    }
    assert ("equips-with", "inbound", "Paramedic") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in medikit["display_relations"]
    }
    paramedic_medikit = next(
        relation
        for relation in paramedic["display_relations"]
        if relation["type"] == "equips-with"
    )
    assert paramedic_medikit["presentation"]["label"] == "Equips with"
    assert paramedic_medikit["record"]["army_links"] == [
        {"entity": "equipment", "id": "medikit"}
    ]
    tech_recovery_gizmokit = next(
        relation
        for relation in tech_recovery["display_relations"]
        if relation["type"] == "applies-effects-to"
    )
    assert tech_recovery_gizmokit["record"]["army_links"] == [
        {"entity": "equipment", "id": "gizmokit"}
    ]
    assert ("cancels-state", "outbound", "Targeted State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in tech_recovery["display_relations"]
    }
    assert ("cancels-state", "outbound", "Unconscious State") not in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in tech_recovery["display_relations"]
    }
    assert ("cancels-state", "inbound", "Tech-Recovery") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in states["state:targeted"]["display_relations"]
    }
    assert ("applies-effects-to", "inbound", "Tech-Recovery") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in gizmokit["display_relations"]
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in technorganic["display_relations"]
        if relation["direction"] == "outbound"
    } == {
        ("applies-effects-to", "outbound", "Doctor"),
        ("applies-effects-to", "outbound", "Engineer"),
        ("applies-effects-to", "outbound", "GizmoKit"),
        ("applies-effects-to", "outbound", "MediKit"),
    }


def test_fireteam_and_scenario_support_skills_are_composed(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    records = {
        slug: next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )
        for slug, record_id in {
            "ft-master": "skill:ft-master",
            "number-2": "skill:number-2",
            "specialist-operative": "skill:specialist-operative",
            "journalist": "skill:journalist",
            "tagcom": "skill:tagcom",
        }.items()
    }

    assert records["ft-master"]["label_ids"] == ["obligatory"]
    assert "Regular" in " ".join(records["ft-master"]["facts"]["effects"])
    assert records["number-2"]["label_ids"] == ["optional"]
    assert "[[state:isolated]]" in " ".join(
        records["number-2"]["facts"]["requirements"]
    )
    assert "Specialist Troop" in " ".join(records["specialist-operative"]["facts"]["effects"])
    assert "Guts Rolls" in " ".join(records["journalist"]["facts"]["effects"])
    assert "Combat Group" in " ".join(records["tagcom"]["facts"]["effects"])
    assert all(not record.get("display_relations") for record in records.values())


def test_profile_runtime_identity_skills_are_composed(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    records = {
        slug: next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )
        for slug, record_id in {
            "g-jumper": "skill:g-jumper",
            "infinity-spec-ops": "skill:infinity-spec-ops",
            "morpho-scan": "skill:morpho-scan",
            "remdriver": "skill:remdriver",
            "transmutation": "skill:transmutation",
        }.items()
    }
    ai_motorcycle = next(
        item
        for item in database.composed_records_for_army_link("equipment", "ai-motorcycle")
        if item["id"] == "equipment:ai-motorcycle"
    )
    escape_system = next(
        item
        for item in database.composed_records_for_army_link("equipment", "escape-system")
        if item["id"] == "equipment:escape-system"
    )

    assert records["g-jumper"]["label_ids"] == ["obligatory"]
    assert "Proxies" in " ".join(records["g-jumper"]["facts"]["effects"])
    assert records["infinity-spec-ops"]["label_ids"] == ["optional"]
    assert "Enhanced Profile" in " ".join(records["infinity-spec-ops"]["facts"]["effects"])
    assert records["morpho-scan"]["label_ids"] == ["comms-attack", "no-roll", "optional"]
    assert ("imposes-modifiers-on", "outbound", "Reset") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in records["morpho-scan"]["display_relations"]
    }
    assert records["remdriver"]["facts"]["typeIds"] == ["deployment-skill"]
    assert "Null State" in " ".join(records["remdriver"]["facts"]["restrictions"])
    assert records["transmutation"]["facts"]["typeIds"] == ["automatic"]
    assert ("uses-effects-of", "inbound", "AI Motorcycle") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in records["transmutation"]["display_relations"]
    }
    assert ("uses-effects-of", "inbound", "Escape System") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in records["transmutation"]["display_relations"]
    }
    for equipment in (ai_motorcycle, escape_system):
        assert ("uses-effects-of", "outbound", "Transmutation") in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in equipment["display_relations"]
        }


def test_final_semantic_link_cleanup_is_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def record(record_id: str) -> dict:
        kind = record_id.split(":", 1)[0]
        return next(
            candidate
            for candidate in database.composed_records_by_kind(kind)
            if candidate["id"] == record_id
        )

    expected = [
        ("state:camouflaged", "restricts-use-of", "skill:place-deployable"),
        ("skill:warhorse", "negates-effects-of", "rule:loss-of-lieutenant"),
        ("skill:super-jump", "modifies-use-of", "skill:jump"),
        ("trait:perimeter", "modifies-use-of", "skill:place-deployable"),
        ("equipment:motorcycle", "prevents-state-entry", "state:prone"),
        ("skill:aerial", "prevents-state-entry", "state:prone"),
        ("skill:aerial", "prevents-state-entry", "state:engaged"),
        ("skill:warhorse", "prevents-state-entry", "state:isolated"),
        ("skill:impetuous", "prevents-state-entry", "state:prone"),
        ("skill:explode", "triggered-by-state-entry", "state:unconscious"),
        ("trait:non-lethal", "restricts-use-of", "skill:immunity"),
        ("skill:hacker", "enables-use-of", "equipment:hacking-device"),
    ]
    for source_id, relation_type, target_id in expected:
        assert (relation_type, "outbound", target_id) in {
            (relation["type"], relation["direction"], relation["record"]["id"])
            for relation in record(source_id)["display_relations"]
        }
        assert (relation_type, "inbound", source_id) in {
            (relation["type"], relation["direction"], relation["record"]["id"])
            for relation in record(target_id)["display_relations"]
        }


def test_hacker_skill_is_composed(current_rules_database: RulesDatabase) -> None:
    database = current_rules_database

    hacker = next(
        item
        for item in database.composed_records_for_army_link("skill", "hacker")
        if item["id"] == "skill:hacker"
    )

    assert hacker["label_ids"] == ["obligatory"]
    assert hacker["facts"]["typeIds"] == ["automatic"]
    effects = " ".join(hacker["facts"]["effects"])
    assert "[[equipment:hacking-device]]" in effects
    assert "Upgrade Programs" in effects
    assert "Null State" in effects
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in hacker["display_relations"]
    } == {("enables-use-of", "outbound", "Hacking Device")}


def test_damage_resilience_skills_are_composed(current_rules_database: RulesDatabase) -> None:
    database = current_rules_database

    records = {
        slug: next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )
        for slug, record_id in {
            "explode": "skill:explode",
            "exrah": "skill:exrah",
            "immunity": "skill:immunity",
            "vulnerability": "skill:vulnerability",
        }.items()
    }
    symbiomate = next(
        item
        for item in database.composed_records_for_army_link("equipment", "symbiomate")
        if item["id"] == "equipment:symbiomate"
    )

    assert records["explode"]["label_ids"] == ["attack", "obligatory"]
    assert ("enters-state", "outbound", "Dead State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in records["explode"]["display_relations"]
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in records["exrah"]["display_relations"]
        if relation["direction"] == "outbound"
    } == {
        ("enters-state", "outbound", "Dead State"),
        ("overrides-effects-of", "outbound", "Unconscious State"),
    }
    assert ("restricts-use-of", "outbound", "Immunity") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in records["vulnerability"]["display_relations"]
    }
    assert ("uses-effects-of", "outbound", "Immunity") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in symbiomate["display_relations"]
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in records["immunity"]["display_relations"]
        if relation["direction"] == "inbound"
    } >= {
        ("restricts-use-of", "inbound", "Vulnerability"),
        ("uses-effects-of", "inbound", "SymbioMate"),
    }


def test_rules_database_preserves_variant_inheritance_and_variant_links(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    current_path, current, hacking_programs = _current_core_with_hacking_programs(root)
    document = copy.deepcopy(current)
    common = {
        "kind": "skill",
        "summary": "Variant contract test.",
        "scope": {"game": "N5", "seasons": ["current"]},
        "facts": {"category": "special-skill", "typeIds": ["automatic"]},
        "labelIds": [],
        "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 76}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
    }
    document["records"].extend(
        [
            {
                **common,
                "id": "skill:variant-family-test",
                "name": "Variant Family Test",
                "armyLinks": [{"entity": "skill", "id": "variant-family-test"}],
                "variantSemantics": {"inheritance": "family"},
            },
            {
                **common,
                "id": "skill:variant-family-test-l2",
                "name": "Variant Family Test L2",
                "armyLinks": [{"entity": "skill", "id": 92020}],
                "variantSemantics": {
                    "inheritance": "source",
                    "sourceVariant": {"kind": "named", "label": "test variant"},
                },
                "relations": [
                    {"type": "variant-of", "recordId": "skill:variant-family-test"}
                ],
            },
        ]
    )
    output = tmp_path / "rules.db"
    export_rules_database([(current_path, document), hacking_programs], output)

    database = RulesDatabase(output)
    family = database.composed_records_for_army_link("skill", "variant-family-test")
    exact = database.composed_records_for_army_link("skill", 92020)

    assert family[0]["variant_semantics"] == {"inheritance": "family"}
    assert exact[0]["variant_semantics"] == {
        "inheritance": "source",
        "source_variant": {"kind": "named", "label": "test variant"},
    }
    assert exact[0]["relations"] == [
        {
            "type": "variant-of",
            "record_id": "skill:variant-family-test",
            "collection_id": "n5-core-v5.3",
        }
    ]
    assert {
        (relation["type"], relation["direction"], relation["record_id"])
        for relation in database.relations_for_record("skill:variant-family-test")
        if relation["type"] == "variant-of"
    } == {("variant-of", "inbound", "skill:variant-family-test-l2")}


def test_export_rejects_source_specific_variant_without_family_relation(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    current_path, current, hacking_programs = _current_core_with_hacking_programs(root)
    document = copy.deepcopy(current)
    document["records"].append(
        {
            "id": "skill:orphan-variant-test",
            "kind": "skill",
            "name": "Orphan Variant Test",
            "summary": "Invalid source-specific variant.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {"category": "special-skill", "typeIds": ["automatic"]},
            "labelIds": [],
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 76}],
            "composition": {"role": "definition"},
            "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            "armyLinks": [{"entity": "skill", "id": 20}],
            "variantSemantics": {
                "inheritance": "source",
                "sourceVariant": {"kind": "named", "label": "test variant"},
            },
        }
    )

    with pytest.raises(ValueError, match="requires exactly one 'variant-of' relation"):
        export_rules_database(
            [(current_path, document), hacking_programs], tmp_path / "rules.db"
        )


def test_targeted_interaction_hub_is_bidirectional(current_rules_database: RulesDatabase) -> None:
    database = current_rules_database

    def skill(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )

    forward_observer = skill("forward-observer", "skill:forward-observer")
    reset = skill("reset", "skill:reset")
    bs_attack = skill("bs-attack", "skill:bs-attack")
    cautious_movement = skill("cautious-movement", "skill:cautious-movement")
    states = {item["id"]: item for item in database.composed_records_by_kind("state")}
    targeted = states["state:targeted"]
    immobilized_b = states["state:immobilized-b"]

    assert ("causes-state", "outbound", "Targeted State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in forward_observer["display_relations"]
    }
    assert ("causes-state", "inbound", "Forward Observer") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in targeted["display_relations"]
    }
    assert ("cancels-state", "outbound", "Targeted State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in reset["display_relations"]
    }
    assert ("cancels-state", "inbound", "Reset") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in immobilized_b["display_relations"]
    }
    assert ("modifies-rolls-for", "inbound", "Targeted State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in bs_attack["display_relations"]
    }
    assert ("restricts-use-of", "inbound", "Targeted State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in cautious_movement["display_relations"]
    }


def test_state_self_recovery_relations_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def skill(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )

    dodge = skill("dodge", "skill:dodge")
    reset = skill("reset", "skill:reset")
    states = {item["id"]: item for item in database.composed_records_by_kind("state")}
    immobilized_a = states["state:immobilized-a"]
    immobilized_b = states["state:immobilized-b"]
    isolated = states["state:isolated"]

    assert ("cancels-state", "outbound", "Immobilized-A State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in dodge["display_relations"]
    }
    assert ("modifies-rolls-for", "inbound", "Immobilized-A State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in dodge["display_relations"]
    }
    assert ("cancels-state", "inbound", "Dodge") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in immobilized_a["display_relations"]
    }
    assert ("modifies-rolls-for", "outbound", "Reset") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in immobilized_b["display_relations"]
    }
    assert ("cancels-state", "outbound", "Isolated State") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in reset["display_relations"]
    }
    assert ("modifies-rolls-for", "outbound", "Reset") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in isolated["display_relations"]
    }


def test_equipment_roll_interactions_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def equipment_rule(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("equipment", slug)
            if item["id"] == record_id
        )

    def skill_rule(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )

    nanoscreen = equipment_rule("nanoscreen", "equipment:nanoscreen")
    x_visor = equipment_rule("x-visor", "equipment:x-visor")
    bs_attack = skill_rule("bs-attack", "skill:bs-attack")
    discover = skill_rule("discover", "skill:discover")
    suppressive_fire = next(
        item
        for item in database.composed_records_by_kind("skill")
        if item["id"] == "skill:suppressive-fire"
    )

    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in nanoscreen["display_relations"]
    } == {("imposes-modifiers-on", "outbound", "BS Attack")}
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in x_visor["display_relations"]
    } == {
        ("modifies-rolls-for", "outbound", "BS Attack"),
        ("modifies-rolls-for", "outbound", "Discover"),
        ("modifies-rolls-for", "outbound", "Suppressive Fire"),
    }
    assert (
        "imposes-modifiers-on",
        "inbound",
        "Nanoscreen",
    ) in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in bs_attack["display_relations"]
    }
    for target in (bs_attack, discover, suppressive_fire):
        assert (
            "modifies-rolls-for",
            "inbound",
            "X-Visor",
        ) in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in target["display_relations"]
        }


def test_second_equipment_slice_relations_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def equipment_rule(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("equipment", slug)
            if item["id"] == record_id
        )

    def skill_rule(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("skill", slug)
            if item["id"] == record_id
        )

    biometric = equipment_rule("biometric-visor", "equipment:biometric-visor")
    deactivator = equipment_rule("deactivator", "equipment:deactivator")
    cover = equipment_rule("deployable-cover", "equipment:deployable-cover")
    deployable_repeater = equipment_rule(
        "deployable-repeater", "equipment:deployable-repeater"
    )
    fastpanda = equipment_rule("fastpanda", "equipment:fastpanda")
    repeater = equipment_rule("repeater", "equipment:repeater")
    discover = skill_rule("discover", "skill:discover")
    surprise_attack = skill_rule("surprise-attack", "skill:surprise-attack")
    mimetism = skill_rule("mimetism", "skill:mimetism")
    bs_attack = skill_rule("bs-attack", "skill:bs-attack")

    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in biometric["display_relations"]
    } == {
        ("modifies-rolls-for", "outbound", "Discover"),
        ("ignores-modifiers-from", "outbound", "Surprise Attack"),
        ("cancels-state", "outbound", "Impersonation-1 State"),
    }
    assert ("modifies-rolls-for", "inbound", "Biometric Visor") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in discover["display_relations"]
    }
    assert ("ignores-modifiers-from", "inbound", "Biometric Visor") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in surprise_attack["display_relations"]
    }
    assert ("ignores-modifiers-from", "outbound", "Mimetism") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in deactivator["display_relations"]
    }
    assert ("ignores-modifiers-from", "inbound", "Deactivator") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in mimetism["display_relations"]
    }
    assert ("modifies-rolls-for", "outbound", "BS Attack") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in cover["display_relations"]
    }
    assert ("modifies-rolls-for", "inbound", "Deployable Cover") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in bs_attack["display_relations"]
    }
    for source in (deployable_repeater, fastpanda):
        assert ("uses-effects-of", "outbound", "Repeater") in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in source["display_relations"]
        }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in repeater["display_relations"]
    } == {
        ("uses-effects-of", "inbound", "Deployable Repeater"),
        ("uses-effects-of", "inbound", "FastPanda"),
        ("uses-effects-of", "inbound", "TinBot: Repeater"),
    }


def test_remaining_equipment_slice_relations_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    def equipment_rule(slug: str, record_id: str) -> dict:
        return next(
            item
            for item in database.composed_records_for_army_link("equipment", slug)
            if item["id"] == record_id
        )

    bangbomb = equipment_rule("bangbomb", "equipment:bangbomb")
    gizmokit = equipment_rule("gizmokit", "equipment:gizmokit")
    medikit = equipment_rule("medikit", "equipment:medikit")
    motorcycle = equipment_rule("motorcycle", "equipment:motorcycle")
    ai_motorcycle = equipment_rule("ai-motorcycle", "equipment:ai-motorcycle")

    assert ("modifies-rolls-for", "outbound", "Dodge") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in bangbomb["display_relations"]
    }
    for source in (gizmokit, medikit):
        assert ("cancels-state", "outbound", "Unconscious State") in {
            (relation["type"], relation["direction"], relation["record"]["name"])
            for relation in source["display_relations"]
        }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in motorcycle["display_relations"]
        if relation["direction"] == "outbound"
    } == {
        ("restricts-use-of", "outbound", "Cautious Movement"),
        ("restricts-use-of", "outbound", "Climb"),
        ("restricts-use-of", "outbound", "Jump"),
        ("prevents-state-entry", "outbound", "Prone State"),
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in ai_motorcycle["display_relations"]
        if relation["direction"] == "outbound"
    } == {
        ("uses-effects-of", "outbound", "Motorcycle"),
        ("uses-effects-of", "outbound", "Peripheral (Synchronized)"),
        ("uses-effects-of", "outbound", "Transmutation"),
    }

    tinbot_albedo = next(
        item
        for item in database.composed_records_for_army_link("equipment", 193)
        if item["id"] == "equipment:tinbot-albedo"
    )
    tinbot_discover = next(
        item
        for item in database.composed_records_for_army_link("equipment", 244)
        if item["id"] == "equipment:tinbot-discover"
    )
    tinbot_ecm = next(
        item
        for item in database.composed_records_for_army_link("equipment", 247)
        if item["id"] == "equipment:tinbot-ecm-guided"
    )
    tinbot_repeater = next(
        item
        for item in database.composed_records_for_army_link("equipment", 248)
        if item["id"] == "equipment:tinbot-repeater"
    )
    assert ("uses-effects-of", "outbound", "Albedo") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in tinbot_albedo["display_relations"]
    }
    assert ("modifies-rolls-for", "outbound", "Discover") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in tinbot_discover["display_relations"]
    }
    assert ("uses-effects-of", "outbound", "ECM") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in tinbot_ecm["display_relations"]
    }
    assert ("uses-effects-of", "outbound", "Repeater") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in tinbot_repeater["display_relations"]
    }

def test_counterintelligence_protects_owners_first_turn_command_tokens(
    current_rules_database: RulesDatabase,
) -> None:
    counterintelligence = current_rules_database.composed_record("skill:counterintelligence")
    assert counterintelligence is not None
    assert "opponent's Strategic Use" in counterintelligence["summary"]
    assert "your first Turn" in counterintelligence["summary"]

    order_removal, token_limit = counterintelligence["facts"]["effects"]
    assert "opponent uses Strategic Use to remove two Regular Orders" in order_removal
    assert "reduces the removal to one" in order_removal
    assert "more than ten Regular, Irregular, and Tactical Orders in total" in order_removal
    assert "opponent uses Strategic Use to limit your Command Token spending" in token_limit
    assert "lets you spend up to two instead" in token_limit
    assert "adversary may use" not in token_limit
    assert ("applies-effects-to", "outbound", "Command Token: Strategic Use") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in counterintelligence["display_relations"]
    }
    assert counterintelligence["citations"]


def test_command_order_skill_relations_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    database = current_rules_database

    records = {
        item["id"]: item
        for kind in ("skill", "rule", "training", "state")
        for item in database.composed_records_by_kind(kind)
    }

    chain = records["skill:chain-of-command"]
    lieutenant = records["skill:lieutenant"]
    nco = records["skill:nco"]
    tactical_awareness = records["skill:tactical-awareness"]
    loss = records["rule:loss-of-lieutenant"]
    strategic_use = records["rule:command-token-strategic-use"]
    isolated = records["state:isolated"]

    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in chain["display_relations"]
        if relation["direction"] == "outbound"
    } == {
        ("uses-effects-of", "outbound", "Lieutenant"),
        ("negates-effects-of", "outbound", "Loss of Lieutenant"),
    }
    assert ("uses-effects-of", "inbound", "Chain of Command") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in lieutenant["display_relations"]
    }
    assert ("restricts-use-of", "outbound", "NCO") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in isolated["display_relations"]
    }
    assert ("uses-effects-of", "outbound", "Tactical Order") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in tactical_awareness["display_relations"]
    }
    assert ("overrides-effects-of", "outbound", "Special Lieutenant Order") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in nco["display_relations"]
    }
    assert ("uses-effects-of", "outbound", "Irregular") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in loss["display_relations"]
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in strategic_use["display_relations"]
        if relation["direction"] == "outbound"
    } == {
        ("causes-state", "outbound", "Suppressive Fire State"),
        ("enables-use-of", "outbound", "Request Speedball"),
    }


def test_annihilation_mission_round_trips_through_existing_rules_storage(
    current_rules_database: RulesDatabase,
) -> None:
    from infinity_db.scenario_definition import parse_scenario_definition_record
    from infinity_db.scenario_mission import NumericRangeCondition

    record = current_rules_database.composed_record("scenario:annihilation")
    assert record is not None
    definition = parse_scenario_definition_record(record)
    assert definition.mission is not None
    assert [size.army_points for size in definition.mission.game_sizes] == [
        150,
        200,
        250,
        300,
        350,
        400,
    ]
    issue = definition.mission.source_issues[0]
    assert (issue.army_points, issue.objective_id, issue.status) == (
        (350,),
        "preserve-forces",
        "reviewed-resolution",
    )
    assert "85–175" in issue.description and "more than 270" in issue.description
    survival = definition.mission.objectives[1]
    ranges: list[tuple[int, int | None]] = []
    for award in survival.awards:
        if 350 not in award.army_points:
            continue
        condition = award.condition
        assert isinstance(condition, NumericRangeCondition)
        ranges.append((condition.minimum, condition.maximum))
    assert ranges == [(85, 175), (176, 270), (271, None)]
    assert (
        "[[skill:lieutenant]]"
        in record["facts"]["mission"]["objectives"][2]["awards"][0]["condition"]["text"]
    )
    assert {(citation["source_id"], citation["page"]) for citation in record["citations"]} == {
        ("n5-core-v5.3-pdf", 149),
        ("n5-core-v5.3-pdf", 150),
    }


def test_domination_mission_round_trips_scoring_geometry_and_minimum_vp(
    current_rules_database: RulesDatabase,
) -> None:
    from infinity_db.scenario_definition import parse_scenario_definition_record
    from infinity_db.scenario_mission import DominatedRegionComparison, ElementStatusCount

    record = current_rules_database.composed_record("scenario:domination")
    assert record is not None
    mission = parse_scenario_definition_record(record).mission
    assert mission is not None
    assert [size.minimum_victory_points for size in mission.game_sizes] == [38, 50, 63, 75, 88, 100]
    assert mission.game_sizes[4].swc == 6
    assert isinstance(mission.objectives[0].awards[0].condition, DominatedRegionComparison)
    assert isinstance(mission.objectives[1].awards[0].condition, ElementStatusCount)
    assert mission.objectives[0].maximum_points_per_round == 2
    assert mission.end_conditions[1].uses_minimum_victory_points
    assert mission.source_issues[0].game_size_field == "swc"
    assert {(c["source_id"], c["page"]) for c in record["citations"]} == {
        ("n5-core-v5.3-pdf", 151),
        ("n5-core-v5.3-pdf", 152),
    }
    specialist_rules = mission.rules[-1].paragraphs
    assert "skill:chain-of-command" in mission.rules[-1].specialist_skill_ids
    assert "[[skill:peripheral:plural]]" in specialist_rules[0]


def test_supplies_mission_round_trips_control_conditions_and_resolved_geometry(
    current_rules_database: RulesDatabase,
) -> None:
    from infinity_db.scenario_definition import parse_scenario_definition_record
    from infinity_db.scenario_mission import ElementStatusComparison, ElementStatusCount

    record = current_rules_database.composed_record("scenario:supplies")
    assert record is not None
    mission = parse_scenario_definition_record(record).mission
    assert mission is not None
    assert [s.swc for s in mission.game_sizes] == [3, 4, 5, 6, 7, 8]
    assert isinstance(mission.objectives[0].awards[0].condition, ElementStatusCount)
    assert isinstance(mission.objectives[1].awards[0].condition, ElementStatusComparison)
    all_boxes = mission.objectives[2].awards[0].condition
    assert isinstance(all_boxes, ElementStatusComparison) and all_boxes.comparison == "all"
    assert mission.end_conditions[1].uses_minimum_victory_points
    assert mission.source_issues == ()
    assert {(c["source_id"], c["page"]) for c in record["citations"]} == {
        ("n5-core-v5.3-pdf", 153), ("n5-core-v5.3-pdf", 154),
    }


def test_firefight_mission_round_trips_without_changing_canonical_skill_facts(
    current_rules_database: RulesDatabase,
) -> None:
    from infinity_db.curated import load_curated_document
    from infinity_db.scenario_definition import parse_scenario_definition_record
    from infinity_db.scenario_mission import MetricComparison

    record = current_rules_database.composed_record("scenario:firefight")
    assert record is not None
    mission = parse_scenario_definition_record(record).mission
    assert mission is not None
    assert [o.awards[0].objective_points for o in mission.objectives] == [2, 1, 3, 4]
    assert all(isinstance(o.awards[0].condition, MetricComparison) for o in mission.objectives)
    assert "[[skill:lieutenant:plural]]" in mission.objectives[2].name
    assert not mission.end_conditions[1].uses_minimum_victory_points
    assert {(c["source_id"], c["page"]) for c in record["citations"]} == {
        ("n5-core-v5.3-pdf", 155), ("n5-core-v5.3-pdf", 156),
    }
    rules = {r.id: " ".join(r.paragraphs) for r in mission.rules}
    assert "always Open Information" in rules["reinforced-tactical-link"]
    assert "+3 MOD" in rules["designated-landing-area"]
    core = load_curated_document(Path("data/curated/rules/n5-core-v5.3.json"))
    for identifier in ("skill:lieutenant", "skill:combat-jump"):
        source = next(r for r in core["records"] if r["id"] == identifier)
        canonical = current_rules_database.composed_record(identifier)
        assert canonical is not None and canonical["facts"] == source["facts"]


def test_scenario_publication_resolution_separates_identity_collection_and_revision(
    current_rules_database: RulesDatabase,
) -> None:
    publications = current_rules_database.scenario_publications("annihilation")
    assert len(publications) == 1
    publication = publications[0]
    assert publication["scenario_id"] == "scenario:annihilation"
    assert publication["name"] == "Annihilation"
    assert publication["collection"] == "n5-core"
    assert publication["revision"] == "5.3"
    assert publication["publication_revision"] == "n5-core-v5.3"
    assert len(publication["content_sha256"]) == 64
    assert publication["status"] == "current"
    assert publication["effective_from"] == "2026-08-10"
    assert [source["version"] for source in publication["sources"]] == ["5.3"]

    assert current_rules_database.resolve_scenario_publication("annihilation") == publication
    assert (
        current_rules_database.resolve_scenario_publication(
            "scenario:annihilation", collection="n5-core"
        )
        == publication
    )
    assert (
        current_rules_database.resolve_scenario_publication(
            "annihilation", collection="n5-core", revision="5.3"
        )
        == publication
    )


def test_scenario_publication_resolution_never_falls_back_from_explicit_selection(
    current_rules_database: RulesDatabase,
) -> None:
    assert (
        current_rules_database.resolve_scenario_publication(
            "annihilation", collection="missing-set"
        )
        is None
    )
    assert (
        current_rules_database.resolve_scenario_publication(
            "annihilation", collection="n5-core", revision="5.2"
        )
        is None
    )
    assert (
        current_rules_database.resolve_scenario_publication(
            "annihilation",
            collection="missing-set",
            revision="5.3",
        )
        is None
    )
    assert current_rules_database.resolve_scenario_publication("missing") is None

    with pytest.raises(ValueError, match="scenario collection"):
        current_rules_database.resolve_scenario_publication("annihilation", collection=" ")
    with pytest.raises(ValueError, match="scenario revision"):
        current_rules_database.resolve_scenario_publication(
            "annihilation", collection="n5-core", revision=" v5.3"
        )
    with pytest.raises(ValueError, match="requires a scenario collection"):
        current_rules_database.resolve_scenario_publication("annihilation", revision="5.3")


def test_scenario_publication_resolution_can_select_exact_historical_revision(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    core_path, core = next(
        item for item in documents if item[1]["collection"]["id"] == "n5-core-v5.3"
    )
    historical = copy.deepcopy(core)
    historical["collection"].update(
        {
            "id": "n5-core-v5.2",
            "title": "N5 Core Rules v5.2",
            "status": "historical",
            "effectiveFrom": "2026-01-01",
        }
    )
    historical["scenarioCollection"]["revision"] = "5.2"
    for source in historical["sources"]:
        if source["id"] == "n5-core-v5.3-pdf":
            source["version"] = "5.2"
            source["publishedDate"] = "2026-01-01"

    output = tmp_path / "rules.db"
    export_rules_database(
        [*documents, (core_path.with_name("n5-core-v5.2.json"), historical)],
        output,
    )
    database = RulesDatabase(output)

    current = database.resolve_scenario_publication("annihilation")
    historical_publication = database.resolve_scenario_publication(
        "annihilation", collection="n5-core", revision="5.2"
    )
    assert current is not None and current["revision"] == "5.3"
    assert current["publication_revision"] == "n5-core-v5.3"
    assert historical_publication is not None
    assert historical_publication["revision"] == "5.2"
    assert historical_publication["publication_revision"] == "n5-core-v5.2"
    assert historical_publication["status"] == "historical"
    assert historical_publication["sources"][0]["version"] == "5.2"
    assert database.resolve_scenario_publication(
        "annihilation", collection="n5-core", revision="5.2"
    ) == historical_publication


def test_ammunition_conditional_state_links_are_bidirectional(
    current_rules_database: RulesDatabase,
) -> None:
    ammunition = {
        record["id"]: record
        for record in current_rules_database.composed_records_by_kind("ammunition")
    }
    states = {
        record["id"]: record
        for record in current_rules_database.composed_records_by_kind("state")
    }
    for ammunition_id, state_id in (
        ("ammunition:em", "state:isolated"),
        ("ammunition:em", "state:immobilized-b"),
        ("ammunition:para", "state:immobilized-a"),
        ("ammunition:shock", "state:dead"),
        ("ammunition:stun", "state:stunned"),
    ):
        assert ("causes-state", "outbound", state_id) in {
            (relation["type"], relation["direction"], relation["record"]["id"])
            for relation in ammunition[ammunition_id]["display_relations"]
        }
        assert ("causes-state", "inbound", ammunition_id) in {
            (relation["type"], relation["direction"], relation["record"]["id"])
            for relation in states[state_id]["display_relations"]
        }


@pytest.mark.parametrize(
    ("record_id", "required_fragments"),
    [
        (
            "skill:doctor",
            (
                "must have VITA and be in [[state:unconscious|Unconscious State]]",
                "A failed Roll puts the target directly into [[state:dead|Dead State]]",
                "[[state:stunned|Stunned State]] may instead be canceled",
                "replacement value does not apply to a subsequent Command Token reroll",
                "Neither restriction is a general Allied-only requirement",
            ),
        ),
        (
            "skill:engineer",
            (
                "STR is required to remove Wounds by ordinary repair, but not to cancel",
                "a failed condition-cancellation Roll has no negative consequence",
                "[[state:stunned|Stunned State]], Engineer applies to STR",
                "cancellation first, then the new effect",
                "Neither restriction is a general Allied-only requirement",
            ),
        ),
        (
            "skill:intuitive-attack",
            (
                "one unmodified [[attribute:wip|WIP]] Roll",
                "do not make a second attack Roll",
                "reaction opposes that WIP Roll",
                "Critical only against that Main Target",
                "On a failed WIP Roll, do not place the weapon",
            ),
        ),
        (
            "equipment:medikit",
            (
                "target roll [[attribute:ph|PH]], not a Saving Roll",
                "any one successful target PH Roll is enough to recover",
                "only one Wound is removed in total",
            ),
        ),
        (
            "equipment:gizmokit",
            (
                "target roll [[attribute:ph|PH]], not a Saving Roll",
                "any one successful target PH Roll removes only one Wound",
                "cancel either level of [[state:unconscious|Unconscious State]]",
            ),
        ),
        (
            "trait:disposable-x",
            (
                "Burst increases consume additional charges",
                "+1 SD does not spend an extra charge",
            ),
        ),
        (
            "trait:double-shot",
            (
                "both charges must remain unspent",
                "using it expends both",
                "a legal B1 use can still consume the remaining charge",
            ),
        ),
    ],
)
def test_recovery_and_intuitive_attack_explanations_survive_rules_export(
    current_rules_database: RulesDatabase,
    record_id: str,
    required_fragments: tuple[str, ...],
) -> None:
    """N5.3 corrections must be available in published composed rules, not just JSON."""
    record = current_rules_database.composed_record(record_id)
    assert record is not None
    facts = record.get("facts") or {}
    sections = ("requirements", "effects", "restrictions")
    text = " ".join(
        [record["summary"]]
        + [part for key in sections for part in facts.get(key, [])]
    )
    for fragment in required_fragments:
        assert fragment in text
    assert any(citation["source_id"] == "n5-core-v5.3-pdf" for citation in record["citations"])


def test_rea003_published_intuitive_attack_three_resolution_examples(
    current_rules_database: RulesDatabase,
) -> None:
    record = current_rules_database.composed_record("skill:intuitive-attack")
    trait = current_rules_database.composed_record("trait:intuitive-attack")
    assert record is not None and trait is not None
    effects = " ".join(record["facts"]["effects"])
    assert "do not make a second attack Roll" in effects
    assert "Critical only against that Main Target" in effects
    examples = record["facts"]["clarifications"]
    assert len(examples) == 3
    assert "**[[state:camouflaged|CAMO]] Marker does not react:**" in examples[0]
    assert "[[rule:saving-rolls|Saving Roll]]" in examples[0]
    assert "**Opposing reactions and Criticals:**" in examples[1]
    assert "its own eligible reaction" in examples[1]
    assert "non-Critical successful Roll" in examples[1]
    assert "**[[trait:deployable|Deployable]] placement:**" in examples[2]
    assert "On failure" in examples[2] and "loses one use" in examples[2]
    assert "this specific [[skill:intuitive-attack|Intuitive Attack]] requirement" in examples[2]
    cited = {(c["source_id"], c.get("page")) for c in record["citations"]}
    assert cited >= {("n5-core-v5.3-pdf", 49), ("n5-core-v5.3-es-pdf", 48)}
    assert "[[skill:intuitive-attack:plural]]" in trait["summary"]


def test_rea002_published_doctor_recovery_and_exception_boundaries(
    current_rules_database: RulesDatabase,
) -> None:
    doctor = current_rules_database.composed_record("skill:doctor")
    nwi = current_rules_database.composed_record("skill:no-wound-incapacitation")
    technorganic = current_rules_database.composed_record("skill:technorganic")
    stunned = current_rules_database.composed_record("state:stunned")
    assert doctor is not None and nwi is not None
    assert technorganic is not None and stunned is not None
    facts = doctor["facts"]
    requirements = " ".join(facts["requirements"])
    assert "VITA" in requirements and "[[state:unconscious|Unconscious State]]" in requirements
    assert "A failed Roll puts the target directly" in " ".join(facts["effects"])
    examples = facts["clarifications"][-4:]
    assert "**Ordinary recovery example:**" in examples[0]
    assert "**[[state:stunned|Stunned]] exception:**" in examples[1]
    assert "No Wound Incapacitation" in examples[2]
    assert "[[skill:technorganic|Technorganic]]" in examples[3]
    assert "Once that Trooper is no longer" in examples[3]
    assert "[[skill:doctor]] or [[skill:engineer]]" not in " ".join(examples)
    assert "[[skill:doctor]]" in " ".join(nwi["facts"]["effects"])
    assert "[[skill:doctor]]" in " ".join(technorganic["facts"]["effects"])
    assert "[[skill:doctor]] can cancel" in " ".join(stunned["facts"]["effects"])
    assert {citation["page"] for citation in doctor["citations"] if (
        citation["source_id"] == "n5-core-v5.3-pdf" and "page" in citation
    )} >= {90, 104, 116, 170}


def test_rea001_engineer_examples_are_published_as_player_clarifications(
    current_rules_database: RulesDatabase,
) -> None:
    engineer = current_rules_database.composed_record("skill:engineer")
    targeted = current_rules_database.composed_record("state:targeted")
    stunned = current_rules_database.composed_record("state:stunned")
    assert engineer is not None and targeted is not None and stunned is not None
    clarifications = " ".join(engineer["facts"]["clarifications"])
    assert "allied VITA Trooper" in clarifications
    assert "[[state:targeted|Targeted State]]" in clarifications
    assert "failure does not inflict a Wound" in clarifications
    assert "[[skill:doctor|Doctor]]" in clarifications
    assert "This condition-specific rule" in clarifications
    assert "[[skill:engineer]] WIP Roll" in " ".join(targeted["facts"]["effects"])
    assert "[[skill:doctor]] can cancel" in " ".join(stunned["facts"]["effects"])
    assert "[[skill:engineer]] can cancel" in " ".join(stunned["facts"]["effects"])
    pages = {
        c["page"] for c in engineer["citations"]
        if c["source_id"] == "n5-core-v5.3-pdf"
    }
    assert pages >= {91, 170, 171}


@pytest.mark.parametrize(
    ("skill_id", "kit_id", "source_page"),
    [("skill:doctor", "equipment:medikit", 90),
     ("skill:engineer", "equipment:gizmokit", 91)],
)
def test_rea038_direct_recovery_contact_does_not_inherit_allied_gate(
    current_rules_database: RulesDatabase,
    skill_id: str,
    kit_id: str,
    source_page: int,
) -> None:
    direct = current_rules_database.composed_record(skill_id)
    kit = current_rules_database.composed_record(kit_id)
    servant = current_rules_database.composed_record("rule:peripheral-type:servant")
    cyberplug = current_rules_database.composed_record("rule:peripheral-type:cyberplug")
    assert direct is not None and kit is not None
    assert servant is not None and cyberplug is not None

    requirements = " ".join(direct["facts"]["requirements"])
    restrictions = " ".join(direct["facts"]["restrictions"])
    clarifications = " ".join(direct["facts"]["clarifications"])
    notes = direct["facts"]["sourceNotes"]
    assert "Silhouette contact with the target" in requirements
    assert "Allied" not in requirements
    assert "[[state:engaged|Engaged State]] cannot declare this Skill" in restrictions
    assert "already [[state:engaged|Engaged]]" in restrictions
    assert "(N5.3 p. 51)" in restrictions
    assert "direct " + direct["name"] + " Skill" in clarifications
    assert "does not print a universal Allied-only prerequisite" in clarifications
    assert f"[[{kit_id}|" in clarifications
    assert "[[rule:peripheral-type:servant|Servant]]" in clarifications
    assert "[[rule:peripheral-type:cyberplug|Cyberplug]]" in clarifications
    assert "Allied" in " ".join(kit["facts"]["requirements"])
    assert "allied Model" in " ".join(servant["facts"]["effects"])
    assert "allied target" in " ".join(cyberplug["facts"]["clarifications"])
    assert len(notes) == 1
    assert "does not itself verify a blanket permission" in notes[0]
    assert "[[state:unconscious|Unconscious]]" in notes[0]
    assert "No scoped current N5 ruling" in notes[0]
    assert {
        (ref["source_id"], ref.get("page"))
        for ref in direct["citations"]
    } >= {
        ("n5-core-v5.3-pdf", 51),
        ("n5-core-v5.3-pdf", source_page),
    }


def test_recovery_and_intuitive_attack_avoid_the_old_misleading_baselines(
    current_rules_database: RulesDatabase,
) -> None:
    doctor = current_rules_database.composed_record("skill:doctor")
    engineer = current_rules_database.composed_record("skill:engineer")
    intuitive = current_rules_database.composed_record("skill:intuitive-attack")
    assert doctor is not None and engineer is not None and intuitive is not None
    assert "friendly VITA-based" not in " ".join(doctor["facts"]["requirements"])
    assert "friendly STR-based" not in " ".join(engineer["facts"]["requirements"])
    assert "on success, the user performs a single" not in " ".join(
        intuitive["facts"]["effects"]
    )


def test_impersonation_discover_has_correct_mods_and_retry_limit(
    current_rules_database: RulesDatabase,
) -> None:
    """REA-035: IMP-2 has no special -3, but ordinary Discover MODs remain."""
    discover = current_rules_database.composed_record("skill:discover")
    imp1 = current_rules_database.composed_record("state:impersonation-1")
    imp2 = current_rules_database.composed_record("state:impersonation-2")
    biometric = current_rules_database.composed_record("equipment:biometric-visor")
    assert discover is not None
    assert imp1 is not None
    assert imp2 is not None
    assert biometric is not None

    restrictions = " ".join(discover["facts"]["restrictions"])
    assert "Discover's own Range bands" in restrictions
    assert "Cover and [[skill:mimetism|Mimetism]]" in restrictions
    assert "same Marker in one Order" in restrictions
    assert "until the next Player Turn" in restrictions
    assert "counts as a different Marker" in restrictions

    assert "no additional -3 WIP penalty" in imp2["summary"]
    assert "ordinary" in imp2["summary"]
    assert any("Cover" in rule and "Mimetism" in rule
               for rule in imp2["facts"]["clarifications"])
    assert any("After a failed" in rule and "next Player Turn" in rule
               for rule in imp2["facts"]["restrictions"])
    assert any("only to" in rule and "IMP-2" in rule
               for rule in imp1["facts"]["clarifications"])
    assert "ignores the WIP -3 MOD" in str(biometric["facts"])
    assert "impersonation-1" in str(biometric["facts"])
    assert "unmodified Discover" not in imp2["summary"]


def test_deployable_cover_has_full_placement_and_saving_cap(
    current_rules_database: RulesDatabase,
) -> None:
    """REA-036: source-listed properties and cap order are playable."""
    cover = current_rules_database.composed_record("equipment:deployable-cover")
    assert cover is not None
    effects = cover["facts"]["effects"]
    restrictions = cover["facts"]["restrictions"]
    text = " ".join(effects)
    for trait in (
        "[[trait:deployable|Deployable]]",
        "[[trait:disposable-x|Disposable (2)]]",
        "[[trait:indiscriminate|Indiscriminate]]",
        "[[trait:perimeter|Perimeter]]",
    ):
        assert trait in text
    assert "Silhouette S3" in text
    assert "completely inside the user's Zone of Control" in text
    assert "Silhouette contact" in text
    assert "ordinary partial-obscuration conditions" in text
    assert "does not stack" in text
    assert (
        "capping ARM/BTS plus all applicable Saving Roll MODs "
        "at 12 before adding the attack's PS"
    ) in text
    assert "ARM 9 plus Vitroferro +6 is capped at 12 before PS" in text
    assert "Cutting Foam" in text
    assert any("cannot end movement on" in rule for rule in restrictions)
    assert any("available on the Unit Profile" in rule for rule in restrictions)
    assert any(source["source_id"] == "n5-core-v5.3-pdf" and source["page"] == 122
               for source in cover["citations"])


def test_rea022_same_order_kit_recovery_and_disposable_burst_examples(
    current_rules_database: RulesDatabase,
) -> None:
    """N5.3 pp. 75, 123-124 and 175: distinguish hit, PH, recovery and charges."""
    for kit, page in (("medikit", 124), ("gizmokit", 123)):
        record = current_rules_database.composed_record(f"equipment:{kit}")
        assert record is not None
        effects = " ".join(record["facts"]["effects"])
        clarifications = " ".join(record["facts"]["clarifications"])
        assert "Each successful hit/use makes the target roll [[attribute:ph|PH]]" in effects
        assert "PH Rolls succeed" in effects
        assert "two target PH Rolls" in clarifications
        assert "If one succeeds and the other fails" in clarifications
        assert "only one Wound" in clarifications or "one Wound in total" in clarifications
        assert (
            "one Wound per hit" in clarifications
            or "one Wound for each hit" in clarifications
        )
        assert any(
            citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == page
            for citation in record["citations"]
        )
    remote = current_rules_database.composed_record("skill:remote-presence")
    gizmokit = current_rules_database.composed_record("equipment:gizmokit")
    assert remote is not None and gizmokit is not None
    assert "cancel either level of [[state:unconscious|Unconscious]]" in (
        " ".join(gizmokit["facts"]["clarifications"])
    )

    disposable = current_rules_database.composed_record("trait:disposable-x")
    double_shot = current_rules_database.composed_record("trait:double-shot")
    special_dice = current_rules_database.composed_record("rule:special-dice")
    assert disposable is not None and double_shot is not None and special_dice is not None
    explanation = " ".join(disposable["facts"]["clarifications"])
    assert "B1" in explanation and "B2" in explanation
    assert "spends both charges" in explanation
    assert "With only one charge left" in explanation
    assert "With +1 SD instead" in explanation
    assert "spending only the original B1 charge" in explanation
    assert "both charges must remain unspent" in double_shot["summary"]
    assert "Unloaded State" in double_shot["summary"]
    assert "the bonus is unavailable" in double_shot["summary"]
    assert "do not spend" in " ".join(special_dice["facts"]["restrictions"])
    for record, page in ((disposable, 175), (double_shot, 175)):
        assert any(
            citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == page
            for citation in record["citations"]
        )


def test_rea023_deployable_placement_geometry_and_exception_owners(
    current_rules_database: RulesDatabase,
) -> None:
    """N5.3 pp. 70, 74, 82, 102, 175 and FAQ v0.1: scoped placement rules."""
    def source(record: dict, source_id: str, page: int) -> bool:
        return any(
            cite["source_id"] == source_id and cite["page"] == page
            for cite in record["citations"]
        )

    place = current_rules_database.composed_record("skill:place-deployable")
    perimeter = current_rules_database.composed_record("trait:perimeter")
    deployable = current_rules_database.composed_record("trait:deployable")
    minelayer = current_rules_database.composed_record("skill:minelayer")
    indiscriminate = current_rules_database.composed_record("trait:indiscriminate")
    assert place is not None
    assert perimeter is not None
    assert deployable is not None
    assert minelayer is not None
    assert indiscriminate is not None
    place_effects = " ".join(place["facts"]["effects"])
    place_limits = " ".join(place["facts"]["restrictions"])
    assert "after movement, with any point along their movement path" in place_effects
    assert "In the Reactive Turn, Silhouette contact" in place_effects
    assert "fully supported on its surface" in place_effects
    assert "placement on a vertical surface is not legal" in place_effects
    assert "active only in subsequent Orders" in place_effects
    assert "Silhouette contact" in place_effects
    assert "passable-path" in place_limits
    assert "Camouflaged Marker" in place_limits
    assert "valid non-camouflaged enemy" in place_limits
    assert "[[trait:indiscriminate|Indiscriminate]]" in place_limits
    assert "another Trooper occupies the declared placement" in place_limits
    assert "If no legal location remains" in place_limits
    assert source(place, "n5-core-v5.3-pdf", 82)
    assert source(place, "n5-faq-v0.1-en-pdf", 3)

    perim_reqs = " ".join(perimeter["facts"]["requirements"])
    assert "wholly inside" in perim_reqs
    assert "Silhouette" in perim_reqs
    assert "without an impassable obstacle" in perim_reqs
    assert "a gap too narrow" in perim_reqs
    assert source(perimeter, "n5-core-v5.3-pdf", 82)

    assert "enters [[state:dead|Dead State]] immediately" in deployable["summary"]
    assert "cannot activate other Deployable Weapons" in deployable["summary"]
    assert source(deployable, "n5-core-v5.3-pdf", 175)
    assert "no otherwise valid target nearby" in (
        " ".join(indiscriminate["facts"]["clarifications"])
    )
    assert source(indiscriminate, "n5-core-v5.3-pdf", 175)

    minelayer_reqs = " ".join(minelayer["facts"]["requirements"])
    minelayer_effects = " ".join(minelayer["facts"]["effects"])
    assert "no enemy Troopers" in minelayer_reqs
    assert "item's Trigger Area" in minelayer_reqs
    assert "entire [[trait:zone-of-control-zc|Zone of Control]]" in minelayer_reqs
    assert "Trooper's permitted Deployment area" in minelayer_effects
    assert "Minelayer (X)" in minelayer_effects
    assert "Superior Deployment Roll fails" in minelayer_effects
    assert source(minelayer, "n5-core-v5.3-pdf", 102)

    turret = current_rules_database.composed_record("weapon:armed-turret")
    wildparrot = current_rules_database.composed_record("weapon:wildparrot")
    panda = current_rules_database.composed_record("equipment:fastpanda")
    repeater = current_rules_database.composed_record("equipment:deployable-repeater")
    assert turret is not None
    assert wildparrot is not None
    assert panda is not None
    assert repeater is not None
    assert "enemy **Model**, not a Marker" in turret["summary"]
    assert "Unresolved source conflict" not in turret["summary"]
    assert "one BTS/2 Saving Roll" not in turret["summary"]
    assert "one Saving Roll" in turret["facts"]["sourceNotes"][1]
    assert "two BTS/2 Saving Rolls" in turret["facts"]["sourceNotes"][1]
    assert "passable" in wildparrot["summary"]
    assert "instead of in Silhouette contact" in wildparrot["summary"]
    assert "passable path" in " ".join(panda["facts"]["effects"])
    assert "Silhouette-contact placement" in " ".join(repeater["facts"]["effects"])
    assert source(turret, "n5-core-v5.3-pdf", 70)
    assert source(wildparrot, "n5-core-v5.3-pdf", 74)


def test_reviewed_normal_da_smoke_eclipse_interactions_publish(
    current_rules_database: RulesDatabase,
) -> None:
    """N5.3 pp. 63-64, 66: canonical saves, Smoke geometry and Eclipse inheritance."""
    normal = current_rules_database.composed_record("ammunition:normal")
    da = current_rules_database.composed_record("ammunition:da")
    smoke = current_rules_database.composed_record("ammunition:smoke")
    eclipse = current_rules_database.composed_record("ammunition:eclipse")
    assert normal is not None and da is not None
    assert smoke is not None and eclipse is not None

    assert normal["facts"]["ammunitionResolution"]["rollsPerHit"] == 1
    assert normal["facts"]["ammunitionResolution"]["criticalAdditionalSavingRolls"] == 1
    assert da["facts"]["ammunitionResolution"]["rollsPerHit"] == 2
    assert da["facts"]["ammunitionResolution"]["criticalAdditionalSavingRolls"] == 1
    assert "second roll is mandatory" in da["summary"]
    assert "[[state:unconscious|Unconscious]]" in da["summary"]
    assert "three total per Critical hit" in da["summary"]
    assert any(c["source_id"] == "n5-core-v5.3-pdf" and c["page"] == 63
               for c in normal["citations"])
    assert any(c["source_id"] == "n5-core-v5.3-pdf" and c["page"] == 64
               for c in da["citations"])

    smoke_notes = " ".join(smoke["facts"]["clarifications"])
    assert "[[term:scenery-element:plural|Scenery Elements]]" in smoke_notes
    assert "horizontally and vertically" in smoke_notes
    assert smoke["facts"]["visibilityZone"]["multispectralVisor"] == "can-draw-lof"
    assert eclipse["facts"]["visibilityZone"]["multispectralVisor"] == "blocked"
    assert ("uses-effects-of", "outbound", "ammunition:smoke") in {
        (r["type"], r["direction"], r["record"]["id"])
        for r in eclipse["display_relations"]
    }
    assert ("uses-effects-of", "inbound", "ammunition:eclipse") in {
        (r["type"], r["direction"], r["record"]["id"])
        for r in smoke["display_relations"]
    }


def test_rea024_bioweapon_condition_and_viral_mine_baseline(
    current_rules_database: RulesDatabase,
) -> None:
    """Official N5.3 pp. 63-65, 174, 181: source values vs conditional effects."""
    trait = current_rules_database.composed_record("trait:bioweapon")
    mines = current_rules_database.composed_record("weapon:mines")
    normal = current_rules_database.composed_record("ammunition:normal")
    da = current_rules_database.composed_record("ammunition:da")
    shock = current_rules_database.composed_record("ammunition:shock")
    vulnerability = current_rules_database.composed_record("skill:vulnerability")
    assert trait is not None
    assert mines is not None
    assert normal is not None
    assert da is not None
    assert shock is not None
    assert vulnerability is not None

    assert "[[ammunition:da|DA]]" in trait["summary"]
    assert "[[ammunition:shock|Shock]]" in trait["summary"]
    assert "[[attribute:vita|VITA]]" in trait["summary"]
    assert "[[attribute:str|STR]]" in trait["summary"]
    notes = " ".join(trait["facts"]["clarifications"])
    assert "**Derived interaction:**" in notes
    assert "two Saving Rolls" in notes
    assert "VITA 1" in notes and "if a Saving Roll fails" in notes
    assert "[[skill:immunity|Immunity]]" in notes
    assert "Against STR, BioWeapon adds neither DA nor Shock" in notes
    assert "[[weapon-property:viral|Viral Weapon Property]]" in notes
    assert trait["facts"]["sourceIdentity"]["prefixes"] == [
        "BioWeapon (", "Bioweapon (",
    ]
    assert any(c["source_id"] == "n5-core-v5.3-pdf" and c["page"] == 174
               for c in trait["citations"])

    # The family profile must not turn a source N/BTS/1 into DA by default.
    assert mines["facts"]["variantRuleReferences"]["viral-mine"] == [
        "ammunition:normal", "trait:bioweapon",
    ]
    assert "**Viral Mine:**" in mines["summary"]
    assert "[[weapon-property:viral|shared Viral Weapon Property]]" in mines["summary"]
    assert "VITA-versus-STR" in mines["summary"]
    assert any(c["source_id"] == "n5-core-v5.3-pdf" and c["page"] == 181
               for c in mines["citations"])

    assert normal["facts"]["ammunitionResolution"]["rollsPerHit"] == 1
    assert da["facts"]["ammunitionResolution"]["rollsPerHit"] == 2
    assert shock["facts"]["ammunitionResolution"]["stateEffects"][0][
        "targetAttribute"
    ] == {"name": "VITA", "equals": 1}
    assert "weapon with Viral in its name" in " ".join(
        vulnerability["facts"]["effects"]
    )


def test_rea020_fireteam_action_ownership_and_integrity_are_distinct(
    current_rules_database: RulesDatabase,
) -> None:
    """N5.3 pp. 132-136: activation, dissent, cancellation and departure."""
    record = current_rules_database.composed_record("rule:fireteam-general")
    assert record is not None
    rules = record["facts"]["rules"]
    assert len(rules) == 13
    joined = " ".join(rules)
    assert "formation requirements" in record["summary"]
    assert "Type does not change" in joined
    for phrase in (
        "only the designated Team Leader performs it",
        "other members declare [[skill:idle|Idle]]",
        "[[skill:reset|Reset]]",
        "A Reactive Trooper chooses only one member",
        "more than half of the members who actually declare",
        "otherwise the player chooses",
        "Dissenting members leave the Fireteam",
        "dissenting Team Leader cancels the Fireteam",
        "one remaining member",
        "voluntarily cancel before an Order is spent",
        "**Individual departure:**",
        "Departure occurs when the Order or [[trait:aro|ARO]] is declared",
        "Recalculate bonuses and cancellation immediately",
        "end of the next States Phase",
        "[[skill:number-2|Number 2]]",
        "[[skill:ft-master|FT Master]]",
        "[[skill:nco|NCO]]",
        "[[skill:tactical-awareness|Tactical Awareness]]",
        "[[state:suppressive-fire|Suppressive Fire]]",
        "[[skill:peripheral|Peripheral]]",
    ):
        assert phrase in joined
    pages = {
        c["page"]
        for c in record["citations"]
        if c["source_id"] == "n5-core-v5.3-pdf" and "page" in c
    }
    assert {132, 133, 134, 135, 136} <= pages
    for ref in ("skill:number-2", "skill:ft-master", "skill:nco",
                "skill:tactical-awareness", "state:suppressive-fire"):
        assert current_rules_database.composed_record(ref) is not None


def test_rea027_flash_pulse_bilingual_publication_conflict_preserves_outcome(
    current_rules_database: RulesDatabase,
) -> None:
    """One BTS save in Army and both N5.3 PDFs; Spanish Wiki remains conflicting."""
    flash = current_rules_database.composed_record("weapon:flash-pulse")
    immunity = current_rules_database.composed_record("skill:immunity")
    stun = current_rules_database.composed_record("ammunition:stun")
    assert flash is not None
    assert immunity is not None
    assert stun is not None
    summary = flash["summary"]
    assert "one BTS Saving Roll per hit" in summary
    assert "[[ammunition:stun|Stun Ammunition]]" in summary
    assert "[[trait:non-lethal|Non-Lethal]]" in summary
    assert "[[trait:state|State: Stunned]]" in summary
    assert "Saving Roll remains BTS, not ARM" in summary
    assert "[[state:stunned|Stunned]] applies only if the BTS Saving Roll fails" in summary

    notes = " ".join(flash["facts"]["sourceNotes"])
    for term in (
        "revision 3987", "revision 3988", "2026-10-14",
        "two PB/BTS Saving Rolls", "one BTS Saving Roll",
        "pinned Army weapon 72", "p. 196", "p. 186",
        "revision 3677", "conflicting publication",
        "does not establish a superseding rules change",
    ):
        assert term in notes

    cited = {
        (entry["source_id"], entry.get("page"))
        for entry in flash["citations"]
    }
    for expected in (
        ("n5-core-v5.3-pdf", 186),
        ("n5-core-v5.3-pdf", 96),
        ("n5-core-v5.3-es-pdf", 196),
        ("n5-core-v5.3-es-pdf", 99),
        ("wiki-es-weapon-chart-oldid-3987", None),
        ("wiki-es-weapon-chart-alternatives-oldid-3988", None),
        ("wiki-es-immunity-oldid-3677", None),
        ("wiki-weapon-chart-oldid-4083", None),
    ):
        assert expected in cited
    interaction = immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"]
    case = next(item for item in interaction if
                item["when"]["weaponId"] == "weapon:flash-pulse")
    assert case["when"]["savingAttribute"] == "BTS"
    assert case["ammunitionTreatedAs"] == "ammunition:normal"
    assert set(case["survivingTraits"]) == {"trait:non-lethal", "trait:state"}
    assert case["stateEffect"] == {
        "stateId": "state:stunned", "condition": "failed-saving-roll"
    }


def test_rea030_general_faq_and_its_only_scope_stay_separate(
    current_rules_database: RulesDatabase,
) -> None:
    """FAQ v0.1: general SS/MSV1 versus ITS-only objectives (pp. 2-4)."""
    sixth = current_rules_database.composed_record("skill:sixth-sense")
    visor = current_rules_database.composed_record("equipment:multispectral-visor")
    targeted = current_rules_database.composed_record("state:targeted")
    ancillary = current_rules_database.composed_record("rule:peripheral-type:ancillary")
    curated = json.loads(
        (Path(__file__).resolve().parents[1]
         / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    scoped_records = {record["id"]: record for record in curated["records"]}
    supplies = scoped_records["rule:scenario:carrying-supply-boxes"]
    killing = scoped_records["rule:scenario:killing"]
    assert sixth is not None
    assert visor is not None
    assert targeted is not None
    assert ancillary is not None
    assert supplies is not None
    assert killing is not None

    faq_sources = {"n5-faq-v0.1-en-pdf", "n5-faq-v0.1-es-pdf"}
    for record, page in ((sixth, 2), (visor, 2), (targeted, 3), (ancillary, 4)):
        assert {
            citation["source_id"]
            for citation in record["citations"]
            if citation.get("page") == page
        } >= faq_sources

    ss_note = " ".join(sixth["facts"]["clarifications"])
    assert (
        "both [[equipment:multispectral-visor|Multispectral Visor Level 1]]"
        " and Sixth Sense"
    ) in ss_note
    assert "target of a [[skill:bs-attack|BS Attack]]" in ss_note
    assert "does not cancel other MODs" in ss_note
    msv_note = " ".join(visor["facts"]["clarifications"])
    assert "[[skill:sixth-sense|Sixth Sense]]" in msv_note
    assert "Level 1 alone still uses the listed -6 LoF MOD" in msv_note
    assert "applying a -6 MOD to Skills that require LoF" in " ".join(
        visor["facts"]["levels"][0]["effects"]
    )

    targeted_note = " ".join(targeted["facts"]["sourceNotes"])
    assert "ITS Classified Objective scoring condition" in targeted_note
    assert "not necessarily entry into [[state:targeted|Targeted State]]" in targeted_note
    assert "successful [[hacking-program:spotlight|Spotlight]] Rolls" in targeted_note
    ancillary_note = " ".join(ancillary["facts"]["clarifications"])
    assert "ITS FAQ v0.1, page 4" in ancillary_note
    assert "undeployed Ancillary is not counted as Killed" in ancillary_note
    assert "core Annihilation/Firefight is not independently established" in ancillary_note

    # The ITS FAQ does not silently change the published core missions.
    assert supplies["scope"]["scenarios"] == ["scenario:supplies"]
    assert supplies["facts"]["effects"] == [
        "Each Specialist Troop may carry at most one Supply Box.",
        "Only Models can carry Supply Boxes; Markers cannot carry them.",
        "Keep the Supply Box Token on the table even if its carrier becomes classified as Null.",
    ]
    assert killing["scope"]["scenarios"] == [
        "scenario:annihilation", "scenario:firefight",
    ]
    assert "never deployed on the table as a Model or Marker" in " ".join(
        killing["facts"]["effects"]
    )
    for record in (supplies, killing):
        assert not (faq_sources & {
            citation["sourceId"] for citation in record["citations"]
        })
        assert "sourceNotes" not in record["facts"]


def test_armed_turret_source_placement_clauses_are_published(
    current_rules_database: RulesDatabase,
) -> None:
    record = current_rules_database.composed_record('weapon:armed-turret')
    assert record is not None
    assert '[[trait:disposable-x|Disposable (1)]]' in record['summary']
    assert '[[trait:non-reloadable|Non-Reloadable]]' in record['summary']
    assert 'totally inside the deploying Trooper' in record['summary']
    assert '[[trait:zone-of-control-zc|Zone of Control]]' in record['summary']
    assert record['facts']['specialProfile']['stats'][-1] == ['S', '2']
    assert any(
        rel['type'] == 'enables-use-of'
        and rel['record_id'] == 'skill:place-deployable'
        for rel in record['relations']
    )
    assert any(
        source['source_id'] == 'n5-core-v5.3-pdf'
        and source['page'] == 70
        for source in record['citations']
    )
