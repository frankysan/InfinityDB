"""Source, identity and release-integrity checks for Weapon Chart locators."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from infinity_db.database.repository import Database
from infinity_db.weapon_profile_publication import (
    file_sha256,
    load_weapon_profile_publication,
    profile_sha256,
)
from tools.audit_enrichment_coverage import audit_coverage
from tools.audit_weapon_chart_profiles import audit_chart
from tools.build_weapon_profile_publication import (
    DEFAULT_ARMY,
    DEFAULT_OUTPUT,
    DEFAULT_REVIEWS,
    DEFAULT_RULES,
    build_publication,
    check_publication,
    publication_bytes,
)

PDF_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"


@pytest.fixture(scope="module")
def publication() -> dict[str, Any]:
    return json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))


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


def test_weapon_profile_publication_rebuilds_to_exact_tracked_bytes(
    publication: dict[str, Any],
) -> None:
    rebuilt = build_publication(DEFAULT_ARMY, DEFAULT_RULES, DEFAULT_REVIEWS)
    assert publication_bytes(rebuilt) == publication_bytes(publication)
    assert publication_bytes(rebuilt) == DEFAULT_OUTPUT.read_bytes()
    check_publication(DEFAULT_ARMY, DEFAULT_RULES, DEFAULT_REVIEWS, DEFAULT_OUTPUT)


def test_pinned_pdf_contains_every_published_weapon_profile_mode_and_page(
    publication: dict[str, Any],
) -> None:
    root = Path(__file__).resolve().parents[1]
    pdf = root / "data/pdf/rules/n5-rules-v5.3-en.pdf"
    if not pdf.is_file():
        pytest.skip("Ignored N5.3 PDF unavailable")
    pytest.importorskip("fitz")
    report = audit_chart(pdf, DEFAULT_ARMY)
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


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("army", "does not match release databases"),
        ("rules", "does not match release databases"),
        ("review", "lacks review provenance"),
        ("source", "source does not match current rules"),
        ("fingerprint", "profile identity changed"),
        ("slug", "profile identity changed"),
        ("page", "Invalid or duplicate reviewed Weapon mode"),
        ("duplicate", "Invalid or duplicate reviewed Weapon mode"),
        ("missing-mode", "modes do not match"),
        ("unknown-mode", "modes do not match"),
    ),
)
def test_loader_rejects_stale_or_ambiguous_publication(
    tmp_path: Path, publication: dict[str, Any], mutation: str, message: str,
) -> None:
    document = deepcopy(publication)
    weapon = next(item for item in document["weapons"] if item["slug"] == "uragan-mrl")
    if mutation == "army":
        document["sourceSnapshot"]["armyDatabaseSha256"] = "0" * 64
    elif mutation == "rules":
        document["sourceSnapshot"]["rulesDatabaseSha256"] = "0" * 64
    elif mutation == "review":
        document["sourceSnapshot"]["reviewsSha256"] = "invalid"
    elif mutation == "source":
        document["source"]["sha256"] = "0" * 64
    elif mutation == "fingerprint":
        weapon["profileSha256"] = "0" * 64
    elif mutation == "slug":
        weapon["slug"] = "not-uragan"
    elif mutation == "page":
        weapon["profiles"][0]["page"] = 189
    elif mutation == "duplicate":
        weapon["profiles"].append(deepcopy(weapon["profiles"][0]))
    elif mutation == "missing-mode":
        weapon["profiles"].pop()
    elif mutation == "unknown-mode":
        weapon["profiles"][0]["mode"] = "Unknown Mode"
    with pytest.raises(ValueError, match=message):
        load_weapon_profile_publication(
            _write(tmp_path / "weapon-profile-sources.json", document),
            DEFAULT_ARMY,
            DEFAULT_RULES,
        )


def test_missing_or_malformed_publication_is_explicit(
    tmp_path: Path, publication: dict[str, Any],
) -> None:
    path = tmp_path / "weapon-profile-sources.json"
    assert load_weapon_profile_publication(path, DEFAULT_ARMY, DEFAULT_RULES) is None
    with pytest.raises(ValueError, match="missing or differs"):
        check_publication(DEFAULT_ARMY, DEFAULT_RULES, DEFAULT_REVIEWS, path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid Weapon profile publication JSON"):
        load_weapon_profile_publication(path, DEFAULT_ARMY, DEFAULT_RULES)
    _write(path, publication)
    with pytest.raises(ValueError, match="requires a rules database"):
        load_weapon_profile_publication(path, DEFAULT_ARMY, None)


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


def test_deployment_check_rejects_changed_publication_bytes(
    tmp_path: Path, publication: dict[str, Any],
) -> None:
    document = deepcopy(publication)
    document["weapons"][0]["profiles"][0]["page"] += 1
    path = _write(tmp_path / "weapon-profile-sources.json", document)
    with pytest.raises(ValueError, match="missing or differs"):
        check_publication(DEFAULT_ARMY, DEFAULT_RULES, DEFAULT_REVIEWS, path)
