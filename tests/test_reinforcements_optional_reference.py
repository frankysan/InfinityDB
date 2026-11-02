"""Protect optional N4-origin Reinforcements references in the N5-era player catalog.

These assertions cover the source boundary, not verified N5 adoption of N4 procedures.
"""

from __future__ import annotations

from pathlib import Path

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.database.repository import Database
from infinity_db.reference_catalog import RulesRecordCatalog
from infinity_db.rules_database import RulesDatabase
from infinity_db.skill_catalog import SkillCatalog
from tools.release_rules_export import export_release_rules

ROOT = Path(__file__).resolve().parents[1]
ANNEX = ROOT / "data/curated/rules/reinforcements-extra-n4-reference.json"


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
    assert records["skill:commlink"]["variantSemantics"] == {"inheritance": "family"}
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
    army = Database(ROOT / "data/generated/infinity.db")

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
