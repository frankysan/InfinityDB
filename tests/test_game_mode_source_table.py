"""Source-exact N5.3 Game Modes table and independent setup reconciliation."""

from __future__ import annotations

import copy
import json
import sys

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.restriction_conditions import compile_restriction_conditions
from tools.audit_game_mode_source_table import (
    MANIFEST,
    PDF,
    PINNED,
    SETUP_MANIFEST,
    audit_game_mode_source,
    audit_published_game_setup,
    audit_source_files,
    main,
    verify_pinned_pdf,
)
from tools.audit_restrictions_source_chart import (
    CURATED as RESTRICTIONS_CURATED,
)
from tools.audit_restrictions_source_chart import (
    MANIFEST as RESTRICTIONS_MANIFEST,
)
from tools.audit_restrictions_source_chart import (
    PDF as RESTRICTIONS_PDF,
)
from tools.audit_restrictions_source_chart import (
    PUBLICATION as RESTRICTIONS_PUBLICATION,
)
from tools.audit_restrictions_source_chart import (
    audit_source_files as audit_restrictions_files,
)
from tools.audit_restrictions_source_chart import (
    main as restrictions_main,
)
from tools.audit_restrictions_source_chart import (
    project_public_restrictions,
    restrictions_audit,
    verify_published_restrictions,
)
from tools.audit_restrictions_source_chart import (
    publication_bytes as restrictions_publication_bytes,
)
from tools.audit_restrictions_source_chart import (
    verify_pinned_pdf as verify_restrictions_pdf,
)


def _inputs() -> tuple[dict, dict]:
    return (
        json.loads(MANIFEST.read_text(encoding="utf-8")),
        json.loads(SETUP_MANIFEST.read_text(encoding="utf-8")),
    )


def test_game_mode_chart_corresponds_to_independent_setup_tables() -> None:
    result = audit_source_files()
    assert result["scope"] == "recommended-game-modes-not-mandatory-scenario-rules"
    assert result["sourcePage"] == 6
    assert result["corroboratingSourcePages"] == [146, 147]
    assert result["rowCount"] == 6
    assert result["publicRuleId"] == "rule:game-modes"
    assert result["publishedRowCount"] == 6
    assert result["durationScope"] == "recommended-minutes-not-round-count"
    assert result["swcScope"] == "base-allowance-excludes-unit-specific-bonuses"
    assert result["deploymentZoneScope"] == "two-dimensional-per-player-inches"
    assert [
        (
            r["name"], r["armyPoints"], r["swc"], tuple(r["tableInches"]),
            tuple(r["deploymentZoneInches"]), r["durationMinutes"],
        )
        for r in result["rows"]
    ] == list(PINNED)
    assert len(result["gameModesSha256"]) == 64
    assert len(result["independentSetupSha256"]) == 64


def test_game_mode_chart_rejects_drift_or_scenario_overrides() -> None:
    chart, setup = _inputs()
    assert audit_game_mode_source(chart, setup)["rowCount"] == 6
    for row_index, field, substitute in (
        (0, "swc", 4),
        (1, "deploymentZoneInches", [12, 32]),
        (2, "durationMinutes", 90),
        (3, "tableInches", [32, 48]),
        (4, "armyPoints", 300),
        (5, "name", "New Game"),
    ):
        changed = copy.deepcopy(chart)
        changed["rows"][row_index][field] = substitute
        with pytest.raises(ValueError, match="chart drift"):
            audit_game_mode_source(changed, setup)
    mandatory = copy.deepcopy(chart)
    mandatory["classification"]["scope"] = "mandatory-scenario-rule"
    with pytest.raises(ValueError, match="scope drift"):
        audit_game_mode_source(mandatory, setup)
    changed_setup = copy.deepcopy(setup)
    changed_setup["rows"][0]["recommendedTableInches"] = [48, 48]
    with pytest.raises(ValueError, match="cross-check failed"):
        audit_game_mode_source(chart, changed_setup)


def test_public_game_setup_rows_match_both_manifests_and_fail_closed() -> None:
    chart, setup = _inputs()
    curated = load_curated_document(
        MANIFEST.parents[2] / "data/curated/rules/n5-core-v5.3.json"
    )
    assert audit_published_game_setup(chart, setup, curated) == {
        "publicRuleId": "rule:game-modes", "publishedRowCount": 6,
    }
    for index, field, value in (
        (0, "baseSwc", 4),
        (2, "deploymentZoneInches", [12, 32]),
        (4, "retreatThresholdVictoryPoints", 87),
        (5, "durationMinutes", 60),
    ):
        changed = copy.deepcopy(curated)
        record = next(r for r in changed["records"] if r["id"] == "rule:game-modes")
        record["facts"]["gameSetupTable"]["rows"][index][field] = value
        with pytest.raises(ValueError, match="Published Game Modes rows"):
            audit_published_game_setup(chart, setup, changed)
    changed = copy.deepcopy(curated)
    record = next(r for r in changed["records"] if r["id"] == "rule:game-modes")
    record["facts"]["gameSetupTable"]["scope"] = "mandatory-scenario"
    with pytest.raises(ValueError, match="advisory scope"):
        audit_published_game_setup(chart, setup, changed)


def test_curated_game_setup_table_rejects_malformed_rows(tmp_path) -> None:
    source = MANIFEST.parents[2] / "data/curated/rules/n5-core-v5.3.json"
    curated = load_curated_document(source)
    for mutation in ("missing-row", "swc-boolean", "wrong-rounding",
                     "missing-dimensions", "unknown-column", "wrong-scope"):
        changed = copy.deepcopy(curated)
        record = next(r for r in changed["records"] if r["id"] == "rule:game-modes")
        table = record["facts"]["gameSetupTable"]
        if mutation == "missing-row":
            table["rows"].pop()
        elif mutation == "swc-boolean":
            table["rows"][0]["baseSwc"] = True
        elif mutation == "wrong-rounding":
            table["rows"][4]["retreatThresholdVictoryPoints"] = 87
        elif mutation == "missing-dimensions":
            table["rows"][2]["tableInches"] = [48]
        elif mutation == "unknown-column":
            table["rows"][3]["extra"] = "unreviewed"
        elif mutation == "wrong-scope":
            table["scope"] = "mandatory"
        target = tmp_path / f"{mutation}.json"
        target.write_text(json.dumps(changed), encoding="utf-8")
        with pytest.raises(ValueError, match="gameSetupTable"):
            load_curated_document(target)


def test_optional_pdf_check_verifies_game_mode_rows() -> None:
    pytest.importorskip("pymupdf")
    if not PDF.is_file():
        pytest.skip("Pinned local N5.3 PDF not available")
    report = audit_source_files(pdf_path=PDF)
    assert len(report["verifiedPdfSha256"]) == 64
    chart, _ = _inputs()
    assert verify_pinned_pdf(PDF, chart) == report["verifiedPdfSha256"]
    changed = copy.deepcopy(chart)
    changed["rows"][0]["durationMinutes"] = 70
    with pytest.raises(ValueError, match="source row mismatch"):
        verify_pinned_pdf(PDF, changed)
    changed = copy.deepcopy(chart)
    changed["rows"][0]["deploymentZoneInches"] = [12, 24]
    with pytest.raises(ValueError, match="source dimensions mismatch"):
        verify_pinned_pdf(PDF, changed)


def test_game_mode_chart_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_game_mode_source_table"])
    assert main() == 0
    output = capsys.readouterr().out
    assert "Game Modes source rows: 6" in output
    assert "150 pts: Beginner Games; SWC 3; 40 minutes" in output
    assert "400 pts: Large-Scale Games; SWC 8; 120 minutes" in output
    assert "scenario-specific setup and forces take precedence" in output


def _restriction_inputs() -> tuple[dict, dict]:
    manifest = json.loads(RESTRICTIONS_MANIFEST.read_text(encoding="utf-8"))
    curated = json.loads(RESTRICTIONS_CURATED.read_text(encoding="utf-8"))
    return manifest, {row["id"]: row for row in curated["records"]}


def test_n53_restrictions_chart_six_subjects_and_fourteen_prohibitions() -> None:
    report = audit_restrictions_files()
    assert report["rowCount"] == 6
    assert report["negativeConditionCount"] == 14
    assert report["typedConditionCount"] == 14
    assert report["typedOperationKinds"] == [
        "army-role-selection", "directional-skill-movement",
        "skill-declaration", "state-entry", "terrain-traversal",
    ]
    assert report["scope"] == "source-restriction-conditions-not-live-action-legality"
    assert report["sourceOnlyTroopTypeSubjects"] == ["TAG", "VH", "REM"]
    assert len(report["missingTypedRelations"]) == 7
    assert report["automaticLegalityInference"] is False
    assert {
        (entry["subject"], entry["action"])
        for entry in report["conditionalRelationWarnings"]
    } == {
        ("Motorcycle", "upward-jump"),
        ("Irregular", "lieutenant-selection"),
    }
    assert {entry["action"] for entry in report["missingTypedRelations"]} >= {
        "enter-prone", "declare-cautious-movement", "use-ladders", "lieutenant-selection"
    }
    assert len(report["manifestSha256"]) == 64
    assert len(report["curatedSha256"]) == 64


def test_n53_seven_non_graph_restrictions_keep_source_scoped_api_and_browser_coverage(
    tmp_path,
) -> None:
    """Test explicit v9 Restrictions without assuming tracked release schema v9."""
    from infinity_db.curated import load_curated_directory
    from infinity_db.rules_database import RulesDatabase, export_rules_database
    from tools.audit_restrictions_source_chart import ROOT

    manifest, records = _restriction_inputs()
    report = restrictions_audit(manifest, records)
    missing = {(row["subject"], row["action"]) for row in report["missingTypedRelations"]}
    source_only = {"TAG", "VH", "REM"}
    assert missing == {
        ("TAG", "enter-prone"),
        ("TAG", "declare-cautious-movement"),
        ("Motorcycle", "use-ladders"),
        ("VH", "enter-prone"),
        ("VH", "declare-cautious-movement"),
        ("REM", "declare-cautious-movement"),
        ("REM", "lieutenant-selection"),
    }

    typed = {
        (item.subject, item.action): item
        for item in compile_restriction_conditions(manifest, records)
    }
    published = json.loads(RESTRICTIONS_PUBLICATION.read_text(encoding="utf-8"))
    browser = {
        (row["sourceSubject"], condition["action"]): (row, condition)
        for row in published["rows"]
        for condition in row["conditions"]
    }
    # The tracked baseline is v8; exercise the explicitly reviewed v9 schema
    # rather than treating a v8 compatibility response as a missing source row.
    staged = tmp_path / "rules-v9.db"
    export_rules_database(
        load_curated_directory(ROOT / "data/curated/rules"), staged,
        restrictions_manifest=manifest,
    )
    database = RulesDatabase(staged)
    database.validate()
    api = database.restrictions_payload()
    assert api["available"] is True
    assert api["evaluationSupported"] is False
    assert api["polarity"] == "prohibition"
    assert len(api["items"]) == 14
    api_by_key = {(item["subject"], item["action"]): item for item in api["items"]}
    assert set(api_by_key) == set(typed) == set(browser)

    for subject, action in sorted(missing):
        condition = typed[(subject, action)]
        browser_row, browser_condition = browser[(subject, action)]
        api_condition = api_by_key[(subject, action)]
        assert browser_row["ownerRecordId"] == condition.owner_record_id
        assert browser_condition["targetRecordId"] == condition.target_record_id
        assert browser_condition["scope"] == api_condition["scope"] == condition.scope
        assert browser_condition["operation"] == api_condition["operation"] == (
            condition.publication_operation()
        )
        assert api_condition["polarity"] == "prohibition"
        assert api_condition["ownerRecordId"] == condition.owner_record_id
        assert api_condition["targetRecordId"] == condition.target_record_id

        if subject in source_only:
            # Troop Types are PDF selectors, not fabricated canonical rules IDs.
            assert condition.subject_kind == "troop-type"
            assert condition.owner_record_id is None
            assert browser_row["ownerHref"] is None
            assert browser_condition["href"] is not None
            assert any(
                item["action"] == action
                for item in database.restrictions_payload(
                    subject=subject, record_id=condition.target_record_id,
                )["items"]
            )
        else:
            # Ladders are traversal terrain, not a generic Skill or relation.
            assert (subject, action) == ("Motorcycle", "use-ladders")
            assert condition.owner_record_id == "equipment:motorcycle"
            assert condition.target_record_id is None
            assert condition.operation_kind == "terrain-traversal"
            assert condition.qualifier == {"terrain": "ladders"}
            assert browser_condition["href"] is None
            assert not any(
                edge["recordId"] == "skill:use-ladders"
                for edge in records[condition.owner_record_id].get("relations", ())
            )
            assert any(
                item["action"] == action
                for item in database.restrictions_payload(
                    subject=subject, record_id=condition.owner_record_id,
                )["items"]
            )

    # No absence of a negative constraint may imply positive legality.
    unmatched = database.restrictions_payload(record_id="skill:dodge")
    assert unmatched["available"] is True
    assert unmatched["items"] == []
    assert unmatched["evaluationSupported"] is False


def test_n53_restrictions_chart_rejects_changed_scope_actions_and_relations() -> None:
    chart, records = _restriction_inputs()
    assert restrictions_audit(chart, records)["negativeConditionCount"] == 14
    for row_index, field, replacement in (
        (0, "subjectKind", "skill"),
        (1, "ownerRecordId", "skill:jump"),
        (3, "subject", "HI"),
    ):
        edited = copy.deepcopy(chart)
        edited["rows"][row_index][field] = replacement
        with pytest.raises(ValueError, match="Restrictions Chart"):
            restrictions_audit(edited, records)
    edited = copy.deepcopy(chart)
    edited["classification"]["action"] = "permission-to-act"
    with pytest.raises(ValueError, match="provenance/scope"):
        restrictions_audit(edited, records)
    edited = copy.deepcopy(chart)
    edited["rows"][1]["restrictions"][4]["scope"] = "while-mounted"
    with pytest.raises(ValueError, match="action-scope drift"):
        restrictions_audit(edited, records)
    edited = copy.deepcopy(chart)
    edited["rows"][1]["restrictions"][4]["action"] = "declare-climb"
    with pytest.raises(ValueError, match="repeated action"):
        restrictions_audit(edited, records)
    edited = copy.deepcopy(chart)
    edited["rows"][1]["restrictions"][4]["targetRecordId"] = "skill:climb"
    with pytest.raises(ValueError, match="target identity drift"):
        restrictions_audit(edited, records)
    edited = copy.deepcopy(records)
    edited["equipment:motorcycle"]["facts"]["restrictions"] = []
    with pytest.raises(ValueError, match="Motorcycle maintained restriction"):
        restrictions_audit(chart, edited)


def test_n53_typed_restrictions_preserve_source_selectors_and_operation_qualifiers() -> None:
    chart, records = _restriction_inputs()
    conditions = compile_restriction_conditions(chart, records)
    assert len(conditions) == 14
    assert {(item.subject, item.action) for item in conditions} == {
        (row["subject"], entry["action"])
        for row in chart["rows"] for entry in row["restrictions"]
    }
    assert {item.subject for item in conditions if item.owner_record_id is None} == {
        "TAG", "VH", "REM"
    }
    jump = next(item for item in conditions if item.action == "upward-jump")
    assert jump.subject == "Motorcycle"
    assert jump.owner_record_id == "equipment:motorcycle"
    assert jump.operation_kind == "directional-skill-movement"
    assert jump.scope == "while-mounted-upwards-only"
    assert jump.qualifier == {"direction": "upward"}
    assert jump.target_record_id == "skill:jump"

    ladders = next(item for item in conditions if item.action == "use-ladders")
    assert ladders.operation_kind == "terrain-traversal"
    assert ladders.qualifier == {"terrain": "ladders"}
    assert ladders.target_record_id is None
    lieutenant = [item for item in conditions if item.action == "lieutenant-selection"]
    assert len(lieutenant) == 2
    assert {item.subject for item in lieutenant} == {"REM", "Irregular"}
    assert all(
        item.operation_kind == "army-role-selection"
        and item.qualifier == {"role": "lieutenant"}
        and item.scope == "army-selection-only"
        for item in lieutenant
    )
    assert all(item.operation_kind != "skill-declaration" for item in lieutenant)
    assert all(
        item.operation_kind == "state-entry"
        for item in conditions if item.action == "enter-prone"
    )


def test_n53_typed_restrictions_fail_closed_on_scope_selector_or_permission() -> None:
    chart, records = _restriction_inputs()
    for subject_index, restriction_index, property_name, changed_value in (
        (1, 4, "scope", "while-mounted"),
        (1, 4, "targetRecordId", "skill:climb"),
        (1, 3, "targetRecordId", "skill:climb"),
        (5, 0, "scope", "all"),
        (4, 1, "action", "declare-climb"),
    ):
        altered = copy.deepcopy(chart)
        altered["rows"][subject_index]["restrictions"][restriction_index][
            property_name
        ] = changed_value
        with pytest.raises(ValueError, match="Restrictions model"):
            compile_restriction_conditions(altered, records)
    altered = copy.deepcopy(chart)
    altered["classification"]["action"] = "positive-permission"
    with pytest.raises(ValueError, match="negative-only"):
        compile_restriction_conditions(altered, records)
    altered = copy.deepcopy(chart)
    altered["rows"][0]["ownerRecordId"] = "skill:cautious-movement"
    with pytest.raises(ValueError, match="source identity drift"):
        compile_restriction_conditions(altered, records)
    altered_records = dict(records)
    del altered_records["skill:lieutenant"]
    with pytest.raises(ValueError, match="missing target"):
        compile_restriction_conditions(chart, altered_records)
    altered_records = copy.deepcopy(records)
    altered_records["skill:jump"]["kind"] = "state"
    with pytest.raises(ValueError, match="invalid target kind"):
        compile_restriction_conditions(chart, altered_records)
    altered_records = copy.deepcopy(records)
    altered_records["equipment:motorcycle"]["kind"] = "skill"
    with pytest.raises(ValueError, match="invalid owner kind"):
        compile_restriction_conditions(chart, altered_records)


def test_n53_restrictions_optional_pinned_pdf_exact_six_lines() -> None:
    pytest.importorskip("pymupdf")
    if not RESTRICTIONS_PDF.is_file():
        pytest.skip("Pinned N5.3 PDF unavailable")
    report = audit_restrictions_files(pdf_path=RESTRICTIONS_PDF)
    assert report["verifiedPdfSha256"] == (
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    )
    chart, _ = _restriction_inputs()
    edited = copy.deepcopy(chart)
    edited["rows"][1]["sourceText"] = edited["rows"][1]["sourceText"].replace(
        "an upwards Jump", "any Jump",
    )
    with pytest.raises(ValueError, match="printed line mismatch"):
        verify_restrictions_pdf(RESTRICTIONS_PDF, edited)


def test_n53_restrictions_chart_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["audit_restrictions_source_chart"])
    assert restrictions_main() == 0
    output = capsys.readouterr().out
    assert "6 rows, 14 negative conditions" in output
    assert "Source-only: no action-legality" in output


def test_published_restrictions_reference_is_exact_source_projection() -> None:
    manifest, records = _restriction_inputs()
    published = json.loads(RESTRICTIONS_PUBLICATION.read_text(encoding="utf-8"))
    expected = project_public_restrictions(manifest, records)
    assert published == expected
    assert RESTRICTIONS_PUBLICATION.read_bytes() == restrictions_publication_bytes(expected)
    assert len(verify_published_restrictions(manifest, records, RESTRICTIONS_PUBLICATION)) == 64
    assert published["scope"] == "reviewed-negative-conditions-not-action-legality"
    assert len(published["rows"]) == 6
    assert sum(len(item["conditions"]) for item in published["rows"]) == 14

    motorcycle = published["rows"][1]
    assert motorcycle["ownerHref"] == "/equipment/motorcycle"
    assert motorcycle["ownerRecordId"] == "equipment:motorcycle"
    assert {item["action"] for item in motorcycle["conditions"]} == {
        "enter-prone", "declare-cautious-movement", "declare-climb",
        "use-ladders", "upward-jump",
    }
    jump = motorcycle["conditions"][4]
    assert jump["scope"] == "while-mounted-upwards-only"
    assert "horizontal/downward Jump" in jump["note"]
    assert jump["href"] == "/skills/jump"
    assert jump["targetRecordId"] == "skill:jump"
    assert jump["operation"] == {
        "kind": "directional-skill-movement",
        "qualifier": {"direction": "upward"},
    }
    assert motorcycle["conditions"][3]["operation"] == {
        "kind": "terrain-traversal", "qualifier": {"terrain": "ladders"},
    }
    assert motorcycle["conditions"][3]["href"] is None
    irregular = published["rows"][-1]
    assert irregular["ownerHref"] is None
    assert irregular["ownerRecordId"] == "training:irregular"
    assert irregular["conditions"][0]["targetRecordId"] == "skill:lieutenant"
    assert irregular["conditions"][0]["operation"] == {
        "kind": "army-role-selection", "qualifier": {"role": "lieutenant"},
    }
    assert irregular["conditions"][0]["scope"] == "army-selection-only"
    assert "not a ban on using" in irregular["conditions"][0]["note"]
    for row in published["rows"]:
        if row["category"] == "Troop Type":
            assert row["subjectKind"] == "troop-type"
            assert row["ownerHref"] is None
            assert row["ownerRecordId"] is None

    altered = copy.deepcopy(manifest)
    altered["rows"][1]["restrictions"][4]["scope"] = "while-mounted"
    with pytest.raises(ValueError, match="action-scope drift"):
        project_public_restrictions(altered, records)
    assert audit_restrictions_files(
        publication_path=RESTRICTIONS_PUBLICATION,
    )["publishedReferenceSha256"]


def test_restrictions_reference_is_served_from_normal_rules_catalog() -> None:
    from wsgiref.util import setup_testing_defaults

    from infinity_db.web import create_app
    from tools.audit_restrictions_source_chart import ROOT

    app = create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )

    def get(path: str) -> tuple[int, dict[str, str], bytes]:
        environ: dict[str, object] = {}
        setup_testing_defaults(environ)
        environ["PATH_INFO"] = path
        status_code = 0
        response_headers: dict[str, str] = {}

        def respond(status: str, headers: list[tuple[str, str]], exc_info=None) -> None:
            nonlocal status_code, response_headers
            status_code = int(status.split()[0])
            response_headers = dict(headers)

        result = app(environ, respond)
        try:
            body = b"".join(result)
        finally:
            close = getattr(result, "close", None)
            if close:
                close()
        return status_code, response_headers, body

    status, headers, body = get("/static/restrictions-reference.json")
    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    assert body == RESTRICTIONS_PUBLICATION.read_bytes()
    assert json.loads(body)["rows"][1]["conditions"][4]["action"] == "upward-jump"
    status, _, body = get("/rules")
    assert status == 200
    assert b'data-catalog="rules"' in body
    status, _, script = get("/static/reference-catalog.js")
    assert status == 200
    assert b'getRestrictionsReference(pageController.signal)' in script
    assert b'anchor.href = "/rules#restrictions"' in script
    status, _, script = get("/static/restrictions-reference.js")
    assert status == 200
    assert b'Other rules may also restrict' not in script
    assert b'not a complete list of legal actions' in script
    assert b'linkOrText(condition.label, condition.href)' in script


def test_restrictions_chart_normal_chromium_at_three_widths(
    chromium_test_slot: None,
) -> None:
    """Check source-scoped labels, navigable anchors, and actual DOM at mobile widths."""
    from socketserver import ThreadingMixIn
    from threading import Thread
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

    playwright = pytest.importorskip("playwright.sync_api")
    from infinity_db.web import create_app
    from tools.audit_restrictions_source_chart import ROOT

    app = create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )

    class ThreadedServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = make_server(
        "127.0.0.1", 0, app,
        server_class=ThreadedServer, handler_class=QuietHandler,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as driver:
            try:
                browser = driver.chromium.launch(headless=True)
            except Exception as exc:
                if "Executable doesn't exist" in str(exc):
                    pytest.skip(f"Chromium unavailable: {exc}")
                raise
            try:
                for width in (1440, 390, 320):
                    page = browser.new_page(viewport={"width": width, "height": 844})
                    errors: list[str] = []
                    page.on("pageerror", lambda exc, sink=errors: sink.append(str(exc)))
                    page.goto(
                        f"http://127.0.0.1:{server.server_port}/rules#restrictions",
                        wait_until="domcontentloaded",
                    )
                    section = page.locator("#restrictions")
                    section.wait_for(state="visible", timeout=15000)
                    assert page.locator("#restrictions .restrictions-subject").count() == 6
                    assert section.locator("li[data-action]").count() == 14
                    assert page.locator(
                        "#restriction-motorcycle li[data-action='upward-jump']"
                    ).get_attribute("data-scope") == "while-mounted-upwards-only"
                    assert page.locator(
                        "#restriction-motorcycle-upward-jump"
                    ).get_attribute("data-operation-kind") == "directional-skill-movement"
                    assert page.locator(
                        "#restriction-motorcycle-use-ladders"
                    ).get_attribute("data-operation-kind") == "terrain-traversal"
                    assert page.locator(
                        "#restriction-motorcycle li[data-action='upward-jump']"
                    ).inner_text().find("horizontal/downward Jump") >= 0
                    assert page.locator(
                        "#restriction-irregular li[data-action='lieutenant-selection']"
                    ).get_attribute("data-scope") == "army-selection-only"
                    assert page.locator(
                        "#restriction-irregular-lieutenant-selection"
                    ).get_attribute("data-operation-kind") == "army-role-selection"
                    assert page.locator(
                        "#restriction-motorcycle li[data-action='use-ladders'] a"
                    ).count() == 0
                    assert page.locator("#restriction-tag h3 a").count() == 0
                    assert page.locator(
                        "#restriction-motorcycle h3 a[href='/equipment/motorcycle']"
                    ).count() == 1
                    assert page.locator(
                        "#restrictions .detail-source a"
                        "[href='https://experience.corvusbelli.com/en/infinity/resources']"
                    ).count() == 1
                    assert page.locator(
                        "a[href='/rules#restrictions']"
                    ).is_visible()
                    assert not page.evaluate(
                        "() => document.documentElement.scrollWidth > innerWidth + 1"
                    ), width
                    assert errors == [], errors

                    reverse_cases = (
                        ("/equipment/motorcycle", "motorcycle", "upward-jump", 5),
                        ("/skills/aerial", "aerial", "enter-prone", 2),
                        ("/skills/cautious-movement", "rem", "declare-cautious-movement", 5),
                        ("/skills/climb", "motorcycle", "declare-climb", 1),
                        ("/skills/jump", "motorcycle", "upward-jump", 1),
                        ("/skills/lieutenant", "irregular", "lieutenant-selection", 2),
                        ("/states/prone", "tag", "enter-prone", 4),
                    )
                    for route, subject, action, count in reverse_cases:
                        page.goto(
                            f"http://127.0.0.1:{server.server_port}{route}",
                            wait_until="domcontentloaded",
                        )
                        context = page.locator(".restrictions-context")
                        context.wait_for(state="visible", timeout=15000)
                        assert context.locator("li").count() == count, (width, route)
                        anchor = context.locator(
                            f"a[href='/rules#restriction-{subject}-{action}']"
                        )
                        assert anchor.count() == 1, (width, route)
                        if route.endswith("/jump") and width == 390:
                            anchor.click()
                            destination = page.locator("#restriction-motorcycle-upward-jump")
                            destination.wait_for(state="visible", timeout=15000)
                            assert page.url.endswith(
                                "/rules#restriction-motorcycle-upward-jump"
                            )
                            assert destination.get_attribute(
                                "data-scope"
                            ) == "while-mounted-upwards-only"
                            # Restore the individual Skill page before its context checks.
                            page.goto(
                                f"http://127.0.0.1:{server.server_port}{route}",
                                wait_until="domcontentloaded",
                            )
                            context = page.locator(".restrictions-context")
                            context.wait_for(state="visible", timeout=15000)
                        if route.endswith("/jump"):
                            assert context.locator("li").first.get_attribute(
                                "data-scope"
                            ) == "while-mounted-upwards-only"
                            assert "horizontal/downward Jump" in context.inner_text()
                        if route.endswith("/lieutenant"):
                            assert all(
                                scope == "army-selection-only"
                                for scope in context.locator("li").evaluate_all(
                                    "(items) => items.map((item) => item.dataset.scope)"
                                )
                            )
                        assert not page.evaluate(
                            "() => document.documentElement.scrollWidth > innerWidth + 1"
                        ), (width, route)
                    page.goto(
                        f"http://127.0.0.1:{server.server_port}/skills/dodge",
                        wait_until="domcontentloaded",
                    )
                    page.locator("#skill-content").wait_for(state="visible")
                    assert page.locator(".restrictions-context").count() == 0
                    assert errors == [], errors
                    page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
