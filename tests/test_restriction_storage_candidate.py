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
    pdf = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
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
    assert len(pdfs) == 12
    source_pins: dict[str, str] = {}
    for _, source in pdfs:
        assert len(source["sha256"]) == 64
        assert source_pins.setdefault(source["id"], source["sha256"]) == source["sha256"]
        path = ROOT / source["localPath"]
        if path.exists():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
    assert len(source_pins) == 6
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)
    with sqlite3.connect(output) as db:
        actual = db.execute(
            "SELECT collection_id, id, sha256 FROM sources WHERE kind='pdf' "
            "ORDER BY collection_id,id",
        ).fetchall()
    assert actual == sorted((collection, source["id"], source["sha256"])
                            for collection, source in pdfs)


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


def test_v9_cli_requires_separate_staging_output() -> None:
    from infinity_db.cli import build_parser, cmd_build_rules

    args = build_parser().parse_args([
        "build-rules", "--restrictions-manifest",
        "config/validation/restrictions-source-chart.json",
    ])
    with pytest.raises(ValueError, match="explicit staging --output"):
        cmd_build_rules(args)


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
        "build-rules", "--restrictions-manifest",
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
