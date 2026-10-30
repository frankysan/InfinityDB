"""Audit the four N5.3 p. 58 Hacking Device-to-Program chart rows.

This is an access matrix, not the separate Hacking Programs statistics chart,
or evidence of a Unit carrier, deployed object, or additional Program.
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
MANIFEST = ROOT / "config/validation/hacking-device-program-source-chart.json"
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
PROGRAMS = ROOT / "data/curated/rules/n5-hacking-programs-v5.3.json"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"

# Ordered exactly as the printed four-row English N5.3 device chart.
PINNED = (
    ("equipment:hacking-device", "Hacking Device",
     ("carbonite", "spotlight", "total-control", "oblivion")),
    ("equipment:hacking-device-plus", "Hacking Device Plus",
     ("carbonite", "spotlight", "total-control", "oblivion",
      "white-noise", "cybermask")),
    ("equipment:killer-hacking-device", "Killer Hacking Device",
     ("trinity", "cybermask")),
    ("equipment:evo-hacking-device", "EVO Hacking Device",
     ("assisted-fire", "enhanced-reaction", "fairy-dust", "controlled-jump")),
)
CLASSIFICATION = {
    "domain": "hacking-device-program-access",
    "scope": "equipment-granted-program-sets-not-individual-program-statistics",
    "relationship": "device-to-program-entitlement-not-army-carrier-or-target",
    "order": "printed-chart-column-order",
    "authority": "source-chart-versus-maintained-device-definitions",
}
_LINKS = re.compile(r"\[\[hacking-program:([a-z0-9-]+)(?:\|[^\]]*)?\]\]")


def audit_device_program_chart(
    manifest: dict[str, Any],
    curated: dict[str, Any],
    programs: dict[str, Any],
) -> dict[str, Any]:
    """Compare chart rows to authored Equipment and Program definitions."""
    if set(manifest) != {
        "formatVersion", "sourceId", "sourcePage", "reviewStatus",
        "classification", "deviceRows",
    }:
        raise ValueError("Unexpected device/program source chart schema")
    if (
        type(manifest["formatVersion"]) is not int
        or manifest["formatVersion"] != 1
        or manifest["sourceId"] != "n5-core-v5.3-pdf"
        or manifest["sourcePage"] != 58
        or manifest["reviewStatus"] != "source-reviewed-audit-only"
        or manifest["classification"] != CLASSIFICATION
    ):
        raise ValueError("Device chart source/scope drift")
    rows = manifest["deviceRows"]
    if not isinstance(rows, list) or len(rows) != 4:
        raise ValueError("Expected exactly four device/program rows")
    records = {item["id"]: item for item in curated["records"]}
    program_records = {item["id"]: item for item in programs["records"]}
    if len(records) != len(curated["records"]) or len(program_records) != len(
        programs["records"]
    ):
        raise ValueError("Duplicate maintained Equipment or Program record")
    missing_direct_citations: list[str] = []
    for index, (row, (device_id, name, slug_set)) in enumerate(
        zip(rows, PINNED, strict=True),
    ):
        expected = [f"hacking-program:{slug}" for slug in slug_set]
        if (
            not isinstance(row, dict)
            or set(row) != {"deviceId", "name", "programIds"}
            or row != {"deviceId": device_id, "name": name, "programIds": expected}
        ):
            raise ValueError(f"N5.3 device/program chart row drift: {index}")
        device = records.get(device_id)
        if (
            device is None
            or device.get("kind") != "equipment"
            or device.get("name") != name
            or device.get("composition", {}).get("role") != "definition"
        ):
            raise ValueError(f"Maintained hacking device missing: {device_id}")
        direct = [
            citation for citation in device.get("citations", [])
            if citation.get("sourceId") == "n5-core-v5.3-pdf"
        ]
        if direct and direct != [{"sourceId": "n5-core-v5.3-pdf", "page": 58}]:
            raise ValueError(f"Unreviewed N5.3 Hacking Device citation: {device_id}")
        if not direct:
            missing_direct_citations.append(device_id)
        effects = device.get("facts", {}).get("effects")
        if not isinstance(effects, list) or len(effects) != 1 or not isinstance(
            effects[0], str
        ):
            raise ValueError(f"Unsupported device program facts: {device_id}")
        refs = _LINKS.findall(effects[0])
        if len(refs) != len(set(refs)) or set(refs) != set(slug_set):
            raise ValueError(f"Maintained device Program access drift: {device_id}")
        for program_id in expected:
            program = program_records.get(program_id)
            if (
                program is None
                or program.get("kind") != "hacking-program"
                or program.get("composition", {}).get("role") != "definition"
            ):
                raise ValueError(f"Missing canonical Program: {program_id}")
    if len(missing_direct_citations) not in (0, 4):
        raise ValueError("Partial Hacking Device N5.3 citation migration")
    return {
        "scope": CLASSIFICATION["scope"],
        "sourcePage": 58,
        "deviceCount": len(rows),
        "distinctProgramCount": len({
            program_id for row in rows for program_id in row["programIds"]
        }),
        "programStatisticsIncluded": False,
        "missingMaintainedN53ChartCitations": missing_direct_citations,
        "deviceRows": rows,
    }


def verify_pinned_pdf(path: Path, manifest: dict[str, Any]) -> str:
    """Check bounded printed chart wording separately from the statistics chart."""
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("PDF verification requires PyMuPDF") from exc
    raw = path.read_bytes()
    with pymupdf.open(stream=raw, filetype="pdf") as source:
        if len(source) < 58:
            raise ValueError("Pinned English N5.3 PDF lacks p. 58")
        extracted = source[57].get_text("text", sort=False)
        if not isinstance(extracted, str):
            raise ValueError("Missing Hacking Device Program chart PDF text")
    text = " ".join(extracted.upper().split())
    marker = "HACKER DEVICE PROGRAMS CHART"
    if marker not in text or "HACKING PROGRAMS CHART" not in text:
        raise ValueError("N5.3 p. 58 device/statistics chart boundary drift")
    device_table = text.split(marker, 1)[1]
    # Expected visible device-to-program groups in extracted PDF order.
    for expression in (
        r"HACKING DEVICE\s+CARBONITE\s+SPOTLIGHT\s+TOTAL CONTROL\s+OBLIVION",
        (
            r"HACKING DEVICE PLUS\s+CARBONITE\s+SPOTLIGHT\s+TOTAL CONTROL"
            r"\s+OBLIVION\s+WHITE NOISE\s+CYBERMASK"
        ),
        r"KILLER HACKING DEVICE\s+TRINITY\s+CYBERMASK",
        (
            r"EVO HACKING DEVICE\s+ASSISTED FIRE\s+ENHANCED REACTION"
            r"\s+FAIRY DUST\s+CONTROLLED JUMP"
        ),
    ):
        if re.search(expression, device_table) is None:
            raise ValueError(f"Printed device-to-program chart mismatch: {expression}")
    if len(manifest["deviceRows"]) != len(PINNED):
        raise ValueError("Source chart row count drift")
    return hashlib.sha256(raw).hexdigest()


def audit_source_files(
    manifest_path: Path = MANIFEST,
    curated_path: Path = CURATED,
    programs_path: Path = PROGRAMS,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    raw = manifest_path.read_bytes()
    curated_raw = curated_path.read_bytes()
    program_raw = programs_path.read_bytes()
    manifest = json.loads(raw)
    report = audit_device_program_chart(
        manifest,
        load_curated_document(curated_path),
        load_curated_document(programs_path),
    )
    return {
        **report,
        "manifestSha256": hashlib.sha256(raw).hexdigest(),
        "curatedSha256": hashlib.sha256(curated_raw).hexdigest(),
        "programsSha256": hashlib.sha256(program_raw).hexdigest(),
        "verifiedPdfSha256": verify_pinned_pdf(pdf_path, manifest) if pdf_path else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--curated", type=Path, default=CURATED)
    parser.add_argument("--programs", type=Path, default=PROGRAMS)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_source_files(
        args.manifest, args.curated, args.programs, args.pdf,
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            f"Hacking Device chart: {report['deviceCount']} devices; "
            f"{report['distinctProgramCount']} distinct Programs"
        )
        for row in report["deviceRows"]:
            print(f"  {row['name']}: {len(row['programIds'])} Programs")
        print("Scope: device access only; no Program statistics or Unit carriers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
