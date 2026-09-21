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
    resolve_weapon_category_config,
    resolve_weapon_override_config,
)
from infinity_army_data.weapon_profiles import weapon_name_override, weapon_profile_override

SOURCE_WEAPON_NAMES = {
    1: "Akrylat-Kanone",
    14: "Blitzen",
    18: "Chain Rifle",
    62: "Monofilament Mine",
    63: "Viral Mine",
    82: "Flammenspeer",
    96: "Drop Bears",
    174: "Cybermine",
    177: "Trench-Hammer",
    182: "WildParrot",
    196: "Shock Mine",
    197: "E/M Mine",
    199: "AP Mine",
    217: "Spitfire MULTI",
    220: "PARA Mine",
    226: "Armed Turret",
}


def _document(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_weapon_category_config_preserves_order_and_slug_authored_overrides() -> None:
    authored = load_weapon_category_config()
    config = resolve_weapon_category_config(authored, SOURCE_WEAPON_NAMES)

    assert authored.overrides["trench-hammer"] == "CC Weapons"
    assert config.categories.index("Grenade Launchers") < config.categories.index("Grenades")
    assert config.categories.index("Sniper Rifles") < config.categories.index("Rifles")
    assert config.categories[-1] == "Uncategorized"
    assert config.overrides[177] == "CC Weapons"
    assert config.overrides[174] == "Mines"
    assert config.overrides[18] == "Uncategorized"


def test_weapon_classifier_keeps_specific_rules_before_broad_rules() -> None:
    assert weapon_category("Light Grenade Launcher") == "Grenade Launchers"
    assert weapon_category("MULTI Sniper Rifle") == "Sniper Rifles"


def test_weapon_override_config_contains_current_slug_authored_corrections() -> None:
    authored = load_weapon_override_config()
    config = resolve_weapon_override_config(authored, SOURCE_WEAPON_NAMES)

    assert authored.profile_overrides["monofilament-mine"] == "ARM=0, BTS=0, STR=1, S=1"
    assert config.profile_overrides[62] == "ARM=0, BTS=0, STR=1, S=1"
    assert config.profile_overrides[220] == "ARM=0, BTS=0, STR=1, S=1"
    assert config.name_overrides[217] == "MULTI Spitfire"
    assert [
        (suppression.name, suppression.mode)
        for suppression in config.metadata_profile_suppressions[226]
    ] == [
        ("Armed Turret", None),
        ("Armed Turret", "PARA CC Weapon"),
    ]


def test_weapon_config_numeric_references_remain_supported() -> None:
    category_document = _document("config/catalogs/weapon-categories.json")
    category_document["overrides"][0]["weapon_id"] = 177
    category = resolve_weapon_category_config(
        parse_weapon_category_config(category_document), SOURCE_WEAPON_NAMES
    )
    assert category.overrides[177] == "CC Weapons"

    override_document = _document("config/catalogs/weapon-overrides.json")
    override_document["corrections"][0]["weapon_id"] = 62
    corrections = resolve_weapon_override_config(
        parse_weapon_override_config(override_document), SOURCE_WEAPON_NAMES
    )
    assert corrections.profile_overrides[62] == "ARM=0, BTS=0, STR=1, S=1"


def test_weapon_config_slug_resolution_fails_on_ambiguity() -> None:
    authored = parse_weapon_category_config(
        {
            **_document("config/catalogs/weapon-categories.json"),
            "overrides": [
                {
                    "weapon_id": "same-name",
                    "category": "Mines",
                    "reason": "test",
                }
            ],
        }
    )
    with pytest.raises(WeaponConfigError, match="ambiguous"):
        resolve_weapon_category_config(authored, {1: "Same Name", 2: "Same Name"})


def test_unconfigured_weapon_has_no_source_correction() -> None:
    assert weapon_name_override(999999) is None
    assert weapon_profile_override(999999) is None


def test_weapon_configs_are_independent_of_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    categories = resolve_weapon_category_config(load_weapon_category_config(), SOURCE_WEAPON_NAMES)
    corrections = resolve_weapon_override_config(load_weapon_override_config(), SOURCE_WEAPON_NAMES)
    assert categories.overrides[177] == "CC Weapons"
    assert corrections.name_overrides[217] == "MULTI Spitfire"


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


def test_weapon_category_config_rejects_duplicate_override_refs() -> None:
    document = _document("config/catalogs/weapon-categories.json")
    document["overrides"].append(copy.deepcopy(document["overrides"][0]))

    with pytest.raises(WeaponConfigError, match="duplicate weapon reference 'trench-hammer'"):
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


def test_weapon_override_config_rejects_duplicate_refs() -> None:
    document = _document("config/catalogs/weapon-overrides.json")
    document["corrections"].append(copy.deepcopy(document["corrections"][0]))

    with pytest.raises(WeaponConfigError, match="duplicate weapon reference 'monofilament-mine'"):
        parse_weapon_override_config(document)


def test_weapon_override_config_requires_a_correction_action() -> None:
    document = _document("config/catalogs/weapon-overrides.json")
    document["corrections"][0].pop("profile")

    with pytest.raises(WeaponConfigError, match="must define name, profile, and/or"):
        parse_weapon_override_config(document)


def test_weapon_override_config_validates_metadata_profile_suppressions() -> None:
    document = _document("config/catalogs/weapon-overrides.json")
    turret = next(item for item in document["corrections"] if item["weapon_id"] == "armed-turret")
    turret["suppress_metadata_profiles"] = []

    with pytest.raises(WeaponConfigError, match="must be a non-empty array"):
        parse_weapon_override_config(document)

    document = _document("config/catalogs/weapon-overrides.json")
    turret = next(item for item in document["corrections"] if item["weapon_id"] == "armed-turret")
    turret["suppress_metadata_profiles"].append(
        copy.deepcopy(turret["suppress_metadata_profiles"][0])
    )
    with pytest.raises(WeaponConfigError, match="duplicate matcher"):
        parse_weapon_override_config(document)
