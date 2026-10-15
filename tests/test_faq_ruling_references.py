"""Cross-collection FAQ topic/supersession safety; synthetic test rulings only."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database


@pytest.fixture(scope="module")
def base_documents() -> list[tuple[Path, dict]]:
    return load_curated_directory(Path("data/curated"))


def _ruling(
    ruling_id: str,
    *,
    start: str = "2026-09-01",
    end: str | None = None,
    revision: str = "5.3",
    season: dict[str, str] | None = None,
    scenario_ids: list[str] | None = None,
    supersedes: list[str] | None = None,
) -> dict:
    scope: dict[str, Any] = {"rulesRevision": revision, "effectiveFrom": start}
    if end:
        scope["effectiveUntil"] = end
    if season:
        scope["season"] = season
    if scenario_ids:
        scope["scenarioIds"] = scenario_ids
    return {
        "id": ruling_id,
        "kind": "faq-ruling",
        "name": "Synthetic FAQ case",
        "summary": "Fixture only, not a verified or published ruling.",
        "scope": {"game": "N5", "seasons": ["current"]},
        "citations": [{"sourceId": "n5-faq-v0.1-en-pdf", "page": 2}],
        "composition": {"role": "definition"},
        "review": {"status": "draft", "reviewedOn": "2026-10-15"},
        "facts": {
            "question": "Is this a test question?",
            "answer": "Yes, synthetic only.",
            "topicIds": ["skill:camouflage"],
            "applicability": [scope],
            "originalPublication": {
                "collectionId": "n5-faq-v0.1",
                "sourceId": "n5-faq-v0.1-en-pdf",
                "version": "0.1",
                "publishedDate": "2026-09-01",
                "page": 2,
            },
            "selectedCitation": {"sourceId": "n5-faq-v0.1-en-pdf", "page": 2},
            "selectionReason": "Explicit synthetic selection for test.",
            "conflictingCitations": [],
            "supersedes": supersedes or [],
        },
    }


def _fixture(
    base: list[tuple[Path, dict]],
    records: list[dict],
    *,
    history: list[dict] | None = None,
) -> list[tuple[Path, dict]]:
    current_path, current = next(
        (path, doc) for path, doc in base if doc["collection"]["id"] == "n5-core-v5.3"
    )
    faq = deepcopy(current)
    faq.pop("scenarioCollection", None)
    faq.pop("scenarioComponents", None)
    faq["collection"].update({
        "id": "n5-faq-v0.1",
        "title": "Synthetic current FAQ",
        "domain": "faq",
        "effectiveFrom": "2026-09-01",
    })
    faq["records"] = records
    faq["labels"] = []
    faq["skillTypes"] = []
    docs = [*base, (current_path.parent / "synthetic-faq.json", faq)]
    if history is not None:
        old = deepcopy(faq)
        old["collection"].update(
            id="n5-faq-historical",
            title="Synthetic FAQ history",
            status="superseded",
            effectiveFrom="2026-08-01",
        )
        old["records"] = history
        docs.append((current_path.parent / "synthetic-faq-history.json", old))
    return docs


def _export(base: list[tuple[Path, dict]], temp: Path, records: list[dict],
            *, history: list[dict] | None = None) -> RulesDatabase:
    output = temp / "rules.db"
    export_rules_database(_fixture(base, records, history=history), output, finalize=False)
    db = RulesDatabase(output)
    db.validate()
    return db


def test_current_topics_and_historical_predecessor_are_allowed(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
) -> None:
    old = _ruling("faq-ruling:predecessor", end="2026-09-30")
    new = _ruling(
        "faq-ruling:successor", start="2026-09-15",
        scenario_ids=["scenario:annihilation"],
        supersedes=["faq-ruling:predecessor"],
    )
    db = _export(base_documents, tmp_path, [new], history=[old])
    assert any(item["id"] == "skill:camouflage" for item in db.records_by_kind("skill"))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing-topic", "does not resolve to a current canonical definition"),
        ("obsolete-topic", "does not resolve to a current canonical definition"),
        ("missing-scenario", "not a current published Scenario"),
        ("wrong-kind-scenario", "not a current published Scenario"),
        ("missing-predecessor", "supersedes missing ruling"),
        ("different-rules", "without overlapping applicability"),
        ("different-seasons", "without overlapping applicability"),
        ("different-scenarios", "without overlapping applicability"),
        ("different-dates", "without overlapping applicability"),
        ("cycle", "FAQ supersession cycle"),
        ("origin-drift", "conflicting originalPublication"),
    ],
)
def test_export_rejects_bad_faq_references(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
    change: str, message: str,
) -> None:
    old = _ruling("faq-ruling:predecessor")
    new = _ruling(
        "faq-ruling:successor",
        start="2026-09-10",
        supersedes=["faq-ruling:predecessor"],
    )
    history: list[dict] | None = None
    if change == "missing-topic":
        new["facts"]["topicIds"] = ["skill:does-not-exist"]
    elif change == "obsolete-topic":
        new["facts"]["topicIds"] = ["skill:historical-only"]
        # Obsolete terms do not become current just because a historical
        # copy would have held them.
    elif change == "missing-scenario":
        new["facts"]["applicability"][0]["scenarioIds"] = ["scenario:its-not-published"]
    elif change == "wrong-kind-scenario":
        new["facts"]["applicability"][0]["scenarioIds"] = ["skill:camouflage"]
    elif change == "missing-predecessor":
        old = None
    elif change == "different-rules":
        new["facts"]["applicability"][0]["rulesRevision"] = "5.2"
    elif change == "different-seasons":
        old["facts"]["applicability"][0]["season"] = {
            "id": "its-17", "revision": "1.0.2",
        }
        new["facts"]["applicability"][0]["season"] = {
            "id": "its-18", "revision": "2026.09.01",
        }
    elif change == "different-scenarios":
        old["facts"]["applicability"][0]["scenarioIds"] = ["scenario:domination"]
        new["facts"]["applicability"][0]["scenarioIds"] = ["scenario:annihilation"]
    elif change == "different-dates":
        old["facts"]["applicability"][0]["effectiveUntil"] = "2026-09-05"
    elif change == "cycle":
        old["facts"]["supersedes"] = ["faq-ruling:successor"]
    elif change == "origin-drift":
        history = [deepcopy(old)]
        history[0]["id"] = "faq-ruling:successor"
        history[0]["facts"]["originalPublication"]["page"] = 3
        # Origination values are inconsistent even if the underlying
        # historical document would be valid on its own.
        old = None
        new["facts"]["supersedes"] = []
    records = [new] + ([old] if old else [])
    with pytest.raises(ValueError, match=message):
        _export(base_documents, tmp_path, records, history=history)
    assert not (tmp_path / "rules.db").exists()


def test_valid_explicit_supersession_does_not_override_base_rule(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
) -> None:
    old = _ruling("faq-ruling:predecessor", end="2026-10-01")
    new = _ruling(
        "faq-ruling:successor", start="2026-09-20",
        supersedes=["faq-ruling:predecessor"],
    )
    db = _export(base_documents, tmp_path, [old, new])
    base = next(
        row for row in db.composed_records_by_kind("skill")
        if row["id"] == "skill:camouflage"
    )
    assert base is not None
    assert base["id"] == "skill:camouflage"
    assert "supplements" not in base
