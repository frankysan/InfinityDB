"""N5.3 Weapon Chart word-coordinate extraction for offline source review.

This identifies printed rows; it does not approve database facts or gameplay rules.
Column positions intentionally apply to the reviewed N5.3 PDF layout only.
"""

from __future__ import annotations

import re
from typing import Any

PDF_PAGES = range(176, 189)


class WeaponChartAuditError(ValueError):
    """Chart structure or input prevents a reproducible comparison."""


def _cell(
    words: list[tuple[float, float, str]], y: float, left: float,
    right: float, *, wrapped: bool = False,
) -> str:
    """Read a chart cell, including the two baselines of combined saves."""
    tolerance = 5.2 if wrapped else 3.2
    relevant = [
        (x, wy, word) for x, wy, word in words
        if left <= x < right and abs(wy - y) < tolerance
    ]
    return " ".join(
        word for x, wy, word in sorted(relevant, key=lambda item: (round(item[1] / 3), item[0]))
    ).strip()


def _chart_burst_anchors(words: list[tuple[float, float, str]]) -> list[tuple[float, str]]:
    """Locate chart rows, including the early rows on N5.3 page 188."""
    return sorted(
        (y, word) for x, y, word in words
        if 294 <= x <= 310 and 100 < y < 800
        and re.fullmatch(r"(?:[1-9]|10|--)", word)
    )


def rows_from_words(words: list[tuple[float, float, str]], page_number: int
                    ) -> list[dict[str, Any]]:
    """Reassemble rows of the *specific* N5 v5.3 Weapon Chart layout.

    Burst values anchor table rows. Name text may span up to four baselines;
    midpoints between Burst anchors stop adjacent names from merging. Limit
    the name window to the printed name column and 14.9 vertical points.
    Unreadable cells are left blank, never reconstructed by guessing.
    """
    anchors = _chart_burst_anchors(words)
    result: list[dict[str, Any]] = []
    for index, (y, _) in enumerate(anchors):
        low = max(y - 14.9, (anchors[index - 1][0] + y) / 2) if index else y - 14.9
        high = (
            min(y + 14.9, (anchors[index + 1][0] + y) / 2)
            if index + 1 < len(anchors) else y + 14.9
        )
        name_words = [
            (wy, x, word) for x, wy, word in words
            if 12 <= x < 90 and low < wy < high and word != "NAME"
        ]
        name = " ".join(
            word for _, _, word in sorted(
                name_words, key=lambda entry: (round(entry[0] / 4.8), entry[1])
            )
        )
        result.append({
            "page": page_number,
            "name": name,
            "ps": _cell(words, y, 263, 293),
            "burst": _cell(words, y, 293, 314),
            "ammunition": _cell(words, y, 315, 367),
            "savingAttribute": _cell(words, y, 367, 418, wrapped=True),
            "savingRolls": _cell(words, y, 418, 462),
        })
    return result
