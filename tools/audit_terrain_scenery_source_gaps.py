"""Read-only inventory of N5.3 terrain examples and scenery access tokens.

Printed pp. 143-145 are table/session context, not Weapon/Equipment
inventory or automatically canonical Terrain Type identities.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_document

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
PUBLICATION = ROOT / "data/generated/deployed-objects.json"

# The printed table is titled "Special Terrain Suggestions and Examples".
# Its example names are NOT extra Type-of-Terrain identities.
TERRAIN_TYPES = ("Aquatic", "Desert", "Mountain", "Jungle", "Zero-G")
EXAMPLE_LABELS = (
    "Beach", "Open Sea", "Swamp", "Rocky Ground", "Sand Dunes",
    "Low Mountain or Steep Hills", "Artic Plains", "Mid-Mountain",
    "High Mountain", "Woods", "Jungle", "Dense Jungle",
    "Primeval Forest", "Zero-G", "Storm", "Engine Room",
    "Generator Room", "Energy Core Room",
)
GATE_MARKERS = ("Narrow Gate", "Wide Gate")
EXPECTED_UNMAINTAINED = ("rule:special-terrain", "rule:access-width")


def audit_terrain_scenery_boundary(
    curated: dict[str, Any], publication: dict[str, Any],
) -> dict[str, Any]:
    """Classify the source elements while preventing published-object promotion."""
    records = {record["id"]: record for record in curated["records"]}
    if len(records) != len(curated["records"]):
        raise ValueError("Duplicate curated rule ID")
    if records.get("skill:terrain", {}).get("kind") != "skill":
        raise ValueError("Missing existing Terrain Special Skill reference")
    objects = publication.get("objects")
    if not isinstance(objects, list):
        raise ValueError("Missing reviewed deployed-object publication")
    excluded = {name.casefold() for name in (*EXAMPLE_LABELS, *GATE_MARKERS)}
    if any(
        isinstance(obj.get("name"), str)
        and obj["name"].strip().casefold() in excluded
        for obj in objects
    ):
        raise ValueError("Terrain or access token promoted to deployed object")
    if len(objects) != 17:
        raise ValueError("Reviewed deployed-object publication count changed")
    if any(key in records for key in EXPECTED_UNMAINTAINED):
        raise ValueError("New terrain/access source record needs re-review")
    if any(
        records.get(f"term:{name.lower().replace(' ', '-')}", {}).get("kind") == "term"
        for name in GATE_MARKERS
    ):
        raise ValueError("New gate token definition needs review")
    return {
        "scope": "terrain-scene-context-not-army-deployed-object-inventory",
        "sourcePages": [143, 144, 145],
        "optionalGameTableRules": True,
        "terrainTypes": list(TERRAIN_TYPES),
        "namedExampleCount": len(EXAMPLE_LABELS),
        "terrainExamples": [
            {"printedName": label, "disposition": "example-not-canonical-terrain-type"}
            for label in EXAMPLE_LABELS
        ],
        "sceneryGateTokens": [
            {"printedName": label, "disposition": "access-width-label-not-device"}
            for label in GATE_MARKERS
        ],
        "reviewStatus": {
            "terrainSkill": "maintained",
            "specialTerrainRule": "unmodelled",
            "accessWidthRule": "unmodelled",
            "accessWidthTokens": "unmodelled",
            "exampleTable": "unmodelled-not-18-missing-types",
        },
        "publishedDeployedObjectCount": len(objects),
    }


def verify_pinned_pdf(source: Path) -> str:
    """Verify source text of all three printed pages, without treating names as objects."""
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("PDF verification requires PyMuPDF") from exc
    raw = source.read_bytes()
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        if len(pdf) < 145:
            raise ValueError("Pinned PDF lacks terrain/scenery pages")
        page_text: dict[int, str] = {}
        for page in (143, 144, 145):
            extracted = pdf[page - 1].get_text("text", sort=False)
            if not isinstance(extracted, str):
                raise ValueError(f"Missing PDF text on page {page}")
            page_text[page] = " ".join(extracted.upper().split())
    for term in ("SPECIAL TERRAIN", "TYPES OF TERRAIN"):
        if term not in page_text[143]:
            raise ValueError(f"Terrain source heading drift: {term}")
    for label in TERRAIN_TYPES:
        if f"{label.upper()} TERRAIN" not in page_text[143]:
            raise ValueError(f"Terrain Type source drift: {label}")
    for term in ("DIFFICULT TERRAIN", "SATURATION", "VISIBILITY CONDITION"):
        if term not in page_text[144]:
            raise ValueError(f"Terrain characteristic source drift: {term}")
    table = page_text[145]
    if "SPECIAL TERRAIN SUGGESTIONS AND EXAMPLES" not in table:
        raise ValueError("Terrain suggestions table is missing")
    if "SCENERY STRUCTURES" not in table or "ACCESS WIDTH (AW)" not in table:
        raise ValueError("Scenery access width source is missing")
    # The longest label wraps around other table columns in PDF text output.
    for name in EXAMPLE_LABELS:
        needle = "LOW MOUNTAIN OR STEEP" if name == "Low Mountain or Steep Hills" else name.upper()
        if re.search(r"(?<![A-Z0-9])" + re.escape(needle) + r"(?![A-Z0-9])", table) is None:
            raise ValueError(f"Missing source table example: {name}")
    if "NARROW GATE" not in table or "WIDE GATE" not in table:
        raise ValueError("Access width token evidence is missing")
    if "SILHOUETTE ATTRIBUTE OF 2 OR LOWER" not in table:
        raise ValueError("Narrow gate eligibility text changed")
    return hashlib.sha256(raw).hexdigest()


def audit_source_files(
    curated_path: Path = CURATED,
    publication_path: Path = PUBLICATION,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    source = curated_path.read_bytes()
    published = publication_path.read_bytes()
    report = audit_terrain_scenery_boundary(
        load_curated_document(curated_path),
        json.loads(published),
    )
    return {
        **report,
        "curatedSha256": hashlib.sha256(source).hexdigest(),
        "publishedObjectSha256": hashlib.sha256(published).hexdigest(),
        "verifiedPdfSha256": verify_pinned_pdf(pdf_path) if pdf_path else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curated", type=Path, default=CURATED)
    parser.add_argument("--publication", type=Path, default=PUBLICATION)
    parser.add_argument("--pdf", type=Path, help="Check the locally pinned English N5.3 PDF")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_source_files(args.curated, args.publication, args.pdf)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Current terrain Types: {len(report['terrainTypes'])}")
        print(f"Suggested terrain examples: {report['namedExampleCount']}")
        print(f"Scenery gate tokens: {len(report['sceneryGateTokens'])}")
        print("Unmodelled reference scope: Special Terrain, Access Width and gate labels")
        print(f"Unchanged deployed objects: {report['publishedDeployedObjectCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
