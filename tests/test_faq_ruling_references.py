"""Cross-collection FAQ topic/supersession safety; synthetic test rulings only."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database


@pytest.fixture(scope="module")
def base_documents() -> list[tuple[Path, dict]]:
    # Synthetic current FAQ fixtures intentionally replace the real pilot
    # collection; preserve canonical core and hacking sources as reference targets.
    return [
        (path, document)
        for path, document in load_curated_directory(Path("data/curated"))
        if document["collection"]["id"] != "n5-faq-v0.1"
    ]


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


@pytest.mark.parametrize(
    "source_id",
    (
        "n5-faq-v0.0-en-pdf",
        "n5-faq-v0.1-en-pdf",
        "n5-faq-v0.1-es-pdf",
    ),
)
def test_pinned_faq_pdf_source_identity_and_available_bytes(source_id: str) -> None:
    """Audit-only byte pins; a clean CI checkout cannot verify ignored PDFs."""
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads(
        (root / "config/validation/n5-faq-v0.1-question-inventory.json")
        .read_text(encoding="utf-8")
    )
    faq = json.loads(
        (root / "data/curated/rules/n5-faq-v0.1.json").read_text(encoding="utf-8")
    )
    artifacts = inventory["sourceArtifacts"]
    assert set(artifacts) == {
        "n5-faq-v0.0-en-pdf",
        "n5-faq-v0.1-en-pdf",
        "n5-faq-v0.1-es-pdf",
    }
    sources = {source["id"]: source for source in faq["sources"]}
    assert set(artifacts) <= set(sources)
    source = sources[source_id]
    pin = artifacts[source_id]
    assert source["kind"] == "pdf"
    assert source["version"] == pin["version"]
    assert source["localPath"] == pin["localPath"]
    assert source["pageCount"] == pin["filePages"]
    assert re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])

    path = root / pin["localPath"]
    if not path.exists():
        pytest.skip(f"Local-only source PDF unavailable: {pin['localPath']}")
    assert path.is_file()
    with path.open("rb") as stream:
        actual_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    assert actual_sha256 == pin["sha256"], f"FAQ source bytes changed: {source_id}"


def test_pinned_faq_v01_question_inventory_is_complete_and_scoped(
    published_pilot: RulesDatabase,
) -> None:
    """Independently reviewed printed-question list, not inferred from curation.

    ITS-only mission questions are inventoried but deliberately not promoted
    into universal N5 rules. Two exceptions have separately reviewed narrow
    core-scenario overlaps.
    """
    root = Path(__file__).resolve().parents[1]
    inventory = json.loads(
        (root / "config/validation/n5-faq-v0.1-question-inventory.json")
        .read_text(encoding="utf-8")
    )
    faq = json.loads(
        (root / "data/curated/rules/n5-faq-v0.1.json").read_text(encoding="utf-8")
    )
    expected = {
        f"faq-ruling:{slug}": page
        for slug, page in inventory["coreQuestions"]
    }
    assert len(inventory["coreQuestions"]) == len(expected) == 29
    # Independently inventoried from all three printed pages of English FAQ v0.0.
    historical_expected = {
        f"faq-ruling:{slug}": page
        for slug, page in inventory["historicalV00CoreQuestions"]
    }
    assert len(historical_expected) == 20
    assert set(historical_expected) <= set(expected)
    assert {
        page: list(historical_expected.values()).count(page) for page in (1, 2)
    } == {1: 10, 2: 10}
    assert {page: list(expected.values()).count(page) for page in range(1, 5)} == {
        1: 11, 2: 12, 3: 5, 4: 1,
    }
    assert {row["page"] for row in inventory["deferredItsOnlyQuestions"]} == {3, 4}
    assert len(inventory["deferredItsOnlyQuestions"]) == 8
    assert len({
        row["subject"] for row in inventory["deferredItsOnlyQuestions"]
    }) == 8
    assert [
        row["v00Page"] for row in inventory["deferredItsOnlyQuestions"]
    ] == [2, 2, 3, 3, 3, 3, 3, 3]
    # All 28 v0.0 questions persist in v0.1; the other nine v0.1 Q&As are new.
    assert len(historical_expected) + len(inventory["deferredItsOnlyQuestions"]) == 28
    assert len(expected) + len(inventory["deferredItsOnlyQuestions"]) == 37
    assert len(expected) - len(historical_expected) == 9
    records = {record["id"]: record for record in faq["records"]}
    assert len(records) == len(faq["records"])
    assert set(records) == set(expected), (
        "Pinned FAQ source inventory and published question identities differ"
    )
    source_ids = inventory["sourceIds"]
    overlaps = {
        f"faq-ruling:{slug}": scenarios
        for slug, scenarios in inventory["coreScenarioOverlaps"].items()
    }
    assert set(overlaps) == {
        "faq-ruling:scenario-element-carrier-marker-state",
        "faq-ruling:undeployed-ancillary-not-killed",
    }

    historical = 0
    for identifier, record in records.items():
        facts = record["facts"]
        page = expected[identifier]
        assert record["review"]["status"] == "reviewed"
        assert facts["question"] and facts["answer"]
        assert facts["topicIds"]
        assert facts["selectedCitation"] == {
            "sourceId": source_ids["english"], "page": page,
        }
        assert {citation["sourceId"] for citation in record["citations"]} >= {
            source_ids["english"], source_ids["spanish"],
        }
        original = facts["originalPublication"]
        if identifier in historical_expected:
            assert original["version"] == "0.0", identifier
            assert original["sourceId"] == "n5-faq-v0.0-en-pdf", identifier
            assert original["page"] == historical_expected[identifier], identifier
            historical += 1
        else:
            assert original["version"] == "0.1", identifier
            assert original["sourceId"] == source_ids["english"], identifier
            assert original["page"] == page, identifier
        assert facts["selectionReason"]
        assert facts["applicability"] == [{
            "rulesRevision": "5.3",
            "effectiveFrom": "2026-09-01",
            **({"scenarioIds": overlaps[identifier]} if identifier in overlaps else {}),
        }]
        assert facts["supersedes"] == []
    assert historical == 20
    published = {row["id"] for row in published_pilot.records_by_kind("faq-ruling")}
    assert published == set(expected)

    # Verify actual runtime selection, not only the maintained JSON shape.
    for identifier, record in records.items():
        topic = record["facts"]["topicIds"][0]
        scenarios = overlaps.get(identifier)
        selected = published_pilot.faq_rulings_for_topic(
            topic,
            rules_revision="5.3",
            as_of="2026-09-01",
            **({"scenario_id": scenarios[0]} if scenarios else {}),
        )
        result = next((row for row in selected if row["id"] == identifier), None)
        assert result is not None, identifier
        assert result["selected_citation"] == {
            "sourceId": source_ids["english"], "page": expected[identifier],
        }
        assert result["selected_source"]["version"] == "0.1"
        assert result["matched_applicability"] == record["facts"]["applicability"]
        for context in (
            {"rules_revision": "5.2", "as_of": "2026-09-01"},
            {"rules_revision": "5.3", "as_of": "2026-08-31"},
        ):
            assert identifier not in {
                row["id"] for row in published_pilot.faq_rulings_for_topic(
                    topic, **context,
                    **({"scenario_id": scenarios[0]} if scenarios else {}),
                )
            }
        if scenarios:
            for other in (None, "scenario:domination"):
                assert identifier not in {
                    row["id"] for row in published_pilot.faq_rulings_for_topic(
                        topic, rules_revision="5.3", as_of="2026-09-01",
                        scenario_id=other,
                    )
                }


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


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        ({"rules_revision": "5.3", "as_of": "2026-08-31"}, []),
        ({"rules_revision": "5.2", "as_of": "2026-10-01"}, []),
        ({"rules_revision": "5.3", "as_of": "2026-09-01"}, ["faq-ruling:general"]),
        ({"rules_revision": "5.3", "as_of": "2026-09-16"},
         ["faq-ruling:general", "faq-ruling:scenario"]),
        ({"rules_revision": "5.3", "as_of": "2026-09-16", "scenario_id": "scenario:annihilation"},
         ["faq-ruling:general", "faq-ruling:scenario"]),
    ],
)
def test_faq_context_requires_explicit_time_and_revision(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
    context: dict[str, str], expected: list[str],
) -> None:
    general = _ruling("faq-ruling:general")
    scenario = _ruling(
        "faq-ruling:scenario", start="2026-09-15",
        scenario_ids=["scenario:annihilation"],
    )
    general["review"]["status"] = "reviewed"
    scenario["review"]["status"] = "reviewed"
    db = _export(base_documents, tmp_path, [general, scenario])
    ids = [r["id"] for r in db.faq_rulings_for_topic(
        "skill:camouflage", **context,
    )]
    # Scenario-scoped rulings never match without an explicit scenario.
    if "scenario_id" not in context:
        expected = [rid for rid in expected if rid != "faq-ruling:scenario"]
    assert ids == expected


def test_faq_read_model_preserves_selected_source_and_base_rule(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
) -> None:
    ruling = _ruling("faq-ruling:general")
    ruling["review"]["status"] = "reviewed"
    db = _export(base_documents, tmp_path, [ruling])
    items = db.faq_rulings_for_topic(
        "skill:camouflage", rules_revision="5.3", as_of="2026-09-20",
    )
    assert len(items) == 1
    item = items[0]
    assert item["id"] == "faq-ruling:general"
    assert item["selected_source"]["id"] == "n5-faq-v0.1-en-pdf"
    assert item["selected_source"]["version"] == "0.1"
    assert item["selected_source"]["published_date"] == "2026-09-01"
    assert item["original_publication"]["publishedDate"] == "2026-09-01"
    assert item["matched_applicability"] == [{
        "rulesRevision": "5.3", "effectiveFrom": "2026-09-01",
    }]
    assert item["citations"][0]["page"] == 2
    assert item["selection_reason"] == "Explicit synthetic selection for test."
    assert "facts" not in item
    assert all("faq" not in (r["summary"] or "") for r in db.records_by_kind("skill"))


def test_faq_selection_never_publishes_draft_or_future_source(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
) -> None:
    draft = _ruling("faq-ruling:draft")
    selected = _ruling("faq-ruling:reviewed")
    selected["review"]["status"] = "reviewed"
    db = _export(base_documents, tmp_path, [draft, selected])
    assert [r["id"] for r in db.faq_rulings_for_topic(
        "skill:camouflage", rules_revision="5.3", as_of="2026-10-15",
    )] == ["faq-ruling:reviewed"]
    from infinity_db.faq_rulings import select_applicable_faq_rulings

    candidates = db.records_by_kind("faq-ruling")
    for candidate in candidates:
        candidate["selected_source"] = {
            "published_date": "2026-11-01",
        }
    assert select_applicable_faq_rulings(
        candidates, topic_id="skill:camouflage",
        rules_revision="5.3", as_of="2026-10-15",
    ) == []
    for candidate in candidates:
        candidate["selected_source"]["published_date"] = "2026-09-01"
        candidate["collection"]["effective_from"] = "2026-11-01"
    assert select_applicable_faq_rulings(
        candidates, topic_id="skill:camouflage",
        rules_revision="5.3", as_of="2026-10-15",
    ) == []


def test_faq_supersession_only_hides_eligible_active_predecessor(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
) -> None:
    old = _ruling("faq-ruling:old", start="2026-09-01")
    new = _ruling(
        "faq-ruling:new", start="2026-09-20",
        scenario_ids=["scenario:annihilation"], supersedes=["faq-ruling:old"],
    )
    for record in (old, new):
        record["review"]["status"] = "reviewed"
    db = _export(base_documents, tmp_path, [old, new])
    def selected(as_of: str, scenario_id: str | None = None) -> list[str]:
        return [item["id"] for item in db.faq_rulings_for_topic(
            "skill:camouflage", rules_revision="5.3",
            as_of=as_of, scenario_id=scenario_id,
        )]
    assert selected("2026-09-19", "scenario:annihilation") == ["faq-ruling:old"]
    assert selected("2026-09-21", "scenario:annihilation") == ["faq-ruling:new"]
    assert selected("2026-09-21", "scenario:domination") == ["faq-ruling:old"]
    assert selected("2026-09-21") == ["faq-ruling:old"]


def test_faq_season_revision_is_exact_not_inferred(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
) -> None:
    ruling = _ruling("faq-ruling:season", season={
        "id": "its-18", "revision": "2026.09.01",
    })
    ruling["review"]["status"] = "reviewed"
    db = _export(base_documents, tmp_path, [ruling])
    def selected(**kwargs: str) -> list[dict]:
        return db.faq_rulings_for_topic(
            "skill:camouflage", rules_revision="5.3",
            as_of="2026-10-15", **kwargs,
        )
    assert selected() == []
    assert selected(season_id="its-18", season_revision="2026.08.01") == []
    assert len(selected(season_id="its-18", season_revision="2026.09.01")) == 1
    with pytest.raises(ValueError, match="provided together"):
        selected(season_id="its-18")


@pytest.mark.parametrize(
    ("context", "reason"),
    [
        ({"topic_id": "not-typed", "rules_revision": "5.3", "as_of": "2026-10-15"}, "topic"),
        ({"topic_id": "skill:camouflage", "rules_revision": "", "as_of": "2026-10-15"},
         "rules_revision"),
        ({"topic_id": "skill:camouflage", "rules_revision": "5.3", "as_of": "2026-02-31"},
         "as_of"),
        ({"topic_id": "skill:camouflage", "rules_revision": "5.3", "as_of": "2026-10-15",
          "season_id": "its-18"}, "provided together"),
        ({"topic_id": "skill:camouflage", "rules_revision": "5.3", "as_of": "2026-10-15",
          "scenario_id": "skill:camouflage"}, "scenario_id"),
    ],
)
def test_faq_context_rejects_invalid_query_even_without_data(
    context: dict[str, str], reason: str,
) -> None:
    from infinity_db.faq_rulings import select_applicable_faq_rulings

    with pytest.raises(ValueError, match=reason):
        select_applicable_faq_rulings([], **context)


def test_faq_api_uses_explicit_context_without_merging_base_rules(
    base_documents: list[tuple[Path, dict]], tmp_path: Path,
) -> None:
    import json
    from wsgiref.util import setup_testing_defaults

    from infinity_db.web import create_app

    old = _ruling("faq-ruling:old")
    new = _ruling(
        "faq-ruling:new", start="2026-09-15",
        supersedes=["faq-ruling:old"],
    )
    for record in (old, new):
        record["review"]["status"] = "reviewed"
    db = _export(base_documents, tmp_path, [old, new])
    app = create_app(Path("data/generated/infinity.db"), db.path)

    def query(query_string: str) -> tuple[int, dict]:
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO="/api/faq-rulings",
                       QUERY_STRING=query_string, REQUEST_METHOD="GET")
        statuses: list[str] = []
        body = b"".join(app(
            environ, lambda status, headers, exc_info=None: statuses.append(status),
        ))
        return int(statuses[0].split()[0]), json.loads(body)

    status, result = query(
        "topic_id=skill%3Acamouflage&rules_revision=5.3&as_of=2026-09-14"
    )
    assert status == 200
    assert [r["id"] for r in result["items"]] == ["faq-ruling:old"]
    assert result["items"][0]["selected_source"]["published_date"] == "2026-09-01"
    status, result = query(
        "topic_id=skill%3Acamouflage&rules_revision=5.3&as_of=2026-09-20"
    )
    assert status == 200
    assert [r["id"] for r in result["items"]] == ["faq-ruling:new"]
    for invalid in (
        "",
        "topic_id=skill%3Acamouflage&rules_revision=5.3",
        "topic_id=skill%3Acamouflage&rules_revision=5.3&as_of=2026-02-31",
        "topic_id=skill%3Acamouflage&rules_revision=5.3&as_of=2026-09-20&season_id=its-18",
        "topic_id=skill%3Acamouflage&rules_revision=5.3&as_of=2026-09-20&unknown=1",
        "topic_id=skill%3Acamouflage&topic_id=skill%3Acamouflage&rules_revision=5.3&as_of=2026-09-20",
    ):
        status, result = query(invalid)
        assert status == 400, invalid
        assert "error" in result


@pytest.fixture(scope="module")
def published_pilot(tmp_path_factory: pytest.TempPathFactory) -> RulesDatabase:
    """Real reviewed FAQ sources, separate from the synthetic validation fixture."""
    path = tmp_path_factory.mktemp("faq-pilot") / "rules.db"
    export_rules_database(load_curated_directory(Path("data/curated")), path)
    db = RulesDatabase(path)
    db.validate()
    return db


def test_published_faq_pilot_retains_selected_and_spanish_source_evidence(
    published_pilot: RulesDatabase,
) -> None:
    records = published_pilot.records_by_kind("faq-ruling")
    assert {record["id"] for record in records} == {
        "faq-ruling:hacking-device-firewall-disabled",
        "faq-ruling:undeployed-ancillary-not-killed",
        "faq-ruling:scenario-element-carrier-marker-state",
        "faq-ruling:skill-declaration-target-position",
        "faq-ruling:fired-deployable-vertical-surface",
        "faq-ruling:peripheral-controller-unable-to-declare",
        "faq-ruling:camouflaged-marker-total-cover",
        "faq-ruling:coordinated-order-special-dice",
        "faq-ruling:fireteam-required-member-lost",
        "faq-ruling:fireteam-type-after-member-loss",
        "faq-ruling:prone-movement-label",
        "faq-ruling:vault-during-climb-and-jump",
        "faq-ruling:direct-template-secondary-target-los",
        "faq-ruling:place-deployable-space-occupied",
        "faq-ruling:surprise-attack-multiple-users",
        "faq-ruling:sixth-sense-msv1-zero-visibility",
        "faq-ruling:protheion-excess-saving-rolls",
        "faq-ruling:camouflage-one-use-infiltration-failure",
        "faq-ruling:deployment-private-zoc-coherency",
        "faq-ruling:prone-at-end-of-move-distance",
        "faq-ruling:bs-attack-roll-label-mods",
        "faq-ruling:controlled-jump-speedball",
        "faq-ruling:marker-automatic-skill-declarations",
        "faq-ruling:aerial-boost-no-silhouette-contact",
        "faq-ruling:stealth-aro-multiple-activations",
        "faq-ruling:deployable-cover-no-placement",
        "faq-ruling:null-state-marker-and-cautious-movement",
        "faq-ruling:discover-fireteam-sd-bonuses",
        "faq-ruling:deployment-phase-reposition-after-measurement",
    }
    for record in records:
        assert record["review"]["status"] == "reviewed"
        origin = record["facts"]["originalPublication"]
        sources = {citation["source_id"] for citation in record["citations"]}
        if origin["version"] == "0.0":
            assert origin["collectionId"] == "n5-faq-v0.0"
            assert origin["publishedDate"] == "2025-10-15"
            assert origin["sourceId"] == "n5-faq-v0.0-en-pdf"
            assert sources == {
                "n5-faq-v0.0-en-pdf", "n5-faq-v0.1-en-pdf", "n5-faq-v0.1-es-pdf",
            }
        else:
            assert origin["version"] == "0.1"
            assert origin["publishedDate"] == "2026-09-01"
            assert sources == {"n5-faq-v0.1-en-pdf", "n5-faq-v0.1-es-pdf"}
        if record["id"] == "faq-ruling:fireteam-type-after-member-loss":
            assert record["facts"]["conflictingCitations"] == [
                {"sourceId": "n5-faq-v0.1-es-pdf", "page": 3},
            ]
        else:
            assert record["facts"]["conflictingCitations"] == []
        assert record["facts"]["supersedes"] == []

    general = published_pilot.faq_rulings_for_topic(
        "equipment:hacking-device", rules_revision="5.3", as_of="2026-09-01",
    )
    assert [item["id"] for item in general] == [
        "faq-ruling:hacking-device-firewall-disabled",
    ]
    assert general[0]["selected_citation"] == {
        "sourceId": "n5-faq-v0.1-en-pdf", "page": 1,
    }
    assert "Isolated" in general[0]["answer"] and "Null State" in general[0]["answer"]
    assert general[0]["selected_source"]["version"] == "0.1"
    assert general[0]["selected_source"]["published_date"] == "2026-09-01"
    assert published_pilot.faq_rulings_for_topic(
        "equipment:hacking-device", rules_revision="5.3", as_of="2026-08-31",
    ) == []

    contextual = published_pilot.faq_rulings_for_topic(
        "scenario:annihilation", rules_revision="5.3",
        as_of="2026-09-01", scenario_id="scenario:annihilation",
    )
    assert [item["id"] for item in contextual] == [
        "faq-ruling:undeployed-ancillary-not-killed",
    ]
    assert contextual[0]["selected_citation"]["page"] == 4
    assert "was deployed" in contextual[0]["answer"]
    assert contextual[0]["matched_applicability"][0]["scenarioIds"] == [
        "scenario:annihilation",
    ]
    assert published_pilot.faq_rulings_for_topic(
        "scenario:annihilation", rules_revision="5.3", as_of="2026-09-01",
    ) == []
    assert published_pilot.faq_rulings_for_topic(
        "scenario:annihilation", rules_revision="5.3",
        as_of="2026-09-01", scenario_id="scenario:domination",
    ) == []


def test_fireteam_faq_source_omission_is_not_a_contradictory_ruling(
    published_pilot: RulesDatabase,
) -> None:
    """Keep the omitted Spanish qualification distinct from the Haris count conflict."""
    rulings = {
        item["id"]: item
        for item in published_pilot.faq_rulings_for_topic(
            "rule:fireteam-general", rules_revision="5.3", as_of="2026-09-01",
        )
    }
    required = rulings["faq-ruling:fireteam-required-member-lost"]
    assert required["selected_citation"] == {
        "sourceId": "n5-faq-v0.1-en-pdf", "page": 3,
    }
    assert required["conflicting_citations"] == []
    assert "FT Master Special Skill" in required["answer"]
    assert "Spanish FAQ v0.1" in required["selection_reason"]
    assert "omits" in required["selection_reason"]
    assert "not a contradictory Spanish ruling" in required["selection_reason"]
    assert {
        (citation["source_id"], citation["page"])
        for citation in required["citations"]
    } == {
        ("n5-faq-v0.1-en-pdf", 3), ("n5-faq-v0.1-es-pdf", 3),
    }

    master = published_pilot.composed_record("skill:ft-master")
    assert master is not None
    assert any(
        "canceled if the FT Master leaves the Fireteam" in clause
        for clause in master["facts"]["restrictions"]
    )

    haris = rulings["faq-ruling:fireteam-type-after-member-loss"]
    assert haris["conflicting_citations"] == [
        {"sourceId": "n5-faq-v0.1-es-pdf", "page": 3},
    ]
    assert "three-member HARIS" in haris["answer"]
    assert "two-member HARIS" in haris["answer"]


@pytest.mark.parametrize(
    ("topic", "scenario", "selected"),
    [
        ("scenario:annihilation", "scenario:annihilation", True),
        ("rule:scenario:killing", "scenario:annihilation", True),
        ("rule:scenario:killing", "scenario:firefight", False),
        ("scenario:firefight", "scenario:firefight", False),
        ("rule:scenario:killing", "scenario:domination", False),
        ("rule:scenario:killing", "scenario:supplies", False),
        ("rule:scenario:killing", None, False),
    ],
)
def test_undeployed_ancillary_does_not_inherit_firefight_killing_scope(
    published_pilot: RulesDatabase,
    topic: str,
    scenario: str | None,
    selected: bool,
) -> None:
    """Shared Core Killing wording is not an adopted FAQ applicability grant.

    N5.3 Annihilation p. 150 and Firefight p. 155 use the same Killing
    text. The ITS-section FAQ v0.1 p. 4 does not identify either Core
    mission: preserve the currently reviewed Annihilation-only scope.
    """
    core = next(
        document for _, document in load_curated_directory(Path("data/curated"))
        if document["collection"]["id"] == "n5-core-v5.3"
    )
    killing = next(
        row for row in core["records"] if row["id"] == "rule:scenario:killing"
    )
    assert set(killing["scope"]["scenarios"]) == {
        "scenario:annihilation", "scenario:firefight",
    }
    assert {citation["page"] for citation in killing["citations"]
            if citation["sourceId"] == "n5-core-v5.3-pdf"} >= {150, 155}
    results = published_pilot.faq_rulings_for_topic(
        topic, rules_revision="5.3", as_of="2026-09-01",
        scenario_id=scenario,
    )
    matching = [
        row for row in results
        if row["id"] == "faq-ruling:undeployed-ancillary-not-killed"
    ]
    assert len(matching) == int(selected)
    if selected:
        ruling = matching[0]
        assert ruling["matched_applicability"] == [{
            "rulesRevision": "5.3",
            "effectiveFrom": "2026-09-01",
            "scenarioIds": ["scenario:annihilation"],
        }]
        assert ruling["selected_citation"] == {
            "sourceId": "n5-faq-v0.1-en-pdf", "page": 4,
        }
        assert {(cite["source_id"], cite["page"]) for cite in ruling["citations"]} == {
            ("n5-faq-v0.1-en-pdf", 4),
            ("n5-faq-v0.1-es-pdf", 4),
        }


def test_published_faq_pilot_reaches_api_with_unmodified_base_reference(
    published_pilot: RulesDatabase,
) -> None:
    import json
    from urllib.parse import urlencode
    from wsgiref.util import setup_testing_defaults

    from infinity_db.web import create_app
    from infinity_db.web.presentation import ASSETS

    assert "/static/faq-rulings.js" in ASSETS
    assert published_pilot.composed_record("equipment:hacking-device") is not None
    assert published_pilot.composed_record("scenario:annihilation") is not None
    app = create_app(Path("data/generated/infinity.db"), published_pilot.path)

    def request(topic: str, **extra: str) -> tuple[int, dict]:
        query = urlencode({
            "topic_id": topic, "rules_revision": "5.3",
            "as_of": "2026-09-01", **extra,
        })
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(
            PATH_INFO="/api/faq-rulings", QUERY_STRING=query,
            REQUEST_METHOD="GET",
        )
        statuses: list[str] = []
        body = b"".join(app(
            environ, lambda status, headers, exc_info=None: statuses.append(status),
        ))
        return int(statuses[0].split()[0]), json.loads(body)

    status, response = request("equipment:hacking-device")
    assert status == 200
    assert response["items"][0]["id"] == "faq-ruling:hacking-device-firewall-disabled"
    assert response["items"][0]["selected_source"]["published_date"] == "2026-09-01"
    assert response["items"][0]["selected_citation"]["page"] == 1
    status, response = request(
        "scenario:annihilation", scenario_id="scenario:annihilation",
    )
    assert status == 200
    assert response["items"][0]["id"] == "faq-ruling:undeployed-ancillary-not-killed"
    status, response = request(
        "scenario:annihilation", scenario_id="scenario:domination",
    )
    assert status == 200 and response["items"] == []

    status, response = request("scenario:supplies", scenario_id="scenario:supplies")
    assert status == 200
    assert [r["id"] for r in response["items"]] == [
        "faq-ruling:scenario-element-carrier-marker-state",
    ]
    assert response["items"][0]["selected_citation"] == {
        "sourceId": "n5-faq-v0.1-en-pdf", "page": 3,
    }
    for extra in ({}, {"scenario_id": "scenario:domination"}):
        status, response = request("scenario:supplies", **extra)
        assert status == 200
        assert response["items"] == []

    status, response = request("rule:fireteam-general")
    assert status == 200
    type_ruling = next(
        item for item in response["items"]
        if item["id"] == "faq-ruling:fireteam-type-after-member-loss"
    )
    assert "three-member HARIS" in type_ruling["answer"]
    assert "two-member HARIS" in type_ruling["answer"]
    assert type_ruling["selected_citation"] == {
        "sourceId": "n5-faq-v0.1-en-pdf", "page": 3,
    }
    assert type_ruling["conflicting_citations"] == [
        {"sourceId": "n5-faq-v0.1-es-pdf", "page": 3},
    ]


@pytest.mark.parametrize(
    ("topic_id", "ruling_id", "en_page", "es_page", "answer_term"),
    [
        ("skill:bs-attack", "skill-declaration-target-position", 1, 1, "Resolution"),
        ("trait:deployable", "fired-deployable-vertical-surface", 1, 2, "vertical"),
        ("skill:peripheral", "peripheral-controller-unable-to-declare", 2, 2, "Idle"),
        ("state:camouflaged", "camouflaged-marker-total-cover", 3, 3, "Total Cover"),
        ("rule:coordinated-orders", "coordinated-order-special-dice", 2, 3, "Burst"),
        ("rule:special-dice", "coordinated-order-special-dice", 2, 3, "Burst"),
        ("rule:fireteam-general", "fireteam-required-member-lost", 3, 3, "FT Master"),
        ("rule:fireteam-general", "fireteam-type-after-member-loss", 3, 3, "HARIS"),
    ],
)
def test_expanded_faq_v01_topic_page_and_applicability(
    published_pilot: RulesDatabase,
    topic_id: str,
    ruling_id: str,
    en_page: int,
    es_page: int,
    answer_term: str,
) -> None:
    items = published_pilot.faq_rulings_for_topic(
        topic_id, rules_revision="5.3", as_of="2026-09-01",
    )
    item = next((row for row in items if row["id"] == f"faq-ruling:{ruling_id}"), None)
    assert item is not None
    assert answer_term in item["answer"]
    assert item["selected_citation"] == {
        "sourceId": "n5-faq-v0.1-en-pdf", "page": en_page,
    }
    assert {(citation["source_id"], citation["page"]) for citation in item["citations"]} == {
        ("n5-faq-v0.1-en-pdf", en_page),
        ("n5-faq-v0.1-es-pdf", es_page),
    }
    assert item["matched_applicability"] == [{
        "rulesRevision": "5.3", "effectiveFrom": "2026-09-01",
    }]
    assert (
        "cross-checked" in item["selection_reason"]
        or "source discrepancy" in item["selection_reason"]
    )
    assert published_pilot.faq_rulings_for_topic(
        topic_id, rules_revision="5.3", as_of="2026-08-31",
    ) == []
    assert published_pilot.faq_rulings_for_topic(
        topic_id, rules_revision="5.2", as_of="2026-10-15",
    ) == []


@pytest.mark.parametrize(
    ("topic_id", "ruling", "original_page", "current_page", "spanish_page", "key_phrase"),
    [
        ("state:prone", "prone-movement-label", 1, 1, 1, "Jump and Berserk"),
        ("skill:climb", "vault-during-climb-and-jump", 1, 1, 1, "vaulting"),
        ("trait:direct-template", "direct-template-secondary-target-los",
         1, 1, 1, "Line of Fire"),
        ("skill:place-deployable", "place-deployable-space-occupied",
         1, 2, 2, "lost"),
        ("skill:surprise-attack", "surprise-attack-multiple-users",
         1, 2, 2, "separately"),
        ("skill:sixth-sense", "sixth-sense-msv1-zero-visibility",
         2, 2, 2, "-6 MOD"),
        ("skill:protheion", "protheion-excess-saving-rolls",
         2, 2, 2, "Dead State"),
        ("skill:camouflage", "camouflage-one-use-infiltration-failure",
         2, 2, 2, "one use"),
    ],
)
def test_v00_carried_forward_rulings_preserve_original_and_current_sources(
    published_pilot: RulesDatabase,
    topic_id: str,
    ruling: str,
    original_page: int,
    current_page: int,
    spanish_page: int,
    key_phrase: str,
) -> None:
    result = published_pilot.faq_rulings_for_topic(
        topic_id, rules_revision="5.3", as_of="2026-09-01",
    )
    item = next((row for row in result if row["id"] == f"faq-ruling:{ruling}"), None)
    assert item is not None
    assert key_phrase in item["answer"]
    assert item["selected_source"]["id"] == "n5-faq-v0.1-en-pdf"
    assert item["selected_source"]["version"] == "0.1"
    assert item["selected_citation"] == {
        "sourceId": "n5-faq-v0.1-en-pdf", "page": current_page,
    }
    assert item["original_publication"] == {
        "collectionId": "n5-faq-v0.0",
        "sourceId": "n5-faq-v0.0-en-pdf",
        "version": "0.0",
        "publishedDate": "2025-10-15",
        "page": original_page,
    }
    assert {
        (source["source_id"], source["page"])
        for source in item["citations"]
    } == {
        ("n5-faq-v0.0-en-pdf", original_page),
        ("n5-faq-v0.1-en-pdf", current_page),
        ("n5-faq-v0.1-es-pdf", spanish_page),
    }
    assert "not an independently verified" in item["selection_reason"]
    assert item["matched_applicability"] == [{
        "rulesRevision": "5.3", "effectiveFrom": "2026-09-01",
    }]
    assert published_pilot.faq_rulings_for_topic(
        topic_id, rules_revision="5.3", as_of="2025-10-15",
    ) == []
    assert published_pilot.faq_rulings_for_topic(
        topic_id, rules_revision="5.2", as_of="2026-10-15",
    ) == []


def test_supplies_scenario_element_marker_faq_is_strictly_scoped(
    published_pilot: RulesDatabase,
) -> None:
    ruling_id = "faq-ruling:scenario-element-carrier-marker-state"
    for topic in ("scenario:supplies", "rule:scenario:carrying-supply-boxes"):
        scoped = published_pilot.faq_rulings_for_topic(
            topic, rules_revision="5.3", as_of="2026-09-01",
            scenario_id="scenario:supplies",
        )
        selected = [item for item in scoped if item["id"] == ruling_id]
        assert len(selected) == 1
        ruling = selected[0]
        assert "cannot enter Marker State" in ruling["answer"]
        assert ruling["matched_applicability"] == [{
            "rulesRevision": "5.3",
            "effectiveFrom": "2026-09-01",
            "scenarioIds": ["scenario:supplies"],
        }]
        assert ruling["selected_citation"] == {
            "sourceId": "n5-faq-v0.1-en-pdf", "page": 3,
        }
        assert {(c["source_id"], c["page"]) for c in ruling["citations"]} == {
            ("n5-faq-v0.0-en-pdf", 2),
            ("n5-faq-v0.1-en-pdf", 3),
            ("n5-faq-v0.1-es-pdf", 3),
        }
        assert ruling["original_publication"] == {
            "collectionId": "n5-faq-v0.0",
            "sourceId": "n5-faq-v0.0-en-pdf",
            "version": "0.0",
            "publishedDate": "2025-10-15",
            "page": 2,
        }
        for context in ({}, {"scenario_id": "scenario:annihilation"}):
            other = published_pilot.faq_rulings_for_topic(
                topic, rules_revision="5.3", as_of="2026-09-01", **context,
            )
            assert ruling_id not in {item["id"] for item in other}
        older = published_pilot.faq_rulings_for_topic(
            topic, rules_revision="5.2", as_of="2026-09-01",
            scenario_id="scenario:supplies",
        )
        assert ruling_id not in {item["id"] for item in older}


def test_earlier_faq_identity_is_not_inferred_from_current_publication(
    published_pilot: RulesDatabase,
) -> None:
    records = published_pilot.records_by_kind("faq-ruling")
    assert len(records) == 29
    assert sum(
        record["facts"]["originalPublication"]["version"] == "0.0"
        for record in records
    ) == 20
    assert sum(
        record["facts"]["originalPublication"]["version"] == "0.1"
        for record in records
    ) == 9
    assert published_pilot.composed_record("skill:climb") is not None


def test_carried_forward_ruling_identity_reused_for_multiple_topics(
    published_pilot: RulesDatabase,
) -> None:
    def ids(topic: str) -> set[str]:
        return {
            item["id"]
            for item in published_pilot.faq_rulings_for_topic(
                topic, rules_revision="5.3", as_of="2026-09-01",
            )
        }
    assert ids("skill:jump") == {
        "faq-ruling:prone-movement-label",
        "faq-ruling:vault-during-climb-and-jump",
    }
    assert ids("equipment:multispectral-visor") == ids("skill:sixth-sense")
    assert ids("skill:infiltration") == ids("skill:camouflage")


@pytest.mark.parametrize(
    ("topic", "slug", "origin_page", "selected_page", "es_page", "term"),
    [
        ("skill:minelayer", "deployment-private-zoc-coherency", 1, 1, 1, "looking away"),
        ("state:prone", "prone-at-end-of-move-distance", 1, 1, 1, "moves normally"),
        ("skill:intuitive-attack", "bs-attack-roll-label-mods", 1, 1, 1, "Long Skills"),
        ("hacking-program:controlled-jump", "controlled-jump-speedball", 1, 1, 1, "Speedballs"),
        ("skill:stealth", "marker-automatic-skill-declarations", 2, 2, 2, "restricts AROs"),
        ("skill:aerial", "aerial-boost-no-silhouette-contact", 2, 2, 2, "Silhouette"),
        ("skill:stealth", "stealth-aro-multiple-activations", 2, 2, 2, "becomes Idle"),
        ("equipment:deployable-cover", "deployable-cover-no-placement", 2, 2, 3, "cannot end"),
        (
            "state:disconnected", "null-state-marker-and-cautious-movement",
            2, 2, 3, "Cautious Movement",
        ),
        ("skill:discover", "discover-fireteam-sd-bonuses", 2, 3, 3, "bonus"),
    ],
)
def test_remaining_general_v00_carry_forwards_retain_three_source_pages(
    published_pilot: RulesDatabase,
    topic: str,
    slug: str,
    origin_page: int,
    selected_page: int,
    es_page: int,
    term: str,
) -> None:
    results = published_pilot.faq_rulings_for_topic(
        topic, rules_revision="5.3", as_of="2026-09-01",
    )
    item = next((r for r in results if r["id"] == f"faq-ruling:{slug}"), None)
    assert item is not None
    assert term in item["answer"]
    assert item["original_publication"] == {
        "collectionId": "n5-faq-v0.0",
        "sourceId": "n5-faq-v0.0-en-pdf",
        "version": "0.0",
        "publishedDate": "2025-10-15",
        "page": origin_page,
    }
    assert item["selected_citation"] == {
        "sourceId": "n5-faq-v0.1-en-pdf", "page": selected_page,
    }
    assert item["selected_source"]["version"] == "0.1"
    assert {(c["source_id"], c["page"]) for c in item["citations"]} == {
        ("n5-faq-v0.0-en-pdf", origin_page),
        ("n5-faq-v0.1-en-pdf", selected_page),
        ("n5-faq-v0.1-es-pdf", es_page),
    }
    assert published_pilot.faq_rulings_for_topic(
        topic, rules_revision="5.2", as_of="2026-10-15",
    ) == []
    assert published_pilot.faq_rulings_for_topic(
        topic, rules_revision="5.3", as_of="2026-08-31",
    ) == []


def test_remaining_general_v00_cross_topic_identity_is_shared(
    published_pilot: RulesDatabase,
) -> None:
    def ids(topic: str) -> set[str]:
        return {
            r["id"]
            for r in published_pilot.faq_rulings_for_topic(
                topic, rules_revision="5.3", as_of="2026-09-01",
            )
        }

    assert "faq-ruling:deployment-private-zoc-coherency" in ids("skill:decoy")
    assert "faq-ruling:deployment-private-zoc-coherency" in ids("state:holoecho")
    assert "faq-ruling:controlled-jump-speedball" in ids("skill:request-speedball")
    assert "faq-ruling:aerial-boost-no-silhouette-contact" in ids("trait:boost")
    assert "faq-ruling:discover-fireteam-sd-bonuses" in ids(
        "rule:fireteam-level-bonuses"
    )
    assert "faq-ruling:null-state-marker-and-cautious-movement" in ids(
        "state:unconscious"
    )


def test_deployment_phase_faq_has_canonical_basic_rule_and_historical_sources(
    published_pilot: RulesDatabase,
) -> None:
    base = published_pilot.composed_record("rule:deployment-phase")
    assert base is not None
    assert base["name"] == "Deployment Phase"
    assert base["citations"] and any(
        c["source_id"] == "n5-core-v5.3-pdf" and c["page"] == 15
        for c in base["citations"]
    )
    assert "reposition" not in base["summary"].lower()

    items = published_pilot.faq_rulings_for_topic(
        "rule:deployment-phase", rules_revision="5.3", as_of="2026-09-01",
    )
    assert [item["id"] for item in items] == [
        "faq-ruling:deployment-phase-reposition-after-measurement",
    ]
    answer = items[0]
    assert "Roll or measurement" in answer["answer"]
    assert "Fireteam Coherency Check" in answer["answer"]
    assert answer["original_publication"] == {
        "collectionId": "n5-faq-v0.0",
        "sourceId": "n5-faq-v0.0-en-pdf",
        "version": "0.0",
        "publishedDate": "2025-10-15",
        "page": 1,
    }
    assert answer["selected_citation"] == {
        "sourceId": "n5-faq-v0.1-en-pdf", "page": 1,
    }
    assert {(c["source_id"], c["page"]) for c in answer["citations"]} == {
        ("n5-faq-v0.0-en-pdf", 1),
        ("n5-faq-v0.1-en-pdf", 1),
        ("n5-faq-v0.1-es-pdf", 1),
    }
    assert published_pilot.faq_rulings_for_topic(
        "rule:deployment-phase", rules_revision="5.2", as_of="2026-09-01",
    ) == []
    assert published_pilot.faq_rulings_for_topic(
        "rule:deployment-phase", rules_revision="5.3", as_of="2026-08-31",
    ) == []
    assert published_pilot.faq_rulings_for_topic(
        "skill:minelayer", rules_revision="5.3", as_of="2026-09-01",
    )[0]["id"] == "faq-ruling:deployment-private-zoc-coherency"
