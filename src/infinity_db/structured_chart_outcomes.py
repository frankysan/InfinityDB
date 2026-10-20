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
