"""Canonical persistent text/JSON output helpers.

Persistent build artifacts must not inherit the host platform's newline policy.
These helpers always emit UTF-8 text with LF line endings and provide one
stable JSON formatting contract for generated files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_text_lf(path: Path, text: str, *, atomic: bool = False) -> None:
    """Write UTF-8 text with LF line endings, optionally by atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    target = path.with_suffix(path.suffix + ".tmp") if atomic else path
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical)
    if atomic:
        target.replace(path)


def json_text(
    value: Any,
    *,
    compact: bool = False,
    sort_keys: bool = False,
    final_newline: bool | None = None,
) -> str:
    """Return InfinityDB's canonical UTF-8 JSON text representation."""
    if compact:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=sort_keys,
            separators=(",", ":"),
            allow_nan=False,
        )
    else:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=sort_keys,
            indent=2,
            allow_nan=False,
        )
    if final_newline is None:
        final_newline = not compact
    if final_newline:
        text += "\n"
    return text


def write_json_lf(
    path: Path,
    value: Any,
    *,
    compact: bool = False,
    sort_keys: bool = False,
    final_newline: bool | None = None,
    atomic: bool = False,
) -> None:
    """Write JSON with deterministic formatting and LF line endings."""
    write_text_lf(
        path,
        json_text(
            value,
            compact=compact,
            sort_keys=sort_keys,
            final_newline=final_newline,
        ),
        atomic=atomic,
    )
