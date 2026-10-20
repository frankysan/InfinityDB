"""Source-preserving typed projections for conditional Army reference-chart outcomes."""

from __future__ import annotations

import re
from typing import Any

_BOOTY_CONDITIONAL = re.compile(
    r"TAG: (?P<tag>[^/]+?) / Other Troop Types: (?P<other>[^/]+)"
)


_METACHEMISTRY_COMPOUND_ROLLS = {"16", "17", "18", "19", "20"}
_ATTRIBUTE_MODIFIER = re.compile(r"(?P<modifier>[+-]\d+) (?P<attribute>PH|ARM|BTS)")
_MOV_VALUE = re.compile(r"MOV: (?P<value>\d+-\d+)")
_SPECIAL_SKILL = re.compile(
    r"(?P<name>Immunity|Dogged|Regeneration|Super-Jump|Climbing Plus)"
    r"(?: \((?P<parameter>ARM|Enhanced)\))?"
)


def _metachemistry_component(text: str) -> dict[str, Any]:
    if match := _ATTRIBUTE_MODIFIER.fullmatch(text):
        return {
            "kind": "attribute-modifier",
            "text": text,
            "attribute": match.group("attribute"),
            "modifier": int(match.group("modifier")),
        }
    if match := _MOV_VALUE.fullmatch(text):
        return {"kind": "movement-value", "text": text, "value": match.group("value")}
    if match := _SPECIAL_SKILL.fullmatch(text):
        result: dict[str, Any] = {
            "kind": "special-skill",
            "text": text,
            "name": match.group("name"),
        }
        if match.group("parameter") is not None:
            if match.group("name") != "Immunity":
                raise ValueError(f"Unexpected MetaChemistry Skill parameter: {text!r}")
            result["parameter"] = match.group("parameter")
        elif match.group("name") == "Immunity":
            raise ValueError(f"Missing MetaChemistry Immunity parameter: {text!r}")
        return result
    raise ValueError(f"Unrecognized MetaChemistry component: {text!r}")


def project_metachemistry_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose compound chart components without inferring how their effects resolve.

    Only the five source-verified compound roll rows are supported. Keep the
    original source text for display, provenance and compatibility, and reject
    unexpected source formatting rather than silently losing a component.
    """

    projected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for original in rows:
        row = original.copy()
        roll, result = str(row["roll"]), row["result"]
        if not isinstance(result, str):
            raise ValueError(f"MetaChemistry outcome must be text: {roll!r}")
        if roll in _METACHEMISTRY_COMPOUND_ROLLS:
            if roll in seen:
                raise ValueError(f"Duplicate MetaChemistry compound roll: {roll!r}")
            seen.add(roll)
            parts = result.split(" + ")
            if len(parts) != 2:
                raise ValueError(f"Unexpected MetaChemistry combination: {roll!r}")
            row["outcome_components"] = [
                _metachemistry_component(part) for part in parts
            ]
        elif " + " in result:
            raise ValueError(f"Unreviewed MetaChemistry combination: {roll!r}")
        projected.append(row)
    return projected


def link_metachemistry_skill_components(
    rows: list[dict[str, Any]],
    *,
    reviewed_records: list[dict[str, Any]],
    public_skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach only unique reviewed Skill-family destinations to typed components.

    This is a discovery link, not a claim that a parameterized effect is
    identical to the base Skill or that the effect is active on any Trooper.
    """

    by_name: dict[str, list[dict[str, Any]]] = {}
    for record in reviewed_records:
        if (
            record.get("kind") != "skill"
            or record.get("facts", {}).get("category")
            not in {"common-skill", "special-skill"}
            or (record.get("variant_semantics") or {}).get("inheritance") == "source"
        ):
            continue
        name = record.get("name")
        if isinstance(name, str):
            by_name.setdefault(name.casefold(), []).append(record)

    published: dict[str, list[dict[str, Any]]] = {}
    for skill in public_skills:
        name = skill.get("name")
        if isinstance(name, str):
            published.setdefault(name.casefold(), []).append(skill)

    result: list[dict[str, Any]] = []
    for source_row in rows:
        row = source_row.copy()
        if "outcome_components" in row:
            components: list[dict[str, Any]] = []
            for original in row["outcome_components"]:
                component = original.copy()
                if component.get("kind") == "special-skill":
                    key = str(component["name"]).casefold()
                    reviewed = by_name.get(key, [])
                    matches = published.get(key, [])
                    if len(reviewed) == len(matches) == 1:
                        record_id = reviewed[0].get("id")
                        public_slug = matches[0].get("slug")
                        if (
                            isinstance(record_id, str)
                            and record_id.startswith("skill:")
                            and public_slug == record_id.removeprefix("skill:")
                        ):
                            component["public_reference"] = {
                                "catalog": "skills",
                                "id": public_slug,
                            }
                components.append(component)
            row["outcome_components"] = components
        result.append(row)
    return result


# Exact Weapon labels present in the reviewed Booty table. The public
# Weapon catalog must independently provide a unique matching identity.
_BOOTY_WEAPON_NAMES = frozenset({
    "Light Flamethrower",
    "Grenades",
    "DA CC Weapon",
    "EXP CC Weapon",
    "Adhesive Launcher Rifle",
    "Panzerfaust",
    "Monofilament CC Weapon",
    "MULTI Rifle",
    "MULTI Sniper Rifle",
    "HMG",
})


def link_booty_weapon_outcomes(
    rows: list[dict[str, Any]],
    *,
    public_weapons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Link only exact, uniquely published Weapon names from reviewed Booty rows.

    Keep conditional TAG/non-TAG semantics, source outcomes, and unresolved
    aliases unchanged; do not interpret the randomly selected result.
    """

    published: dict[str, list[str]] = {}
    for item in public_weapons:
        name, slug = item.get("name"), item.get("slug")
        if isinstance(name, str) and isinstance(slug, str) and slug:
            published.setdefault(name.casefold(), []).append(slug)

    def reference(value: str) -> dict[str, str] | None:
        if value not in _BOOTY_WEAPON_NAMES:
            return None
        slugs = published.get(value.casefold(), [])
        if len(slugs) != 1:
            return None
        return {"catalog": "weapons", "id": slugs[0]}

    result: list[dict[str, Any]] = []
    for original in rows:
        row = original.copy()
        branches = original.get("conditional_outcomes")
        if branches:
            projected = []
            for branch in branches:
                copy = branch.copy()
                link = reference(branch["result"])
                if link is not None:
                    copy["public_reference"] = link
                projected.append(copy)
            row["conditional_outcomes"] = projected
        else:
            link = reference(row["result"])
            if link is not None:
                row["public_reference"] = link
        result.append(row)
    return result


# Reviewed Booty source spellings and their canonical *family* identities.
# HMG is the official abbreviation for Heavy Machine Gun; the other
# entries preserve the printed level/MOD/parameter without asserting a
# separate variant-specific page or derived in-game effect.
_BOOTY_FAMILY_OUTCOMES: dict[str, tuple[str, str, dict[str, str] | None]] = {
    "HMG": ("weapons", "Heavy Machine Gun", None),
    "Multispectral Visor L1": (
        "equipment", "Multispectral Visor", {"kind": "level", "value": "1"}
    ),
    "Mimetism (-6)": ("skills", "Mimetism", {"kind": "modifier", "value": "-6"}),
    "BS Attack (Shock)": ("skills", "BS Attack", {"kind": "named", "value": "Shock"}),
    "BS Attack (+1B)": (
        "skills", "BS Attack", {"kind": "burst-modifier", "value": "+1B"}
    ),
    "Immunity (AP)": ("skills", "Immunity", {"kind": "named", "value": "AP"}),
    "Immunity (ARM)": ("skills", "Immunity", {"kind": "named", "value": "ARM"}),
}


def link_booty_family_outcomes(
    rows: list[dict[str, Any]],
    *,
    public_catalogs: dict[str, list[dict[str, Any]]],
    reviewed_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach verified family links, never inferred parameter-specific mechanics.

    Only explicitly reviewed source spellings can match. Every target must have
    exactly one published name and, for Skill/Equipment, one reviewed rule family.
    If identities become ambiguous or disappear, the original text remains.
    """

    names_by_catalog: dict[str, dict[str, list[str]]] = {}
    for catalog in ("weapons", "equipment", "skills"):
        names: dict[str, list[str]] = {}
        for item in public_catalogs.get(catalog, []):
            name, slug = item.get("name"), item.get("slug")
            if isinstance(name, str) and isinstance(slug, str) and slug:
                names.setdefault(name.casefold(), []).append(slug)
        names_by_catalog[catalog] = names

    rule_names: dict[tuple[str, str], list[str]] = {}
    for record in reviewed_records:
        kind, name = record.get("kind"), record.get("name")
        if kind not in {"skill", "equipment"} or not isinstance(name, str):
            continue
        if (record.get("variant_semantics") or {}).get("inheritance") == "source":
            continue
        if kind == "skill" and record.get("facts", {}).get("category") not in {
            "common-skill", "special-skill"
        }:
            continue
        identity = record.get("id")
        if isinstance(identity, str):
            rule_names.setdefault((kind, name.casefold()), []).append(identity)

    def resolve(outcome: dict[str, Any]) -> dict[str, Any]:
        value = outcome.get("result")
        match = _BOOTY_FAMILY_OUTCOMES.get(value) if isinstance(value, str) else None
        if match is None:
            return outcome
        catalog, name, variant = match
        slugs = names_by_catalog[catalog].get(name.casefold(), [])
        if len(slugs) != 1:
            return outcome
        slug = slugs[0]
        if catalog != "weapons":
            kind = "skill" if catalog == "skills" else "equipment"
            if rule_names.get((kind, name.casefold())) != [f"{kind}:{slug}"]:
                return outcome
        updated = outcome.copy()
        updated["public_reference"] = {"catalog": catalog, "id": slug}
        if variant is not None:
            updated["outcome_variant"] = variant.copy()
        if value != name and variant is None:
            updated["reference_name"] = name
        return updated

    result: list[dict[str, Any]] = []
    for original in rows:
        row = original.copy()
        if "conditional_outcomes" in row:
            row["conditional_outcomes"] = [
                resolve(branch) for branch in row["conditional_outcomes"]
            ]
        else:
            row = resolve(row)
        result.append(row)
    return result


def project_booty_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose two explicit Booty branches without replacing the Army result text.

    No eligibility decision, selected roll, or derived gameplay effect is stored.
    Unexpected conditional syntax fails closed instead of flattening a distinction.
    """

    projected: list[dict[str, Any]] = []
    for original in rows:
        row = original.copy()
        result = row["result"]
        if not isinstance(result, str):
            raise ValueError(f"Booty outcome must be text: {row['roll']!r}")
        if "TAG:" in result or "Other Troop Types:" in result:
            match = _BOOTY_CONDITIONAL.fullmatch(result)
            if match is None:
                raise ValueError(f"Unrecognized conditional Booty result: {row['roll']!r}")
            tag, other = match.group("tag").strip(), match.group("other").strip()
            if not tag or not other:
                raise ValueError(f"Empty conditional Booty branch: {row['roll']!r}")
            row["conditional_outcomes"] = [
                {"scope": "tag", "label": "TAG", "result": tag},
                {"scope": "other-troop-types", "label": "Other Troop Types", "result": other},
            ]
        projected.append(row)
    return projected
