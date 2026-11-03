"""Protect optional N4-origin Reinforcements references in the N5-era player catalog.

These assertions cover the source boundary, not verified N5 adoption of N4 procedures.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.database.repository import Database
from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.reference_catalog import RulesRecordCatalog
from infinity_db.rules_database import RulesDatabase
from infinity_db.skill_catalog import SkillCatalog
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.release_rules_export import export_release_rules
from tools.restrictions_v9_release import _check_variant_semantics_delta
from tools.stage_commlink_v9_candidate import (
    promote_commlink_candidate,
    stage_commlink_candidate,
)

ROOT = Path(__file__).resolve().parents[1]
ANNEX = ROOT / "data/curated/rules/reinforcements-extra-n4-reference.json"


def test_commlink_candidate_stages_matched_pair_without_promoting(tmp_path: Path) -> None:
    """Make an inspectable v9 candidate, leaving the active release byte-for-byte intact."""
    root = _disposable_commlink_release(tmp_path)
    baseline = root / "data/generated/rules.db"
    publication = root / "data/generated/deployed-objects.json"
    old_rules = hashlib.sha256(baseline.read_bytes()).hexdigest()
    old_publication = hashlib.sha256(publication.read_bytes()).hexdigest()
    destination = root / "local/unpromoted"
    manifest = stage_commlink_candidate(destination, root=root)
    assert manifest["kind"] == "staged-commlink-v9-pair-not-promoted"
    assert manifest["record"] == "skill:commlink"
    assert manifest["deployedObjectCount"] == 17
    assert set(path.name for path in destination.iterdir()) == {
        "rules.db", "deployed-objects.json", "manifest.json",
    }
    assert manifest["previousSha256"] == {
        "rules.db": old_rules, "deployed-objects.json": old_publication,
    }
    assert RulesDatabase(destination / "rules.db").skill_reviewed_extra_semantics()[
        "commlink"
    ]["extra_values"][0]["effect"]["count"] == 1
    assert load_deployed_object_publication(
        destination / "deployed-objects.json",
        root / "data/generated/infinity.db",
        destination / "rules.db",
    ) is not None
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == old_rules
    assert hashlib.sha256(publication.read_bytes()).hexdigest() == old_publication
    with pytest.raises(ValueError, match="already exists"):
        stage_commlink_candidate(destination, root=root)


def _disposable_commlink_release(tmp_path: Path) -> Path:
    """Copy only required release inputs into a disposable Git-backed checkout."""
    root = tmp_path / "release"
    (root / "local").mkdir(parents=True)
    shutil.copytree(ROOT / "data/curated/rules", root / "data/curated/rules")
    files = (
        "data/generated/infinity.db",
        "data/generated/rules.db",
        "data/generated/deployed-objects.json",
        "config/validation/deployed-object-delivery-reviews.json",
        "config/validation/deployed-object-candidate-reviews.json",
    )
    for relative in files:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    # Exercise one-time promotion even after the real tracked release is promoted:
    # reconstruct the exact prior family-only row in a disposable v9 database.
    rules = root / "data/generated/rules.db"
    if "commlink" in RulesDatabase(rules).skill_reviewed_extra_semantics():
        with closing(sqlite3.connect(rules)) as database:
            row = database.execute(
                "SELECT variant_json FROM records "
                "WHERE collection_id = ? AND id = ?",
                ("reinforcements-extra-n4-reference", "skill:commlink"),
            ).fetchone()
            assert row is not None
            variant = json.loads(row[0])
            assert variant["inheritance"] == "family"
            assert len(variant["occurrenceParameters"]) == 1
            database.execute(
                "UPDATE records SET variant_json = ? "
                "WHERE collection_id = ? AND id = ?",
                ('{"inheritance":"family"}',
                 "reinforcements-extra-n4-reference", "skill:commlink"),
            )
            database.commit()
        source_paths = (
            root / "data/curated/rules/n5-core-v5.3.json",
            root / "config/validation/deployed-object-delivery-reviews.json",
            root / "config/validation/deployed-object-candidate-reviews.json",
        )
        previous = build_publication(root / "data/generated/infinity.db", rules, *source_paths)
        (root / "data/generated/deployed-objects.json").write_bytes(
            publication_bytes(previous)
        )
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "add", "data/generated/rules.db", "data/generated/deployed-objects.json"],
        cwd=root, check=True,
    )
    subprocess.run(
        ["git", "-c", "user.name=Local Test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "baseline"], cwd=root, check=True,
    )
    return root


def test_commlink_candidate_promotion_restores_recovery_and_matches_staging(
    tmp_path: Path,
) -> None:
    """Promote both binaries in a disposable checkout, never the tracked project."""
    root = _disposable_commlink_release(tmp_path)
    destination = root / "local/staged"
    manifest = stage_commlink_candidate(destination, root=root)
    originals = {
        name: (root / "data/generated" / name).read_bytes()
        for name in ("rules.db", "deployed-objects.json")
    }
    recovery = promote_commlink_candidate(destination, root=root)
    assert recovery.parent == root / "local"
    for name, previous in originals.items():
        assert (recovery / "data/generated" / name).read_bytes() == previous
        assert hashlib.sha256((root / "data/generated" / name).read_bytes()).hexdigest() == (
            manifest["candidateSha256"][name]
        )
    assert load_deployed_object_publication(
        root / "data/generated/deployed-objects.json",
        root / "data/generated/infinity.db",
        root / "data/generated/rules.db",
    ) is not None
    assert destination.is_dir()


def test_commlink_candidate_promotion_refuses_changed_stage(tmp_path: Path) -> None:
    root = _disposable_commlink_release(tmp_path)
    destination = root / "local/staged"
    stage_commlink_candidate(destination, root=root)
    original = (root / "data/generated/rules.db").read_bytes()
    (destination / "rules.db").write_bytes((destination / "rules.db").read_bytes() + b"x")
    with pytest.raises(ValueError, match="Staged Commlink artifact changed"):
        promote_commlink_candidate(destination, root=root)
    assert (root / "data/generated/rules.db").read_bytes() == original


def test_commlink_candidate_promotion_rolls_back_on_post_validation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _disposable_commlink_release(tmp_path)
    destination = root / "local/staged"
    stage_commlink_candidate(destination, root=root)
    originals = {
        name: (root / "data/generated" / name).read_bytes()
        for name in ("rules.db", "deployed-objects.json")
    }
    import infinity_db.web

    def fail_post_validation(*_args: object, **_kwargs: object) -> None:
        raise ValueError("injected post-promotion failure")

    monkeypatch.setattr(infinity_db.web, "create_app", fail_post_validation)
    with pytest.raises(RuntimeError, match="promotion rolled back"):
        promote_commlink_candidate(destination, root=root)
    assert all(
        (root / "data/generated" / name).read_bytes() == previous
        for name, previous in originals.items()
    )
    recovery = list((root / "local").glob("commlink-v9-recovery-*"))
    assert len(recovery) == 1
    assert all(
        (recovery[0] / "data/generated" / name).read_bytes() == previous
        for name, previous in originals.items()
    )


def test_annex_current_optional_reference_discloses_n4_source_boundary() -> None:
    document = load_curated_document(ANNEX)
    assert document["collection"]["id"] == "reinforcements-extra-n4-reference"
    assert document["collection"]["authority"] == "secondary"
    assert document["collection"]["status"] == "current"
    sources = {source["id"]: source for source in document["sources"]}
    assert sources["reinforcements-annex-wiki-n4"]["version"].startswith("N4 Annex")
    assert sources["reinforcements-its-season-18"]["version"] == "2026.09.01"
    assert sources["reinforcements-n5-core"]["version"] == "5.3"

    records = {record["id"]: record for record in document["records"]}
    assert set(records) == {
        "rule:reinforcements-extra", "skill:commlink", "skill:request-reinforcements",
    }
    for record in records.values():
        assert record["scope"] == {"game": "N5", "seasons": ["current"]}
        assert record["review"]["status"] == "reviewed"
        assert "N4" in record["summary"]
        assert record["facts"]["sourceNotes"]
        assert any(
            citation["sourceId"] == "reinforcements-annex-wiki-n4"
            for citation in record["citations"]
        )
    assert records["rule:reinforcements-extra"]["facts"]["category"] == "optional-extra"
    assert records["skill:commlink"]["armyLinks"] == [
        {"entity": "skill", "id": "commlink"},
    ]
    variant = records["skill:commlink"]["variantSemantics"]
    assert variant["inheritance"] == "family"
    assert variant["occurrenceParameters"] == [{
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [
            {
                "extraId": extra_id, "extraType": "TEXT", "rawValue": f"+{count}",
                "effect": {
                    "kind": "max-trooper-count-increase",
                    "appliesTo": "optional-reinforcements-extra-army-list",
                    "count": count,
                },
            }
            for extra_id, count in ((298, 1), (299, 2))
        ],
    }]
    assert records["skill:request-reinforcements"]["facts"]["typeIds"] == [
        "tactical-phase-step",
    ]
    assert not records["skill:request-reinforcements"].get("armyLinks")
    assert all(
        record["id"] not in {"rule:reinforcements-extra", "skill:commlink",
                             "skill:request-reinforcements"}
        for _path, core in load_curated_directory(ROOT / "data/curated/rules")
        if core["collection"]["id"] == "n5-core-v5.3"
        for record in core["records"]
    )


def test_annex_read_model_is_discoverable_and_separate_from_core_matrix(tmp_path: Path) -> None:
    documents = load_curated_directory(ROOT / "data/curated/rules")
    output = tmp_path / "rules.db"
    export_release_rules(documents, output)
    rules = RulesDatabase(output)
    rules.validate()
    # Accept either the pre-promotion v9 pair or the future promoted one.
    # The only permitted pending record delta is Commlink's exact metadata.
    commlink = next(
        record
        for _, document in documents
        for record in document["records"]
        if record["id"] == "skill:commlink"
    )
    baseline = ROOT / "data/generated/rules.db"
    with sqlite3.connect(baseline) as old, sqlite3.connect(output) as new:
        old_rows = {
            (row[0], row[1]): row
            for row in old.execute("SELECT * FROM records ORDER BY collection_id, id")
        }
        new_rows = {
            (row[0], row[1]): row
            for row in new.execute("SELECT * FROM records ORDER BY collection_id, id")
        }
    differing = [
        key for key in sorted(set(old_rows) | set(new_rows))
        if old_rows.get(key) != new_rows.get(key)
    ]
    key = ("reinforcements-extra-n4-reference", "skill:commlink")
    published = "commlink" in RulesDatabase(baseline).skill_reviewed_extra_semantics()
    assert differing == ([] if published else [key]), (
        f"Unexpected v9 rules-record drift: {differing[:25]}"
    )
    if not published:
        _check_variant_semantics_delta(
            baseline, output,
            {key: json.dumps(commlink["variantSemantics"], ensure_ascii=False,
                             separators=(",", ":"))},
        )

    # A prospective publication may only re-pin the rules DB hash.
    # All 17 object definitions, reviewed Unit uses and other source
    # fingerprints must remain byte-equivalent in their JSON values.
    army_path = ROOT / "data/generated/infinity.db"
    sources = (
        ROOT / "data/curated/rules/n5-core-v5.3.json",
        ROOT / "config/validation/deployed-object-delivery-reviews.json",
        ROOT / "config/validation/deployed-object-candidate-reviews.json",
    )
    previous = build_publication(army_path, baseline, *sources)
    staged = build_publication(army_path, output, *sources)
    expected = json.loads(json.dumps(previous))
    expected["sourceSnapshot"]["rulesDatabaseSha256"] = hashlib.sha256(
        output.read_bytes()
    ).hexdigest()
    assert len(staged["objects"]) == 17
    assert staged == expected
    proposed_path = tmp_path / "deployed-objects.json"
    proposed_path.write_bytes(publication_bytes(staged))
    assert load_deployed_object_publication(proposed_path, army_path, output) == staged
    army = Database(army_path)

    general = RulesRecordCatalog(rules, "rules")
    assert any(item["slug"] == "reinforcements-extra" for item in general.list_items())
    entry = general.get_item("reinforcements-extra")
    assert entry is not None
    assert entry["rules"][0]["facts"]["category"] == "optional-extra"
    assert "N4" in entry["description"]

    skills = SkillCatalog(army, rules)
    for name in ("commlink", "request-reinforcements"):
        entry = skills.get_skill(name)
        assert entry is not None
        assert entry["rules"][0]["id"] == f"skill:{name}"
        assert "N4" in entry["rules"][0]["summary"]
    assert any(item["slug"] == "request-reinforcements" for item in skills.list_skills())
    request = rules.composed_record("skill:request-reinforcements")
    assert request is not None
    assert request["skill_types"][0]["id"] == "tactical-phase-step"
    # The core 57-row Orders/AROs projection is intentionally unchanged.
    from infinity_db.declaration_matrix import core_declaration_matrix

    matrix = core_declaration_matrix(army, rules)
    items = [item for section in matrix["sections"] for item in section["items"]]
    assert len(items) == 57
    assert not any(item["name"] == "Request Reinforcements" for item in items)


def test_every_published_reinforcement_profile_and_loadout_keeps_source_army() -> None:
    """Canonical Units must retain each Section's exact source profile/loadout rows."""
    from collections import defaultdict

    path = ROOT / "data/generated/infinity.db"
    profiles: dict[int, dict[int, set[tuple[int, str]]]] = defaultdict(
        lambda: defaultdict(set)
    )
    loadouts: dict[int, dict[int, set[tuple[object, ...]]]] = defaultdict(
        lambda: defaultdict(set)
    )
    with sqlite3.connect(path) as connection:
        for logical_id, army_id, group_id, name in connection.execute(
            "SELECT lus.logical_unit_id, aas.application_army_id, "
            "ppo.group_id, pp.name "
            "FROM profile_payload_occurrences AS ppo "
            "JOIN logical_unit_sources AS lus ON lus.source_unit_id = ppo.unit_id "
            "JOIN application_army_sources AS aas ON aas.source_army_id = ppo.army_id "
            "JOIN application_armies AS a ON a.id = aas.application_army_id "
            "AND a.role = 'reinforcement' "
            "JOIN profile_payloads AS pp ON pp.id = ppo.profile_payload_id"
        ):
            profiles[logical_id][army_id].add((group_id, name))
        for logical_id, army_id, group_id, option_id, name, points, swc in connection.execute(
            "SELECT lus.logical_unit_id, aas.application_army_id, "
            "lpo.group_id, lpo.option_id, lp.name, lpo.points, lpo.swc "
            "FROM loadout_payload_occurrences AS lpo "
            "JOIN logical_unit_sources AS lus ON lus.source_unit_id = lpo.unit_id "
            "JOIN application_army_sources AS aas ON aas.source_army_id = lpo.army_id "
            "JOIN application_armies AS a ON a.id = aas.application_army_id "
            "AND a.role = 'reinforcement' "
            "JOIN loadout_payloads AS lp ON lp.id = lpo.loadout_payload_id"
        ):
            loadouts[logical_id][army_id].add(
                (group_id, option_id, name, points, swc)
            )

    logical_ids = set(profiles) | set(loadouts)
    assert len(profiles) > 20, "No substantive published Reinforcement profile corpus"
    assert len(loadouts) > 20, "No substantive published Reinforcement loadout corpus"
    database = Database(path)
    compared_sections = 0
    for logical_id in sorted(logical_ids):
        unit = database.get_unit(logical_id)
        assert unit is not None, logical_id
        actual_profiles: dict[int, set[tuple[int, str]]] = defaultdict(set)
        actual_loadouts: dict[int, set[tuple[object, ...]]] = defaultdict(set)
        for army in unit["armies"]:
            if army["role"] != "reinforcement":
                continue
            if army["profiles"]:
                actual_profiles[army["id"]].update(
                    (item["group_id"], item["name"]) for item in army["profiles"]
                )
            if army["loadouts"]:
                actual_loadouts[army["id"]].update(
                    (item["group_id"], item["option_id"], item["name"],
                     item["points"], item["swc"])
                    for item in army["loadouts"]
                )
        expected_profiles = dict(profiles.get(logical_id, {}))
        expected_loadouts = dict(loadouts.get(logical_id, {}))
        assert dict(actual_profiles) == expected_profiles, (
            logical_id, unit["name"], actual_profiles, expected_profiles,
        )
        assert dict(actual_loadouts) == expected_loadouts, (
            logical_id, unit["name"], actual_loadouts, expected_loadouts,
        )
        compared_sections += len(set(expected_profiles) | set(expected_loadouts))
    assert compared_sections > 20


def test_commlink_source_extras_remain_on_their_exact_army_loadouts() -> None:
    """Source Commlink (+X) signatures must not leak across canonical Unit/Army rows."""
    from collections import Counter, defaultdict

    path = ROOT / "data/generated/infinity.db"
    # Include unqualified Commlink and preserve all extras belonging to each
    # source Skill occurrence. Source IDs are not inferred from display names.
    occurrences: dict[tuple[int, int, int, int, int], list[tuple[int, str]]] = defaultdict(
        list
    )
    with sqlite3.connect(path) as connection:
        for logical_id, army_id, group_id, option_id, position, extra_id, extra_name in (
            connection.execute(
                "SELECT lus.logical_unit_id, aas.application_army_id, "
                "lpo.group_id, lpo.option_id, s.position, e.extra_id, x.name "
                "FROM loadout_payload_occurrences AS lpo "
                "JOIN logical_unit_sources AS lus ON lus.source_unit_id = lpo.unit_id "
                "JOIN application_army_sources AS aas ON aas.source_army_id = lpo.army_id "
                "JOIN loadout_payload_skills AS s "
                "ON s.loadout_payload_id = lpo.loadout_payload_id AND s.item_id = 260 "
                "LEFT JOIN loadout_payload_skill_extras AS e "
                "ON e.loadout_payload_id = s.loadout_payload_id "
                "AND e.occurrence_position = s.position "
                "LEFT JOIN extras AS x ON x.id = e.extra_id "
                "ORDER BY lus.logical_unit_id, aas.application_army_id, "
                "lpo.group_id, lpo.option_id, s.position, e.position"
            )
        ):
            key = (logical_id, army_id, group_id, option_id, position)
            occurrences.setdefault(key, [])
            if extra_id is not None:
                occurrences[key].append((extra_id, extra_name))

    assert occurrences, "No source-backed Commlink occurrences"
    expected: dict[tuple[int, int, int, int], set[tuple[tuple[int, str], ...]]] = (
        defaultdict(set)
    )
    signatures: Counter[tuple[tuple[int, str], ...]] = Counter()
    for (*loadout, _position), extras in occurrences.items():
        signature = tuple(extras)
        expected[tuple(loadout)].add(signature)
        signatures[signature] += 1
    assert signatures[((298, "+1"),)] > 0
    assert signatures[((299, "+2"),)] > 0
    assert signatures[()] > 0
    assert set(signatures) == {(), ((298, "+1"),), ((299, "+2"),)}

    actual: dict[tuple[int, int, int, int], set[tuple[tuple[int, str], ...]]] = (
        defaultdict(set)
    )
    database = Database(path)
    for logical_id in sorted({key[0] for key in expected}):
        unit = database.get_unit(logical_id)
        assert unit is not None
        for army in unit["armies"]:
            for loadout in army["loadouts"]:
                key = (logical_id, army["id"], loadout["group_id"], loadout["option_id"])
                for skill in loadout["skills"]:
                    if skill["id"] != 260:
                        continue
                    actual[key].add(tuple(
                        (extra["id"], extra["name"]) for extra in skill.get("extras", [])
                    ))
    assert dict(actual) == dict(expected), (
        "Commlink source variant leak or missing exact loadout",
        [
            (key, actual.get(key), expected.get(key))
            for key in sorted(set(actual) | set(expected))
            if actual.get(key) != expected.get(key)
        ][:20],
    )
