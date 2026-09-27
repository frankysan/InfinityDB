"""Interpret evidence-backed date information encoded in Army source revisions."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import date, timedelta

_SOURCE_VERSION_RE = re.compile(r"^\d+\.(\d{3,5})\.\d+$")


def army_source_version_date(version: object) -> date | None:
    """Return the observed Army revision date encoded by one source version.

    Current and historical Corvus Belli Army versions use a middle component made
    from a two-digit year followed by a non-zero-padded ordinal day of year.  The
    interpretation is evidence-backed rather than an upstream documented contract,
    so unknown formats return ``None`` instead of being guessed.
    """

    if not isinstance(version, str):
        return None
    match = _SOURCE_VERSION_RE.fullmatch(version)
    if match is None:
        return None

    date_code = match.group(1)
    year = 2000 + int(date_code[:2])
    ordinal = int(date_code[2:])
    if ordinal < 1:
        return None

    candidate = date(year, 1, 1) + timedelta(days=ordinal - 1)
    if candidate.year != year:
        return None
    return candidate


def latest_army_source_change_date(
    versions: Mapping[str, object] | Iterable[str],
) -> date | None:
    """Return the latest encoded date when every observed revision is understood."""

    values = versions.keys() if isinstance(versions, Mapping) else versions
    parsed: list[date] = []
    for version in values:
        changed_on = army_source_version_date(version)
        if changed_on is None:
            return None
        parsed.append(changed_on)
    return max(parsed, default=None)
