from pathlib import Path
from typing import Any

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.state_catalog import StateCatalog


def test_state_catalog_exposes_reviewed_states_and_reverse_relations(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    catalog = StateCatalog(RulesDatabase(rules_path))

    states = {item["id"]: item for item in catalog.list_states()}
    assert len(states) == 24
    assert {
        "dead",
        "engaged",
        "holoecho",
        "holomask",
        "normal",
        "prone",
        "possessed",
        "retreat",
        "sepsitorized",
        "suppressive-fire",
    } <= states.keys()
    assert "unconscious" in states
    assert "immobilized-a" in states
    assert "targeted" in states
    assert "unloaded" in states
    assert states["unconscious"]["name"] == "Unconscious State"

    unconscious = catalog.get_state("unconscious")
    assert unconscious is not None
    relations = {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in unconscious["rules"][0]["display_relations"]
    }
    assert ("cancels-state", "inbound", "Doctor") in relations
    assert ("cancels-state", "inbound", "Engineer") in relations

    targeted = catalog.get_state("targeted")
    assert targeted is not None
    assert ("cancels-state", "inbound", "Engineer") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in targeted["rules"][0]["display_relations"]
    }

    unloaded = catalog.get_state("unloaded")
    assert unloaded is not None
    assert ("causes-state", "inbound", "Disposable (X)") in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in unloaded["rules"][0]["display_relations"]
    }

    suppressive_fire = catalog.get_state("suppressive-fire")
    assert suppressive_fire is not None
    suppressive_relations = {
        (relation["type"], relation["direction"], relation["record"]["id"])
        for relation in suppressive_fire["rules"][0]["display_relations"]
    }
    assert ("enters-state", "inbound", "skill:suppressive-fire") in suppressive_relations
    assert ("cancels-state", "inbound", "state:dead") in suppressive_relations
    assert ("cancels-state", "inbound", "state:retreat") in suppressive_relations


def test_state_catalog_caches_composed_records_and_isolates_detail_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules = RulesDatabase(rules_path)
    original = rules.composed_records_by_kind
    calls = 0

    def composed_records_by_kind(kind: str) -> list[dict[str, Any]]:
        nonlocal calls
        calls += 1
        return original(kind)

    monkeypatch.setattr(rules, "composed_records_by_kind", composed_records_by_kind)
    catalog = StateCatalog(rules)

    catalog.list_states()
    first = catalog.get_state("unconscious")
    second = catalog.get_state("unconscious")

    assert calls == 1
    assert first is not None
    assert second is not None
    first["rules"][0]["name"] = "mutated"
    assert second["rules"][0]["name"] == "Unconscious State"
    third = catalog.get_state("unconscious")
    assert third is not None
    assert third["rules"][0]["name"] == "Unconscious State"


def test_state_catalog_without_rules_is_empty() -> None:
    catalog = StateCatalog(None)
    assert catalog.list_states() == []
    assert catalog.get_state("unconscious") is None
