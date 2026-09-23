from pathlib import Path

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.state_catalog import StateCatalog


def test_state_catalog_exposes_reviewed_states_and_reverse_relations(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    catalog = StateCatalog(RulesDatabase(rules_path))

    states = {item["id"]: item for item in catalog.list_states()}
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


def test_state_catalog_without_rules_is_empty() -> None:
    catalog = StateCatalog(None)
    assert catalog.list_states() == []
    assert catalog.get_state("unconscious") is None
