from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from infinity_army_data.weapon_categories import weapon_category
from infinity_army_data.weapon_config import (
    WeaponConfigError,
    load_weapon_category_config,
    load_weapon_override_config,
    parse_weapon_category_config,
    parse_weapon_override_config,
)
from infinity_army_data.weapon_profiles import weapon_name_override, weapon_profile_override


def _document(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_weapon_category_config_preserves_order_and_manual_overrides() -> None:
    config = load_weapon_category_config()

    assert config.categories.index("Grenade Launchers") < config.categories.index("Grenades")
    assert config.categories.index("Sniper Rifles") < config.categories.index("Rifles")
    assert config.categories[-1] == "Uncategorized"
    assert config.overrides[177] == "CC Weapons"
    assert config.overrides[174] == "Mines"
    assert config.overrides[18] == "Uncategorized"


def test_weapon_classifier_keeps_specific_rules_before_broad_rules() -> None:
    assert weapon_category("Light Grenade Launcher") == "Grenade Launchers"
    assert weapon_category("MULTI Sniper Rifle") == "Sniper Rifles"


def test_weapon_override_config_contains_current_source_corrections() -> None:
    config = load_weapon_override_config()

    assert config.profile_overrides[62] == "ARM=0, BTS=0, STR=1, S=1"
    assert config.profile_overrides[220] == "ARM=0, BTS=0, STR=1, S=1"
    assert config.name_overrides[217] == "MULTI Spitfire"


def test_unconfigured_weapon_has_no_source_correction() -> None:
    assert weapon_name_override(999999) is None
    assert weapon_profile_override(999999) is None


def test_weapon_configs_are_independent_of_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert load_weapon_category_config().overrides[177] == "CC Weapons"
    assert load_weapon_override_config().name_overrides[217] == "MULTI Spitfire"


def test_weapon_category_config_rejects_invalid_regex() -> None:
    document = _document("config/catalogs/weapon-categories.json")
    document["categories"][0]["patterns"] = ["["]

    with pytest.raises(WeaponConfigError, match="not a valid regex"):
        parse_weapon_category_config(document)


def test_weapon_category_config_rejects_unknown_override_target() -> None:
    document = _document("config/catalogs/weapon-categories.json")
    document["overrides"][0]["category"] = "Not a category"

    with pytest.raises(WeaponConfigError, match="must name a declared category"):
        parse_weapon_category_config(document)


def test_weapon_category_config_rejects_duplicate_override_ids() -> None:
    document = _document("config/catalogs/weapon-categories.json")
    document["overrides"].append(copy.deepcopy(document["overrides"][0]))

    with pytest.raises(WeaponConfigError, match="duplicate weapon ID 177"):
        parse_weapon_category_config(document)


def test_weapon_category_config_requires_fallback_last_and_patternless() -> None:
    document = _document("config/catalogs/weapon-categories.json")
    fallback = document["categories"].pop()
    document["categories"].insert(0, fallback)

    with pytest.raises(WeaponConfigError, match="fallback category must be the final category"):
        parse_weapon_category_config(document)

    document = _document("config/catalogs/weapon-categories.json")
    document["categories"][-1]["patterns"] = ["uncategorized"]
    with pytest.raises(WeaponConfigError, match="must not define regex patterns"):
        parse_weapon_category_config(document)


def test_weapon_override_config_rejects_duplicate_ids() -> None:
    document = _document("config/catalogs/weapon-overrides.json")
    document["corrections"].append(copy.deepcopy(document["corrections"][0]))

    with pytest.raises(WeaponConfigError, match="duplicate weapon ID 62"):
        parse_weapon_override_config(document)


def test_weapon_override_config_requires_name_or_profile() -> None:
    document = _document("config/catalogs/weapon-overrides.json")
    document["corrections"][0].pop("profile")

    with pytest.raises(WeaponConfigError, match="must define name and/or profile"):
        parse_weapon_override_config(document)
