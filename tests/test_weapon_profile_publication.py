"""Source, identity and release-integrity checks for Weapon Chart locators."""

from __future__ import annotations

import json
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from storage_fixture_support import weapon_publication

from infinity_db.database.repository import Database
from infinity_db.weapon_profile_publication import file_sha256, profile_sha256
from tools.audit_enrichment_coverage import audit_coverage
from tools.audit_weapon_chart_profiles import audit_chart
from tools.build_weapon_profile_publication import (
    DEFAULT_ARMY,
    DEFAULT_REVIEWS,
    DEFAULT_RULES,
    build_publication,
    check_embedded_profiles,
    main,
)

PDF_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"


@pytest.fixture(scope="module")
def publication() -> dict[str, Any]:
    return weapon_publication()


def _write(path: Path, document: dict[str, Any]) -> Path:
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def test_reviewed_profile_publication_matches_every_eligible_identity_and_mode(
    publication: dict[str, Any],
) -> None:
    policy = json.loads(DEFAULT_REVIEWS.read_text(encoding="utf-8"))
    decisions = {review["slug"]: review for review in policy["reviews"]}
    gaps = audit_coverage(DEFAULT_ARMY, DEFAULT_RULES)["domains"]["weapons"]["items"]
    eligible = {
        row["slug"] for row in gaps if row["gapCodes"] == ["missing_rule_definition"]
    }
    assert len(eligible) == 62
    assert set(decisions) - eligible == {"crazykoala", "madtraps"}
    assert {weapon["slug"] for weapon in publication["weapons"]} == eligible
    assert sum(len(weapon["profiles"]) for weapon in publication["weapons"]) == 69
    assert publication["source"]["id"] == policy["sourceId"]
    assert publication["source"]["collectionId"] == policy["sourceCollectionId"]
    assert publication["source"]["sha256"] == policy["sourceSha256"] == PDF_SHA256
    assert publication["sourceSnapshot"] == {
        "armyDatabaseSha256": file_sha256(DEFAULT_ARMY),
        "rulesDatabaseSha256": file_sha256(DEFAULT_RULES),
        "reviewsSha256": file_sha256(DEFAULT_REVIEWS),
    }
    database = Database(DEFAULT_ARMY)
    for weapon in publication["weapons"]:
        decision = decisions[weapon["slug"]]
        item = database.get_catalog_item("weapons", weapon["id"])
        assert item is not None
        assert (item["name"], database.application_slug("weapons", weapon["id"])) == (
            decision["name"], weapon["slug"],
        )
        assert profile_sha256(item["profiles"]) == (
            weapon["profileSha256"]
        ) == decision["profileSha256"]
        assert {
            (profile["sourceId"], profile["mode"], profile["page"])
            for profile in weapon["profiles"]
        } == {
            (profile["id"], profile["mode"], decision["chartPage"])
            for profile in item["profiles"]
        }


def test_weapon_profile_diagnostic_matches_embedded_projection(
    publication: dict[str, Any],
) -> None:
    assert build_publication(DEFAULT_ARMY, DEFAULT_RULES, DEFAULT_REVIEWS) == publication
    assert check_embedded_profiles(DEFAULT_ARMY, DEFAULT_RULES, DEFAULT_REVIEWS) == 69
    assert main([]) == 0


def test_weapon_profile_diagnostic_does_not_publish_json() -> None:
    with pytest.raises(SystemExit, match="2"):
        main(["--output", "data/generated/weapon-profile-sources.json"])


def test_pinned_pdf_contains_every_published_weapon_profile_mode_and_page(
    publication: dict[str, Any], pinned_n53_core_pdf: Path,
) -> None:
    pytest.importorskip("fitz")
    report = audit_chart(pinned_n53_core_pdf, DEFAULT_ARMY)
    assert report["corePdfSha256"] == PDF_SHA256
    rows = report["comparison"]["compared"]
    for weapon in publication["weapons"]:
        for profile in weapon["profiles"]:
            matching = [
                row for row in rows
                if row["name"] == weapon["name"] and row["mode"] == (profile["mode"] or "")
            ]
            assert len(matching) == 1, (weapon["slug"], profile["mode"])
            assert matching[0]["page"] == profile["page"]
            assert matching[0]["status"] == "fields-match"
    katyusha = next(row for row in rows if row["name"] == "Katyusha MRL")
    assert katyusha["rangeComparison"]["status"] == "candidate-discrepancy"
    assert katyusha["rangeComparison"]["pdf"][1:3] == ["3", "3"]
    assert katyusha["rangeComparison"]["army"][1:3] == ["+3", "+3"]


def test_runtime_weapon_citations_ignore_invalid_json_sidecar(tmp_path: Path) -> None:
    from infinity_db.weapon_profile_publication import load_runtime_weapon_profile_publication

    army, rules = tmp_path / "army.db", tmp_path / "rules_n5.db"
    shutil.copyfile(DEFAULT_ARMY, army)
    shutil.copyfile(DEFAULT_RULES, rules)
    (tmp_path / "weapon-profile-sources.json").write_bytes(b"obsolete invalid JSON")

    citations, digest = load_runtime_weapon_profile_publication(army, rules)
    assert citations is not None and len(citations) == 69
    assert digest == file_sha256(rules)
    assert load_runtime_weapon_profile_publication(army, None) == (None, None)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("source", "does not match the current PDF"),
        ("profile", "profile changed"),
        ("page", "Incomplete reviewed Weapon entry"),
        ("missing-review", "lack reviewed chart citations"),
        ("duplicate-review", "Duplicate reviewed Weapon"),
        ("missing-reason", "Incomplete reviewed Weapon entry"),
        ("changed-name", "Reviewed Weapon identity changed"),
        ("invalid-format", "Unsupported reviewed Weapon source policy"),
    ),
)
def test_builder_rejects_stale_or_incomplete_review(
    tmp_path: Path, mutation: str, message: str,
) -> None:
    policy = json.loads(DEFAULT_REVIEWS.read_text(encoding="utf-8"))
    if mutation == "source":
        policy["sourceSha256"] = "0" * 64
    elif mutation == "profile":
        policy["reviews"][0]["profileSha256"] = "0" * 64
    elif mutation == "page":
        policy["reviews"][0]["chartPage"] = 189
    elif mutation == "missing-review":
        policy["reviews"].pop(0)
    elif mutation == "duplicate-review":
        policy["reviews"].append(deepcopy(policy["reviews"][0]))
    elif mutation == "missing-reason":
        policy["reviews"][0]["reason"] = ""
    elif mutation == "changed-name":
        policy["reviews"][0]["name"] = "Incorrect identity"
    elif mutation == "invalid-format":
        policy["format"] = "unreviewed"
    with pytest.raises(ValueError, match=message):
        build_publication(DEFAULT_ARMY, DEFAULT_RULES, _write(tmp_path / "reviews.json", policy))


def test_embedded_weapon_diagnostic_rejects_corrupted_relational_citations(
    tmp_path: Path,
) -> None:
    rules = tmp_path / "rules_n5.db"
    shutil.copyfile(DEFAULT_RULES, rules)
    with sqlite3.connect(rules) as connection:
        connection.execute(
            "DELETE FROM weapon_chart_profile_citations "
            "WHERE rowid=(SELECT MIN(rowid) FROM weapon_chart_profile_citations)"
        )
    with pytest.raises(ValueError):
        check_embedded_profiles(DEFAULT_ARMY, rules, DEFAULT_REVIEWS)
