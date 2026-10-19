"""Source-preserving typed projections for conditional Army reference-chart outcomes."""

from __future__ import annotations

import re
from typing import Any

_BOOTY_CONDITIONAL = re.compile(
    r"TAG: (?P<tag>[^/]+?) / Other Troop Types: (?P<other>[^/]+)"
)


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
