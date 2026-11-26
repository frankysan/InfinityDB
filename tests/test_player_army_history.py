"""Player history preview preserves observed scope and hides technical evidence."""

from tools.research import render_player_army_history as player


def fixture():
    date = {"earlierObservedDate": "2025-01-01", "laterObservedDate": "2025-02-01"}
    group = {
        **date, "armyIds": [101], "status": "observedCandidate",
        "sourcePath": ["units", 42, "profileGroups", 1, "profiles", 2],
        "historicalLabels": [[{"id": 42, "name": "Unit"}, {"id": 1, "isc": "Group"},
                              {"id": 2, "name": "Peripheral <X>"}]],
        "changes": [
            {"field": "bs", "before": {"present": True, "value": 11},
             "after": {"present": True, "value": 12}},
            {"field": "skills", "before": {}, "after": {}},
        ],
    }
    unit = {
        "logicalUnitId": 42, "name": "Unit <X>", "slug": "unit-x",
        "composition": [group], "reviewEvidence": {}, "catalogEvidence": {},
        "sourceIdentities": [],
    }
    row = {
        **date, "logicalUnitId": 42, "sourceUnitId": 42, "groupId": 1,
        "field": "points", "summary": "-2 Points", "allGroupLoadouts": True,
        "loadouts": [{"optionId": 1, "label": "HMG", "before": 32, "after": 30}],
        "evidence": [{"armyId": 101}, {"armyId": 102}],
    }
    semantic = {k: [] for k in (*player.STREAMS, "outcomes", "lifecycleOutcomes",
                                "availabilityOutcomes", "relationshipOutcomes")}
    semantic["summaries"] = [row, row, {**row, "laterObservedDate": "2025-03-01"}]
    semantic["outcomes"] = [{"logicalUnitId": 42, "outcome": "partialChanged"}]
    return {"units": [unit, {**unit, "logicalUnitId": 43, "composition": []}]}, semantic


def test_combines_supported_streams_and_keeps_exact_windows_and_scope():
    preview, semantic = fixture()
    units, counts = player.model(
        preview, semantic, lambda row, ev, stream: player.effective_scope(row, "Group"),
    )
    assert counts["scalarCandidates"] == 1
    assert counts["summaries"] == 3
    assert counts["timelineEntries"] == 3
    assert counts["unitsWithHistory"] == 1
    newest, *earlier = units[0]["entries"]
    assert newest["laterObservedDate"] == "2025-03-01"
    cost = next(row for row in earlier if row["kind"] == "summaries")
    assert cost["text"] == "Points: 32 → 30"
    assert cost["scope"] == "Group · All loadouts in this group"
    assert cost["armyIds"] == [101, 102]
    assert len(cost["evidence"]) == 2
    scalar = next(row for row in earlier if row["kind"] == "characteristic")
    assert scalar["scope"] == "Group / Peripheral <X> (profile)"
    assert scalar["text"] == "BS: 11 → 12"
    assert units[0]["semanticReview"]["outcomes"] == semantic["outcomes"]


def test_different_historical_scopes_are_not_consolidated():
    preview, semantic = fixture()
    semantic["summaries"] = semantic["summaries"][:1]
    units, _ = player.model(preview, semantic, lambda row, ev, stream: str(ev["armyId"]))
    costs = [r for r in units[0]["entries"] if r["kind"] == "summaries"]
    assert {tuple(r["armyIds"]) for r in costs} == {(101,), (102,)}


def test_group_wide_effect_consolidates_despite_army_loadout_variants():
    preview, semantic = fixture()
    row = semantic["summaries"][0]
    variant = {**row, "loadouts": [{"optionId": 7, "label": "Rifle",
                                    "before": 32, "after": 30}],
               "evidence": [{"armyId": 103}]}
    semantic["summaries"] = [row, variant]
    units, _ = player.model(
        preview, semantic, lambda row, ev, stream: player.effective_scope(row, "Group"),
    )
    costs = [r for r in units[0]["entries"] if r["kind"] == "summaries"]
    assert len(costs) == 1
    assert costs[0]["armyIds"] == [101, 102, 103]
    assert len(costs[0]["evidence"]) == 2
    # Different displayed costs or partial coverage must remain separate.
    variant["loadouts"][0].update(before=30, after=28)
    units, _ = player.model(
        preview, semantic, lambda row, ev, stream: player.effective_scope(row, "Group"),
    )
    assert len([r for r in units[0]["entries"] if r["kind"] == "summaries"]) == 2


def test_partial_profile_and_attachment_scope():
    row = {
        "allGroupLoadouts": False,
        "loadouts": [{"label": "HMG", "relationshipScope": "directOwners"}],
        "profiles": [{"name": "Pilot", "allProfileLoadouts": False}],
    }
    assert player.effective_scope(row, "TAG") == (
        "TAG · HMG · Profiles: Pilot · Own capabilities only"
    )
    row["profiles"][0]["allProfileLoadouts"] = True
    assert player.effective_scope(row, "TAG") == (
        "TAG · All loadouts for Pilot · Own capabilities only"
    )


def test_scalar_display_uses_units_and_non_applicable_marker():
    assert player.scalar_text("move", {"present": True, "value": [10, 10]}) == '4-4"'
    assert player.scalar_text("move", {"present": True, "value": [15, 5]}) == '6-2"'
    assert player.scalar_text("move", {"present": True, "value": [-1, -1]}) == "—"
    assert player.scalar_text("bs", {"present": True, "value": -1}) == "—"


def test_compact_option_labels_distinguish_siblings_without_shared_references(monkeypatch):
    def resolve(values, field, army, contexts):
        return [{"filter": {"name": v}, "occurrence": {}} for v in values], "resolved"

    monkeypatch.setattr(player, "resolve_references", resolve)
    options = {
        1: {"name": "Trooper", "weapons": ["Pistol", "Rifle"], "points": 10, "swc": 0},
        2: {"name": "Trooper", "weapons": ["Pistol", "HMG"], "points": 20, "swc": 1},
        3: {"name": "Trooper", "weapons": ["Pistol", "HMG"], "points": 21, "swc": 1},
    }
    labels = player.compact_option_labels(options, {}, [])
    assert labels == {
        1: "Trooper — Rifle",
        2: "Trooper — HMG (20 Points, 1 SWC)",
        3: "Trooper — HMG (21 Points, 1 SWC)",
    }
    options[3]["points"] = 20
    labels = player.compact_option_labels(options, {}, [])
    assert labels[2] == labels[3]
    assert labels[2].endswith("(not uniquely distinguished)")


def test_unresolved_option_references_do_not_suppress_known_common_items(monkeypatch):
    def resolve(values, field, army, contexts):
        if values == ["unknown"]:
            return None, "unresolved"
        return [{"filter": {"name": v}, "occurrence": {}} for v in values], "resolved"

    monkeypatch.setattr(player, "resolve_references", resolve)
    labels = player.compact_option_labels({
        1: {"name": "A", "weapons": ["Pistol"], "skills": ["unknown"]},
        2: {"name": "B", "weapons": ["Pistol"]},
    }, {}, [])
    assert labels[1] == "A — Pistol; Unresolved Skills"
    assert labels[2] == "B — Pistol"


def test_html_keeps_all_units_searchable_and_escapes_historical_text():
    preview, semantic = fixture()
    units, _ = player.model(preview, semantic, lambda row, ev, stream: "Group")
    html = player.render(units, {101: "Army <A>", 102: "Army B"}, {"private": True})
    assert 'data-history="no"' in html
    assert 'id="with-history" checked' in html
    assert 'id="technical"' in html
    assert 'class="technical-only"' in html
    assert "Peripheral &lt;X&gt;" in html
    assert "Army &lt;A&gt;" in html
    assert "No supported changes found" in html
    assert "<X>" not in html
    assert html.index('<time datetime="2025-03-01">') < html.index('<time datetime="2025-02-01">')
    assert "Observation window: 2025-01-01 – 2025-02-01" in html


def test_same_observation_date_shares_heading_but_preserves_distinct_windows():
    preview, semantic = fixture()
    original = semantic["summaries"][0]
    semantic["summaries"] = [original, {
        **original, "earlierObservedDate": "2025-01-15",
        "evidence": [{"armyId": 103}],
    }]
    units, counts = player.model(preview, semantic, lambda row, ev, stream: "Group")
    assert counts["timelineEntries"] == 3
    html = player.render(units, {101: "Army A", 102: "Army B", 103: "Army C"}, {})
    assert html.count('<time datetime="2025-02-01">') == 1
    assert html.count("<strong>Points: 32 → 30</strong>") == 1
    assert "Observation window: 2025-01-01 – 2025-02-01" in html
    assert "Observation window: 2025-01-15 – 2025-02-01" in html
    assert '<p class="armies">Army A, Army B, Army C</p>' in html


def test_presentation_keeps_distinct_targets_and_overlapping_army_observations():
    preview, semantic = fixture()
    row = semantic["summaries"][0]
    variant = {**row, "earlierObservedDate": "2025-01-15",
               "evidence": [{"armyId": 101}, {"armyId": 103}]}
    semantic["summaries"] = [row, variant]
    units, _ = player.model(preview, semantic, lambda row, ev, stream: "Group")
    rows = [r for r in units[0]["entries"] if r["kind"] == "summaries"]
    assert len(player.presentation_rows(rows)) == 2

    variant["evidence"] = [{"armyId": 103}]
    variant["groupId"] = 2
    units, _ = player.model(preview, semantic, lambda row, ev, stream: "Group")
    rows = [r for r in units[0]["entries"] if r["kind"] == "summaries"]
    assert len(player.presentation_rows(rows)) == 2

    variant["groupId"] = 1
    variant["laterObservedDate"] = "2025-03-01"
    units, _ = player.model(preview, semantic, lambda row, ev, stream: "Group")
    rows = [r for r in units[0]["entries"] if r["kind"] == "summaries"]
    assert len(player.presentation_rows(rows)) == 2


def test_exact_cross_catalog_transition_keeps_both_source_observations():
    preview, semantic = fixture()
    row = semantic["summaries"][0]
    base = {k: v for k, v in row.items() if k not in {"field", "summary", "loadouts"}}
    base["loadouts"] = [{"optionId": 1, "label": "HMG"}]
    before = {"filter": {"id": 266, "name": "Bangbomb", "wiki": "wiki"},
              "occurrence": {"extra": [{"id": 310, "name": "+4", "type": "TEXT"}], "q": 1}}
    after = {**before, "filter": {**before["filter"], "id": 246, "type": "WEAPON"}}
    lost = {**base, "field": "skills", "summary": "Lost Bangbomb (+4)",
            "lost": [before], "gained": []}
    gained = {**base, "field": "equip", "summary": "Gained Bangbomb (+4)",
              "lost": [], "gained": [after]}
    semantic["summaries"] = [lost, gained]
    units, counts = player.model(preview, semantic, lambda row, ev, stream: "Group")
    assert counts["summaries"] == 2
    changes = [r for r in units[0]["entries"] if r["kind"] != "characteristic"]
    assert len(changes) == 1
    change = changes[0]
    assert change["kind"] == "classification"
    assert change["text"] == (
        f"Bangbomb (+4): {player.FIELDS['skills']} → {player.FIELDS['equip']} (classification)"
    )
    assert change["evidence"][0]["from"]["lost"] == [before]
    assert change["evidence"][0]["to"]["gained"] == [after]
    # Same display label is insufficient when coverage, modifiers or targets differ.
    for variant in (
        {**gained, "evidence": [{"armyId": 103}]},
        {**gained, "loadouts": [{"optionId": 2, "label": "HMG"}]},
        {**gained, "gained": [{**after, "occurrence": {"q": 2}}]},
        {**gained, "gained": [{**after, "filter": {**after["filter"], "wiki": "other"}}]},
    ):
        semantic["summaries"] = [lost, variant]
        units, _ = player.model(preview, semantic, lambda row, ev, stream: "Group")
        assert len([r for r in units[0]["entries"] if r["kind"] == "summaries"]) == 2


def test_group_wide_same_delta_different_cost_pairs_stay_separate():
    preview, semantic = fixture()
    row = semantic["summaries"][0]
    row["loadouts"].append({"optionId": 2, "label": "Rifle", "before": 30, "after": 28})
    variant = {**row, "loadouts": [
        {"optionId": 1, "label": "HMG", "before": 35, "after": 33},
        {"optionId": 2, "label": "Rifle", "before": 33, "after": 31},
    ], "evidence": [{"armyId": 103}]}
    semantic["summaries"] = [row, variant]
    units, _ = player.model(preview, semantic, lambda row, ev, stream: "Group")
    rows = [r for r in units[0]["entries"] if r["kind"] == "summaries"]
    assert len(rows) == 2
    assert len(player.presentation_rows(rows)) == 2
