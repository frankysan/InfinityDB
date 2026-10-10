"""Load human-reviewed reference facts prepared from external documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infinity_db.domain_slugs import require_domain_slug, validate_typed_domain_id
from infinity_db.maintained_text import validate_maintained_text_syntax
from infinity_db.rule_relations import RULE_RELATION_TYPES
from infinity_db.scenario_definition import (
    ScenarioDefinitionError,
    parse_scenario_definition_record,
)

CURATED_FORMAT = "InfinityDB curated reference"
CURATED_FORMAT_VERSION = 23
REQUIRED_COLLECTION_FIELDS = frozenset(
    {"id", "title", "domain", "status", "effectiveFrom", "authority"}
)
REQUIRED_SOURCE_FIELDS = frozenset({"id", "kind", "title", "version", "authority"})
REQUIRED_RECORD_FIELDS = frozenset(
    {
        "id",
        "kind",
        "name",
        "summary",
        "scope",
        "citations",
        "review",
        "composition",
    }
)
REQUIRED_SKILL_TYPE_FIELDS = frozenset({"id", "name", "labels", "descriptions"})
REQUIRED_LABEL_FIELDS = frozenset({"id", "name", "description"})
EXCLUDED_CURATED_FILENAMES = frozenset({"example.json"})
ARMY_LINK_SLUG_DOMAINS = {
    "skill": "skills",
    "equipment": "equipment",
    "weapon": "weapons",
}
CATALOG_RULE_KINDS = frozenset({"skill", "equipment", "weapon"})
VARIANT_INHERITANCE_MODES = frozenset({"family", "source"})
VARIANT_PARAMETER_SOURCES = frozenset({"army-extra"})
VARIANT_PARAMETER_KINDS = frozenset({"distance"})
SOURCE_VARIANT_KINDS = frozenset({"attribute-replacement", "level", "named"})
TRAINING_ORDER_TYPES = frozenset({"regular", "irregular"})


def _validate_variant_semantics(
    value: object, context: str, army_links: list[object]
) -> str:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: must be an object")
    allowed = {"inheritance", "occurrenceParameters", "sourceVariant", "sourceMode"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{context}: unsupported fields {sorted(unknown)}")
    inheritance = value.get("inheritance")
    if inheritance not in VARIANT_INHERITANCE_MODES:
        raise ValueError(
            f"{context}: 'inheritance' must be one of "
            f"{sorted(VARIANT_INHERITANCE_MODES)}"
        )

    parameters = value.get("occurrenceParameters", [])
    if not isinstance(parameters, list):
        raise ValueError(f"{context}: 'occurrenceParameters' must be an array")
    seen_parameters: set[tuple[str, str]] = set()
    for index, parameter in enumerate(parameters):
        parameter_context = f"{context}.occurrenceParameters[{index}]"
        if not isinstance(parameter, dict):
            raise ValueError(f"{parameter_context}: must be an object")
        source = parameter.get("source")
        kind = parameter.get("kind")
        if source not in VARIANT_PARAMETER_SOURCES:
            raise ValueError(
                f"{parameter_context}: unsupported parameter source {source!r}; "
                f"expected one of {sorted(VARIANT_PARAMETER_SOURCES)}"
            )
        if kind not in VARIANT_PARAMETER_KINDS:
            raise ValueError(
                f"{parameter_context}: unsupported parameter kind {kind!r}; "
                f"expected one of {sorted(VARIANT_PARAMETER_KINDS)}"
            )
        expected_fields = {"source", "kind", "positiveSign"}
        if set(parameter) != expected_fields:
            raise ValueError(
                f"{parameter_context}: distance parameters must contain only "
                "'source', 'kind', and 'positiveSign'"
            )
        if parameter["positiveSign"] not in {"preserve", "omit", "force"}:
            raise ValueError(
                f"{parameter_context}: 'positiveSign' must be one of "
                "'preserve', 'omit', or 'force'"
            )
        key = (source, kind)
        if key in seen_parameters:
            raise ValueError(f"{parameter_context}: duplicate parameter {key!r}")
        seen_parameters.add(key)

    source_variant = value.get("sourceVariant")
    source_mode = value.get("sourceMode")
    if source_mode is not None:
        if (
            inheritance != "source"
            or len(army_links) != 1
            or not isinstance(army_links[0], dict)
            or army_links[0].get("entity") != "weapon"
        ):
            raise ValueError(f"{context}: sourceMode requires source-specific Weapon semantics")
        _require_string(source_mode, "sourceMode", context)
        if source_variant is not None:
            raise ValueError(f"{context}: sourceMode and sourceVariant are mutually exclusive")
    if inheritance == "source":
        if len(army_links) != 1:
            raise ValueError(
                f"{context}: source-specific semantics require exactly one Army link"
            )
        link = army_links[0]
        if not isinstance(link, dict) or type(link.get("id")) is not int:
            raise ValueError(
                f"{context}: source-specific semantics require an exact numeric Army source id"
            )
        if source_mode is not None:
            return inheritance
        if not isinstance(source_variant, dict):
            raise ValueError(
                f"{context}: source-specific semantics require 'sourceVariant'"
            )
        kind = source_variant.get("kind")
        if kind not in SOURCE_VARIANT_KINDS:
            raise ValueError(
                f"{context}.sourceVariant: 'kind' must be one of "
                f"{sorted(SOURCE_VARIANT_KINDS)}"
            )
        if kind == "level":
            if set(source_variant) != {"kind", "value"}:
                raise ValueError(
                    f"{context}.sourceVariant: level variants must contain only "
                    "'kind' and 'value'"
                )
            _require_positive_int(
                source_variant.get("value"), "value", f"{context}.sourceVariant"
            )
        elif kind == "named":
            if set(source_variant) != {"kind", "label"}:
                raise ValueError(
                    f"{context}.sourceVariant: named variants must contain only "
                    "'kind' and 'label'"
                )
            _require_string(
                source_variant.get("label"), "label", f"{context}.sourceVariant"
            )
        else:
            if set(source_variant) != {"kind", "attribute", "value"}:
                raise ValueError(
                    f"{context}.sourceVariant: attribute-replacement variants must "
                    "contain only 'kind', 'attribute', and 'value'"
                )
            _require_string(
                source_variant.get("attribute"),
                "attribute",
                f"{context}.sourceVariant",
            )
            _require_positive_int(
                source_variant.get("value"), "value", f"{context}.sourceVariant"
            )
    elif source_variant is not None:
        raise ValueError(
            f"{context}: family semantics must not declare 'sourceVariant'"
        )
    return inheritance


def _require_string(value: Any, field: str, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: '{field}' must be a non-empty string")


def _require_positive_int(value: Any, field: str, context: str) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{context}: '{field}' must be a positive integer")


def _validate_related_categories(facts: dict[str, Any], context: str) -> None:
    related_categories = facts.get("relatedCategories")
    if related_categories is None:
        return
    if (
        not isinstance(related_categories, list)
        or not related_categories
        or any(not isinstance(value, str) or not value for value in related_categories)
    ):
        raise ValueError(
            f"{context}.relatedCategories: must be a non-empty array of category slugs"
        )
    if len(related_categories) != len(set(related_categories)):
        raise ValueError(f"{context}.relatedCategories: must not contain duplicates")
    for index, category in enumerate(related_categories):
        require_domain_slug(
            category, context=f"{context}.relatedCategories[{index}]"
        )


def _validate_reviewed_immunity_combined_cases(value: object, context: str) -> None:
    """Validate conditional reviewed examples, never a general roll evaluator."""
    if not isinstance(value, list) or not value:
        raise ValueError(f"{context}: expected reviewed combined examples")
    seen: set[tuple[int, str]] = set()
    arm_when = {
        "immunity": "ARM", "savingAttribute": "ARM", "attackClass": "non-comms"
    }
    ap_when = {
        "immunity": "AP", "savingAttribute": "ARM", "attackClass": "non-comms"
    }
    for index, case in enumerate(value):
        item = f"{context}[{index}]"
        if not isinstance(case, dict) or set(case) != {
            "sourceAmmunitionId", "sourceAmmunitionName", "components", "when",
            "withoutImmunity", "withImmunity", "evidence",
        }:
            raise ValueError(f"{item}: invalid combined Immunity case fields")
        source_id = case["sourceAmmunitionId"]
        when = case["when"]
        if when not in (arm_when, ap_when):
            raise ValueError(f"{item}: unsupported Immunity applicability")
        identity = (source_id, when["immunity"])
        if type(source_id) is not int or source_id < 1 or identity in seen:
            raise ValueError(f"{item}: invalid or duplicate source Ammunition ID")
        seen.add(identity)
        _require_string(case["sourceAmmunitionName"], "sourceAmmunitionName", item)
        components = case["components"]
        if not isinstance(components, list) or len(components) != 2:
            raise ValueError(f"{item}: expected two reviewed component identities")
        for component in components:
            validate_typed_domain_id(
                component, expected_domain="ammunition", context=f"{item}.components"
            )
        if len(set(components)) != 2:
            raise ValueError(f"{item}: duplicate combined component")
        original = case["withoutImmunity"]
        if (
            not isinstance(original, dict)
            or set(original) != {"hitRolls", "criticalRolls"}
            or type(original["hitRolls"]) is not int
            or original["hitRolls"] < 2
            or type(original["criticalRolls"]) is not int
            or original["criticalRolls"] != original["hitRolls"] + 1
        ):
            raise ValueError(f"{item}: invalid source hit/Critical Saving Roll counts")
        if when == arm_when:
            expected = {
                "hitRolls": 1, "criticalRolls": 2, "treatedAs": "ammunition:normal"
            }
        else:
            # Only this specific AP+DA example has been reviewed; retaining DA
            # is not a general component-immunity evaluation algorithm.
            if (
                source_id != 10
                or case["sourceAmmunitionName"] != "AP+DA"
                or components != ["ammunition:ap", "ammunition:da"]
                or original != {"hitRolls": 2, "criticalRolls": 3}
            ):
                raise ValueError(f"{item}: unsupported Immunity applicability")
            expected = {
                "hitRolls": 2,
                "criticalRolls": 3,
                "treatedAs": "ammunition:da",
                "ignoredComponents": ["ammunition:ap"],
                "remainingComponents": ["ammunition:da"],
            }
        if case["withImmunity"] != expected:
            raise ValueError(f"{item}: unsupported covered-attack result")
        if case["evidence"] != "derived-from-pinned-general-rules":
            raise ValueError(f"{item}: evidence must identify the rule-derived conclusion")


def _validate_immunity_interaction(value: object, context: str) -> None:
    """Validate source-reviewed Immunity boundaries without evaluating attacks."""
    if not isinstance(value, dict) or set(value) != {
        "coveredAmmunition", "criticalAgainstCoveredAmmunition", "exceptions",
        "reviewedCombinedCases", "reviewedVulnerabilityCases", "reviewedWeaponCases",
    }:
        raise ValueError(f"{context}: invalid Immunity interaction fields")
    covered = value["coveredAmmunition"]
    if (
        not isinstance(covered, dict)
        or set(covered) != {"treatAs", "ignore"}
        or covered["treatAs"] != "ammunition:normal"
        or covered["ignore"] != [
            "special-effects", "saving-roll-attribute-modifiers",
            "saving-roll-count-modifiers",
        ]
    ):
        raise ValueError(f"{context}: invalid covered Ammunition treatment")
    critical = value["criticalAgainstCoveredAmmunition"]
    if (
        not isinstance(critical, dict)
        or set(critical) != {"additionalSavingRolls", "unless", "rollEffects"}
        or type(critical["additionalSavingRolls"]) is not int
        or critical["additionalSavingRolls"] != 1
        or critical["unless"] != "immunity-critical"
        or critical["rollEffects"] != "normal-ammunition"
    ):
        raise ValueError(f"{context}: invalid Immunity Critical exception")
    exceptions = value["exceptions"]
    if (
        not isinstance(exceptions, dict)
        or set(exceptions) != {"commsAttacks", "notNegatedByImmunity"}
        or exceptions["commsAttacks"] != "immunity-state-only"
        or exceptions["notNegatedByImmunity"] != [
            "trait:non-lethal", "state:stunned",
        ]
    ):
        raise ValueError(f"{context}: invalid Immunity exceptions")
    # This is the one printed Flash Pulse example, not a weapon/trait evaluator.
    # In particular, the stunned condition must not be inferred for other weapons.
    if value["reviewedWeaponCases"] != [
        {
            "when": {
                "weaponId": "weapon:flash-pulse",
                "immunity": "BTS",
                "savingAttribute": "BTS",
                "attackClass": "non-comms",
            },
            "ammunitionTreatedAs": "ammunition:normal",
            "survivingTraits": ["trait:non-lethal", "trait:state"],
            "stateEffect": {
                "stateId": "state:stunned",
                "condition": "failed-saving-roll",
            },
            "evidence": "explicit-pinned-wiki-example",
        }
    ]:
        raise ValueError(f"{context}: unsupported Flash Pulse Immunity example")
    # The pinned Vulnerability example names a *weapon*, not just an
    # Ammunition component. Do not turn this into substring-based runtime logic.
    if value["reviewedVulnerabilityCases"] != [
        {
            "when": {
                "immunity": "Enhanced",
                "vulnerability": "Viral",
                "weaponNameContains": "Viral",
            },
            "result": "cannot-apply-immunity",
            "evidence": "explicit-pinned-wiki-example",
        }
    ]:
        raise ValueError(f"{context}: unsupported Vulnerability interaction example")
    _validate_reviewed_immunity_combined_cases(
        value["reviewedCombinedCases"], f"{context}.reviewedCombinedCases"
    )


def _validate_ammunition_resolution(value: object, context: str) -> None:
    """Validate reviewed effects without treating them as executable roll logic."""
    if (
        not isinstance(value, dict)
        or not value
        or set(value) - {
            "defenseModifier", "rollsPerHit", "stateEffects", "savingRoll",
            "woundsPerFailedSave", "gutsEffect", "criticalAdditionalSavingRolls",
        }
    ):
        raise ValueError(f"{context}: unsupported ammunition resolution facts")
    modifier = value.get("defenseModifier")
    if modifier is not None:
        if (
            not isinstance(modifier, dict)
            or set(modifier) != {"operation", "attributes"}
            or modifier["operation"] != "halve"
            or not isinstance(modifier["attributes"], list)
            or not modifier["attributes"]
            or any(
                not isinstance(attribute, str) or attribute not in {"ARM", "BTS"}
                for attribute in modifier["attributes"]
            )
            or len(set(modifier["attributes"])) != len(modifier["attributes"])
        ):
            raise ValueError(f"{context}.defenseModifier: invalid defense modifier")
    saving_roll = value.get("savingRoll")
    if saving_roll is not None and (
        not isinstance(saving_roll, dict)
        or set(saving_roll) != {"attribute", "modifier", "missingAttribute"}
        or saving_roll["attribute"] != "PH"
        or type(saving_roll["modifier"]) is not int
        or saving_roll["modifier"] >= 0
        or saving_roll["missingAttribute"] != "no-effect"
    ):
        raise ValueError(f"{context}.savingRoll: invalid PH Saving Roll specification")
    wounds = value.get("woundsPerFailedSave")
    if wounds is not None and (
        not isinstance(wounds, dict)
        or set(wounds) != {"hit", "criticalAdditionalRoll"}
        or any(type(wounds[key]) is not int or wounds[key] < 1 for key in wounds)
    ):
        raise ValueError(f"{context}.woundsPerFailedSave: invalid Wound specification")
    guts = value.get("gutsEffect")
    if guts is not None and (
        not isinstance(guts, dict)
        or guts != {
            "condition": "failed-saving-roll",
            "result": "automatic-failure",
            "exception": "courage-or-equivalent",
        }
    ):
        raise ValueError(f"{context}.gutsEffect: unsupported Guts effect")
    critical = value.get("criticalAdditionalSavingRolls")
    if critical is not None and (type(critical) is not int or critical != 1):
        raise ValueError(
            f"{context}.criticalAdditionalSavingRolls: must be exactly one extra roll"
        )
    rolls = value.get("rollsPerHit")
    if rolls is not None and (type(rolls) is not int or rolls < 1):
        raise ValueError(f"{context}.rollsPerHit: must be a positive integer")
    states = value.get("stateEffects")
    if states is not None:
        if not isinstance(states, list) or not states:
            raise ValueError(f"{context}.stateEffects: must be a non-empty array")
        seen: set[str] = set()
        for index, state in enumerate(states):
            state_context = f"{context}.stateEffects[{index}]"
            if not isinstance(state, dict) or set(state) not in (
                {"stateId", "condition"},
                {"stateId", "condition", "targetTypes"},
                {"stateId", "condition", "targetAttribute", "application"},
            ):
                raise ValueError(f"{state_context}: invalid State effect fields")
            validate_typed_domain_id(
                state["stateId"], expected_domain="state", context=state_context
            )
            if state["stateId"] in seen:
                raise ValueError(f"{state_context}: duplicate State effect")
            seen.add(state["stateId"])
            if state["condition"] != "failed-saving-roll":
                raise ValueError(f"{state_context}: unsupported State effect condition")
            target_attribute = state.get("targetAttribute")
            application = state.get("application")
            if (target_attribute is not None or application is not None) and (
                not isinstance(target_attribute, dict)
                or target_attribute != {"name": "VITA", "equals": 1}
                or type(target_attribute["equals"]) is not int
                or application != "bypass-unconscious"
                or state["stateId"] != "state:dead"
            ):
                raise ValueError(f"{state_context}: invalid conditional State transition")
            types = state.get("targetTypes")
            if types is not None and (
                not isinstance(types, list)
                or not types
                or any(
                    not isinstance(kind, str) or kind not in {"HI", "TAG", "REM", "VH"}
                    for kind in types
                )
                or len(set(types)) != len(types)
            ):
                raise ValueError(f"{state_context}.targetTypes: invalid target restriction")


def _validate_ammunition_visibility_zone(value: object, context: str) -> None:
    """Keep non-damaging visibility facts separate from Saving Roll resolution."""
    if (
        not isinstance(value, dict)
        or set(value) != {
            "visibility", "template", "height", "expires", "multispectralVisor"
        }
        or value["visibility"] != "zero"
        or value["template"] != "circular"
        or value["height"] != "infinite"
        or value["expires"] != "start-of-states-phase"
        or not isinstance(value["multispectralVisor"], str)
        or value["multispectralVisor"] not in {"can-draw-lof", "blocked"}
    ):
        raise ValueError(f"{context}: unsupported Ammunition visibility zone")


def _validate_scope(value: object, context: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: must be an object")
    if {"game", "seasons"} - set(value) or set(value) - {"game", "seasons", "scenarios"}:
        raise ValueError(f"{context}: requires game/seasons and only optional scenarios")
    if "scenarios" in value:
        scenario_ids = value["scenarios"]
        if not isinstance(scenario_ids, list) or not scenario_ids:
            raise ValueError(f"{context}.scenarios must be a non-empty array")
        for scenario_id in scenario_ids:
            validate_typed_domain_id(
                scenario_id, expected_domain="scenario", context=f"{context}.scenarios"
            )
        if len(set(scenario_ids)) != len(scenario_ids):
            raise ValueError(f"{context}.scenarios contains duplicates")
    _require_string(value.get("game"), "game", context)
    seasons = value.get("seasons")
    if (
        not isinstance(seasons, list)
        or not seasons
        or any(not isinstance(item, str) or not item.strip() for item in seasons)
    ):
        raise ValueError(f"{context}: 'seasons' must be a non-empty array of strings")
    if len(set(seasons)) != len(seasons):
        raise ValueError(f"{context}: 'seasons' must not contain duplicates")


def _validate_review(value: object, context: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: must be an object")
    if set(value) != {"status", "reviewedOn"}:
        raise ValueError(f"{context}: must contain only 'status' and 'reviewedOn'")
    if value.get("status") not in {"draft", "reviewed"}:
        raise ValueError(f"{context}: 'status' must be 'draft' or 'reviewed'")
    _require_string(value.get("reviewedOn"), "reviewedOn", context)
    reviewed_on = value["reviewedOn"]
    parts = reviewed_on.split("-")
    if (
        len(parts) != 3
        or any(not part.isdecimal() for part in parts)
        or len(parts[0]) != 4
        or len(parts[1]) != 2
        or len(parts[2]) != 2
    ):
        raise ValueError(f"{context}: 'reviewedOn' must use YYYY-MM-DD")


def _validate_composition(value: object, context: str) -> str:
    if not isinstance(value, dict) or set(value) != {"role"}:
        raise ValueError(f"{context}: must contain only 'role'")
    role = value.get("role")
    if role not in {"definition", "supplement"}:
        raise ValueError(f"{context}: 'role' must be 'definition' or 'supplement'")
    return role


def _validate_rule_relation(value: object, context: str) -> None:
    if not isinstance(value, dict) or set(value) != {"type", "recordId"}:
        raise ValueError(f"{context}: must contain only 'type' and 'recordId'")
    relation_type = value.get("type")
    if relation_type not in RULE_RELATION_TYPES:
        raise ValueError(
            f"{context}: unsupported relation type {relation_type!r}; "
            f"expected one of {sorted(RULE_RELATION_TYPES)}"
        )
    record_id = value.get("recordId")
    _require_string(record_id, "recordId", context)
    assert isinstance(record_id, str)
    domain = record_id.split(":", 1)[0]
    validate_typed_domain_id(record_id, expected_domain=domain, context=f"{context}.recordId")


def _validate_army_link_id(entity: str, value: Any, context: str) -> None:
    if type(value) is int:
        _require_positive_int(value, "id", context)
        return
    if not isinstance(value, str):
        raise ValueError(f"{context}: 'id' must be a positive integer or domain slug")
    if entity not in ARMY_LINK_SLUG_DOMAINS:
        raise ValueError(
            f"{context}: string 'id' references are not supported for entity {entity!r}"
        )
    if value.isdecimal():
        raise ValueError(
            f"{context}: numeric source ids must be JSON integers, not slug strings"
        )
    require_domain_slug(value, context=f"{context} 'id'")


def _validate_reference(
    reference: dict[str, Any],
    source: dict[str, Any],
    context: str,
    *,
    require_heading: bool = False,
) -> None:
    deprecated = reference.keys() & {"path", "snapshotDate"}
    if deprecated:
        raise ValueError(f"{context}: unsupported legacy fields {sorted(deprecated)}")
    if require_heading:
        _require_string(reference.get("heading"), "heading", context)

    if source["kind"] == "pdf":
        _require_positive_int(reference.get("page"), "page", context)
        if "member" in reference:
            raise ValueError(f"{context}: PDF references must not contain 'member'")
        return

    if source.get("localPath"):
        _require_string(reference.get("member"), "member", context)
        if "page" in reference:
            raise ValueError(f"{context}: archived wiki references must not contain 'page'")
        return

    if "page" in reference or "member" in reference:
        raise ValueError(f"{context}: URL-backed wiki references use the source URL directly")


def _validate_source(source: dict[str, Any], context: str) -> None:
    missing = REQUIRED_SOURCE_FIELDS - source.keys()
    if missing:
        raise ValueError(f"{context}: missing fields {sorted(missing)}")
    for field in REQUIRED_SOURCE_FIELDS:
        _require_string(source[field], field, context)
    if source["kind"] not in {"pdf", "wiki"}:
        raise ValueError(f"{context}: 'kind' must be 'pdf' or 'wiki'")

    _require_string(source.get("url"), "url", context)
    if source["kind"] == "pdf":
        _require_string(source.get("publishedDate"), "publishedDate", context)
        _require_string(source.get("localPath"), "localPath", context)
        _require_positive_int(source.get("pageCount"), "pageCount", context)
        return

    if source.get("localPath") is not None:
        _require_string(source.get("localPath"), "localPath", context)
        _require_string(source.get("acquiredAt"), "acquiredAt", context)
        _require_string(source.get("sha256"), "sha256", context)
        sha256 = source["sha256"]
        if len(sha256) != 64 or any(char not in "0123456789abcdefABCDEF" for char in sha256):
            raise ValueError(f"{context}: 'sha256' must be a 64-character hexadecimal digest")
        _require_string(source.get("language"), "language", context)
        _require_positive_int(source.get("documentCount"), "documentCount", context)
    else:
        _require_string(source.get("retrievedDate"), "retrievedDate", context)


def discover_curated_documents(directory: Path) -> list[Path]:
    """Return curated rules collections, excluding non-rule curated categories.

    Passing the common ``data/curated`` parent remains supported, but once a
    dedicated ``rules/`` subtree exists only that subtree is an input to this
    rules-reference loader.
    """
    if not directory.is_dir():
        raise ValueError(f"Curated source directory does not exist: {directory}")
    rules_directory = directory / "rules"
    search_root = rules_directory if rules_directory.is_dir() else directory
    return sorted(
        path
        for path in search_root.rglob("*.json")
        if path.is_file() and path.name.casefold() not in EXCLUDED_CURATED_FILENAMES
    )


def load_curated_directory(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Load every curated collection below a directory except example templates."""
    documents = [
        (path, load_curated_document(path)) for path in discover_curated_documents(directory)
    ]
    if not documents:
        raise ValueError(f"No curated collection JSON files found in {directory}")
    return documents


def _validate_weapon_special_profile(profile: object, context: str) -> None:
    if not isinstance(profile, dict):
        raise ValueError(f"{context}: must be an object")
    required = {"stats", "equipment", "skills", "ccWeapon"}
    missing = required - profile.keys()
    unknown = profile.keys() - required
    if missing:
        raise ValueError(f"{context}: missing fields {sorted(missing)}")
    if unknown:
        raise ValueError(f"{context}: unsupported fields {sorted(unknown)}")

    stats = profile["stats"]
    if not isinstance(stats, list) or not stats:
        raise ValueError(f"{context}.stats: must be a non-empty array")
    seen_stats: set[str] = set()
    for index, stat in enumerate(stats):
        stat_context = f"{context}.stats[{index}]"
        if (
            not isinstance(stat, list)
            or len(stat) != 2
            or not all(isinstance(value, str) and value.strip() for value in stat)
        ):
            raise ValueError(f"{stat_context}: must be [name, value] strings")
        if stat[0] in seen_stats:
            raise ValueError(f"{stat_context}: duplicate stat name {stat[0]!r}")
        seen_stats.add(stat[0])

    for field in ("equipment", "skills"):
        values = profile[field]
        if not isinstance(values, list) or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError(f"{context}.{field}: must be an array of non-empty strings")
    _require_string(profile["ccWeapon"], "ccWeapon", context)


def _validate_controller_eligibility(value: object, context: str) -> set[str]:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: must be an object")
    if set(value) == {"status"}:
        if value["status"] != "not-stated":
            raise ValueError(f"{context}.status: must be 'not-stated'")
        return set()
    if set(value) == {"hasSkill"}:
        skill_id = value["hasSkill"]
        validate_typed_domain_id(
            skill_id, expected_domain="skill", context=f"{context}.hasSkill"
        )
        return {skill_id}
    if set(value) == {"anyOf"}:
        values = value["anyOf"]
        if not isinstance(values, list) or len(values) < 2:
            raise ValueError(f"{context}.anyOf: must contain at least two predicates")
        result: set[str] = set()
        for index, predicate in enumerate(values):
            if not isinstance(predicate, dict) or set(predicate) != {"hasSkill"}:
                raise ValueError(
                    f"{context}.anyOf[{index}]: only 'hasSkill' predicates are supported"
                )
            skill_id = predicate["hasSkill"]
            validate_typed_domain_id(
                skill_id,
                expected_domain="skill",
                context=f"{context}.anyOf[{index}].hasSkill",
            )
            if skill_id in result:
                raise ValueError(f"{context}.anyOf[{index}]: duplicate skill {skill_id!r}")
            result.add(skill_id)
        return result
    raise ValueError(
        f"{context}: must contain exactly 'status', 'hasSkill', or 'anyOf'"
    )


def _validate_peripheral_type_facts(facts: object, context: str) -> set[str]:
    if not isinstance(facts, dict):
        raise ValueError(f"{context}: Peripheral type 'facts' must be an object")
    allowed = {
        "category",
        "controllerEligibility",
        "maxPerController",
        "operatingDistance",
        "profileModes",
    }
    unknown = set(facts) - allowed
    if unknown:
        raise ValueError(
            f"{context}: Peripheral type facts have unsupported fields {sorted(unknown)}"
        )
    required = {"category", "controllerEligibility"}
    missing = required - set(facts)
    if missing:
        raise ValueError(f"{context}: Peripheral type facts missing fields {sorted(missing)}")
    if facts["category"] != "peripheral-type":
        raise ValueError(f"{context}.category: must be 'peripheral-type'")
    skill_ids = _validate_controller_eligibility(
        facts["controllerEligibility"], f"{context}.controllerEligibility"
    )
    if "maxPerController" in facts:
        _require_positive_int(facts["maxPerController"], "maxPerController", context)
    if "operatingDistance" in facts and facts["operatingDistance"] != "unlimited":
        raise ValueError(f"{context}.operatingDistance: only 'unlimited' is supported")
    if "profileModes" in facts:
        modes = facts["profileModes"]
        if (
            not isinstance(modes, list)
            or not modes
            or any(mode not in {"connected", "autonomous"} for mode in modes)
            or len(set(modes)) != len(modes)
        ):
            raise ValueError(
                f"{context}.profileModes: must be a unique non-empty subset of "
                "['connected', 'autonomous']"
            )
    return skill_ids


def _validate_fireteam_general_facts(facts: object, context: str) -> None:
    if not isinstance(facts, dict):
        raise ValueError(f"{context}: Fireteam general facts must be an object")
    expected = {"category", "memberLimits", "types", "rules", "terminology"}
    if set(facts) != expected:
        raise ValueError(
            f"{context}: Fireteam general facts must contain exactly {sorted(expected)}"
        )
    if facts["category"] != "fireteam-general":
        raise ValueError(f"{context}.category: must be 'fireteam-general'")

    limits = facts["memberLimits"]
    if not isinstance(limits, dict) or set(limits) != {"min", "max"}:
        raise ValueError(f"{context}.memberLimits: must contain only 'min' and 'max'")
    _require_positive_int(limits.get("min"), "min", f"{context}.memberLimits")
    _require_positive_int(limits.get("max"), "max", f"{context}.memberLimits")
    if limits["min"] > limits["max"]:
        raise ValueError(f"{context}.memberLimits: min must not exceed max")

    types = facts["types"]
    if not isinstance(types, list) or not types:
        raise ValueError(f"{context}.types: must be a non-empty array")
    seen_types: set[str] = set()
    for index, item in enumerate(types):
        item_context = f"{context}.types[{index}]"
        if not isinstance(item, dict) or set(item) != {"type", "min", "max"}:
            raise ValueError(
                f"{item_context}: must contain only 'type', 'min', and 'max'"
            )
        fireteam_type = item.get("type")
        if fireteam_type not in {"DUO", "HARIS", "CORE"}:
            raise ValueError(
                f"{item_context}.type: must be 'DUO', 'HARIS', or 'CORE'"
            )
        if fireteam_type in seen_types:
            raise ValueError(f"{item_context}.type: duplicate {fireteam_type!r}")
        seen_types.add(fireteam_type)
        _require_positive_int(item.get("min"), "min", item_context)
        _require_positive_int(item.get("max"), "max", item_context)
        if item["min"] > item["max"]:
            raise ValueError(f"{item_context}: min must not exceed max")
    if seen_types != {"DUO", "HARIS", "CORE"}:
        raise ValueError(
            f"{context}.types: must define DUO, HARIS, and CORE exactly once"
        )

    rules = facts["rules"]
    if (
        not isinstance(rules, list)
        or not rules
        or any(not isinstance(rule, str) or not rule.strip() for rule in rules)
        or len(set(rules)) != len(rules)
    ):
        raise ValueError(
            f"{context}.rules: must be a unique non-empty array of non-empty strings"
        )

    terminology = facts["terminology"]
    if not isinstance(terminology, list) or not terminology:
        raise ValueError(f"{context}.terminology: must be a non-empty array")
    seen_terms: set[str] = set()
    for index, item in enumerate(terminology):
        item_context = f"{context}.terminology[{index}]"
        if not isinstance(item, dict) or set(item) != {"term", "provenance", "meaning"}:
            raise ValueError(
                f"{item_context}: must contain only 'term', 'provenance', and 'meaning'"
            )
        _require_string(item.get("term"), "term", item_context)
        _require_string(item.get("meaning"), "meaning", item_context)
        provenance = item.get("provenance")
        if provenance not in {"historical-official", "community-historical"}:
            raise ValueError(
                f"{item_context}.provenance: unsupported value {provenance!r}"
            )
        term = str(item["term"]).casefold()
        if term in seen_terms:
            raise ValueError(f"{item_context}.term: duplicate term {item['term']!r}")
        seen_terms.add(term)


def _validate_fireteam_level_facts(facts: object, context: str) -> None:
    if not isinstance(facts, dict):
        raise ValueError(f"{context}: Fireteam Level facts must be an object")
    expected = {"category", "basis", "cumulative", "levels"}
    if set(facts) != expected:
        raise ValueError(
            f"{context}: Fireteam Level facts must contain exactly {sorted(expected)}"
        )
    if facts["category"] != "fireteam-level-bonuses":
        raise ValueError(f"{context}.category: must be 'fireteam-level-bonuses'")
    _require_string(facts.get("basis"), "basis", context)
    if facts["cumulative"] is not True:
        raise ValueError(f"{context}.cumulative: must be true")

    levels = facts["levels"]
    if not isinstance(levels, list) or len(levels) != 5:
        raise ValueError(f"{context}.levels: must contain exactly five levels")
    for index, item in enumerate(levels, start=1):
        item_context = f"{context}.levels[{index - 1}]"
        if not isinstance(item, dict) or set(item) != {"level", "requirement", "bonuses"}:
            raise ValueError(
                f"{item_context}: must contain only 'level', 'requirement', and 'bonuses'"
            )
        if item.get("level") != index:
            raise ValueError(f"{item_context}.level: expected {index}")
        _require_string(item.get("requirement"), "requirement", item_context)
        bonuses = item.get("bonuses")
        if (
            not isinstance(bonuses, list)
            or not bonuses
            or any(not isinstance(bonus, str) or not bonus.strip() for bonus in bonuses)
            or len(set(bonuses)) != len(bonuses)
        ):
            raise ValueError(
                f"{item_context}.bonuses: must be a unique non-empty array of strings"
            )


def load_curated_document(path: Path) -> dict[str, Any]:
    """Load and validate one curated JSON document.

    This loader intentionally accepts only the intermediary JSON format. Raw
    PDFs, wiki snapshots, and arbitrary JSON are not valid ingestion sources.
    """
    if path.suffix.casefold() != ".json":
        raise ValueError(f"Curated source must be a .json file: {path}")

    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read curated source {path}: {exc}") from exc

    if not isinstance(document, dict):
        raise ValueError("Curated source must contain a top-level object")
    if document.get("format") != CURATED_FORMAT:
        raise ValueError(f"Curated source must declare format '{CURATED_FORMAT}'")
    if document.get("formatVersion") != CURATED_FORMAT_VERSION:
        raise ValueError(f"Unsupported curated format version: {document.get('formatVersion')!r}")

    collection = document.get("collection")
    sources = document.get("sources")
    records = document.get("records")
    skill_types = document.get("skillTypes")
    labels = document.get("labels")
    vocabulary_sources = document.get("vocabularySources")
    if not isinstance(collection, dict):
        raise ValueError("Curated source must contain a collection object")
    missing = REQUIRED_COLLECTION_FIELDS - collection.keys()
    if missing:
        raise ValueError(f"collection: missing fields {sorted(missing)}")
    for field in REQUIRED_COLLECTION_FIELDS:
        _require_string(collection[field], field, "collection")
    if not isinstance(sources, list) or not isinstance(records, list):
        raise ValueError("Curated source must contain 'sources' and 'records' arrays")
    if not isinstance(skill_types, list):
        raise ValueError("Curated source must contain a 'skillTypes' array")
    if not isinstance(labels, list):
        raise ValueError("Curated source must contain a 'labels' array")
    if not isinstance(vocabulary_sources, dict):
        raise ValueError("Curated source must contain a 'vocabularySources' object")
    skill_type_ids: set[str] = set()
    for index, skill_type in enumerate(skill_types):
        context = f"skillTypes[{index}]"
        if not isinstance(skill_type, dict):
            raise ValueError(f"{context}: must be an object")
        missing = REQUIRED_SKILL_TYPE_FIELDS - skill_type.keys()
        if missing:
            raise ValueError(f"{context}: missing fields {sorted(missing)}")
        for field in ("id", "name"):
            _require_string(skill_type[field], field, context)
        skill_type_labels = skill_type["labels"]
        if (
            not isinstance(skill_type_labels, list)
            or len(skill_type_labels) != 2
            or any(not isinstance(label, str) or not label.strip() for label in skill_type_labels)
        ):
            raise ValueError(f"{context}: 'labels' must contain singular and plural strings")
        descriptions = skill_type["descriptions"]
        if not isinstance(descriptions, dict):
            raise ValueError(f"{context}: 'descriptions' must be an object")
        for form in ("singular", "plural"):
            _require_string(descriptions.get(form), f"descriptions.{form}", context)
        if skill_type["id"] in skill_type_ids:
            raise ValueError(f"{context}: duplicate skill type id {skill_type['id']!r}")
        skill_type_ids.add(skill_type["id"])

    label_ids: set[str] = set()
    for index, label in enumerate(labels):
        context = f"labels[{index}]"
        if not isinstance(label, dict):
            raise ValueError(f"{context}: must be an object")
        missing = REQUIRED_LABEL_FIELDS - label.keys()
        if missing:
            raise ValueError(f"{context}: missing fields {sorted(missing)}")
        for field in REQUIRED_LABEL_FIELDS:
            _require_string(label[field], field, context)
        if label["id"] in label_ids:
            raise ValueError(f"{context}: duplicate label id {label['id']!r}")
        label_ids.add(label["id"])

    source_ids: set[str] = set()
    source_by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        context = f"sources[{index}]"
        if not isinstance(source, dict):
            raise ValueError(f"{context}: must be an object")
        _validate_source(source, context)
        source_id = source["id"]
        if source_id in source_ids:
            raise ValueError(f"{context}: duplicate source id {source_id!r}")
        source_ids.add(source_id)
        source_by_id[source_id] = source

    for vocabulary_name in ("skillTypes", "labels"):
        source_list = vocabulary_sources.get(vocabulary_name)
        if not isinstance(source_list, list):
            raise ValueError(f"vocabularySources.{vocabulary_name} must be an array")
        for index, reference in enumerate(source_list):
            context = f"vocabularySources.{vocabulary_name}[{index}]"
            if not isinstance(reference, dict):
                raise ValueError(f"{context}: must be an object")
            _require_string(reference.get("sourceId"), "sourceId", context)
            source_id = reference["sourceId"]
            if source_id not in source_by_id:
                raise ValueError(f"{context}: unknown source id {source_id!r}")
            _validate_reference(
                reference, source_by_id[source_id], context, require_heading=True
            )

    record_ids: set[str] = set()
    record_kind_by_id: dict[str, str] = {}
    peripheral_type_skill_refs: dict[str, set[str]] = {}
    skill_definition_type_ids: dict[int | str, tuple[str, ...]] = {}
    for index, record in enumerate(records):
        context = f"records[{index}]"
        if not isinstance(record, dict):
            raise ValueError(f"{context}: must be an object")
        missing = REQUIRED_RECORD_FIELDS - record.keys()
        if missing:
            raise ValueError(f"{context}: missing fields {sorted(missing)}")
        for field in ("id", "kind", "name", "summary"):
            _require_string(record[field], field, context)
        validate_typed_domain_id(
            record["id"], expected_domain=record["kind"], context=f"{context}.id"
        )
        if not isinstance(record["citations"], list) or not record["citations"]:
            raise ValueError(f"{context}: 'citations' must be a non-empty array")
        for optional_list in ("aliases",):
            if optional_list in record and (
                not isinstance(record[optional_list], list)
                or any(not isinstance(value, str) for value in record[optional_list])
            ):
                raise ValueError(f"{context}: '{optional_list}' must be an array of strings")
        if "relatedRecords" in record:
            raise ValueError(
                f"{context}: 'relatedRecords' was replaced by typed 'relations' in format v6"
            )
        composition_role = _validate_composition(
            record["composition"], f"{context}.composition"
        )
        relations = record.get("relations", [])
        if not isinstance(relations, list):
            raise ValueError(f"{context}: 'relations' must be an array")
        relation_keys: set[tuple[str, str]] = set()
        for relation_index, relation in enumerate(relations):
            _validate_rule_relation(
                relation, f"{context}.relations[{relation_index}]"
            )
            relation_key = (relation["type"], relation["recordId"])
            if relation_key in relation_keys:
                raise ValueError(
                    f"{context}.relations[{relation_index}]: duplicate relation "
                    f"{relation_key!r}"
                )
            relation_keys.add(relation_key)
        _validate_scope(record["scope"], f"{context}.scope")
        _validate_review(record["review"], f"{context}.review")
        if "facts" in record and not isinstance(record["facts"], dict):
            raise ValueError(f"{context}: 'facts' must be an object")
        notes = (record.get("facts") or {}).get("sourceNotes")
        if notes is not None and (
            not isinstance(notes, list)
            or not notes
            or any(not isinstance(note, str) or not note.strip() for note in notes)
        ):
            raise ValueError(f"{context}: 'facts.sourceNotes' must be non-empty strings")
        facts = record.get("facts")
        if isinstance(facts, dict):
            clarifications = facts.get("clarifications")
            if clarifications is not None and (
                not isinstance(clarifications, list)
                or not clarifications
                or any(
                    not isinstance(item, str) or not item.strip()
                    for item in clarifications
                )
            ):
                raise ValueError(
                    f"{context}.facts.clarifications: expected non-empty maintained-text strings"
                )
            _validate_related_categories(facts, f"{context}.facts")
            immunity = facts.get("immunityInteraction")
            if immunity is not None:
                if record["id"] != "skill:immunity":
                    raise ValueError(
                        f"{context}.facts.immunityInteraction: only the Immunity Skill may own it"
                    )
                _validate_immunity_interaction(
                    immunity, f"{context}.facts.immunityInteraction"
                )
            resolution = facts.get("ammunitionResolution")
            if resolution is not None:
                if record["kind"] != "ammunition":
                    raise ValueError(
                        f"{context}.facts.ammunitionResolution: only Ammunition may own effects"
                    )
                _validate_ammunition_resolution(
                    resolution, f"{context}.facts.ammunitionResolution"
                )
            # State links are authored as relations, not inferred by clients.
            # Keep the graph and the conditional facts synchronized so a link
            # never invents or silently loses a State outcome.
            if record["kind"] == "ammunition":
                state_effects = resolution.get("stateEffects", []) if resolution else []
                fact_states = {effect["stateId"] for effect in state_effects}
                relation_states = {
                    relation["recordId"]
                    for relation in relations
                    if relation["type"] == "causes-state"
                }
                if fact_states != relation_states:
                    raise ValueError(
                        f"{context}: Ammunition causes-state relations must match "
                        "facts.ammunitionResolution.stateEffects exactly"
                    )
            zone = facts.get("visibilityZone")
            if zone is not None:
                if record["kind"] != "ammunition":
                    raise ValueError(
                        f"{context}.facts.visibilityZone: only Ammunition may own effects"
                    )
                if resolution is not None:
                    raise ValueError(
                        f"{context}.facts.visibilityZone: must not mix with Saving Roll facts"
                    )
                _validate_ammunition_visibility_zone(zone, f"{context}.facts.visibilityZone")
        if record["kind"] == "skill":
            facts = record.get("facts")
            if composition_role == "definition":
                type_ids = facts.get("typeIds") if isinstance(facts, dict) else None
                if (
                    not isinstance(type_ids, list)
                    or not type_ids
                    or any(
                        not isinstance(type_id, str) or type_id not in skill_type_ids
                        for type_id in type_ids
                    )
                ):
                    raise ValueError(
                        f"{context}: skill 'facts.typeIds' must be a non-empty array "
                        "referencing skillTypes"
                    )
                if len(type_ids) != len(set(type_ids)):
                    raise ValueError(
                        f"{context}: skill 'facts.typeIds' must not contain duplicates"
                    )
                if isinstance(facts, dict) and "typeId" in facts:
                    raise ValueError(
                        f"{context}: skill definitions must use 'facts.typeIds', "
                        "not singular 'facts.typeId'"
                    )
        if record["kind"] == "rule":
            facts = record.get("facts")
            if isinstance(facts, dict):
                category = facts.get("category")
                if category == "peripheral-type":
                    peripheral_type_skill_refs[record["id"]] = _validate_peripheral_type_facts(
                        facts, f"{context}.facts"
                    )
                elif category == "fireteam-general":
                    _validate_fireteam_general_facts(facts, f"{context}.facts")
                elif category == "fireteam-level-bonuses":
                    _validate_fireteam_level_facts(facts, f"{context}.facts")
                elif category == "unit-profile-help":
                    if set(facts) != {"category", "key", "order"}:
                        raise ValueError(
                            f"{context}: unit-profile-help facts must contain only "
                            "'category', 'key', and 'order'"
                        )
                    require_domain_slug(
                        facts["key"], context=f"{context}.facts.key"
                    )
                    if type(facts["order"]) is not int or facts["order"] < 0:
                        raise ValueError(
                            f"{context}: unit-profile-help 'order' must be a "
                            "nonnegative integer"
                        )
        if record["kind"] == "term":
            facts = record.get("facts")
            if not isinstance(facts, dict) or set(facts) != {"scope"}:
                raise ValueError(
                    f"{context}: term 'facts' must contain only 'scope'"
                )
            require_domain_slug(facts["scope"], context=f"{context}.facts.scope")
        if record["kind"] == "trait":
            facts = record.get("facts")
            if facts is not None:
                source_identity = facts.get("sourceIdentity")
                if source_identity is not None:
                    if not isinstance(source_identity, dict):
                        raise ValueError(
                            f"{context}: trait 'facts.sourceIdentity' must be an object"
                        )
                    unknown = source_identity.keys() - {"prefixes"}
                    if unknown:
                        raise ValueError(
                            f"{context}: trait 'facts.sourceIdentity' has unsupported fields "
                            f"{sorted(unknown)}"
                        )
                    prefixes = source_identity.get("prefixes")
                    if not isinstance(prefixes, list) or not prefixes:
                        raise ValueError(
                            f"{context}: trait 'facts.sourceIdentity.prefixes' must be a "
                            "non-empty array"
                        )
                    for prefix_index, prefix in enumerate(prefixes):
                        _require_string(
                            prefix,
                            f"facts.sourceIdentity.prefixes[{prefix_index}]",
                            context,
                        )
        if record["kind"] == "weapon":
            facts = record.get("facts")
            if composition_role == "definition" and not isinstance(facts, dict):
                raise ValueError(f"{context}: weapon 'facts' must be an object")
            if isinstance(facts, dict) and "specialProfile" in facts:
                _validate_weapon_special_profile(
                    facts["specialProfile"], f"{context}.facts.specialProfile"
                )
            if isinstance(facts, dict) and "variantRuleReferences" in facts:
                references = facts["variantRuleReferences"]
                army_refs = {
                    link.get("id") for link in record.get("armyLinks", [])
                    if isinstance(link, dict) and link.get("entity") == "weapon"
                }
                if (
                    composition_role != "definition"
                    or not isinstance(references, dict)
                    or not references
                    or any(slug not in army_refs for slug in references)
                ):
                    raise ValueError(
                        f"{context}.facts.variantRuleReferences: requires linked weapon "
                        "slugs on a definition"
                    )
                for slug, targets in references.items():
                    if not isinstance(slug, str) or not isinstance(targets, list) or not targets:
                        raise ValueError(f"{context}: invalid variant rule references for {slug!r}")
                    for target in targets:
                        if not isinstance(target, str) or ":" not in target:
                            raise ValueError(f"{context}: invalid variant rule target {target!r}")
                        kind = target.split(":", 1)[0]
                        if kind not in {"ammunition", "trait", "state", "skill", "weapon"}:
                            raise ValueError(
                                f"{context}: unsupported variant rule target {target!r}"
                            )
                        validate_typed_domain_id(
                            target, expected_domain=kind,
                            context=f"{context}.facts.variantRuleReferences[{slug!r}]",
                        )
                    if len(targets) != len(set(targets)):
                        raise ValueError(
                            f"{context}: duplicate variant rule reference for {slug!r}"
                        )
        if record["kind"] == "scenario" and composition_role == "definition":
            try:
                parse_scenario_definition_record(record, definitions=document)
            except ScenarioDefinitionError as exc:
                raise ValueError(f"{context}: {exc}") from exc
        if record["kind"] == "training":
            facts = record.get("facts", {})
            if composition_role == "definition":
                if not isinstance(facts, dict) or set(facts) != {"orderType"}:
                    raise ValueError(
                        f"{context}: Training definition facts must contain only 'orderType'"
                    )
                order_type = facts["orderType"]
                if order_type not in TRAINING_ORDER_TYPES:
                    raise ValueError(
                        f"{context}: unsupported Training orderType {order_type!r}"
                    )
                if record["id"] != f"training:{order_type}":
                    raise ValueError(
                        f"{context}: Training id must match its orderType"
                    )
            elif isinstance(facts, dict) and "orderType" in facts:
                raise ValueError(
                    f"{context}: Training supplements must not redefine 'orderType'"
                )
            if record.get("armyLinks"):
                raise ValueError(
                    f"{context}: Training is sourced from regular/irregular Order "
                    "types and must not link to an Army Skill"
                )
        if record["kind"] == "declaration-category":
            facts = record.get("facts")
            if not isinstance(facts, dict) or set(facts) != {"typeId", "order"}:
                raise ValueError(
                    f"{context}: declaration category 'facts' must contain only "
                    "'typeId' and 'order'"
                )
            if facts["typeId"] not in skill_type_ids:
                raise ValueError(
                    f"{context}: declaration category 'facts.typeId' must reference "
                    "skillTypes"
                )
            if type(facts["order"]) is not int or facts["order"] < 0:
                raise ValueError(
                    f"{context}: declaration category 'facts.order' must be "
                    "a non-negative integer"
                )
            links = record.get("armyLinks")
            if not isinstance(links, list) or not links:
                raise ValueError(
                    f"{context}: declaration category requires non-empty 'armyLinks'"
                )
            for link in links:
                if not isinstance(link, dict) or link.get("entity") not in {"skill", "equipment"}:
                    raise ValueError(
                        f"{context}: declaration category armyLinks must reference "
                        "skills or equipment"
                    )
                _validate_army_link_id(link["entity"], link.get("id"), context)
            if len(record["citations"]) != 1:
                raise ValueError(
                    f"{context}: declaration category requires exactly one citation"
                )
            citation_source = record["citations"][0].get("sourceId")
            citation_kind = next(
                (source["kind"] for source in sources if source["id"] == citation_source),
                None,
            )
            if citation_kind != "pdf":
                raise ValueError(
                    f"{context}: declaration category citation must reference a PDF"
                )
        if composition_role == "definition" and record["kind"] in {"skill", "state"}:
            record_labels = record.get("labelIds")
            if not isinstance(record_labels, list):
                raise ValueError(f"{context}: '{record['kind']}' requires a 'labelIds' array")
            if any(label_id not in label_ids for label_id in record_labels):
                raise ValueError(f"{context}: 'labelIds' must reference labels")
        if "armyLinks" in record and not isinstance(record["armyLinks"], list):
            raise ValueError(f"{context}: 'armyLinks' must be an array")
        army_links = record.get("armyLinks", [])
        if record["id"] in record_ids:
            raise ValueError(f"{context}: duplicate record id {record['id']!r}")
        record_ids.add(record["id"])
        record_kind_by_id[record["id"]] = record["kind"]
        for citation_index, citation in enumerate(record["citations"]):
            ref_context = f"{context}.citations[{citation_index}]"
            if not isinstance(citation, dict):
                raise ValueError(f"{ref_context}: must be an object")
            if "sourceId" not in citation:
                raise ValueError(f"{ref_context}: requires 'sourceId'")
            source_id = citation["sourceId"]
            if source_id not in source_ids:
                raise ValueError(f"{ref_context}: unknown source id {source_id!r}")
            _validate_reference(citation, source_by_id[source_id], ref_context)

        for link_index, link in enumerate(record.get("armyLinks", [])):
            link_context = f"{context}.armyLinks[{link_index}]"
            if not isinstance(link, dict):
                raise ValueError(f"{link_context}: must be an object")
            _require_string(link.get("entity"), "entity", link_context)
            if "id" not in link and "name" not in link:
                raise ValueError(f"{link_context}: requires 'id' or 'name'")
            if "id" in link:
                _validate_army_link_id(link["entity"], link["id"], link_context)

        if composition_role == "supplement" and army_links:
            raise ValueError(
                f"{context}: supplement contributions inherit Army routing from their "
                "definition and must not declare 'armyLinks'"
            )
        if composition_role == "definition" and record["kind"] in CATALOG_RULE_KINDS:
            for link in army_links:
                if link["entity"] != record["kind"]:
                    raise ValueError(
                        f"{context}: {record['kind']} definitions may only link to "
                        f"Army {record['kind']} identities"
                    )
                if "id" not in link:
                    raise ValueError(
                        f"{context}: Army-linked {record['kind']} definitions require "
                        "a stable numeric source id or domain slug; name-only links are "
                        "not canonical catalog relationships"
                    )

        variant_semantics = record.get("variantSemantics")
        requires_variant_semantics = (
            composition_role == "definition"
            and record["kind"] in CATALOG_RULE_KINDS
            and bool(army_links)
        )
        if requires_variant_semantics and variant_semantics is None:
            raise ValueError(
                f"{context}: Army-linked {record['kind']} definitions require "
                "'variantSemantics'"
            )
        if variant_semantics is not None:
            if composition_role != "definition":
                raise ValueError(
                    f"{context}: only definition contributions may declare 'variantSemantics'"
                )
            if record["kind"] not in CATALOG_RULE_KINDS:
                raise ValueError(
                    f"{context}: 'variantSemantics' is only supported for "
                    f"{sorted(CATALOG_RULE_KINDS)} records"
                )
            _validate_variant_semantics(
                variant_semantics, f"{context}.variantSemantics", army_links
            )

        if record["kind"] == "skill" and composition_role == "definition":
            facts = record.get("facts")
            if isinstance(facts, dict):
                type_ids = facts.get("typeIds")
                if isinstance(type_ids, list):
                    normalized_type_ids = tuple(
                        type_id for type_id in type_ids if isinstance(type_id, str)
                    )
                    for link in army_links:
                        if link.get("entity") != "skill" or "id" not in link:
                            continue
                        skill_ref = link["id"]
                        if not isinstance(skill_ref, (int, str)):
                            continue
                        existing = skill_definition_type_ids.get(skill_ref)
                        if existing is not None and existing != normalized_type_ids:
                            raise ValueError(
                                f"{context}: Army Skill {skill_ref!r} has conflicting "
                                "full-definition declaration categories"
                            )
                        skill_definition_type_ids[skill_ref] = normalized_type_ids
    for record_id, skill_refs in peripheral_type_skill_refs.items():
        for skill_id in skill_refs:
            if record_kind_by_id.get(skill_id) != "skill":
                raise ValueError(
                    f"Peripheral type {record_id!r} controller eligibility references "
                    f"unknown skill {skill_id!r}"
                )
            controller_record = next(record for record in records if record["id"] == skill_id)
            controller_relations = {
                (relation["type"], relation["recordId"])
                for relation in controller_record.get("relations", [])
            }
            if ("controller-eligible-for", record_id) not in controller_relations:
                raise ValueError(
                    f"Peripheral type {record_id!r} controller eligibility requires a "
                    f"'controller-eligible-for' relation from {skill_id!r}"
                )

        peripheral_record = next(
            (record for record in records if record["id"] == "skill:peripheral"),
            None,
        )
        if peripheral_record is None:
            raise ValueError(
                f"Peripheral type {record_id!r} requires canonical 'skill:peripheral'"
            )
        peripheral_relations = {
            (relation["type"], relation["recordId"])
            for relation in peripheral_record.get("relations", [])
        }
        if ("has-subtype", record_id) not in peripheral_relations:
            raise ValueError(
                f"Peripheral type {record_id!r} requires a 'has-subtype' relation "
                "from 'skill:peripheral'"
            )

    scenario_collection = document.get("scenarioCollection")
    scenario_definition_ids = {
        record["id"]
        for record in records
        if record["kind"] == "scenario" and record["composition"]["role"] == "definition"
    }
    if scenario_collection is None:
        if scenario_definition_ids:
            raise ValueError(
                "Collections with scenario definitions require 'scenarioCollection' metadata"
            )
    else:
        context = "scenarioCollection"
        if not isinstance(scenario_collection, dict):
            raise ValueError(f"{context}: must be an object")
        if set(scenario_collection) != {"id", "title", "revision", "members"}:
            raise ValueError(
                f"{context}: must contain exactly 'id', 'title', 'revision', and 'members'"
            )
        require_domain_slug(scenario_collection["id"], context=f"{context}.id")
        _require_string(scenario_collection["title"], "title", context)
        _require_string(scenario_collection["revision"], "revision", context)
        members = scenario_collection["members"]
        if not isinstance(members, list) or not members:
            raise ValueError(f"{context}.members must be a non-empty array")
        member_ids: list[str] = []
        for index, member in enumerate(members):
            member_context = f"{context}.members[{index}]"
            if not isinstance(member, dict) or set(member) != {"scenarioId"}:
                raise ValueError(
                    f"{member_context}: must contain exactly 'scenarioId'"
                )
            scenario_id = member["scenarioId"]
            validate_typed_domain_id(
                scenario_id, expected_domain="scenario", context=f"{member_context}.scenarioId"
            )
            if scenario_id in member_ids:
                raise ValueError(
                    f"{member_context}: duplicate scenario membership {scenario_id!r}"
                )
            member_ids.append(scenario_id)
        if set(member_ids) != scenario_definition_ids:
            missing = sorted(scenario_definition_ids - set(member_ids))
            unknown = sorted(set(member_ids) - scenario_definition_ids)
            details = []
            if missing:
                details.append(f"missing definitions {missing}")
            if unknown:
                details.append(f"unknown/non-definition members {unknown}")
            raise ValueError(
                f"{context}.members must match local scenario definitions: "
                + "; ".join(details)
            )

    from infinity_db.scenario_components import ScenarioComponents

    registry = ScenarioComponents(document)
    for record in records:
        scoped = record["scope"].get("scenarios")
        if scoped is not None:
            if record.get("armyLinks"):
                raise ValueError("Scenario-scoped definitions cannot grant Army profile facts")
            for scenario_id in scoped:
                if record_kind_by_id.get(scenario_id) != "scenario":
                    raise ValueError(f"Unknown scenario applicability {scenario_id!r}")
        facts = record.get("facts", {})
        if facts.get("category") == "scenario-rule":
            if record["kind"] != "rule" or scoped is None:
                raise ValueError(
                    "Scenario rule definitions require Rule kind and explicit scenarios"
                )
            allowed = {"category", "effects", "restrictions", "definesSkills", "specialists"}
            if set(facts) - allowed:
                raise ValueError("Scenario Rule has unsupported facts")
            for key in ("effects", "restrictions"):
                if not isinstance(facts.get(key), list) or any(
                    not isinstance(x, str) for x in facts[key]
                ):
                    raise ValueError(f"Scenario Rule {key} must be an array of prose")
            for scenario_id in scoped:
                for skill_id in facts.get("definesSkills", []):
                    registry.record(skill_id, "skill", scenario_id)
            if "specialists" in facts:
                baseline = facts["specialists"]
                if not isinstance(baseline, dict) or set(baseline) != {"anyOfSkills"}:
                    raise ValueError("Specialist baseline requires anyOfSkills")
                qualifiers = baseline["anyOfSkills"]
                if (
                    not isinstance(qualifiers, list)
                    or not qualifiers
                    or len(set(qualifiers)) != len(qualifiers)
                ):
                    raise ValueError("Specialist qualifiers must be a unique non-empty array")
                for skill_id in qualifiers:
                    if record_kind_by_id.get(skill_id) != "skill":
                        raise ValueError(f"Unknown Specialist Skill {skill_id!r}")
    if "scenarioComponents" in document:
        for component in document["scenarioComponents"]["definitions"]:
            for citation in component["citations"]:
                source_id = citation.get("sourceId")
                if source_id not in source_by_id:
                    raise ValueError(f"Unknown component citation source {source_id!r}")
                _validate_reference(
                    citation, source_by_id[source_id], "scenario component citation"
                )

    validate_maintained_text_syntax(document)

    return document
