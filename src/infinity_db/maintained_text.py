"""Parse and validate inline semantic tokens in maintained editorial text."""

from __future__ import annotations

import re
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from typing import Any

from infinity_db.domain_slugs import validate_typed_domain_id

MAINTAINED_REFERENCE_KINDS = frozenset(
    {"skill", "equipment", "weapon", "ammunition", "trait", "state", "hacking-program"}
)
DISPLAY_FORMS = frozenset({"plural"})
DISTANCE_UNITS = frozenset({"cm", "inch"})
_DISTANCE_PATTERN = re.compile(
    r"^distance:(?P<value>[+-]?(?:\d+(?:\.\d+)?|\.\d+)):(?P<unit>cm|inch)$"
)
_UNMARKED_DISTANCE_PATTERN = re.compile(
    r"(?<![\w.])[+-]?\d+(?:\.\d+)?\s*(?:cm\b|inches?\b|[\"″])",
    re.IGNORECASE,
)


def _number(value: Decimal) -> int | float:
    integral = value.to_integral_value()
    if value == integral:
        return int(integral)
    return float(value)


def _parse_distance(body: str, context: str) -> dict[str, Any] | None:
    match = _DISTANCE_PATTERN.fullmatch(body)
    if match is None:
        if body.startswith("distance:"):
            raise ValueError(
                f"{context}: distance token must use [[distance:<number>:cm|inch]]"
            )
        return None
    raw_value = match.group("value")
    try:
        value = Decimal(raw_value)
    except InvalidOperation as exc:  # pragma: no cover - guarded by the regex
        raise ValueError(f"{context}: invalid distance value {raw_value!r}") from exc
    if value < 0:
        raise ValueError(f"{context}: distance values must be nonnegative")
    centimeters = value if match.group("unit") == "cm" else value * Decimal("2.5")
    return {
        "type": "distance",
        "centimeters": _number(centimeters),
        "positive_sign": raw_value.startswith("+"),
    }


def _parse_reference(body: str, context: str) -> dict[str, Any]:
    target_text, separator, display_text = body.partition("|")
    target_text = target_text.strip()
    if separator:
        display_text = display_text.strip()
        if not display_text:
            raise ValueError(f"{context}: maintained-text display text must not be empty")
        if "[[" in display_text or "]]" in display_text:
            raise ValueError(
                f"{context}: maintained-text display text must not contain token delimiters"
            )
    else:
        display_text = ""

    display_form = None
    for form in DISPLAY_FORMS:
        suffix = f":{form}"
        if target_text.endswith(suffix):
            display_form = form
            target_text = target_text[: -len(suffix)]
            break

    kind, separator, _ = target_text.partition(":")
    if not separator or kind not in MAINTAINED_REFERENCE_KINDS:
        raise ValueError(
            f"{context}: unsupported maintained-text reference namespace {kind!r}; "
            f"expected one of {sorted(MAINTAINED_REFERENCE_KINDS)}"
        )
    validate_typed_domain_id(
        target_text,
        expected_domain=kind,
        context=f"{context} maintained-text target",
    )
    token: dict[str, Any] = {"type": "reference", "target": target_text}
    if display_form is not None:
        token["display_form"] = display_form
    if display_text:
        token["display_text"] = display_text
    return token


def parse_maintained_text(value: str, *, context: str = "maintained text") -> list[dict[str, Any]]:
    """Parse maintained inline tokens while preserving ordinary text verbatim.

    ``[[skill:jump]]`` references a semantic rules identity. ``:plural`` is a
    supported display-form suffix and ``|Custom text`` overrides the visible label.
    ``[[distance:2:inch]]`` stores a typed distance that the browser can render in
    the active cm/in preference. A literal opening token delimiter is escaped as
    ``\\[[``.
    """

    if not isinstance(value, str):
        raise ValueError(f"{context}: maintained text must be a string")

    tokens: list[dict[str, Any]] = []
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            tokens.append({"type": "text", "text": "".join(buffer)})
            buffer.clear()

    index = 0
    while index < len(value):
        if value.startswith(r"\[[", index):
            end = value.find("]]", index + 3)
            if end < 0:
                buffer.append("[[")
                index += 3
            else:
                buffer.append(value[index + 1 : end + 2])
                index = end + 2
            continue
        if value.startswith("[[", index):
            flush()
            end = value.find("]]", index + 2)
            if end < 0:
                raise ValueError(f"{context}: unclosed maintained-text token")
            body = value[index + 2 : end].strip()
            if not body:
                raise ValueError(f"{context}: maintained-text token must not be empty")
            token = _parse_distance(body, context)
            tokens.append(token if token is not None else _parse_reference(body, context))
            index = end + 2
            continue
        if value.startswith("]]", index):
            raise ValueError(f"{context}: unmatched maintained-text closing delimiter")
        buffer.append(value[index])
        index += 1
    flush()
    return tokens


def maintained_text_fields(document: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield every maintained editorial text field in one curated rules document."""

    for index, skill_type in enumerate(document.get("skillTypes", [])):
        descriptions = skill_type.get("descriptions") if isinstance(skill_type, dict) else None
        if not isinstance(descriptions, dict):
            continue
        for form in ("singular", "plural"):
            value = descriptions.get(form)
            if isinstance(value, str):
                yield f"skillTypes[{index}].descriptions.{form}", value

    for index, label in enumerate(document.get("labels", [])):
        if isinstance(label, dict) and isinstance(label.get("description"), str):
            yield f"labels[{index}].description", label["description"]

    for index, record in enumerate(document.get("records", [])):
        if not isinstance(record, dict):
            continue
        summary = record.get("summary")
        if isinstance(summary, str):
            yield f"records[{index}].summary", summary
        facts = record.get("facts")
        if not isinstance(facts, dict):
            continue
        for key in ("requirements", "effects", "restrictions", "rules"):
            values = facts.get(key)
            if not isinstance(values, list):
                continue
            for value_index, text in enumerate(values):
                if isinstance(text, str):
                    yield f"records[{index}].facts.{key}[{value_index}]", text
        basis = facts.get("basis")
        if isinstance(basis, str):
            yield f"records[{index}].facts.basis", basis
        terminology = facts.get("terminology")
        if isinstance(terminology, list):
            for term_index, term in enumerate(terminology):
                if isinstance(term, dict) and isinstance(term.get("meaning"), str):
                    yield (
                        f"records[{index}].facts.terminology[{term_index}].meaning",
                        term["meaning"],
                    )
        levels = facts.get("levels")
        if isinstance(levels, list):
            for level_index, level in enumerate(levels):
                if not isinstance(level, dict):
                    continue
                requirement = level.get("requirement")
                if isinstance(requirement, str):
                    yield (
                        f"records[{index}].facts.levels[{level_index}].requirement",
                        requirement,
                    )
                bonuses = level.get("bonuses")
                if isinstance(bonuses, list):
                    for bonus_index, bonus in enumerate(bonuses):
                        if isinstance(bonus, str):
                            yield (
                                f"records[{index}].facts.levels[{level_index}]"
                                f".bonuses[{bonus_index}]",
                                bonus,
                            )


def validate_maintained_text_syntax(document: dict[str, Any]) -> None:
    """Validate token syntax in every maintained editorial field of one document."""

    for context, text in maintained_text_fields(document):
        tokens = parse_maintained_text(text, context=context)
        literal_text = "".join(
            token["text"] for token in tokens if token["type"] == "text"
        )
        match = _UNMARKED_DISTANCE_PATTERN.search(literal_text)
        if match is not None:
            raise ValueError(
                f"{context}: distance literal {match.group(0)!r} must use a "
                "[[distance:<number>:cm|inch]] token"
            )


def maintained_text_targets(value: str, *, context: str = "maintained text") -> set[str]:
    """Return semantic reference targets from one maintained text value."""

    return {
        token["target"]
        for token in parse_maintained_text(value, context=context)
        if token["type"] == "reference"
    }
