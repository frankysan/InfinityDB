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
    with pytest.raises(ValueError, match="compatibility revision"):
        RulesDatabase(target).validate()
    # v11 is now a supported transitional schema; test an actually unknown version.
    connection.execute("PRAGMA user_version = 999")
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
    from tools import build_v10_runtime_candidate

    published: list[Path] = []
    monkeypatch.setattr(
        build_v10_runtime_candidate, "publish_checkout_runtime", published.append,
    )
    args = cli.build_parser().parse_args([
        "build-rules", str(ROOT / "data/curated/rules"),
    ])
    assert args.output is None
    assert cli.cmd_build_rules(args) == 0
    assert published == [output]
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
