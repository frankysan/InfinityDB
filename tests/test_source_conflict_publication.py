"""Protect N5.3 source disclosures and reviewed deployed-object boundaries.

The underlying rule semantics are separately source-reviewed. These regressions
protect disclosure, official-source attribution, and normal route availability
in the *tracked* published application/rules databases.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]

PROMOTED_CITATIONS = {
    "deployed-object-non-catalog-reviews.json": {
        "skill:frenzy": 93,
        "state:possessed": 169,
        "rule:command-token-strategic-use": 128,
        "skill:counterintelligence": 90,
        "skill:inspiring-leadership": 99,
        "skill:transmutation": 117,
    },
    "deployed-object-expanded-reviews.json": {
        "state:decoy": 159,
        "trait:concealed": 175,
        "skill:mnemonica": 103,
        "skill:tactical-awareness": 115,
        "skill:explode": 92,
    },
    "deployed-object-source-domain-clause-reviews.json": {
        "equipment:escape-system": 117,
        "equipment:holomask": 124,
        "equipment:holoprojector": 124,
    },
}


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/army.db",
        rules_database_path=ROOT / "data/generated/rules_n5.db",
    )


def _get(app: Any, path: str, *, query: str = "") -> tuple[int, bytes]:
    environment: dict[str, Any] = {}
    setup_testing_defaults(environment)
    environment.update(REQUEST_METHOD="GET", PATH_INFO=path, QUERY_STRING=query)
    statuses: list[int] = []

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any = None,
    ) -> None:
        statuses.append(int(status.split()[0]))

    response = app(environment, start_response)
    try:
        body = b"".join(response)
    finally:
        closer = getattr(response, "close", None)
        if closer is not None:
            closer()
    assert len(statuses) == 1
    return statuses[0], body


@pytest.mark.parametrize(
    ("catalog", "slug", "record_id", "notes", "source_ids"),
    (
        (
            "weapons", "armed-turret", "weapon:armed-turret",
            ("Unresolved Silhouette conflict", "S1", "S2"),
            {"n5-core-v5.3-pdf", "n5-core-v5.3-es-pdf"},
        ),
        (
            "skills", "dodge", "skill:dodge",
            ("failed Dodge PH Roll", "PDF-based wording pending official clarification"),
            {"n5-core-v5.3-pdf", "n5-core-v5.3-es-pdf"},
        ),
        (
            "rules", "special-dice", "rule:special-dice",
            ("Spanish N5.3 p. 140", "pending a scoped official ruling"),
            {"n5-core-v5.3-pdf", "n5-core-v5.3-es-pdf"},
        ),
        (
            "weapons", "flash-pulse", "weapon:flash-pulse",
            ("two PB/BTS Saving Rolls", "Spanish N5.3 PDF Weapon Chart"),
            {
                "n5-core-v5.3-pdf", "n5-core-v5.3-es-pdf",
                "wiki-es-weapon-chart-oldid-3987",
                "wiki-es-weapon-chart-alternatives-oldid-3988",
            },
        ),
    ),
)
def test_public_reference_keeps_unresolved_source_conflict(
    app: Any,
    catalog: str,
    slug: str,
    record_id: str,
    notes: tuple[str, ...],
    source_ids: set[str],
) -> None:
    status, body = _get(app, f"/api/{catalog}/{slug}")
    assert status == 200, (catalog, slug, status)
    payload = json.loads(body)
    record = next(item for item in payload["rules"] if item["id"] == record_id)
    source_note_items = record["facts"]["sourceNotes"]
    source_notes = " ".join(source_note_items)
    assert len(record["fact_tokens"]["sourceNotes"]) == len(source_note_items)
    for fragment in notes:
        assert fragment in source_notes, (record_id, fragment)
    assert source_ids <= {citation["source_id"] for citation in record["citations"]}

    status, page = _get(app, f"/{catalog}/{slug}")
    assert status == 200, (catalog, slug, status)
    assert b"<html" in page.lower()
    assert b"reference-detail.js" in page or b"weapon" in page.lower()


def test_fireteam_reference_keeps_both_independent_printed_conflicts(app: Any) -> None:
    status, body = _get(app, "/api/fireteams")
    assert status == 200
    reference = json.loads(body)["reference"]
    assert reference["levels"]["id"] == "rule:fireteam-level-bonuses"
    notes = " ".join(reference["levels"]["facts"]["sourceNotes"])
    assert "Unresolved Spanish Fireteam reminder" in notes
    assert "Unresolved printed Fireteam example" in notes
    assert len(reference["levels"]["fact_tokens"]["sourceNotes"]) == len(
        reference["levels"]["facts"]["sourceNotes"]
    )
    assert {"n5-core-v5.3-pdf", "n5-core-v5.3-es-pdf"} <= {
        citation["source_id"] for citation in reference["levels"]["citations"]
    }
    status, page = _get(app, "/fireteams")
    assert status == 200
    assert b"fireteams.js" in page


def test_normal_reference_scripts_render_source_notes_as_player_copy(app: Any) -> None:
    status, reference_script = _get(app, "/static/rules-reference.js")
    assert status == 200
    assert b'paragraph.className = "rules-source-note"' in reference_script
    assert b"rule.fact_tokens?.sourceNotes?.[index]" in reference_script

    status, fireteam_script = _get(app, "/static/fireteams.js")
    assert status == 200
    assert b'paragraph.className = "rules-source-note"' in fireteam_script
    assert b"levels.fact_tokens?.sourceNotes?.[index]" in fireteam_script


def test_domination_350_point_language_conflict_stays_scenario_scoped(app: Any) -> None:
    """Publish the English 6 SWC without treating Spanish 7 SWC as corrected."""
    status, body = _get(app, "/api/scenarios/domination", query="army_points=350")
    assert status == 200
    payload = json.loads(body)
    assert payload["selected_army_points"] == 350
    assert payload["setup"]["game_size"]["swc"] == 6

    issues = payload["source_issues"]
    assert len(issues) == 1
    assert issues[0]["status"] == "needs-verification"
    description = issues[0]["description"]
    assert "Spanish N5.3 Domination chart" in description
    assert "Wiki Domination revision 3264" in description
    assert "official language editions" in description

    status, page = _get(app, "/scenarios/domination")
    assert status == 200
    assert b"<html" in page.lower()
    # Scoring and SWC remain a selected scenario configuration,
    # never a global Army-profile Attribute or default game value.



def test_deployed_object_discovery_reviews_remain_source_scoped() -> None:
    """Keep the completed reviews distinct from object and carrier claims."""
    classification_pins = {
        "deployed-object-non-catalog-reviews.json": (
            "47aa0c3712da132a48d0e7a6a863904c2a8070edb6c84443934d834247063c35"
        ),
        "deployed-object-expanded-reviews.json": (
            "49d76afe9dab55fa3133b06664253eae916e5e0d30b8c68413d151740df629e9"
        ),
    }
    curated = json.loads(
        (ROOT / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    records = {record["id"]: record for record in curated["records"]}
    assert len(records) == len(curated["records"])
    reviewed_ids: set[str] = set()
    fields = ("requirements", "effects", "restrictions", "clarifications", "sourceNotes")
    caveat_pins = {
        "skill:request-speedball": ("State Tokens",),
        "rule:access-width": ("Unit carriers", "Prone Trooper"),
        "state:decoy": ("Line of Fire",),
        "state:holoecho": ("trigger Mines or CrazyKoalas",),
    }
    for name, expected_pin in classification_pins.items():
        manifest = json.loads((ROOT / "config/validation" / name).read_text(encoding="utf-8"))
        assert manifest["formatVersion"] == 1
        assert manifest["scope"].startswith("audit-only;")
        reviews = manifest["reviews"]
        ids = [review["recordId"] for review in reviews]
        assert len(ids) == len(set(ids)), name
        assert reviewed_ids.isdisjoint(ids), name
        reviewed_ids.update(ids)

        # Pin the reviewed identity/classification pairs, not JSON formatting or source anchors.
        decisions = sorted((review["recordId"], review["classification"]) for review in reviews)
        encoded = json.dumps(decisions, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        assert hashlib.sha256(encoded).hexdigest() == expected_pin, (
            f"{name}: reviewed identity/classification pairs changed"
        )
        for review in reviews:
            record_id = review["recordId"]
            record = records[record_id]
            assert record["kind"] in {"skill", "rule", "trait", "term", "state"}, record_id
            assert record["kind"] == record_id.split(":", 1)[0], record_id
            assert record["composition"]["role"] == "definition", record_id
            assert review["caveat"] and review.get("objectProfile") is None, record_id
            assert all(
                text in review["caveat"] for text in caveat_pins.get(record_id, ())
            ), record_id
            assert not {"citationStatus", "pdfExcerpt"} & review.keys(), record_id
            assert (
                review["summaryEvidence"] and review["summaryEvidence"] in record["summary"]
            ), record_id
            facts = record.get("facts") or {}
            details = "\n".join(
                text for field in fields for text in facts.get(field, []) if isinstance(text, str)
            )
            evidence = review["factsEvidence"]
            assert isinstance(evidence, list), record_id
            assert evidence or not details.strip(), record_id
            assert all(
                isinstance(text, str) and text and text in details for text in evidence
            ), record_id
            pages = {
                cite.get("page") for cite in record.get("citations", [])
                if cite.get("sourceId") == "n5-core-v5.3-pdf"
            }
            assert review["sourcePages"] and set(review["sourcePages"]) <= pages, record_id
            if record_id in PROMOTED_CITATIONS[name]:
                assert pages == {PROMOTED_CITATIONS[name][record_id]}, record_id


def test_reviewed_n53_citations_match_sources_and_rules_database() -> None:
    """Pin accepted source citations, not historical staging/promotion behavior."""
    import sqlite3

    curated_path = ROOT / "data/curated/rules/n5-core-v5.3.json"
    curated = json.loads(curated_path.read_text(encoding="utf-8"))
    records = {record["id"]: record for record in curated["records"]}
    assert len(records) == len(curated["records"])
    expected_rows = []
    for name, expected in PROMOTED_CITATIONS.items():
        path = ROOT / "config/validation" / name
        reviews = json.loads(path.read_text(encoding="utf-8"))["reviews"]
        indexed = {review["recordId"]: review for review in reviews}
        assert len(indexed) == len(reviews)
        assert set(expected) <= set(indexed)
        for record_id, page in expected.items():
            review = indexed[record_id]
            assert review["sourcePages"] == [page], record_id
            assert not {"citationStatus", "pdfExcerpt"} & review.keys(), record_id
            citation = {"sourceId": "n5-core-v5.3-pdf", "page": page}
            source_citations = records[record_id]["citations"]
            assert source_citations.count(citation) == 1, record_id
            expected_rows.append((record_id, "n5-core-v5.3-pdf", page))

    assert len(expected_rows) == 14
    ids = [row[0] for row in expected_rows]
    placeholders = ", ".join("?" for _ in ids)
    with sqlite3.connect(ROOT / "data/generated/rules_n5.db") as database:
        actual = database.execute(
            "SELECT record_id, source_id, page FROM record_citations "
            f"WHERE source_id = ? AND record_id IN ({placeholders}) "
            "ORDER BY record_id, page",
            ("n5-core-v5.3-pdf", *ids),
        ).fetchall()
    assert actual == sorted(expected_rows)
