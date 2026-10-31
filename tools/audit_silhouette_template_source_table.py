"""Audit the N5.3 p. 18 Silhouette Templates table against browser diagrams.

S0 has a fixed 25 mm base and 3 mm height. SX is the Prone representation
with a 3 mm height and the original Trooper Silhouette's base width, not a
new fixed base size or permanent Unit/Profile attribute.
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
MANIFEST = ROOT / "config/validation/silhouette-template-source-table.json"
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
RENDERER = ROOT / "src/infinity_db/web/static/silhouette-diagrams.js"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"

# Exact source table from N5.3 English p. 18, in printed order.
PINNED = (
    ("X", "SX", None, 3),
    (0, "S0", 25, 3),
    (1, "S1", 25, 25),
    (2, "S2", 25, 40),
    (3, "S3", 40, 32),
    (4, "S4", 55, 32),
    (5, "S5", 40, 45),
    (6, "S6", 40, 55),
    (7, "S7", 55, 67),
    (8, "S8", 70, 70),
)
PRONE_POLICY = {
    "template": "SX",
    "heightMm": 3,
    "baseWidthRule": "retain-trooper-original-silhouette-base-width",
    "context": "prone-state",
    "fixedBaseMm": None,
}
DIAGRAM_POLICY = {
    "diagrams": "S1-S8-only",
    "withoutSvg": ["S0", "SX"],
    "visualization": "source-proportional-uniform-scale",
}
_RENDERER_ROWS = re.compile(
    r"\{\s*id:\s*([1-8]),\s*widthMm:\s*(\d+),\s*heightMm:\s*(\d+),"
    r"\s*viewBoxWidth:\s*([\d.]+),\s*viewBoxHeight:\s*([\d.]+)\s*\}"
)


def audit_silhouette_table(
    manifest: dict[str, Any],
    curated: dict[str, Any],
    renderer: str,
) -> dict[str, Any]:
    """Pin numeric source geometry and block accidental SX/S0 diagram substitutions."""
    if set(manifest) != {
        "formatVersion", "sourceId", "sourcePage", "reviewStatus",
        "domain", "proneSilhouette", "diagramPolicy", "rows",
    }:
        raise ValueError("Unexpected silhouette source manifest schema")
    if (
        type(manifest["formatVersion"]) is not int
        or manifest["formatVersion"] != 1
        or manifest["sourceId"] != "n5-core-v5.3-pdf"
        or manifest["sourcePage"] != 18
        or manifest["reviewStatus"] != "source-reviewed-audit-only"
        or manifest["domain"] != "trooper-geometry-reference-not-deployed-object-profile"
        or manifest["proneSilhouette"] != PRONE_POLICY
        or manifest["diagramPolicy"] != DIAGRAM_POLICY
    ):
        raise ValueError("Silhouette source scope/provenance drift")
    rows = manifest["rows"]
    if not isinstance(rows, list) or len(rows) != len(PINNED):
        raise ValueError("Expected ten Silhouette source rows (SX and S0-S8)")
    for index, (row, (value, template, base, height)) in enumerate(
        zip(rows, PINNED, strict=True),
    ):
        if (
            not isinstance(row, dict)
            or set(row) != {"id", "template", "baseMm", "heightMm"}
            or type(row["id"]) is not type(value)
            or row["id"] != value
            or row["template"] != template
            or row["baseMm"] != base
            or type(row["heightMm"]) is not int
            or row["heightMm"] != height
        ):
            raise ValueError(f"Silhouette geometry source drift at row {index}")
    records = {record["id"]: record for record in curated["records"]}
    if len(records) != len(curated["records"]):
        raise ValueError("Duplicate maintained reference record ID")
    attribute = records.get("attribute:s")
    prone = records.get("state:prone")
    if not (
        attribute is not None
        and attribute["kind"] == "attribute"
        and any(
            cite.get("sourceId") == "n5-core-v5.3-pdf"
            and cite.get("page") == 9
            for cite in attribute.get("citations", [])
        )
        and prone is not None
        and prone["kind"] == "state"
    ):
        raise ValueError("Maintained Silhouette attribute/Prone reference drift")

    numeric = [
        (int(s), int(width), int(height), float(svg_width), float(svg_height))
        for s, width, height, svg_width, svg_height
        in _RENDERER_ROWS.findall(renderer)
    ]
    if len(numeric) != 8 or len({row[0] for row in numeric}) != 8:
        raise ValueError("Browser S1-S8 diagram set changed")
    expected_numeric = [
        (value, base, height)
        for value, _, base, height in PINNED
        if isinstance(value, int) and value >= 1
    ]
    if [(value, base, height) for value, base, height, _, _ in numeric] != expected_numeric:
        raise ValueError("Browser diagram dimensions diverge from N5.3 p. 18")
    if any(svg_width <= 0 or svg_height <= 0 for _, _, _, svg_width, svg_height in numeric):
        raise ValueError("Invalid browser diagram SVG viewport")

    for required in (
        "const SVG_UNITS_PER_MM = 4.23336",
        "(item.viewBoxWidth / SVG_UNITS_PER_MM) * pixelsPerMm",
        "(item.viewBoxHeight / SVG_UNITS_PER_MM) * pixelsPerMm",
        "No supplied source SVG for S0/SX",
        "raw === \"X\" || raw === \"SX\"",
        "id === 0 || id === \"X\"",
        "25 mm base, 3 mm high",
        "3 mm high while Prone; base width follows the Trooper's Silhouette Attribute",
    ):
        if required not in renderer:
            raise ValueError(f"Browser silhouette source/representation drift: {required}")

    for number in range(1, 9):
        if not (ROOT / f"src/infinity_db/web/static/silhouettes/silhouette-{number}.svg").is_file():
            raise ValueError(f"Missing source-backed S{number} diagram SVG")
    return {
        "scope": manifest["domain"],
        "sourcePage": 18,
        "rowCount": len(rows),
        "fixedTemplateCount": 9,
        "browserDiagramCount": len(numeric),
        "specialTemplate": manifest["proneSilhouette"],
        "sourceRows": rows,
    }


def verify_pinned_pdf(path: Path, manifest: dict[str, Any]) -> str:
    """Verify the entire printed table and dynamic SX footnote against local PDF."""
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("PDF verification requires PyMuPDF") from exc
    raw = path.read_bytes()
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        if len(pdf) < 18:
            raise ValueError("Pinned N5.3 PDF lacks p. 18")
        extracted = pdf[17].get_text("text", sort=False)
        if not isinstance(extracted, str):
            raise ValueError("Missing Silhouette source text on p. 18")
    text = " ".join(extracted.upper().split())
    if "SILHOUETTE TEMPLATES" not in text:
        raise ValueError("Printed Silhouette heading missing")
    if "WHILE IN PRONE STATE" not in text or (
        "BASE CORRESPONDS WITH THE TROOPER" not in text
    ):
        raise ValueError("SX dynamic base-width footnote drift")
    for row in manifest["rows"]:
        template = row["template"].upper()
        value = str(row["id"])
        if value == "X":
            pattern = r"\bX\s+\*\s+3\s*MM\s+\(BASE HEIGHT\)\s+SX\b"
        else:
            pattern = (
                rf"\b{value}\s+{row['baseMm']}\s*MM"
                rf"\s+{row['heightMm']}\s*MM\s+{template}\b"
            )
        if re.search(pattern, text) is None:
            raise ValueError(f"Printed Silhouette table mismatch: {template}")
    return hashlib.sha256(raw).hexdigest()


def audit_source_files(
    manifest_path: Path = MANIFEST,
    curated_path: Path = CURATED,
    renderer_path: Path = RENDERER,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    manifest_data = manifest_path.read_bytes()
    curated_data = curated_path.read_bytes()
    renderer_data = renderer_path.read_bytes()
    manifest = json.loads(manifest_data)
    report = audit_silhouette_table(
        manifest,
        load_curated_document(curated_path),
        renderer_data.decode("utf-8"),
    )
    return {
        **report,
        "manifestSha256": hashlib.sha256(manifest_data).hexdigest(),
        "curatedSha256": hashlib.sha256(curated_data).hexdigest(),
        "rendererSha256": hashlib.sha256(renderer_data).hexdigest(),
        "verifiedPdfSha256": verify_pinned_pdf(pdf_path, manifest) if pdf_path else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--curated", type=Path, default=CURATED)
    parser.add_argument("--renderer", type=Path, default=RENDERER)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_source_files(args.manifest, args.curated, args.renderer, args.pdf)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Silhouette source rows: {report['rowCount']}")
        print(f"Browser S1-S8 diagrams: {report['browserDiagramCount']}")
        print("S0: 25 mm base / 3 mm high; SX: dynamic base / 3 mm high (Prone)")
        print("No new deployed-object identities or static Unit/Profile attributes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
