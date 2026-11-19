# ruff: noqa: E501  # Exact pinned source prose in the one-time replacements.
"""One-time, source-reviewed ITS 17 V0.2 token-diameter reconciliation.

The mission pages use matching-diameter scenery; both source editions
independently print a global token table (EN PDF p. 13 / ES PDF p. 14).
This migration updates only reviewed token references, original source pins
and their existing membership tests. It does not change ITS 18 or publish ITS 17.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
TESTS = ROOT / "tests"
EXPECTED_SHA = "245ccbab339c2197e3a3fb4e2ccad303950e0fe03bfd49f9ac2bf6047a446599"
EN, ES = "its-season-17-v0.2-en-pdf", "its-season-17-v0.2-es-pdf"
CHART_CITATIONS = [
    {"sourceId": EN, "page": 13, "section": "Diameter of ITS Tokens"},
    {"sourceId": ES, "page": 14, "section": "Diámetro de los Tokens ITS"},
]

# Replace only the inaccurate omission claim in each independently pinned
# scenario. Original mission-specific representation conflicts remain intact.
CHANGES: dict[str, tuple[tuple[str, str], ...]] = {
    "evacuation": (
        ("The source does not assign a fixed physical base diameter to the Civilian figures or Tokens, so map symbols indicate center positions only.",
         "ITS 17 V0.2 EN p. 13 / ES p. 14 sets Player A/B Tokens at 25 mm, but does not prescribe Civilian Model base sizes; map symbols indicate center positions only."),
        ("Each is a Console A Token or a scenery piece of the same diameter as that Token.",
         "Each is a Console A Token or scenery matching its 40 mm diameter (ITS 17 V0.2 EN p. 13 / ES p. 14)."),
    ),
    "hardlock": (
        ("the ITS 17 mission does not state an independent millimeter diameter.",
         "the ITS 17 V0.2 EN p. 13 / ES p. 14 chart gives Console Tokens 40 mm and Beacon Tokens 25 mm."),
    ),
    "uplink-center": (
        ("the ITS 17 mission does not independently specify a numeric diameter.",
         "the ITS 17 V0.2 EN p. 13 / ES p. 14 chart gives Transmission Antenna and Tech-Coffin Tokens 40 mm."),
    ),
    "superiority": (
        ("ITS 17 does not independently specify a numeric diameter.",
         "The ITS 17 V0.2 EN p. 13 / ES p. 14 chart specifies 40 mm for Console Tokens."),
    ),
    "provisioning": (
        ("the ITS 17 mission does not specify an independent 40 mm size.",
         "the ITS 17 V0.2 EN p. 13 / ES p. 14 chart specifies a 40 mm Tech-Coffin Token."),
    ),
    "area-of-interest": (
        ("Neither ITS 17 language edition independently specifies a 40 mm diameter.",
         "ITS 17 V0.2 EN p. 13 / ES p. 14 specifies a 40 mm Transmission Antenna Token and 25 mm Player A/B Tokens."),
    ),
    "last-launch": (
        ("ITS 17 does not independently specify the 40 mm scenery size of ITS 18.",
         "The ITS 17 V0.2 EN p. 13 / ES p. 14 chart specifies a 40 mm Tech-Coffin Token."),
        ("ITS 17 does not independently specify a 40 mm diameter.",
         "The ITS 17 V0.2 EN p. 13 / ES p. 14 chart specifies a 40 mm Console Token."),
    ),
    "b-pong": (
        ("Neither ITS 17 edition specifies an independent 40 mm or 25 mm diameter for this mission.",
         "ITS 17 V0.2 EN p. 13 / ES p. 14 lists the Beacon Token at 25 mm, not 40 mm."),
    ),
    "crossing-lines": (
        ("do not inherit ITS 18's explicit 40 mm requirement.",
         "both types are 40 mm under the ITS 17 V0.2 EN p. 13 / ES p. 14 chart; the naming conflict remains."),
        ("Neither specifies a fixed 40 mm size.",
         "Both Token types are 40 mm under the ITS 17 V0.2 EN p. 13 / ES p. 14 chart."),
        ("without independently fixing a 40 mm size.",
         "both Token types are 40 mm under the ITS 17 V0.2 EN p. 13 / ES p. 14 chart, despite the naming conflict."),
    ),
    "corporate-appropriation": (
        ("ITS 17 gives no fixed 40 mm.",
         "The ITS 17 V0.2 EN p. 13 / ES p. 14 chart gives the Objective Token a 40 mm diameter."),
    ),
    "critical-intervention": (
        ("Neither edition specifies an independent 40 mm dimension.",
         "ITS 17 V0.2 EN p. 13 / ES p. 14 specifies 40 mm for the Console Token."),
        ("without a specified fixed 40 mm footprint.",
         "at 40 mm under the ITS 17 V0.2 EN p. 13 / ES p. 14 Transmission Antenna chart entry."),
    ),
    "akial-interference": (
        ("Neither original fixes a 40 mm size.",
         "The ITS 17 V0.2 EN p. 13 / ES p. 14 chart fixes the Transmission Antenna Token at 40 mm."),
    ),
}


def _encoded(document: dict) -> bytes:
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _updated_test(path: Path) -> bytes:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    match = [i for i, line in enumerate(lines)
             if 'for ' in line and 'in binding["citations"]] == [' in line]
    if len(match) != 1:
        raise ValueError(f"Expected one member citation assertion: {path.name}")
    start = match[0] + 1
    ending = next((i for i in range(start, len(lines)) if lines[i].strip() == "]"), None)
    if ending is None or ending - start > 8:
        raise ValueError(f"Unexpected citation list: {path.name}")
    if "(EN, 13)" in "".join(lines[start:ending]):
        raise ValueError(f"Token chart already cited in {path.name}")
    lines.insert(ending, '        (EN, 13), (ES, 14),\n')
    return "".join(lines).encode("utf-8")


def main() -> int:
    season = json.loads(SEASON.read_text(encoding="utf-8"))
    raw = SHARED.read_bytes()
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
        raise ValueError("Unexpected ITS 17 shared library revision")
    if season["sharedScenarioLibrary"]["sha256"] != EXPECTED_SHA:
        raise ValueError("Season membership no longer pins the expected library")
    library = json.loads(raw)
    definitions = {entry["id"]: entry for entry in library["definitions"]}
    members = {entry["scenarioId"]: entry for entry in season["scenarioCollection"]["members"]}
    expected = {f"scenario:{slug}" for slug in CHANGES}
    if len(definitions) != 16 or len(members) != 16 or expected - definitions.keys():
        raise ValueError("Unexpected ITS 17 scenario inventory")

    pending: dict[Path, bytes] = {}
    for slug, changes in CHANGES.items():
        identifier = f"scenario:{slug}"
        entry = definitions[identifier]
        record = entry["record"]
        if record["scope"]["seasons"] != ["its-17"]:
            raise ValueError(f"Unexpected season: {slug}")
        contents = json.dumps(record, ensure_ascii=False)
        for before, after in changes:
            if contents.count(before) != 1:
                raise ValueError(f"Missing or repeated source wording: {slug}: {before}")
            contents = contents.replace(before, after)
        entry["record"] = json.loads(contents)
        if not entry["record"]["facts"]["mission"]["rules"]:
            raise ValueError(f"Missing mission rules: {slug}")
        binding = members[identifier]["sharedDefinition"]
        if len(binding["citations"]) != len(record["citations"]):
            raise ValueError(f"Source binding drift: {slug}")
        for field in (entry["record"]["citations"], binding["citations"]):
            if any((p["sourceId"], p["page"]) in {(EN, 13), (ES, 14)} for p in field):
                raise ValueError(f"Chart already pinned: {slug}")
            field.extend(CHART_CITATIONS)
        test_name = slug.replace("-", "_")
        test = TESTS / f"test_its17_{test_name}_publication.py"
        pending[test] = _updated_test(test)

    new_library = _encoded(library)
    season["sharedScenarioLibrary"]["sha256"] = hashlib.sha256(new_library).hexdigest()
    pending[SHARED] = new_library
    pending[SEASON] = _encoded(season)
    if len(pending) != len(CHANGES) + 2:
        raise ValueError("Unexpected migration file set")
    for path, content in pending.items():
        path.write_bytes(content)
    print(f"Reviewed token diameters in {len(CHANGES)} ITS 17 missions")
    print(f"Pinned chart: {EN}:13 / {ES}:14")
    print(f"Shared library SHA-256: {season['sharedScenarioLibrary']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
