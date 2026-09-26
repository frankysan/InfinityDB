"""Shared Fireteam chart semantic helpers used by audits and application projection."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

_FTO_RE = re.compile(r"\bFTO(?:[-\s]?(\d+))?\b", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\(([^()]*)\)")


def ascii_upper(value: str | None) -> str:
    """Return accent-insensitive uppercase text for source-label comparison."""
    normalized = unicodedata.normalize("NFKD", value or "")
    plain = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return plain.upper()


def fto_marker(value: str | None) -> str | None:
    """Return ``generic`` or the numbered FTO variant found in one label."""
    match = _FTO_RE.search(ascii_upper(value))
    if match is None:
        return None
    return match.group(1) or "generic"


def member_fto_marker(name: str | None, comment: str | None) -> str | None:
    """Return the strongest FTO marker present in one Fireteam member row."""
    matches = _FTO_RE.findall(f"{ascii_upper(name)} {ascii_upper(comment)}")
    if not matches:
        return None
    numbered = [match for match in matches if match]
    return numbered[0] if numbered else "generic"


def identity_tokens(value: str | None) -> tuple[str, ...]:
    """Return source-label identity tokens used only for FTO option matching."""
    text = ascii_upper(value)
    text = _FTO_RE.sub(" ", text)
    # Army currently uses both REINF. and REF. around Reinforcement FTO labels.
    text = re.sub(r"\b(?:REINF|REF)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    tokens: list[str] = []
    for token in text.split():
        if token == "THE":
            continue
        if token == "KNIGHTS":
            token = "KNIGHT"
        tokens.append(token)
    return tuple(tokens)


def fto_option_matches(member_name: str | None, marker: str, option_name: str | None) -> bool:
    """Return whether an Army-local loadout option satisfies a chart FTO marker."""
    option_marker = fto_marker(option_name)
    if option_marker is None:
        return False
    if marker != "generic" and option_marker != marker:
        return False
    member_tokens = set(identity_tokens(member_name))
    option_tokens = set(identity_tokens(option_name))
    if not member_tokens or not option_tokens:
        return False
    return member_tokens <= option_tokens or option_tokens <= member_tokens


def equivalence_labels(comment: str | None) -> tuple[str, ...]:
    """Return ordered Fireteam-Level equivalence labels from parenthetical source text."""
    labels: list[str] = []
    for match in _BRACKET_RE.findall(comment or ""):
        labels.extend(part.strip() for part in match.split(",") if part.strip())
    return tuple(labels)


def is_wildcard_name(name: str | None) -> bool:
    """Return whether the source Fireteam row represents Army-local Wildcards."""
    return "WILDCARD" in ascii_upper(name)


def decode_fireteam_spec(value: Any, army_id: int) -> dict[str, int]:
    """Decode and validate one source Fireteam type-limit mapping."""
    if value in (None, ""):
        return {}
    try:
        spec = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError as exc:
        raise ValueError(f"Army {army_id} has invalid fireteam_spec JSON") from exc
    if not isinstance(spec, dict):
        raise ValueError(f"Army {army_id} fireteam_spec must decode to an object")
    result: dict[str, int] = {}
    for key, raw in spec.items():
        if not isinstance(key, str) or type(raw) is not int or raw < 0:
            raise ValueError(
                f"Army {army_id} has invalid Fireteam limit {key!r}={raw!r}"
            )
        normalized_key = key.strip().upper()
        if not normalized_key:
            raise ValueError(f"Army {army_id} has an empty Fireteam limit key")
        if normalized_key in result:
            raise ValueError(
                f"Army {army_id} has duplicate Fireteam limit key {normalized_key!r}"
            )
        result[normalized_key] = raw
    return result
