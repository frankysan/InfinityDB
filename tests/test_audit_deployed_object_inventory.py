"""Conservative deployed-object discovery without new canonical identities."""

from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_deployed_object_inventory import (
    CHART_AUXILIARY,
    _profile_stats,
    audit_inventory,
    validate_candidate_reviews,
    validate_delivery_reviews,
)


def test_source_profile_parser_accepts_only_complete_four_stat_objects() -> None:
    expected = {"ARM": 0, "BTS": 0, "STR": 1, "S": 0}
    assert _profile_stats("ARM=0, BTS=0, STR=1, S=0") == expected
    assert _profile_stats("ARM=0 | BTS=0 | STR=1 | S=0") == expected
    assert _profile_stats("STR=1, BTS=0, ARM=0, S=0") == expected
    assert _profile_stats("ARM=0, STR=1, S=1") is None
    assert _profile_stats("ARM=0, BTS=0, STR=1, S=0, S=1") is None
    assert _profile_stats("S3 scenery; remaining stats not printed") is None
    assert _profile_stats("") is None


def test_inventory_preserves_source_modes_and_review_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / "infinity.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE metadata_weapons ("
            "position INTEGER, id INTEGER, type TEXT, name TEXT, "
            "mode TEXT, profile TEXT)"
        )
        for index, (name, mode, catalog, _) in enumerate(CHART_AUXILIARY):
            conn.execute(
                "INSERT INTO metadata_weapons VALUES (?, ?, ?, ?, ?, ?)",
                (
                    index, 100 + index,
                    "EQUIPMENT" if catalog == "equipment" else "WEAPON",
                    name, mode, "ARM=0, BTS=0, STR=1, S=1",
                ),
            )
        conn.execute(
            "INSERT INTO metadata_weapons VALUES (?, ?, ?, ?, ?, ?)",
            (30, 999, "EQUIPMENT", "Other model", None, "S3 scenery"),
        )
        conn.commit()

    curated = tmp_path / "rules.json"
    records = [
        {
            "id": "weapon:armed-turret", "kind": "weapon", "name": "Armed Turret",
            "composition": {"role": "definition"},
            "facts": {"specialProfile": {"stats": [["S", "2"]]}},
            "summary": "An independent Token with a reviewed profile.",
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 70}],
        },
        {
            "id": "equipment:deployable-cover", "kind": "equipment",
            "composition": {"role": "definition"}, "summary": "Deployable Scenery Element.",
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 122}],
        },
        {
            "id": "weapon:pitcher", "kind": "weapon",
            "composition": {"role": "definition"},
            "summary": "Fires a Deployable Repeater Token.",
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 73}],
        },
        {
            "id": "equipment:unrelated", "kind": "equipment",
            "composition": {"role": "definition"},
            "summary": "Ordinary equipment, not a placed object.",
        },
    ]
    curated.write_text(json.dumps({"records": records}), encoding="utf-8", newline="\n")

    result = audit_inventory(db_path, curated)
    assert result["scope"] == "candidate-inventory-not-canonical-object-model"
    assert len(result["armyDatabaseSha256"]) == 64
    assert len(result["curatedSourceSha256"]) == 64
    assert len(result["chartProfiles"]) == 14
    assert sum(
        row["catalog"] == "equipment" for row in result["chartProfiles"]
    ) == 3
    assert next(
        row for row in result["chartProfiles"] if row["name"] == "Disco Baller"
    )["mode"] == "Disco Ball"
    assert result["additionalSourceProfiles"] == [{
        "sourceId": 999,
        "name": "Other model",
        "mode": None,
        "catalog": "equipment",
        "sourceProfile": "S3 scenery",
        "attributes": None,
    }]
    assert {
        item["recordId"]: item["category"]
        for item in result["reviewedExamples"]
    } == {
        "weapon:armed-turret": "curated-special-profile",
        "equipment:deployable-cover": "nonstandard-scenery",
        "weapon:pitcher": "delivery-not-object",
    }
    assert {
        item["recordId"] for item in result["curatedCandidateMentions"]
    } == {
        "weapon:armed-turret", "equipment:deployable-cover", "weapon:pitcher",
    }
    assert all(
        entry["reviewStatus"] == "identity-not-inferred"
        for entry in result["curatedCandidateMentions"]
    )


def test_pinned_source_inventory_keeps_separate_catalogs_and_review_boundaries() -> None:
    root = Path(__file__).resolve().parents[1]
    db_path = root / "data/generated/infinity.db"
    if not db_path.is_file():
        pytest.skip("Generated Army source database unavailable")
    result = audit_inventory(
        db_path,
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    assert len(result["reviewedDeliveryPaths"]) == 12
    assert len(result["reviewedCandidateDecisions"]) == 12
    assert len(result["candidateReviewSha256"]) == 64
    by_id = {
        entry["recordId"]: entry for entry in result["reviewedCandidateDecisions"]
    }
    assert set(by_id) == {
        "equipment:deployable-cover", "weapon:armed-turret",
        "equipment:deactivator", "weapon:symbiobomb",
        "weapon:wildparrot", "equipment:dazer", "equipment:fastpanda",
        "weapon:mines", "weapon:d-charges", "equipment:cube", "equipment:cube-2",
        "equipment:tinbot",
    }
    assert by_id["equipment:deployable-cover"]["knownAttributes"] == {"S": "3"}
    assert set(by_id["equipment:deployable-cover"]["unreportedAttributes"]) == {
        "ARM", "BTS", "STR",
    }
    assert by_id["weapon:armed-turret"]["knownAttributes"] == {
        "ARM": "2", "BTS": "3", "STR": "1", "S": "2",
    }
    assert by_id["equipment:deactivator"]["profileShape"] == "none"
    assert by_id["weapon:symbiobomb"]["profileShape"] == "none"
    assert {
        candidate["recordId"] for candidate in result["remainingCuratedCandidateMentions"]
    }.isdisjoint(by_id)
    assert len(result["curatedCandidateMentions"]) == 17
    assert result["remainingCuratedCandidateMentions"] == []
    assert {
        entry["recordId"] for entry in result["deliveryCoveredCandidateMentions"]
    } == {
        "weapon:pitcher", "weapon:mine-dispenser", "weapon:drop-bears",
        "weapon:disco-baller", "equipment:deployable-repeater",
        "weapon:armed-turret", "weapon:wildparrot", "equipment:fastpanda",
        "weapon:crazykoala", "weapon:madtraps",
    }
    assert by_id["equipment:dazer"]["knownAttributes"]["S"] == "0"
    assert by_id["weapon:mines"]["profileShape"] == "none"
    assert len(result["deliveryReviewSha256"]) == 64
    assert len(result["chartProfiles"]) == 14
    assert all(
        row["attributes"] is not None for row in result["chartProfiles"]
    )
    assert {
        row["name"] for row in result["chartProfiles"] if row["catalog"] == "equipment"
    } == {"Dazer", "Deployable Repeater", "FastPanda"}
    examples = {row["recordId"]: row for row in result["reviewedExamples"]}
    assert examples["weapon:armed-turret"]["hasCuratedSpecialProfile"] is True
    assert examples["equipment:deployable-cover"]["hasCuratedSpecialProfile"] is False
    assert examples["weapon:pitcher"]["hasCuratedSpecialProfile"] is False
    for key in examples:
        assert key in {row["recordId"] for row in result["curatedCandidateMentions"]}
        assert examples[key]["citations"]
    assert all(
        candidate["reviewStatus"] == "identity-not-inferred"
        for candidate in result["curatedCandidateMentions"]
    )
    assert result["additionalSourceProfiles"] == [{
        "sourceId": 150,
        "name": "Madtraps",
        "mode": None,
        "catalog": "weapon",
        "sourceProfile": "ARM=0, BTS=0, STR=1, S=1",
        "attributes": {"ARM": 0, "BTS": 0, "STR": 1, "S": 1},
    }]
    paths = result["reviewedDeliveryPaths"]
    pitcher = next(path for path in paths if path["originRecordId"] == "weapon:pitcher")
    placed_repeater = next(
        path for path in paths
        if path["originRecordId"] == "equipment:deployable-repeater"
    )
    assert pitcher["sourceProfileEvidence"] == placed_repeater["sourceProfileEvidence"]
    assert pitcher["objectRulesRecordId"] == "equipment:deployable-repeater"
    assert pitcher["originRecordId"] != placed_repeater["originRecordId"]
    ball = next(path for path in paths if path["originRecordId"] == "weapon:disco-baller")
    assert ball["objectLabel"] == "Disco Ball"
    assert ball["sourceProfileEvidence"]["mode"] == "Disco Ball"
    bears = [path for path in paths if path["originRecordId"] == "weapon:drop-bears"]
    assert len(bears) == 2
    assert {path["delivery"] for path in bears} == {
        "BS Mode throw", "Deployable Mode placement",
    }
    assert bears[0]["sourceProfileEvidence"] == bears[1]["sourceProfileEvidence"]
    dispenser = next(
        path for path in paths if path["originRecordId"] == "weapon:mine-dispenser"
    )
    assert dispenser["sourceProfileEvidence"] is None
    assert dispenser["objectRulesRecordId"] is None


def test_delivery_reviews_require_pinned_curated_evidence_and_exact_source_modes() -> None:
    root = Path(__file__).resolve().parents[1]
    reviews = json.loads(
        (root / "config/validation/deployed-object-delivery-reviews.json")
        .read_text(encoding="utf-8")
    )
    records = {
        record["id"]: record
        for record in json.loads(
            (root / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
        )["records"]
        if record["kind"] in {"weapon", "equipment"}
    }
    profiles = []
    for review in reviews["reviewedDeliveryPaths"]:
        profile = review["sourceProfile"]
        if profile and profile not in profiles:
            profiles.append(profile)
    assert len(profiles) == 7
    approved = validate_delivery_reviews(reviews, records, profiles)
    assert len(approved) == 12
    assert all(entry["reviewStatus"] == "source-backed-audit-only" for entry in approved)

    tampered = copy.deepcopy(reviews)
    tampered["reviewedDeliveryPaths"][0]["summaryEvidence"] = "Not in the source"
    with pytest.raises(ValueError, match="summary evidence"):
        validate_delivery_reviews(tampered, records, profiles)

    tampered = copy.deepcopy(reviews)
    tampered["reviewedDeliveryPaths"][0]["sourcePages"] = [999]
    with pytest.raises(ValueError, match="citations"):
        validate_delivery_reviews(tampered, records, profiles)

    tampered = copy.deepcopy(reviews)
    profile_edge = next(
        entry for entry in tampered["reviewedDeliveryPaths"]
        if entry["sourceProfile"] is not None
    )
    profile_edge["sourceProfile"]["mode"] = "Unverified Mode"
    with pytest.raises(ValueError, match="source profile"):
        validate_delivery_reviews(tampered, records, profiles)

    tampered = copy.deepcopy(reviews)
    tampered["reviewedDeliveryPaths"].append(
        copy.deepcopy(tampered["reviewedDeliveryPaths"][0])
    )
    with pytest.raises(ValueError, match="Duplicate"):
        validate_delivery_reviews(tampered, records, profiles)

    tampered = copy.deepcopy(reviews)
    tampered["reviewedDeliveryPaths"][0]["objectRulesRecordId"] = (
        "equipment:unverified"
    )
    with pytest.raises(ValueError, match="Missing object rules owner"):
        validate_delivery_reviews(tampered, records, profiles)

def test_candidate_review_shapes_are_pinned_and_fail_closed() -> None:
    root = Path(__file__).resolve().parents[1]
    reviews = json.loads(
        (root / "config/validation/deployed-object-candidate-reviews.json")
        .read_text(encoding="utf-8")
    )
    records = {
        record["id"]: record
        for record in json.loads(
            (root / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
        )["records"]
        if record["kind"] in {"weapon", "equipment"}
    }
    source_profiles = [
        {
            "catalog": "weapon" if name == "WildParrot" else "equipment",
            "name": name, "mode": None,
            "attributes": {"ARM": 0, "BTS": 0, "STR": 1, "S": silhouette},
        }
        for name, silhouette in (
            ("WildParrot", 1), ("Dazer", 0), ("FastPanda", 1)
        )
    ]
    approved = validate_candidate_reviews(reviews, records, source_profiles)
    assert len(approved) == 12
    assert all(row["reviewStatus"] == "source-backed-audit-only" for row in approved)

    def mutated(index: int, field: str, value: object) -> dict:
        result = copy.deepcopy(reviews)
        result["reviews"][index][field] = value
        return result

    cases = (
        (0, "summaryEvidence", "No source supports this", "summary evidence"),
        (0, "sourcePages", [999], "citation"),
        (0, "factsEvidence", ["No evidence"], "detailed evidence"),
        (0, "knownAttributes", {"S": "1"}, "scenery profile"),
        (1, "knownAttributes", {"ARM": "2", "BTS": "3", "STR": "1", "S": "1"},
         "profile drift"),
        (2, "knownAttributes", {"S": "1"}, "missing-profile"),
        (3, "classification", "invented-object", "classification"),
        (4, "knownAttributes", {"ARM": "0", "BTS": "0", "STR": "1", "S": "0"},
         "profile drift"),
        (5, "sourceProfile", {"catalog": "equipment", "name": "Dazer", "mode": "BS Mode"},
         "Missing exact Army source profile"),
        (6, "sourcePages", [999], "citation drift"),
        (7, "sourceProfile", {"catalog": "weapon", "name": "Mines", "mode": None},
         "Non-source candidate"),
    )
    for index, field, value, message in cases:
        with pytest.raises(ValueError, match=message):
            validate_candidate_reviews(mutated(index, field, value), records, source_profiles)

    duplicate = copy.deepcopy(reviews)
    duplicate["reviews"].append(copy.deepcopy(duplicate["reviews"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_candidate_reviews(duplicate, records, source_profiles)


