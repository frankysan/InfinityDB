"""Select a source-matched checkout runtime without changing Docker release behavior.

The normal local build produces a complete ignored runtime alongside the
tracked release database. Explicit database paths always bypass this selection.
"""
from __future__ import annotations

from pathlib import Path

from infinity_db.rules_database import RulesDatabase
from infinity_db.variant_usage_reference import load_variant_usage_publication
from infinity_db.weapon_profile_publication import (
    file_sha256,
    load_weapon_profile_publication,
)

DEFAULT_ARMY_DATABASE = Path("data/generated/infinity.db")
DEFAULT_STANDALONE_RULES = Path("local/rules-standalone.db")
DEFAULT_CHECKOUT_RUNTIME = Path("local/checkout-runtime")
RUNTIME_FILES = frozenset({
    "infinity.db", "rules.db", "variant-usage.json", "weapon-profile-sources.json",
})


def select_checkout_database(
    *,
    tracked_army: Path = DEFAULT_ARMY_DATABASE,
    standalone_rules: Path = DEFAULT_STANDALONE_RULES,
    checkout: Path = DEFAULT_CHECKOUT_RUNTIME,
) -> Path:
    """Use the complete local build if present; reject stale or mixed snapshots."""
    if not checkout.exists():
        return tracked_army

    message = "Local checkout runtime is incomplete or stale; rerun 'infinity-db build-rules'"
    if not checkout.is_dir() or {entry.name for entry in checkout.iterdir()} != RUNTIME_FILES:
        raise ValueError(message)
    army = checkout / "infinity.db"
    rules_path = checkout / "rules.db"
    if (
        not tracked_army.is_file()
        or not standalone_rules.is_file()
        or file_sha256(army) != file_sha256(tracked_army)
        or file_sha256(rules_path) != file_sha256(standalone_rules)
    ):
        raise ValueError(message)

    rules = RulesDatabase(rules_path)
    rules.validate()
    if rules.deployed_objects_payload(army) is None:
        raise ValueError(message)
    variants = load_variant_usage_publication(
        checkout / "variant-usage.json", army, rules_path,
    )
    if variants is None or variants["formatVersion"] != 2:
        raise ValueError(message)
    if load_weapon_profile_publication(
        checkout / "weapon-profile-sources.json", army, rules_path,
    ) is None:
        raise ValueError(message)
    return army.resolve()
