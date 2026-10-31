"""Ensure unresolved N5.3 source conflicts reach public reference surfaces.

The underlying rule semantics are separately source-reviewed. These regressions
protect disclosure, official-source attribution, and normal route availability
in the *tracked* published application/rules databases.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/infinity.db",
        rules_database_path=ROOT / "data/generated/rules.db",
    )


def _get(app: Any, path: str) -> tuple[int, bytes]:
    environment: dict[str, Any] = {}
    setup_testing_defaults(environment)
    environment.update(REQUEST_METHOD="GET", PATH_INFO=path)
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
