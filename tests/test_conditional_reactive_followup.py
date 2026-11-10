"""V1S-030: bounded follow-up declarations/AROs, not a game-legality engine."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.database import Database
from infinity_db.declaration_matrix import core_declaration_matrix
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/validation/conditional-reactive-followup-v1.json"
CORE = ROOT / "data/curated/rules/n5-core-v5.3.json"
ARMY_DB = ROOT / "data/generated/army.db"
RULES_DB = ROOT / "data/generated/rules_n5.db"
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
# Exact review owners and depth; heading evidence must not become
# purported full printed-clause proof by editing the manifest.
EXPECTED = {
    "cautious-endpoints": ("skill:cautious-movement", "selected-clause"),
    "climbing-plus-first": ("skill:climbing-plus", "selected-clause"),
    "super-jump-first": ("skill:super-jump", "selected-clause"),
    "neurocinetics-reactive": ("skill:neurocinetics", "selected-clause"),
    "total-reaction-one-target": ("skill:total-reaction", "selected-clause"),
    "camouflaged-delay": ("state:camouflaged", "heading-and-curated-clause"),
    "impersonation-delay": ("state:impersonation-1", "heading-and-curated-clause"),
    "suppressive-fire-aro": ("state:suppressive-fire", "selected-clause"),
    "g-jumper-one-proxy": ("skill:g-jumper", "heading-and-curated-clause"),
    "peripheral-shared-skill": ("skill:peripheral", "heading-and-curated-clause"),
    "coordinated-target": ("rule:coordinated-orders", "heading-and-curated-clause"),
    "fireteam-aro-consensus": ("rule:fireteam-general", "heading-and-curated-clause"),
}


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _review_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Fail closed on missing or broadened selection and on curated/database drift."""
    if (
        manifest.get("format") !=
        "InfinityDB V1S-030 conditional declaration and reactive scope evidence"
        or manifest.get("formatVersion") != 1
        or manifest.get("scope") != (
            "selected-follow-up-examples-not-global-aro-legality-or-whole-record-acceptance"
        )
        or manifest.get("reviewedOn") != "2026-11-04"
        or manifest.get("priorReview") != (
            "config/validation/conditional-declaration-evidence-v1.json"
        )
        or manifest.get("source") != {
            "id": "n5-core-v5.3-pdf",
            "path": "data/pdf/rules/n5-rules-v5.3-en.pdf",
            "sha256": PIN,
        }
    ):
        raise ValueError("V1S-030 scope or source pin changed")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != len(EXPECTED):
        raise ValueError("V1S-030 reviewed cases count changed")
    if not all(isinstance(item, dict) for item in entries):
        raise ValueError("V1S-030 reviewed entry is not an object")
    keys = [item.get("key") for item in entries]
    if len(set(keys)) != len(keys) or set(keys) != set(EXPECTED):
        raise ValueError("V1S-030 reviewed case identities changed")

    core = {
        record["id"]: record
        for record in load_curated_document(CORE)["records"]
    }
    published = RulesDatabase(RULES_DB)
    result = []
    for item in entries:
        if (item.get("recordId"), item.get("sourceEvidence")) != EXPECTED[item["key"]]:
            raise ValueError(f"V1S-030 source owner/evidence category drift: {item['key']}")
        record_id = item["recordId"]
        record = core.get(record_id)
        stored = published.composed_record(record_id)
        if not record or not stored:
            raise ValueError(f"V1S-030 reviewed record missing: {record_id}")
        if record["composition"]["role"] != "definition":
            raise ValueError(f"V1S-030 non-definition record: {record_id}")
        field = item["field"]
        if field not in ("effects", "restrictions", "clarifications", "rules"):
            raise ValueError(f"V1S-030 invalid fact field: {record_id}")
        needle = item["factNeedle"]
        if not isinstance(needle, str) or len(needle) < 25:
            raise ValueError(f"V1S-030 missing reviewed fact: {record_id}")
        clauses = record.get("facts", {}).get(field, [])
        stored_clauses = stored.get("facts", {}).get(field, [])
        if (
            not isinstance(clauses, list)
            or not any(isinstance(clause, str) and needle in clause for clause in clauses)
            or not any(
                isinstance(clause, str) and needle in clause for clause in stored_clauses
            )
        ):
            raise ValueError(f"V1S-030 curated/published clause drift: {record_id}")
        page = item["page"]
        if type(page) is not int or page < 1 or page > 250:
            raise ValueError(f"V1S-030 invalid source page: {record_id}")
        if not any(
            c.get("sourceId") == manifest["source"]["id"] and c.get("page") == page
            for c in record.get("citations", ())
        ) or not any(
            c.get("source_id") == manifest["source"]["id"] and c.get("page") == page
            for c in stored.get("citations", ())
        ):
            raise ValueError(f"V1S-030 source citation drift: {record_id}")
        if (
            item.get("sourceEvidence") not in (
                "selected-clause", "heading-and-curated-clause"
            )
            or item.get("disposition") != "selected-source-and-publication-evidence-only"
            or not isinstance(item.get("pdfNeedle"), str)
            or len(item["pdfNeedle"]) < 6
        ):
            raise ValueError(f"V1S-030 source evidence scope drift: {record_id}")
        result.append(item)
    if len({item["recordId"] for item in result}) != len(result):
        raise ValueError("V1S-030 source record duplicated")
    return result


def _get(app: Any, path: str) -> tuple[str, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []
    response = app(
        environ,
        lambda status, _headers, _exc_info=None: statuses.append(status),
    )
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    return statuses[0], body


def _routes(identifier: str) -> tuple[str, str]:
    kind, slug = identifier.split(":", 1)
    if identifier == "rule:fireteam-general":
        return "/api/fireteams", "/fireteams"
    collection = {"skill": "skills", "state": "states", "rule": "rules"}[kind]
    return f"/api/{collection}/{slug}", f"/{collection}/{slug}"


def test_followup_reactive_clauses_match_curated_and_published_api() -> None:
    entries = _review_rows(_manifest())
    assert len(entries) == 12
    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    for item in entries:
        api, detail = _routes(item["recordId"])
        status, body = _get(app, api)
        assert status == "200 OK", api
        payload = json.loads(body)
        record = (
            payload["reference"]["general"] if api == "/api/fireteams"
            else payload["rules"][0]
        )
        assert record["id"] == item["recordId"], api
        assert any(item["factNeedle"] in clause for clause in record["facts"][item["field"]])
        status, html = _get(app, detail)
        assert status == "200 OK" and b"<html" in html.lower(), detail


def test_followup_reactive_clauses_retain_exact_pinned_source_pages() -> None:
    entries = _review_rows(_manifest())
    pdf = ROOT / _manifest()["source"]["path"]
    if not pdf.is_file():
        pytest.skip("Pinned N5.3 English source PDF unavailable")
    pymupdf = pytest.importorskip("pymupdf")
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == PIN
    with pymupdf.open(pdf) as document:
        for item in entries:
            text = " ".join(document[item["page"] - 1].get_text().split()).casefold()
            expected = " ".join(item["pdfNeedle"].split()).casefold()
            assert expected in text, (item["key"], item["page"])
    # Heading-only checks confirm source location, not independent adjudication
    # of the selected authored clause. Those cases remain clearly labelled.


def test_followup_reactive_review_fails_closed_on_scope_and_fact_drift() -> None:
    original = _manifest()
    changes = (
        ("missing", lambda data: data["entries"].pop()),
        ("duplicate", lambda data: data["entries"][0].update(
            key=data["entries"][1]["key"]
        )),
        ("invented", lambda data: data["entries"][0].update(
            factNeedle="invented permission bypassing ordinary reaction eligibility"
        )),
        ("wrong-page", lambda data: data["entries"][0].update(page=250)),
        ("wrong-owner", lambda data: data["entries"][0].update(
            recordId="skill:missing-source-owner"
        )),
        ("broadened", lambda data: data.update(scope="all-aro-legality-approved")),
        ("wrong-source", lambda data: data["source"].update(sha256="0" * 64)),
        ("wrong-kind", lambda data: data["entries"][0].update(field="summary")),
        ("wrong-review", lambda data: data["entries"][0].update(
            sourceEvidence="full-record-accepted"
        )),
    )
    for _name, mutate in changes:
        changed = deepcopy(original)
        mutate(changed)
        with pytest.raises(ValueError):
            _review_rows(changed)


def test_declaration_matrix_does_not_claim_reactive_eligibility() -> None:
    _review_rows(_manifest())
    projected = core_declaration_matrix(Database(ARMY_DB), RulesDatabase(RULES_DB))
    assert projected["legalityEvaluation"] is False
    assert projected["scope"] == "n5-core-current-unscoped"
    referenced = {entry["record_id"] for group in projected["sections"]
                  for entry in group["items"]}
    # Automatic Skills, game States, and general Rules are not newly
    # declarable actions merely because a selected reactive exception exists.
    assert not referenced.intersection({
        "skill:climbing-plus", "skill:super-jump", "skill:neurocinetics",
        "skill:total-reaction", "skill:peripheral", "skill:g-jumper",
        "state:camouflaged", "state:impersonation-1", "state:suppressive-fire",
        "rule:coordinated-orders", "rule:fireteam-general",
    })
