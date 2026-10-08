from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.audit_weapon_trait_cross_sources import (
    WeaponTraitWikiError,
    _load_review,
    markdown_report,
    reconcile_candidates,
    wiki_chart_rows,
)


def _row(name: str, traits: str, rolls: str = "1") -> str:
    columns = [name, *([""] * 7), "7", "1", "DA", "ARM", rolls, traits]
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in columns) + "</tr>"


def _candidate(name: str = "Kobra Pistol") -> dict[str, Any]:
    return {
        "page": 182, "name": name, "mode": "CC Mode",
        "status": "candidate-discrepancy", "printedTraits": ["CC", "[*]"],
        "armyProperties": ["Anti-materiel", "CC", "[*]"],
    }


def _mapping(name: str = "Kobra Pistol") -> list[dict[str, Any]]:
    return [{"name": name, "mode": "CC Mode", "wikiName": "Kobra Pistol (CC Mode)",
             "reviewNote": "Review against sources."}]


def _reviewed() -> dict[str, Any]:
    return {"traitAliases": {}, "combinedFootnotes": {}, "verifiedSourceCells": {}}


def test_wiki_chart_ignores_superseded_profile_and_preserves_its_provenance() -> None:
    html = (
        '<script>var meta={"wgRevisionId":4083};</script>'
        '<div class="original_border"><table>'
        + _row("Kobra Pistol (CC Mode)", "CC, [*]")
        + '</table></div><div class="errata_border"><table>'
        + _row("Kobra Pistol (CC Mode)", "Anti-materiel, CC, [*]", "2")
        + "</table></div>"
    )
    revision, rows, superseded = wiki_chart_rows(
        html.encode(), {"Kobra Pistol (CC Mode)"}
    )
    assert revision == 4083
    assert rows["Kobra Pistol (CC Mode)"]["savingRolls"] == "2"
    assert rows["Kobra Pistol (CC Mode)"]["traits"] == "Anti-materiel, CC, [*]"
    assert superseded["Kobra Pistol (CC Mode)"][0]["savingRolls"] == "1"


def test_wiki_comparison_never_silently_resolves_source_discrepancy() -> None:
    result = reconcile_candidates(
        [_candidate()],
        {"Kobra Pistol (CC Mode)": {
            "savingRolls": "2", "ammunition": "DA",
            "traits": "Anti-materiel, CC, [*]",
        }},
        _mapping(), _reviewed(),
    )
    assert result[0]["status"] == "wiki-agrees-with-army"
    assert result[0]["pdfTraits"] == ["CC", "[*]"]
    assert result[0]["wikiSavingRolls"] == "2"


def test_wiki_comparison_fails_on_stale_or_ambiguous_review_identities() -> None:
    with pytest.raises(WeaponTraitWikiError, match="no longer match"):
        reconcile_candidates([_candidate()], {}, _mapping("Wrong"), _reviewed())
    with pytest.raises(WeaponTraitWikiError, match="no longer match"):
        reconcile_candidates([_candidate()], {}, _mapping() * 2, _reviewed())
    with pytest.raises(WeaponTraitWikiError, match="Missing Wiki chart"):
        reconcile_candidates([_candidate()], {}, _mapping(), _reviewed())


def test_wiki_source_review_requires_exact_pdf_revision_and_member_hash(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / (
        "config/validation/weapon-trait-wiki-review.json"
    )
    review = json.loads(source.read_text(encoding="utf-8"))
    mapping = _load_review(source, review["corePdfSha256"])
    assert len(mapping) == 9
    assert sum(item["semanticReview"]["state"] == "explained" for item in mapping) == 5
    assert sum(item["semanticReview"]["state"] == "partial" for item in mapping) == 4
    assert {item["name"] for item in mapping} == {
        "Cybermine", "Drop Bears", "PARA Mine", "WildParrot", "PT: Endgame",
        "PT: Eraser", "PT: Mirrorball", "Kobra Pistol", "Sepsitor Plus",
    }
    review["wikiMemberSha256"] = "invalid"
    local = tmp_path / "bad-review.json"
    local.write_text(json.dumps(review), encoding="utf-8", newline="\n")
    with pytest.raises(WeaponTraitWikiError, match="exact source"):
        _load_review(local, review["corePdfSha256"])
    with pytest.raises(WeaponTraitWikiError, match="not pinned"):
        _load_review(source, "f" * 64)


def test_cross_source_report_keeps_source_evidence_visible() -> None:
    report = {
        "corePdfSha256": "p" * 64, "wikiArchiveSha256": "w" * 64,
        "wikiRevisionId": 4083, "wikiMemberSha256": "m" * 64,
        "armyDbSha256": "a" * 64,
        "candidates": [{
            "name": "Kobra Pistol", "mode": "CC Mode", "page": 182,
            "status": "wiki-agrees-with-army", "wikiName": "Kobra Pistol (CC Mode)",
            "pdfTraits": ["CC"], "armyTraits": ["Anti-materiel", "CC"],
            "wikiTraits": ["Anti-materiel", "CC"], "wikiSavingRolls": "2",
            "reviewNote": "Keep conflict open.",
            "supersededWikiRows": [{"savingRolls": "1", "ammunition": "SHOCK"}],
        }],
        "limitations": ["Audit only."],
    }
    text = markdown_report(report)
    assert "Wiki agrees with PDF: **0**; with Army: **1**" in text
    assert "Superseded Wiki chart row (not current)" in text
    assert "Keep conflict open" in text


def test_semantic_review_requires_source_pages_and_explicit_uncertainty(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / (
        "config/validation/weapon-trait-wiki-review.json"
    )
    review = json.loads(source.read_text(encoding="utf-8"))
    for invalid in ({"pdfPages": []}, {"state": "resolved"}, {"remaining": ""}):
        bad = json.loads(json.dumps(review))
        bad["candidates"][0]["semanticReview"].update(invalid)
        local = tmp_path / "bad-review.json"
        local.write_text(json.dumps(bad), encoding="utf-8", newline="\n")
        with pytest.raises(WeaponTraitWikiError, match="semantic review"):
            _load_review(local, review["corePdfSha256"])


def test_semantic_review_is_retained_without_overriding_source_status() -> None:
    mapping = _mapping()
    mapping[0]["semanticReview"] = {
        "classification": "saving-roll-rule-and-source-conflict", "state": "partial",
        "finding": "DA requires two rolls.", "remaining": "Anti-materiel is unresolved.",
        "pdfPages": [64, 182],
    }
    result = reconcile_candidates(
        [_candidate()], {"Kobra Pistol (CC Mode)": {
            "savingRolls": "2", "ammunition": "DA",
            "traits": "Anti-materiel, CC, [*]",
        }}, mapping, _reviewed(),
    )
    assert result[0]["status"] == "wiki-agrees-with-army"
    assert result[0]["semanticReview"] == mapping[0]["semanticReview"]
    text = markdown_report({
        "corePdfSha256": "p", "wikiArchiveSha256": "w",
        "wikiRevisionId": 4083, "wikiMemberSha256": "m", "armyDbSha256": "a",
        "candidates": result, "limitations": [],
    })
    assert "Semantic interpretations explained: **0**; partial: **1**" in text
    assert "Anti-materiel is unresolved." in text
