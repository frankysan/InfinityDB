"""Stage four source-backed N5.3 Hacking Device chart citations and binaries.

The staging operation is exclusive and never changes tracked curated source,
rules.db or the deployed-object publication in the active checkout.
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
from tools.audit_hacking_device_program_source_chart import (
    CURATED,
    MANIFEST,
    PINNED,
    PROGRAMS,
    audit_device_program_chart,
    verify_pinned_pdf,
)
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.stage_deployed_object_citation_migration import (
    insert_citations_without_reformatting,
)

ROOT = CURATED.parents[3]
ARMY = ROOT / "data/generated/infinity.db"
PUBLICATION = ROOT / "data/generated/deployed-objects.json"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"
CANDIDATES = ROOT / "config/validation/deployed-object-candidate-reviews.json"
SOURCE_CITATION = {"sourceId": "n5-core-v5.3-pdf", "page": 58}
STAGED_PATHS = (
    "data/curated/rules/n5-core-v5.3.json",
    "data/generated/rules.db",
    "data/generated/deployed-objects.json",
)


def prepare_chart_citations(
    original: dict[str, Any],
    chart: dict[str, Any],
    programs: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Produce exactly four new source citations; reject partial migration."""
    if audit_device_program_chart(chart, original, programs)[
        "missingMaintainedN53ChartCitations"
    ] != [row[0] for row in PINNED]:
        raise ValueError("Citation staging requires all four device citations pending")
    records = {record["id"]: record for record in original["records"]}
    updated = json.loads(json.dumps(original))
    updated_records = {record["id"]: record for record in updated["records"]}
    additions: list[dict[str, Any]] = []
    for record_id, _, _ in PINNED:
        record = records[record_id]
        if not record["citations"] or any(
            cite.get("sourceId") == SOURCE_CITATION["sourceId"]
            for cite in record["citations"]
        ):
            raise ValueError(f"Unexpected existing N5.3 citation: {record_id}")
        updated_records[record_id]["citations"].append(dict(SOURCE_CITATION))
        additions.append({
            "recordId": record_id,
            "proposedCitation": dict(SOURCE_CITATION),
        })
    if audit_device_program_chart(chart, updated, programs)[
        "missingMaintainedN53ChartCitations"
    ]:
        raise ValueError("Citation proposal failed full source reconciliation")
    return updated, additions


def stage_hacking_device_chart_citations(
    output_dir: Path,
    *,
    curated_path: Path = CURATED,
    programs_path: Path = PROGRAMS,
    manifest_path: Path = MANIFEST,
    army_path: Path = ARMY,
    publication_path: Path = PUBLICATION,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    """Create an exclusive staging directory containing three aligned artifacts."""
    output = output_dir.resolve()
    inputs = (
        curated_path, programs_path, manifest_path, army_path,
        publication_path, DELIVERY, CANDIDATES,
        ROOT / "data/generated/rules.db",
    )
    if any(
        output == path.resolve()
        or path.resolve().is_relative_to(output)
        or output.is_relative_to(path.resolve().parent)
        for path in inputs
    ):
        raise ValueError("Staging directory overlaps tracked inputs")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {output}")
    if not army_path.is_file() or not publication_path.is_file():
        raise ValueError("Matching Army database and deployed publication required")
    curated_text = curated_path.read_text(encoding="utf-8")
    original = load_curated_document(curated_path)
    programs = load_curated_document(programs_path)
    chart = json.loads(manifest_path.read_text(encoding="utf-8"))
    updated, entries = prepare_chart_citations(original, chart, programs)
    staged_text = insert_citations_without_reformatting(
        curated_text, entries, updated,
    )
    pdf_sha256 = verify_pinned_pdf(pdf_path, chart) if pdf_path else None

    output.mkdir(parents=True, exist_ok=False)
    rules_dir = output / "data/curated/rules"
    shutil.copytree(curated_path.parent, rules_dir)
    staged_source = rules_dir / curated_path.name
    staged_source.write_text(staged_text, encoding="utf-8", newline="\n")
    # Re-parse the staged data rather than trusting the in-memory proposal.
    if load_curated_document(staged_source) != updated:
        raise ValueError("Staged rules differ from the reviewed four-citation proposal")
    generated = output / "data/generated"
    generated.mkdir(parents=True, exist_ok=True)
    staged_rules_db = generated / "rules.db"
    export_rules_database(load_curated_directory(rules_dir), staged_rules_db)
    published = build_publication(
        army_path, staged_rules_db, staged_source, DELIVERY, CANDIDATES,
    )
    current_published = json.loads(publication_path.read_text(encoding="utf-8"))
    if (
        len(published["objects"]) != 17
        or published["objects"] != current_published["objects"]
    ):
        raise ValueError("Hacking Device citation migration changed deployed objects")
    body = publication_bytes(published)
    staged_publication = generated / "deployed-objects.json"
    staged_publication.write_bytes(body)
    rules_hash = hashlib.sha256(staged_rules_db.read_bytes()).hexdigest()
    if published["sourceSnapshot"]["rulesDatabaseSha256"] != rules_hash:
        raise ValueError("Staged deployment rules fingerprint mismatch")

    report = {
        "scope": "staged-only-hacking-device-p58-citations-not-applied",
        "sourceId": SOURCE_CITATION["sourceId"],
        "sourcePage": SOURCE_CITATION["page"],
        "migratedDeviceIds": [entry["recordId"] for entry in entries],
        "sourceSha256": hashlib.sha256(curated_path.read_bytes()).hexdigest(),
        "armySha256": hashlib.sha256(army_path.read_bytes()).hexdigest(),
        "verifiedPdfSha256": pdf_sha256,
        "reviewedObjects": len(published["objects"]),
        "stagedPaths": list(STAGED_PATHS),
        "stagedSha256": {
            "curated": hashlib.sha256(staged_source.read_bytes()).hexdigest(),
            "rulesDatabase": rules_hash,
            "deployedObjects": hashlib.sha256(body).hexdigest(),
        },
    }
    (output / "staging-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, default=None)
    args = parser.parse_args()
    report = stage_hacking_device_chart_citations(
        args.output_dir, pdf_path=args.pdf,
    )
    print(f"Staged {len(report['migratedDeviceIds'])} N5.3 p. 58 device citations.")
    print(f"Deployed object identities unchanged: {report['reviewedObjects']}")
    print(f"Staging report: {args.output_dir / 'staging-report.json'}")
    print("No tracked files were modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
