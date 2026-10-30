"""Stage N5.3 Special Terrain and Access Width references with matching binaries.

Never modify source files or published artifacts in the active checkout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.rules_database import export_rules_database
from tools.audit_terrain_scenery_source_gaps import (
    CURATED,
    PUBLICATION,
    audit_terrain_scenery_boundary,
    verify_pinned_pdf,
)
from tools.build_deployed_object_publication import build_publication, publication_bytes

ROOT = CURATED.parents[3]
ADDITIONS = ROOT / "config/validation/terrain-scenery-reference-additions.json"
ARMY = ROOT / "data/generated/infinity.db"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"
CANDIDATES = ROOT / "config/validation/deployed-object-candidate-reviews.json"
EXPECTED_IDS = ("rule:special-terrain", "rule:access-width")
EXPECTED_PAGES = (143, 145)


def verify_additions(doc: dict[str, Any]) -> list[dict[str, Any]]:
    if (
        doc.get("formatVersion") != 1
        or doc.get("sourceId") != "n5-core-v5.3-pdf"
        or not isinstance(doc.get("records"), list)
        or tuple(item.get("id") for item in doc["records"]) != EXPECTED_IDS
    ):
        raise ValueError("Unexpected terrain/scenery reference proposal")
    for record, page in zip(doc["records"], EXPECTED_PAGES, strict=True):
        if (
            record.get("kind") != "rule"
            or record.get("composition") != {"role": "definition"}
            or record.get("scope") != {"game": "N5", "seasons": ["current"]}
            or record.get("facts", {}).get("category") != "basic-rule"
            or record.get("facts", {}).get("definesSkills") != []
            or record.get("relations") != []
            or [citation.get("page") for citation in record.get("citations", [])] != [page]
            or any(
                citation.get("sourceId") != "n5-core-v5.3-pdf"
                for citation in record["citations"]
            )
        ):
            raise ValueError(f"Unreviewed source definition shape: {record.get('id')}")
    return doc["records"]


def insert_reference_records(
    original: str, proposed: list[dict[str, Any]],
) -> str:
    """Insert only new records, leaving all preceding and following source text intact."""
    doc = json.loads(original)
    existing = {row["id"] for row in doc["records"]}
    if existing.intersection(EXPECTED_IDS):
        raise ValueError("Terrain/scenery references already exist; refusing duplicate insert")
    anchor = '        }\n    ],\n    "scenarioComponents": {'
    if original.count(anchor) != 1:
        raise ValueError("Unique curated records boundary not found")
    inserted = ",\n".join(
        "\n".join("        " + line for line in json.dumps(
            record, ensure_ascii=False, indent=4,
        ).splitlines())
        for record in proposed
    )
    new_source = original.replace(
        anchor,
        '        },\n' + inserted + '\n    ],\n    "scenarioComponents": {',
        1,
    )
    parsed = json.loads(new_source)
    if parsed["records"] != [*doc["records"], *proposed]:
        raise ValueError("Staged source changed beyond intended records")
    for key in doc:
        if key != "records" and parsed[key] != doc[key]:
            raise ValueError("Staged source changed unrelated data")
    return new_source


def stage_terrain_references(
    output_dir: Path,
    *,
    additions_path: Path = ADDITIONS,
    curated_path: Path = CURATED,
    publication_path: Path = PUBLICATION,
    army_path: Path = ARMY,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    """Create exclusive staging output; check existing publication and source first."""
    output = output_dir.resolve()
    inputs = (curated_path, additions_path, publication_path, army_path, DELIVERY, CANDIDATES)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {output}")
    if any(
        output == path.resolve()
        or path.resolve().is_relative_to(output)
        or output.is_relative_to(path.resolve().parent)
        for path in inputs
    ):
        raise ValueError("Staging must not overlap source or generated inputs")
    added = verify_additions(json.loads(additions_path.read_text(encoding="utf-8")))
    original = curated_path.read_text(encoding="utf-8")
    audit_terrain_scenery_boundary(
        load_curated_document(curated_path),
        json.loads(publication_path.read_text(encoding="utf-8")),
    )
    if not army_path.is_file():
        raise ValueError("Matching Army database unavailable")
    pdf_digest = verify_pinned_pdf(pdf_path) if pdf_path is not None else None
    altered = insert_reference_records(original, added)

    output.mkdir(parents=True, exist_ok=False)
    rules_dir = output / "data/curated/rules"
    shutil.copytree(curated_path.parent, rules_dir)
    modified = rules_dir / curated_path.name
    modified.write_text(altered, encoding="utf-8", newline="\n")
    loaded = load_curated_document(modified)
    for record in added:
        if not any(item["id"] == record["id"] for item in loaded["records"]):
            raise ValueError("Missing staged rule")
    generated = output / "data/generated"
    generated.mkdir(parents=True, exist_ok=True)
    rules_db = generated / "rules.db"
    export_rules_database(load_curated_directory(rules_dir), rules_db)
    pub = build_publication(
        army_path, rules_db, modified, DELIVERY, CANDIDATES,
    )
    if len(pub["objects"]) != 17:
        raise ValueError("Staging changed reviewed object identities")
    built = publication_bytes(pub)
    publication = generated / "deployed-objects.json"
    publication.write_bytes(built)
    if pub["sourceSnapshot"]["rulesDatabaseSha256"] != hashlib.sha256(
        rules_db.read_bytes()
    ).hexdigest():
        raise ValueError("Staging publication fingerprint mismatch")
    report = {
        "scope": "staged-only-no-checkout-modification",
        "proposedIds": list(EXPECTED_IDS),
        "verifiedPdfSha256": pdf_digest,
        "sourceSha256": hashlib.sha256(curated_path.read_bytes()).hexdigest(),
        "reviewedObjects": len(pub["objects"]),
        "stagedSha256": {
            "curated": hashlib.sha256(modified.read_bytes()).hexdigest(),
            "rulesDatabase": hashlib.sha256(rules_db.read_bytes()).hexdigest(),
            "deployedObjects": hashlib.sha256(built).hexdigest(),
        },
        "stagedPaths": [
            f"data/curated/rules/{curated_path.name}",
            "data/generated/rules.db",
            "data/generated/deployed-objects.json",
        ],
    }
    (output / "staging-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, help="Check pinned source pages before staging")
    args = parser.parse_args()
    report = stage_terrain_references(args.output_dir, pdf_path=args.pdf)
    print(f"Staged {len(report['proposedIds'])} source-backed rule definitions.")
    print(f"Reviewed deployed objects unchanged: {report['reviewedObjects']}")
    print(f"Staging report: {args.output_dir / 'staging-report.json'}")
    print("Tracked files and databases were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
