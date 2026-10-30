"""Independent N5.3 p.74 quick profile table cross-check."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.audit_deployed_object_quick_profiles import (
    PRINTED_ROWS,
    SOURCE_SELECTORS,
    audit_p74,
    compare_quick_profiles,
    parse_quick_profiles,
)

ROOT = Path(__file__).resolve().parents[1]


def _printed() -> list[dict[str, object]]:
    text = "DEPLOYABLE PROFILES\n" + "\n".join(
        f"{name} 0 0 1 1" for name in PRINTED_ROWS
    )
    return parse_quick_profiles(text)


def test_p74_parser_preserves_repeated_printed_rows_and_fails_closed() -> None:
    parsed = _printed()
    assert len(parsed) == 13
    assert parsed[0]["printedName"] == "ARMED TURRET"
    assert parsed[0]["printedAttributes"] == {
        "ARM": 0, "BTS": 0, "STR": 1, "S": 1,
    }
    assert parsed[-1]["printedName"] == "MADTRAPS"
    with pytest.raises(ValueError, match="header"):
        parse_quick_profiles("ARMED TURRET 2 3 1 1")
    with pytest.raises(ValueError, match="rows changed"):
        parse_quick_profiles("DEPLOYABLE PROFILES\nARMED TURRET 2 3 1 1")


def test_p74_cross_check_never_collapses_family_or_creates_carriers() -> None:
    references = []
    for catalog, name, mode in set(SOURCE_SELECTORS.values()):
        refs = {
            "id": f"source-{catalog}-{name}-{mode}",
            "originRuleId": None,
            "sourceProfile": {"catalog": catalog, "name": name, "mode": mode},
            "attributes": {
                key: {
                    "status": "known", "value": str(value), "provenance": [
                        {"value": str(value), "source": {"kind": "army"}}
                    ],
                }
                for key, value in {"ARM": 0, "BTS": 0, "STR": 1, "S": 1}.items()
            },
        }
        references.append(refs)
    references.append({
        "id": "reviewed-weapon-armed-turret",
        "originRuleId": "weapon:armed-turret",
        "sourceProfile": None,
        "attributes": {
            key: {
                "status": "known", "value": str(value), "provenance": [
                    {"value": str(value), "source": {"kind": "curated"}}
                ],
            }
            for key, value in {"ARM": 0, "BTS": 0, "STR": 1, "S": 1}.items()
        },
    })
    data = {"scope": "reviewed-projection-not-complete-unit-usage", "objects": references}
    comparison = compare_quick_profiles(_printed(), data)
    assert comparison["printedRows"] == 13
    assert comparison["distinctReferenceObjects"] == 10
    assert comparison["familyRows"] == 1
    assert sorted(comparison["duplicateReferenceRows"].values()) == [2, 2]
    assert comparison["conflictingRows"] == []
    assert next(row for row in comparison["rows"] if row["printedName"] == "MINES")[
        "referenceId"
    ] is None

    mutated = copy.deepcopy(data)
    mutated["objects"] = [
        row for row in mutated["objects"]
        if row["sourceProfile"] is None
        or row["sourceProfile"]["name"] != "Madtraps"
    ]
    with pytest.raises(ValueError, match="Missing or ambiguous"):
        compare_quick_profiles(_printed(), mutated)

    mutated = copy.deepcopy(data)
    item = next(
        row for row in mutated["objects"]
        if row["sourceProfile"] is not None
        and row["sourceProfile"]["name"] == "Crazykoala"
    )
    item["attributes"]["S"]["value"] = "2"
    with pytest.raises(ValueError, match="Unreviewed"):
        compare_quick_profiles(_printed(), mutated)


def test_pinned_p74_table_reconciles_existing_reference_without_new_objects() -> None:
    pytest.importorskip("fitz")
    pdf = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    army_db = ROOT / "data/generated/infinity.db"
    if not pdf.is_file() or not army_db.is_file():
        pytest.skip("Pinned local PDF or Army database unavailable")
    result = audit_p74(
        pdf,
        army_db,
        ROOT / "data/curated/rules/n5-core-v5.3.json",
        ROOT / "config/validation/deployed-object-delivery-reviews.json",
        ROOT / "config/validation/deployed-object-candidate-reviews.json",
    )
    assert len(result["pdfSha256"]) == 64
    assert result["printedRows"] == 13
    assert result["distinctReferenceObjects"] == 10
    assert result["familyRows"] == 1
    assert sorted(result["duplicateReferenceRows"].values()) == [2, 2]
    assert [(row["printedName"], row["differences"]) for row in result["conflictingRows"]] == [
        ("ARMED TURRET", [{
            "field": "S", "printed": 1, "reviewed": 2,
            "status": "known-source-conflict",
        }]),
    ]
    assert {
        row["printedName"] for row in result["rowsWithKnownSourceDisputes"]
    } == {"ARMED TURRET", "DAZER"}
    dazer = next(row for row in result["rows"] if row["printedName"] == "DAZER")
    assert dazer["printedAttributes"]["S"] == 0
    assert dazer["differences"] == []
    assert {item["value"] for item in dazer["knownSourceDisputes"][0]["alternatives"]} == {
        "0", "1",
    }
