"""Read-only deployed-object identity and attribute projection acceptance."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from infinity_db.deployed_object_reference import project_deployed_references
from tools.audit_deployed_object_inventory import audit_inventory


@pytest.fixture(scope="module")
def pinned_inventory() -> dict:
    root = Path(__file__).resolve().parents[1]
    if not (root / "data/generated/infinity.db").is_file():
        pytest.skip("Generated Army snapshot unavailable")
    return audit_inventory(
        root / "data/generated/infinity.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )


def test_all_reviewed_source_objects_keep_stable_provenanced_attributes(
    pinned_inventory: dict,
) -> None:
    result = project_deployed_references(pinned_inventory)
    assert result["formatVersion"] == 1
    assert result["scope"] == "reviewed-projection-not-complete-unit-usage"
    assert result["sourceSnapshot"] == {
        "armyDatabaseSha256": pinned_inventory["armyDatabaseSha256"],
        "curatedSourceSha256": pinned_inventory["curatedSourceSha256"],
    }
    assert len(result["objects"]) == 17  # 14 chart, Madtraps, Armed Turret, Cover
    objects = {row["id"]: row for row in result["objects"]}
    assert len(objects) == 17
    source_keys = [
        (row["sourceProfile"]["catalog"], row["sourceProfile"]["sourceId"],
         row["sourceProfile"]["mode"])
        for row in objects.values() if row["sourceProfile"] is not None
    ]
    assert len(source_keys) == len(set(source_keys)) == 15
    assert ("weapon", 150, None) in source_keys
    for obj in objects.values():
        assert set(obj["attributes"]) == {"ARM", "BTS", "STR", "S"}
        assert "units" not in obj and "carriers" not in obj
        for attr in obj["attributes"].values():
            assert attr["status"] in {"known", "unreported", "disputed"}
            if attr["status"] == "unreported":
                assert attr["value"] is None and attr["provenance"] == []
            else:
                assert attr["value"] is not None and attr["provenance"]


def test_source_disputes_remain_explicit_without_conflating_marker_silhouette(
    pinned_inventory: dict,
) -> None:
    objects = project_deployed_references(pinned_inventory)["objects"]
    by_name = {obj["name"]: obj for obj in objects}
    mine_names = {
        "AP Mine", "E/M Mine", "Monofilament Mine",
        "PARA Mine", "Shock Mine", "Viral Mine",
    }
    for name in mine_names:
        obj = by_name[name]
        silhouette = obj["attributes"]["S"]
        assert silhouette["status"] == "disputed"
        assert silhouette["value"] == "1"  # Retained Army value, not precedence.
        assert [(v["value"], v["source"]["kind"]) for v in silhouette["provenance"]] == [
            ("1", "army"), ("0", "printed"),
        ]
        assert silhouette["provenance"][1]["source"]["page"] == 181
    cybermine = by_name["Cybermine"]["attributes"]["S"]
    assert cybermine["status"] == "known" and cybermine["value"] == "0"
    dazer = by_name["Dazer"]["attributes"]["S"]
    assert dazer["status"] == "disputed"
    assert [(v["value"], v["source"]["kind"]) for v in dazer["provenance"]] == [
        ("0", "army"), ("1", "printed"),
    ]
    turret = by_name["Armed Turret"]["attributes"]["S"]
    assert turret["status"] == "disputed" and turret["value"] == "2"
    assert [v["value"] for v in turret["provenance"]] == ["2", "1"]


def test_missing_scenery_stats_and_distinct_mode_are_not_filled_or_merged(
    pinned_inventory: dict,
) -> None:
    objects = project_deployed_references(pinned_inventory)["objects"]
    by_name = {obj["name"]: obj for obj in objects}
    cover = by_name["Deployable Cover"]
    assert cover["type"] == "scenery"
    assert cover["attributes"]["S"]["value"] == "3"
    for name in ("ARM", "BTS", "STR"):
        assert cover["attributes"][name] == {
            "status": "unreported", "value": None, "provenance": [],
        }
    disco = by_name["Disco Ball"]
    assert disco["sourceProfile"]["name"] == "Disco Baller"
    assert disco["sourceProfile"]["mode"] == "Disco Ball"
    assert disco["id"].endswith("-disco-ball")


def test_shared_delivery_and_unresolved_mine_subtype_have_no_inferred_carriers(
    pinned_inventory: dict,
) -> None:
    result = project_deployed_references(pinned_inventory)
    by_name = {obj["name"]: obj for obj in result["objects"]}
    repeater = by_name["Deployable Repeater"]
    assert {
        (edge["recordId"], edge["method"]) for edge in repeater["deliverySources"]
    } == {
        ("weapon:pitcher", "successful BS Attack shot"),
        ("equipment:deployable-repeater", "Place Deployable Skill"),
    }
    assert {
        edge["method"] for edge in by_name["Drop Bears"]["deliverySources"]
    } == {"BS Mode throw", "Deployable Mode placement"}
    assert by_name["Disco Ball"]["deliverySources"][0]["recordId"] == (
        "weapon:disco-baller"
    )
    assert result["unresolvedDeliveries"] == [{
        "originRecordId": "weapon:mine-dispenser",
        "delivery": "successful BS Attack shot",
        "reason": "source-object-not-resolved",
    }]


def test_projection_fails_closed_on_unreviewed_source_identity(
    pinned_inventory: dict,
) -> None:
    modified = copy.deepcopy(pinned_inventory)
    modified["chartProfiles"][0]["sourceId"] = None
    with pytest.raises(ValueError, match="exact Army ID"):
        project_deployed_references(modified)

    modified = copy.deepcopy(pinned_inventory)
    modified["chartProfiles"][0]["attributes"]["S"] = 0
    with pytest.raises(ValueError, match="Identical values"):
        project_deployed_references(modified)

    modified = copy.deepcopy(pinned_inventory)
    source = modified["reviewedDeliveryPaths"][0]["sourceProfileEvidence"]
    modified["reviewedDeliveryPaths"][0]["sourceProfileEvidence"] = {
        **source, "sourceId": 100000,
    }
    with pytest.raises(ValueError, match="Reviewed delivery"):
        project_deployed_references(modified)

    modified = copy.deepcopy(pinned_inventory)
    modified["reviewedCandidateDecisions"][0]["knownAttributes"]["ARM"] = "0"
    with pytest.raises(ValueError, match="Scenery"):
        project_deployed_references(modified)
