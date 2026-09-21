"""Shared numeric-or-slug identifier primitives for maintained source references."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, TypeAlias

IdentifierRef: TypeAlias = int | str
IDENTIFIER_SLUG_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def normalize_identifier_slug(value: object) -> str:
    """Return the deterministic lowercase ASCII slug candidate for one label."""

    decomposed = unicodedata.normalize("NFKD", str(value or "")).casefold()
    ascii_text = "".join(
        character
        for character in decomposed
        if not unicodedata.category(character).startswith("M") and character.isascii()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def require_identifier_slug(value: object, *, context: str) -> str:
    """Validate one already-authored domain-local slug."""

    if not isinstance(value, str) or not IDENTIFIER_SLUG_PATTERN.fullmatch(value):
        raise ValueError(
            f"{context} must be a lowercase ASCII slug containing only letters, "
            "numbers, and single hyphen separators"
        )
    if value.isdigit():
        raise ValueError(
            f"{context} must not be digit-only; use an integer for numeric references"
        )
    return value


def parse_identifier_ref(value: Any, *, context: str) -> IdentifierRef:
    """Validate a positive integer or unambiguous authored slug reference."""

    if type(value) is int:
        if value <= 0:
            raise ValueError(f"{context} must be a positive integer or slug")
        return value
    if isinstance(value, str):
        return require_identifier_slug(value, context=context)
    raise ValueError(f"{context} must be a positive integer or slug")
