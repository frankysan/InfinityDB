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
        "faq-ruling:skill-declaration-target-position",
        "faq-ruling:fired-deployable-vertical-surface",
        "faq-ruling:peripheral-controller-unable-to-declare",
        "faq-ruling:camouflaged-marker-total-cover",
        "faq-ruling:coordinated-order-special-dice",
        "faq-ruling:fireteam-required-member-lost",
    }
    for record in records:
        assert record["review"]["status"] == "reviewed"
        assert record["facts"]["originalPublication"]["version"] == "0.1"
        assert record["facts"]["originalPublication"]["publishedDate"] == "2026-09-01"
        assert {citation["source_id"] for citation in record["citations"]} == {
            "n5-faq-v0.1-en-pdf", "n5-faq-v0.1-es-pdf",
        }
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
    assert [item["id"] for item in items] == [f"faq-ruling:{ruling_id}"]
    item = items[0]
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
    assert "cross-checked" in item["selection_reason"]
    assert published_pilot.faq_rulings_for_topic(
        topic_id, rules_revision="5.3", as_of="2026-08-31",
    ) == []
    assert published_pilot.faq_rulings_for_topic(
        topic_id, rules_revision="5.2", as_of="2026-10-15",
    ) == []
