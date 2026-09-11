"""Rules-owned weapon family classifications for normalized Army data.

Update ``WEAPON_CATEGORY_RULES`` when the game adds, renames, or reclassifies a
weapon family. Rules are evaluated in order, so put more specific families
before their broader counterparts (for example, Grenade Launchers before
Grenades and Sniper Rifles before Rifles).
"""

from __future__ import annotations

import re

WEAPON_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Bows", (r"\bbow\b",)),
    ("Carbines", (r"\bcarbine\b",)),
    ("CC Weapons", (r"\bcc weapon\b", r"\bclose combat weapon\b")),
    ("Disposable Support Weapons", (r"\bpanzerfaust\b", r"\bfaust\b", r"\bdeployer\b")),
    ("Flamethrowers", (r"\bflamethrower\b",)),
    ("Grenade Launchers", (r"\bgrenade launcher\b", r"\bgl\b")),
    ("Grenades", (r"\bgrenades?\b",)),
    ("Heavy Machine Guns", (r"\bheavy machine gun\b", r"\bhmg\b")),
    ("Marksman Rifles", (r"\bmarksman rifle\b",)),
    ("Mines", (r"\bmine\b",)),
    ("Pheroware Tactics (PT)", (r"\bpheroware\b", r"\bpt\b")),
    ("Pistols", (r"\bpistol\b",)),
    ("Red Furies", (r"\bred fury\b",)),
    ("Riotstoppers", (r"\briotstopper\b",)),
    ("Rocket Launchers", (r"\brocket launcher\b",)),
    ("Shotguns", (r"\bshotgun\b",)),
    ("Sniper Rifles", (r"\bsniper rifle\b",)),
    ("Spitfires", (r"\bspitfire\b",)),
    ("Submachine Guns", (r"\bsubmachine gun\b", r"\bsubmachinegun\b", r"\bsmg\b")),
    ("Thunderbolts", (r"\bthunderbolt\b",)),
    ("Rifles", (r"\brifle\b",)),
)
WEAPON_CATEGORIES = tuple(category for category, _ in WEAPON_CATEGORY_RULES) + ("Uncategorized",)
# Rules exceptions are keyed by the stable Army weapon ID. Add manual decisions
# here when a weapon name is too ambiguous for the reusable name rules above.
WEAPON_CATEGORY_OVERRIDES = {
    177: "CC Weapons",
    1: "Disposable Support Weapons",
    14: "Disposable Support Weapons",
    82: "Disposable Support Weapons",
    174: "Mines",
    96: "Mines",
    182: "Mines",
    18: "Uncategorized",
}


def weapon_category(name: object, weapon_id: int | None = None) -> str:
    """Classify a weapon name, retaining uncategorized names for future review."""
    if weapon_id in WEAPON_CATEGORY_OVERRIDES:
        return WEAPON_CATEGORY_OVERRIDES[weapon_id]
    text = str(name or "")
    for category, patterns in WEAPON_CATEGORY_RULES:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            return category
    return "Uncategorized"
