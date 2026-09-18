"""Weapon-family classification backed by validated project configuration."""

from __future__ import annotations

import re

from .weapon_config import load_weapon_category_config

_CONFIG = load_weapon_category_config()
WEAPON_CATEGORIES = _CONFIG.categories


def weapon_category(name: object, weapon_id: int | None = None) -> str:
    """Classify a weapon name using maintained policy and generic matching mechanics."""

    if weapon_id is not None and weapon_id in _CONFIG.overrides:
        return _CONFIG.overrides[weapon_id]
    text = str(name or "")
    for rule in _CONFIG.rules:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in rule.patterns):
            return rule.name
    return _CONFIG.fallback_category
