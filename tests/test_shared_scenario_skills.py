"""Synthetic shared scenario Skill proof; no published ITS action is being merged."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import build_its_database
from infinity_db.its_source_family import project_its_source_family
from infinity_db.scenario_components import ScenarioComponents, compose_scenario_document
from infinity_db.scenario_definition import parse_scenario_definition_record
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/curated/its/n5-its-season-18.json"
GENERATED = ROOT / "data/generated"
SHARED = "skill:its-shared-synthetic-console"
CONSUMERS = ("hardlock", "b-pong")


def _source() -> dict:
    document = project_its_source_family(load_curated_document(SOURCE))
    scenario = {
        record["id"]: record
        for record in document["records"]
    }
    original = next(
        rule for rule in scenario["scenario:hardlock"]["facts"]["mission"]["rules"]
        if rule["id"] == "activate-console"
    )
    component = {
        "id": SHARED, "kind": "skill", "version": "v1",
        "payload": {
            "skillTypeIds": deepcopy(original["skillTypeIds"]),
            "sourceLabels": deepcopy(original["sourceLabels"]),
            "skillFacts": deepcopy(original["skillFacts"]),
        },
        "citations": deepcopy(scenario["scenario:hardlock"]["citations"]),
        "scenarios": [f"scenario:{value}" for value in CONSUMERS],
    }
    document["scenarioComponents"] = {
        "formatVersion": 1, "definitions": [component],
    }
    for scenario_slug in CONSUMERS:
        record = scenario[f"scenario:{scenario_slug}"]
        target = next(
            rule for rule in record["facts"]["mission"]["rules"]
            if rule["id"] == "activate-console"
        )
        target["name"] = original["name"]
        target.pop("skillFacts")
        target.pop("skillTypeIds")
        target.pop("sourceLabels")
        target["skillDefinition"] = {"ref": SHARED, "version": "v1"}
        if scenario_slug == "b-pong":
            # Context-specific page evidence is authored by the including mission.
            target["skillCitations"] = [
                {"sourceId": cite["sourceId"], "page": cite["page"]}
                for cite in record["citations"]
            ]
    return document


def _build(tmp_path: Path, document: dict):
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = tmp_path / "its_18.db"
    build_its_database(path, output)
    return create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db",
        season_databases={"its-18": output},
    )


def _api(app, path: str) -> dict:
    status, _, payload = wsgi_response(app, "https://reuse.test" + path)
    assert status == 200
    return json.loads(payload)


def test_shared_skill_is_pinned_and_compiled_without_alias_loss(tmp_path: Path) -> None:
    document = _source()
    resolved = compose_scenario_document(document)
    for slug in CONSUMERS:
        scenario = next(r for r in resolved["records"] if r["id"] == f"scenario:{slug}")
        rule = next(
            r for r in scenario["facts"]["mission"]["rules"] if r["id"] == "activate-console"
        )
        assert "skillDefinition" not in rule
        assert rule["sharedSkill"] == {"id": SHARED, "version": "v1"}
        assert rule["skillFacts"]["effects"]
        assert parse_scenario_definition_record(scenario).mission is not None
        assert {
            source["id"] for source in scenario["facts"]["componentSources"]
        } == {SHARED}
    app = _build(tmp_path, document)
    skills = _api(app, "/api/skills")["items"]
    grouped = [s for s in skills if s["slug"] == SHARED.removeprefix("skill:")]
    assert len(grouped) == 1
    canonical = grouped[0]
    assert {s["slug"] for s in canonical["scenarios"]} == set(CONSUMERS)
    assert len(canonical["aliases"]) == 2
    assert len([s for s in skills if s["name"] == "Activate Console"]) == 1

    shared = _api(app, f"/api/skills/{canonical['slug']}")
    assert shared["rules"][0]["id"] == SHARED
    assert len(shared["rules"][0]["applicable_scenarios"]) == 2
    assert [label["name"] for label in shared["rules"][0]["labels"]] == [
        "Attack", "Scenario",
    ]
    assert len(shared["rules"][0]["citations"]) >= 2
    search = _api(app, "/api/search?q=activate%20console")["items"]
    assert any(item["href"] == f"/skills/{canonical['slug']}" for item in search)
    assert not any(item["href"] in {f"/skills/{alias}" for alias in canonical["aliases"]}
                   for item in search)

    for slug in CONSUMERS:
        alias = f"its-18-{slug}-activate-console"
        old = _api(app, f"/api/skills/{alias}")
        assert old["rules"][0]["id"] == f"skill:{alias}"
        assert old["scenario"]["slug"] == slug
        detail = _api(app, f"/api/scenarios/{slug}?collection=its-18&army_points=300")
        rule = next(r for r in detail["special_rules"] if r["id"] == "activate-console")
        assert rule["skill"]["id"] == f"skill:{alias}"
        assert rule["skill"]["facts"] == old["rules"][0]["facts"]


@pytest.mark.parametrize("mutation, expected", [
    ("unknown-version", "exact pinned version"),
    ("unknown-scope", "not applicable"),
    ("unknown-id", "Unknown versioned"),
    ("inline-conflict", "cannot mix"),
    ("missing-requirements", "non-empty"),
    ("duplicate-types", "duplicate"),
])
def test_invalid_shared_skill_references_fail_closed(mutation: str, expected: str) -> None:
    document = _source()
    record = next(r for r in document["records"] if r["id"] == "scenario:hardlock")
    action = next(r for r in record["facts"]["mission"]["rules"] if r["id"] == "activate-console")
    component = document["scenarioComponents"]["definitions"][0]
    if mutation == "unknown-version":
        action["skillDefinition"]["version"] = "future"
    elif mutation == "unknown-scope":
        component["scenarios"] = ["scenario:b-pong"]
    elif mutation == "unknown-id":
        action["skillDefinition"]["ref"] = "skill:missing"
    elif mutation == "inline-conflict":
        action["skillFacts"] = deepcopy(component["payload"]["skillFacts"])
    elif mutation == "missing-requirements":
        component["payload"]["skillFacts"]["requirements"] = []
    else:
        component["payload"]["skillTypeIds"] = ["short-skill", "short-skill"]
    with pytest.raises(ValueError, match=expected):
        ScenarioComponents(document).compose(record)







@pytest.mark.parametrize(("mutation", "message"), [
    ("invalid-page", "exact positive source pages"),
    ("unreviewed-import", "reviewed source evidence"),
    ("incomplete-import", "Only versioned Skills"),
])
def test_shared_skill_metadata_fails_closed(mutation: str, message: str) -> None:
    document = _source()
    component = document["scenarioComponents"]["definitions"][0]
    if mutation == "invalid-page":
        component["citations"][0]["page"] = -1
    else:
        component["origin"] = {
            "sourceCollectionId": "synthetic",
            "seasonId": "its-18",
            "revision": "2026.09.11",
            "sourceIds": ["its-season-18-en-pdf"],
        }
        if mutation == "unreviewed-import":
            component["review"] = {"status": "draft", "reviewedOn": "2026-11-17"}
    with pytest.raises(ValueError, match=message):
        ScenarioComponents(document)

def _cross_season_fixture(tmp_path: Path):
    """Two independent synthetic publications of one pinned shared Skill."""
    import hashlib

    from infinity_db.scenario_reuse import LIBRARY_FORMAT

    original = project_its_source_family(load_curated_document(SOURCE))
    hardlock = next(r for r in original["records"] if r["id"] == "scenario:hardlock")
    action = next(r for r in hardlock["facts"]["mission"]["rules"]
                  if r["id"] == "activate-console")
    payload = {
        "skillTypeIds": deepcopy(action.pop("skillTypeIds")),
        "sourceLabels": deepcopy(action.pop("sourceLabels")),
        "skillFacts": deepcopy(action.pop("skillFacts")),
    }
    action["skillDefinition"] = {"ref": SHARED, "version": "v1"}
    # The synthetic season binding cites only English; keep its action pins
    # inside that exact publication scope as required for real shared Skills.
    action["skillCitations"] = [
        cite for cite in action["skillCitations"]
        if cite["sourceId"] == "its-season-18-en-pdf"
    ]
    origin = {
        "sourceCollectionId": original["collection"]["id"],
        "seasonId": "its-18",
        "revision": original["scenarioCollection"]["revision"],
        "sourceIds": [s["id"] for s in original["sources"]],
    }
    library = {
        "format": LIBRARY_FORMAT, "formatVersion": 1, "id": "synthetic-shared-skills",
        "definitions": [],
        "skills": [{
            "id": SHARED, "version": "v1", "origin": origin,
            "payload": payload, "citations": deepcopy(hardlock["citations"]),
            "review": deepcopy(hardlock["review"]),
        }],
    }
    library_path = tmp_path / "library.json"
    library_path.write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    declared_library = {
        "id": library["id"], "sha256": hashlib.sha256(library_path.read_bytes()).hexdigest(),
    }
    original["sharedScenarioLibrary"] = deepcopy(declared_library)
    original["sharedSkillBindings"] = [{
        "id": SHARED, "version": "v1", "scenarios": ["scenario:hardlock"],
        "citations": [deepcopy(cite) for cite in hardlock["citations"]
                      if cite["sourceId"] == "its-season-18-en-pdf"],
        "review": deepcopy(hardlock["review"]),
    }]
    alternative = deepcopy(original)
    alternative["records"] = [next(r for r in alternative["records"]
                                   if r["id"] == "scenario:hardlock")]
    alternative["records"][0]["scope"]["seasons"] = ["its-17"]
    alternative["collection"].update(
        id="its-season-17-synthetic", title="Synthetic ITS 17 skill reuse",
        effectiveFrom="2025-09-01",
    )
    alternative["scenarioCollection"].update(
        id="its-17", title="Synthetic ITS 17", revision="2025.09.01",
        members=[{"scenarioId": "scenario:hardlock"}],
    )
    alternative["seasonPolicies"] = []
    replacements = {
        s["id"]: "synthetic-its17-" + s["id"].removeprefix("its-season-18-")
        for s in alternative["sources"]
    }

    def rewrite_citations(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "sourceId" and item in replacements:
                    value[key] = replacements[item]
                else:
                    rewrite_citations(item)
        elif isinstance(value, list):
            for item in value:
                rewrite_citations(item)

    rewrite_citations(alternative)
    for source in alternative["sources"]:
        source["id"] = replacements[source["id"]]
        source["version"] = "2025.09.01"
        source["sha256"] = "ab" * 32
        source["localPath"] = "tests/fixtures/nonexistent-its17.pdf"
        source["title"] = "Synthetic ITS 17 source; not historical evidence"
    return original, alternative, library_path, declared_library


@pytest.mark.parametrize(
    ("different_type", "different_summary"),
    [(False, False), (True, False), (False, True)],
)
def test_shared_season_skill_has_no_fabricated_scenario_binding(
    tmp_path: Path, different_type: bool, different_summary: bool,
) -> None:
    """Identical definitions merge; versioned variants route; conflicts fail closed."""
    import hashlib

    original, alternate, path, _ = _cross_season_fixture(tmp_path)
    library = json.loads(path.read_text(encoding="utf-8"))
    global_id = "skill:its-synthetic-global"
    definition = deepcopy(library["skills"][0])
    definition["id"] = global_id
    definition["payload"] = {
        "skillTypeIds": ["short-skill"],
        "skillFacts": {
            "requirements": ["Synthetic general Skill condition."],
            "effects": ["Synthetic general Skill effect."],
            "restrictions": ["Synthetic general Skill restriction."],
        },
    }
    library["skills"].append(definition)
    if different_type:
        # ITS 17/18 use different declaration types for CivEvac and
        # Casevac. Model the exact historical type without publishing
        # synthetic facts as a real ITS 17 source.
        variant = deepcopy(definition)
        variant["version"] = "v2"
        variant["payload"]["skillTypeIds"] = ["short-movement-skill"]
        library["skills"].append(variant)
    path.write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    outputs = {}
    for season, document in (("its-18", original), ("its-17", alternate)):
        document["sharedScenarioLibrary"]["sha256"] = digest
        if different_type and season == "its-17":
            document["skillTypes"].append({
                "id": "short-movement-skill",
                "name": "Short Movement Skills",
                "labels": ["Short Movement Skill", "Short Movement Skills"],
                "descriptions": {
                    "singular": "Historical season Short Movement Skill.",
                    "plural": "Historical season Short Movement Skills.",
                },
            })
        document["sharedSeasonSkillBindings"] = [{
            "id": global_id,
            "version": "v2" if different_type and season == "its-17" else "v1",
            "name": "Synthetic Global Skill",
            "summary": (
                "Conflicting synthetic summary."
                if different_summary and season == "its-17"
                else "Synthetic season-wide rule, not a mission action."
            ),
            "category": "common-skill",
            "applicability": {
                "context": "season", "revision": document["scenarioCollection"]["revision"],
            },
            "citations": [{
                "sourceId": document["sources"][0]["id"], "page": 30,
                "section": "Synthetic global Skill",
            }],
            "review": {"status": "reviewed", "reviewedOn": "2026-11-17"},
        }]
        source = tmp_path / f"{season}-global.json"
        source.write_text(json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
        output = tmp_path / f"{season}-global.db"
        report = build_its_database(source, output, shared_library=path)
        assert global_id in {row["id"] for row in report["skills"]}
        outputs[season] = output

    app = create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db", season_databases=outputs,
    )
    if different_summary:
        with pytest.raises(ValueError, match="Conflicting ITS season Skill facts"):
            app.scenario_catalog.scenario_skill_items()
        return
    if different_type:
        historical_app = create_app(
            GENERATED / "army.db", GENERATED / "rules_n5.db",
            season_databases={"its-17": outputs["its-17"]},
        )
        historical = next(
            item for item in _api(historical_app, "/api/skills")["items"]
            if item["slug"] == global_id.removeprefix("skill:")
        )
        assert historical["categories"][0]["id"] == "short-movement-skill"
        assert historical["categories"][0]["name"] == "Short Movement Skill"
        assert historical["seasons"][0]["collection"] == "its-17"
        items = _api(app, "/api/skills")["items"]
        routes = {item["slug"]: item for item in items if item["name"] == "Synthetic Global Skill"}
        assert set(routes) == {"its-synthetic-global", "its-17-its-synthetic-global"}
        assert routes["its-synthetic-global"]["categories"][0]["id"] == "short-skill"
        assert routes["its-synthetic-global"]["seasons"][0]["collection"] == "its-18"
        older = routes["its-17-its-synthetic-global"]
        assert older["categories"][0]["id"] == "short-movement-skill"
        assert older["seasons"][0]["collection"] == "its-17"
        assert older["rules"][0]["sharedSkill"]["version"] == "v2"
        old_detail = _api(app, "/api/skills/its-17-its-synthetic-global")
        current_detail = _api(app, "/api/skills/its-synthetic-global")
        assert old_detail["rules"][0]["sharedSkill"]["version"] == "v2"
        assert old_detail["rules"][0]["facts"]["typeIds"] == ["short-movement-skill"]
        assert old_detail["rules"][0]["scope"]["seasons"] == ["its-17"]
        assert current_detail["rules"][0]["sharedSkill"]["version"] == "v1"
        assert current_detail["rules"][0]["facts"]["typeIds"] == ["short-skill"]
        assert current_detail["rules"][0]["scope"]["seasons"] == ["its-18"]
        for selection in (outputs, {"its-17": outputs["its-17"], "its-18": outputs["its-18"]}):
            selected_app = create_app(
                GENERATED / "army.db", GENERATED / "rules_n5.db",
                season_databases=selection,
            )
            assert {item["slug"] for item in _api(selected_app, "/api/skills")["items"]
                    if item["name"] == "Synthetic Global Skill"} == set(routes)
        search = _api(app, "/api/search?q=synthetic%20global%20skill")["items"]
        assert {f"/skills/{slug}" for slug in routes} <= {
            item["href"] for item in search
        }
        return
    items = _api(app, "/api/skills")["items"]
    globals_ = [item for item in items if item["slug"] == global_id.removeprefix("skill:")]
    assert len(globals_) == 1
    item = globals_[0]
    assert "scenario" not in item
    assert item["category"] == "Common Skills"
    assert {scope["collection"] for scope in item["seasons"]} == {"its-17", "its-18"}
    assert item["applicability"]["context"] == "season"
    assert set(item["applicability"]["revisions"]) == {"2025.09.01", "2026.09.11"}
    assert {pin["source_id"] for pin in item["rules"][0]["citations"]} == {
        "its-season-18-en-pdf", "synthetic-its17-en-pdf",
    }


def test_skill_library_cross_season_build_and_catalog_dedup(tmp_path: Path) -> None:
    original, alternative, library, pinned = _cross_season_fixture(tmp_path)
    outputs = {}
    for season, document in (("its-18", original), ("its-17", alternative)):
        source_path = tmp_path / f"{season}.json"
        source_path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        output = tmp_path / f"{season}.db"
        result = build_its_database(source_path, output, shared_library=library)
        assert result["inputIdentity"]["sharedScenarioLibrary"] == pinned
        assert result["scenarios"]
        outputs[season] = output
    app = create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db", season_databases=outputs,
    )
    skills = _api(app, "/api/skills")["items"]
    canonical, = [item for item in skills if item["slug"] == SHARED.removeprefix("skill:")]
    assert {s["collection"] for s in canonical["scenarios"]} == {"its-17", "its-18"}
    assert set(canonical["aliases"]) == {
        "its-17-hardlock-activate-console", "its-18-hardlock-activate-console",
    }
    detail = _api(app, f"/api/skills/{canonical['slug']}")
    assert {c["source_id"] for c in detail["rules"][0]["citations"]} == {
        "its-season-18-en-pdf", "synthetic-its17-en-pdf",
    }
    for season, revision in (("its-17", "2025.09.01"), ("its-18", "2026.09.11")):
        old = _api(app, f"/api/skills/{season}-hardlock-activate-console")
        assert old["scenario"]["collection"] == season
        assert old["rules"][0]["sharedSkill"]["origin"]["seasonId"] == "its-18"
        assert {c["source_id"] for c in old["rules"][0]["citations"]} <= (
            {"synthetic-its17-en-pdf", "synthetic-its17-es-pdf"} if season == "its-17"
            else {"its-season-18-en-pdf", "its-season-18-es-pdf"}
        )
        selected = _api(
            app, f"/api/scenarios/hardlock?collection={season}&revision={revision}"
            "&army_points=300",
        )
        action = next(rule for rule in selected["special_rules"]
                      if rule["id"] == "activate-console")
        assert action["skill"]["id"] == f"skill:{season}-hardlock-activate-console"


@pytest.mark.parametrize(("mutation", "error"), [
    ("missing-skill", "Unknown pinned shared Skill"),
    ("wrong-citations", "outside its publication"),
    ("wrong-scenario", "unknown season scenario"),
    ("unused-binding", "unused by scenario"),
    ("draft-review", "requires reviewed evidence"),
    ("duplicate-binding", "Conflicting shared Skill binding"),
])
def test_shared_skill_library_binding_failures(tmp_path: Path, mutation: str, error: str):
    from infinity_db.scenario_reuse import materialize_shared_scenarios

    original, _, library, _ = _cross_season_fixture(tmp_path)
    binding = original["sharedSkillBindings"][0]
    if mutation == "missing-skill":
        binding["version"] = "v2"
    elif mutation == "wrong-citations":
        binding["citations"][0]["sourceId"] = "unbound-other-season"
    elif mutation == "wrong-scenario":
        binding["scenarios"] = ["scenario:unknown"]
    elif mutation == "unused-binding":
        binding["scenarios"] = ["scenario:b-pong"]
    elif mutation == "draft-review":
        binding["review"]["status"] = "draft"
    else:
        original["sharedSkillBindings"].append(deepcopy(binding))
    with pytest.raises(ValueError, match=error):
        materialize_shared_scenarios(original, library)

def test_reviewed_skill_overrides_keep_contextual_variants_separate(tmp_path: Path) -> None:
    original, alternate, library, _ = _cross_season_fixture(tmp_path)
    alternate["sharedSkillBindings"][0]["overrides"] = [{
        "scenarioId": "scenario:hardlock",
        "ruleId": "activate-console",
        "field": "skillFacts.effects",
        "value": ["Synthetic ITS 17 scenario effect; not real historical evidence."],
    }]
    outputs = {}
    for season, document in (("its-18", original), ("its-17", alternate)):
        source = tmp_path / f"{season}-overrides.json"
        source.write_text(json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
        database = tmp_path / f"{season}-overrides.db"
        build_its_database(source, database, shared_library=library)
        outputs[season] = database
    app = create_app(
        GENERATED / "army.db", GENERATED / "rules_n5.db", season_databases=outputs,
    )
    items = _api(app, "/api/skills")["items"]
    canonical, = [item for item in items if item["slug"] == SHARED.removeprefix("skill:")]
    assert [entry["collection"] for entry in canonical["scenarios"]] == ["its-18"]
    legacy = "its-17-hardlock-activate-console"
    variant, = [item for item in items if item["slug"] == legacy]
    assert variant["rules"][0]["sharedSkill"]["overriddenFields"] == ["skillFacts.effects"]
    assert variant["rules"][0]["facts"]["effects"] == [
        "Synthetic ITS 17 scenario effect; not real historical evidence.",
    ]
    assert variant["rules"][0]["facts"]["requirements"] == canonical["rules"][0]["facts"][
        "requirements"
    ]
    assert len(canonical["rules"][0]["citations"]) >= 1
    detail = _api(app, "/api/scenarios/hardlock?collection=its-17&army_points=300")
    action = next(item for item in detail["special_rules"] if item["id"] == "activate-console")
    assert action["skill"]["facts"]["effects"] == variant["rules"][0]["facts"]["effects"]
    search = _api(app, "/api/search?q=activate%20console")["items"]
    assert any(item["href"] == f"/skills/{legacy}" for item in search)
    assert any(item["href"] == f"/skills/{canonical['slug']}" for item in search)


@pytest.mark.parametrize(("mutation", "message"), [
    ("bad-field", "unsupported scope or field"),
    ("bad-scenario", "unsupported scope or field"),
    ("wrong-action", "unknown action or Skill"),
    ("wrong-version", "unused by scenario"),
    ("duplicate-field", "Conflicting shared Skill overrides"),
    ("empty-effects", "requires an array of prose"),
    ("invalid-text", "requires non-empty trimmed text"),
    ("invalid-array", "requires an array of prose"),
])
def test_skill_override_bindings_reject_unsafe_edits(
    tmp_path: Path, mutation: str, message: str,
) -> None:
    from infinity_db.scenario_reuse import materialize_shared_scenarios

    original, _, library, _ = _cross_season_fixture(tmp_path)
    change = {
        "scenarioId": "scenario:hardlock",
        "ruleId": "activate-console",
        "field": "skillFacts.effects",
        "value": ["Synthetic reviewed effect."],
    }
    binding = original["sharedSkillBindings"][0]
    binding["overrides"] = [change]
    if mutation == "bad-field":
        change["field"] = "skillTypeIds"
    elif mutation == "bad-scenario":
        change["scenarioId"] = "scenario:b-pong"
    elif mutation == "wrong-action":
        change["ruleId"] = "missing"
    elif mutation == "wrong-version":
        action = next(r for rec in original["records"] if rec["id"] == "scenario:hardlock"
                      for r in rec["facts"]["mission"]["rules"] if r["id"] == "activate-console")
        action["skillDefinition"]["version"] = "v2"
    elif mutation == "duplicate-field":
        binding["overrides"].append(deepcopy(change))
    elif mutation == "empty-effects":
        change["value"] = []
    elif mutation == "invalid-text":
        change["value"] = [" "]
    else:
        change["value"] = "not an array"
    with pytest.raises(ValueError, match=message):
        materialize_shared_scenarios(original, library)


def test_same_identity_requires_identical_compiled_facts(tmp_path: Path) -> None:
    document = _source()
    # A shared Skill cannot declare different effects for two consumers under
    # the same pinned identity; even synthetic tampering must be rejected.
    app = _build(tmp_path, document)
    catalog = app.scenario_catalog
    rows = deepcopy(catalog._records())
    target = next(record for record, publication in rows
                  if record["id"] == "scenario:b-pong" and publication["collection"] == "its-18")
    action = next(rule for rule in target["facts"]["mission"]["rules"]
                  if rule["id"] == "activate-console")
    action["skillFacts"]["effects"][0] = "Synthetic conflicting effect."
    catalog._records_cache = rows
    catalog._scenario_skills_cache = None
    with pytest.raises(ValueError, match="Conflicting facts"):
        catalog.scenario_skill_items()
