"""Reviewed presentation identities for independently published Scenario Skills.

The identity mapping is deliberately separate from versioned source definitions.
Only enumerated source occurrences (or an explicit pinned sharedSkill identity)
may merge. A matching name alone is never evidence of equivalence.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

# Same objective/action in both reviewed ITS seasons, unless noted otherwise.
# Target-specific acquisition, extraction, neutralization and scoring actions
# are not merged merely because they have similar declaration mechanics.
_FAMILIES = (
    ("scenario-activate-antenna", "Activate Antenna",
     "Activate an Antenna for the player. The declaring Trooper, Roll and "
     "activation consequences depend on the scenario and Antenna condition.",
     (("crossing-lines", "activate-antenna"), ("double-bind", "activate-antenna"),
      ("double-bind", "activate-antenna-destroyed"),
      ("uplink-center", "activate-communication-antenna"),
      ("area-of-interest", "activate-communication-antenna"))),
    ("scenario-activate-console", "Activate Console",
     "A Specialist Troop in contact with a Console attempts to Activate it. "
     "Successful Activation and any limits are defined by the scenario.",
     (("hardlock", "activate-console"), ("b-pong", "activate-console"))),
    ("scenario-hack-consoles", "Hack Consoles",
     "A Specialist Troop in Silhouette contact with a Console makes a WIP Roll "
     "to Hack it. The MOD and ownership/scoring rules depend on the scenario.",
     (("superiority", "hack-consoles"),)),
    ("scenario-pick-up-supply-boxes", "Pick Up Supply Boxes",
     "Pick up a Supply Box in Silhouette contact, subject to the scenario's "
     "eligibility, Roll and carrying requirements.",
     (("provisioning", "pickup-supply-boxes"),)),
    ("scenario-extract-supply-boxes", "Extract Supply Boxes",
     "A Specialist Troop attempts to Extract a Supply Box from a Tech-Coffin.",
     (("provisioning", "extract-supply-boxes"),)),
    ("scenario-pick-up-beacon", "Pick Up Beacon",
     "Pick up the Enemy Beacon after satisfying the Console and contact requirements.",
     (("hardlock", "pick-up-beacon"),)),
    ("scenario-relocate-tracking-beacon", "Relocate the Tracking Beacon",
     "A Specialist Troop in contact with the Tracking Beacon relocates it without a Roll.",
     (("b-pong", "relocate-tracking-beacon"),)),
    ("scenario-activate-extraction-console", "Activate Extraction Console",
     "A Specialist Troop uses an Extraction Console to extract a CivEvaced model.",
     (("evacuation", "activate-extraction-console"),)),
    ("scenario-download-id", "Download ID",
     "A Specialist Troop uses an ID Scanner to acquire an ID Token.",
     (("last-launch", "download-id"),)),
    ("scenario-swap-id", "Swap ID",
     "Transfer an ID Token from an allied Trooper in contact without a Roll.",
     (("last-launch", "swap-id"),)),
    ("scenario-extract-identified-trooper", "Extract Identified Trooper",
     "An ID-carrying Trooper at the ID Checker can extract without a Roll.",
     (("last-launch", "extract-identified-trooper"),)),
    ("scenario-pick-up-prototype", "Pick Up Enemy Prototype",
     "Pick up the enemy Prototype in contact without a Roll.",
     (("corporate-appropriation", "pick-up-prototype"),)),
    ("scenario-use-panoply", "Use Panoply",
     "Use a Panoply in Silhouette contact to acquire equipment or cancel Unloaded State.",
     (("corporate-appropriation", "use-panoply"),)),
    ("scenario-stabilize-infected", "Stabilize Infected",
     "An eligible medical or Specialist Operative Trooper attempts to Stabilize an Infected.",
     (("outbreak", "stabilize-infected"),)),
    ("scenario-scan-infected", "Scan Infected",
     "An eligible medical or Specialist Operative Trooper attempts to Scan an Infected.",
     (("outbreak", "scan-infected"),)),
    ("scenario-extract-data-pack", "Extract Data Pack (Attacker Only)",
     "An Attacker Specialist Troop attempts to Extract a Data Pack from the Data Console.",
     (("critical-intervention", "extract-data-pack"),)),
    ("scenario-use-inhibitor-antenna", "Use Inhibitor Antenna",
     "A Specialist Troop uses the Inhibitor Antenna to unlock the Data Console "
     "or operate the defense system, subject to side restrictions.",
     (("critical-intervention", "use-inhibitor-antenna"),)),
    ("scenario-emit-akial-interference", "Emit Akial Interference",
     "Use the Akial Antenna to cancel an opponent's accomplished Common Classified Objective.",
     (("akial-interference", "emit-akial-interference"),)),
    ("scenario-filter-signal", "Filter the Signal",
     "Use the Akial Antenna to replace a Common Classified Objective card.",
     (("akial-interference", "filter-signal"),)),
)

# Membership is source-scoped, not name-derived.
_REVIEWED = {
    f"{season}-{scenario}-{action}": (slug, name, summary)
    for slug, name, summary, occurrences in _FAMILIES
    for scenario, action in occurrences
    for season in ("its-17", "its-18")
    if scenario != "double-bind" or season == "its-18"
}
_REVIEWED["hack-consoles"] = _REVIEWED["its-18-superiority-hack-consoles"]
_REVIEWED["pick-up-supply-boxes"] = _REVIEWED["its-18-provisioning-pickup-supply-boxes"]


def _mechanics(rule: dict[str, Any]) -> dict[str, Any]:
    facts = {key: value for key, value in rule["facts"].items() if key != "applicability"}
    return {
        "name": rule["name"], "summary": rule.get("summary", ""), "facts": facts,
        "skill_types": rule.get("skill_types", []), "labels": rule.get("labels", []),
    }


def _unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _common(values: list[list[Any]]) -> list[Any]:
    return [value for value in values[0] if all(value in other for other in values[1:])]


def _contexts(uses: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return _unique([context for use in uses for context in (
        [use["scenario"]] if key == "scenarios" and "scenario" in use
        else use.get(key, [])
    )])


def _combined_rule(
    uses: list[dict[str, Any]], slug: str, name: str, summary: str,
) -> dict[str, Any]:
    rules = [use["rules"][0] for use in uses]
    first = rules[0]
    identical = all(_mechanics(rule) == _mechanics(first) for rule in rules)
    if identical:
        result = deepcopy(first)
    else:
        # No context-specific clause or label is promoted to a universal claim.
        facts = {"category": first["facts"]["category"]}
        for key in ("requirements", "effects", "restrictions", "clarifications", "sourceNotes"):
            common = _common([rule["facts"].get(key, []) for rule in rules])
            if common:
                facts[key] = common
        result = {
            "kind": "skill", "summary": summary, "facts": facts,
            "skill_types": _common([rule.get("skill_types", []) for rule in rules]),
            "labels": _common([rule.get("labels", []) for rule in rules]),
        }
    result["id"] = f"skill:{slug}"
    result["name"] = name
    scenarios = _contexts(uses, "scenarios")
    seasons = _contexts(uses, "seasons")
    result["scope"] = {
        "game": "N5",
        "seasons": _unique([context["collection"] for context in scenarios + seasons]),
        "scenarios": _unique([context["id"] for context in scenarios]),
    }
    if scenarios:
        result["applicable_scenarios"] = deepcopy(scenarios)
    result["citations"] = deepcopy(_unique([
        cite for rule in rules for cite in rule.get("citations", [])
    ]))
    return result


def consolidate_family(
    slug: str, name: str, summary: str, uses: list[dict[str, Any]],
) -> dict[str, Any]:
    """One public identity, with exact contextual cards when definitions differ."""
    canonical = deepcopy(uses[0])
    canonical.update(id=slug, slug=slug, name=name)
    canonical.pop("scenario", None)
    scenarios = _contexts(uses, "scenarios")
    seasons = _contexts(uses, "seasons")
    if scenarios:
        canonical["scenarios"] = scenarios
    if seasons:
        canonical["seasons"] = seasons
    canonical["aliases"] = [use["slug"] for use in uses if use["slug"] != slug]
    canonical["alternate_names"] = _unique([
        use["name"] for use in uses if use["name"] != name
    ])
    canonical["categories"] = _unique([
        category for use in uses for category in use["categories"]
    ])
    canonical["rules"] = [_combined_rule(uses, slug, name, summary)]
    variants: list[list[dict[str, Any]]] = []
    for use in uses:
        rule = use["rules"][0]
        matching = next(
            (group for group in variants if _mechanics(group[0]["rules"][0])
             == _mechanics(rule)), None,
        )
        if matching is None:
            variants.append([use])
        else:
            matching.append(use)
    if len(variants) > 1:
        # The exact definition for each context remains available. Keep each
        # original citation and scope, even when multiple variants are similar.
        canonical["context_variants"] = [
            {
                "scenarios": _contexts(group, "scenarios"),
                "seasons": _contexts(group, "seasons"),
                "rules": [deepcopy(use["rules"][0]) for use in group],
            }
            for group in variants
        ]
    return canonical


def consolidate_scenario_actions(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Validate pinned definitions before grouping reviewed presentation identities."""
    aliases = {item["slug"]: deepcopy(item) for item in items}
    if len(aliases) != len(items):
        raise ValueError("Duplicate scoped Scenario Skill route")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    names: dict[str, tuple[str, str]] = {}
    pinned: dict[tuple[str, str], dict[str, Any]] = {}
    origins: dict[str, Any] = {}
    published = []
    for item in items:
        rule = item["rules"][0]
        shared = rule.get("sharedSkill")
        if shared is not None:
            identifier = shared["id"]
            slug = identifier.removeprefix("skill:")
            if identifier in origins and origins[identifier] != shared.get("origin"):
                raise ValueError(f"Conflicting origin for shared scenario Skill {identifier!r}")
            origins[identifier] = shared.get("origin")
            if not shared.get("overriddenFields"):
                key = (identifier, shared["version"])
                prior = pinned.setdefault(key, rule)
                if _mechanics(prior) != _mechanics(rule):
                    raise ValueError(
                        f"Conflicting facts for pinned shared scenario Skill {identifier!r}"
                    )
            name = item["name"]
            summary = "This Skill has context-specific definitions. Use the applicable rule below."
        elif item["slug"] in _REVIEWED:
            slug, name, summary = _REVIEWED[item["slug"]]
        else:
            published.append(item)
            continue
        names.setdefault(slug, (name, summary))
        groups[slug].append(item)
    for slug, uses in groups.items():
        if slug in aliases or any(item["slug"] == slug for item in published):
            raise ValueError(f"Canonical Scenario Skill {slug!r} conflicts with a route")
        name, summary = names[slug]
        canonical = consolidate_family(slug, name, summary, uses)
        published.append(canonical)
        for use in uses:
            aliases[use["slug"]]["canonical_slug"] = slug
    return published, aliases
