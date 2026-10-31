"""Stage a coordinated N5.3 citation migration without changing the checkout.

Requires a clean pending-only preflight. Builds staged curated JSON, three
review manifests, rules.db and its dependent deployed-object publication.
The user can review all generated files before replacing tracked artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import export_rules_database
from tools.audit_deployed_object_citation_migrations import (
    CURATED,
    MANIFEST_PATHS,
    ROOT,
    audit_citations,
    build_citation_migration_plan,
)
from tools.build_deployed_object_publication import build_publication, publication_bytes

RULES_DIR = CURATED.parent
ARMY_DB = ROOT / "data/generated/infinity.db"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"
CANDIDATES = ROOT / "config/validation/deployed-object-candidate-reviews.json"
SOURCE_PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"


def canonical_json(data: dict[str, Any], *, indent: int) -> str:
    return json.dumps(data, ensure_ascii=False, indent=indent) + "\n"


def prepare_migrated_inputs(
    curated: dict[str, Any],
    manifests: dict[str, dict[str, Any]],
    plan: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Append only verified citations; remove only audit-only metadata."""
    if plan["pendingCount"] != 14 or plan["migratedCount"] != 0:
        raise ValueError("Migration requires all 14 citations to be pending")
    indexed = {record["id"]: record for record in curated["records"]}
    if len(indexed) != len(curated["records"]):
        raise ValueError("Duplicate curated rule ID")
    for entry in plan["pending"]:
        record = indexed[entry["recordId"]]
        citation = entry["proposedCitation"]
        if any(item.get("sourceId") == citation["sourceId"] for item in record["citations"]):
            raise ValueError(f"Source already cites N5.3: {entry['recordId']}")
        record["citations"].append(dict(citation))
        matched = [
            review for review in manifests[entry["reviewManifest"]]["reviews"]
            if review["recordId"] == entry["recordId"]
        ]
        if len(matched) != 1:
            raise ValueError(f"Ambiguous review: {entry['recordId']}")
        review = matched[0]
        if review.pop("citationStatus") != "pdf-verified-manifest-only":
            raise ValueError(f"Unexpected review state: {entry['recordId']}")
        if review.pop("pdfExcerpt") != entry["pdfExcerpt"]:
            raise ValueError(f"Stale PDF excerpt: {entry['recordId']}")
    migrated = build_citation_migration_plan(curated, manifests)
    if migrated["pendingCount"] != 0 or migrated["migratedCount"] != 14:
        raise ValueError("Staged migration did not reconcile all 14 citations")
    return curated, manifests


def insert_citations_without_reformatting(
    original: str, pending: list[dict[str, Any]], expected: dict[str, Any],
) -> str:
    """Insert citations into exact record blocks while preserving all other bytes."""
    text = original
    for entry in pending:
        record_id = entry["recordId"]
        marker = f'            "id": "{record_id}",'
        if text.count(marker) != 1:
            raise ValueError(f"Ambiguous curated record anchor: {record_id}")
        start = text.index(marker)
        following = text.find('\n        {\n            "id": ', start + len(marker))
        end = following if following >= 0 else len(text)
        record_segment = text[start:end]
        pattern = re.compile(
            r'(?P<header>^            "citations": \[\n)'
            r'(?P<body>.*?)'
            r'(?P<footer>^            \])',
            re.MULTILINE | re.DOTALL,
        )
        matches = list(pattern.finditer(record_segment))
        if len(matches) != 1:
            raise ValueError(f"Missing/ambiguous citation array: {record_id}")
        match = matches[0]
        body = match.group("body").rstrip("\n")
        if not body.endswith("                }"):
            raise ValueError(f"Unexpected citation item formatting: {record_id}")
        citation = entry["proposedCitation"]
        added = (
            ',\n                {\n'
            f'                    "sourceId": "{citation["sourceId"]}",\n'
            f'                    "page": {citation["page"]}\n'
            '                }\n'
        )
        replacement = match.group("header") + body + added + match.group("footer")
        record_segment = (
            record_segment[:match.start()] + replacement + record_segment[match.end():]
        )
        text = text[:start] + record_segment + text[end:]
    if json.loads(text) != expected:
        raise ValueError("Staged citation-only text does not match reviewed changes")
    return text


def remove_review_metadata_without_reformatting(
    original: str, pending: list[dict[str, Any]], expected: dict[str, Any],
) -> str:
    """Remove only the two temporary PDF-only fields for reviewed records."""
    text = original
    for entry in pending:
        record_id = entry["recordId"]
        marker = f'      "recordId": "{record_id}",'
        if text.count(marker) != 1:
            raise ValueError(f"Ambiguous review anchor: {record_id}")
        start = text.index(marker)
        following = text.find('\n    {\n      "recordId": ', start + len(marker))
        end = following if following >= 0 else len(text)
        snippet = text[start:end]
        for pattern in (
            r'^      "citationStatus": "pdf-verified-manifest-only",\n',
            r'^      "pdfExcerpt": "[^\n]*",\n',
        ):
            snippet, count = re.subn(pattern, "", snippet, count=1, flags=re.MULTILINE)
            if count != 1:
                raise ValueError(f"Missing PDF-only review metadata: {record_id}")
        text = text[:start] + snippet + text[end:]
    if json.loads(text) != expected:
        raise ValueError("Staged review metadata does not match reviewed changes")
    return text


def stage_citation_migration(
    output_dir: Path,
    *,
    pdf: Path | None = None,
    army_db: Path = ARMY_DB,
    curated_path: Path = CURATED,
    manifest_paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Build into an exclusive new directory; never overwrite tracked inputs."""
    paths = MANIFEST_PATHS if manifest_paths is None else manifest_paths
    report = audit_citations(curated_path, paths, pdf)
    if report["pendingCount"] != 14 or report["migratedCount"] != 0:
        raise ValueError("Expected exactly 14 pending citations")
    source_doc = json.loads(curated_path.read_text(encoding="utf-8"))
    source_manifests = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in paths.items()
    }
    if not army_db.is_file():
        raise ValueError(f"Missing matching Army database: {army_db}")
    output = output_dir.resolve()
    inputs = [curated_path, army_db, DELIVERY, CANDIDATES, *paths.values()]
    if (
        any(output == path.resolve() or path.resolve().is_relative_to(output) for path in inputs)
        or any(
            output.is_relative_to(path.resolve())
            for path in (curated_path.parent, army_db.parent, *[p.parent for p in paths.values()])
        )
    ):
        raise ValueError("Staging directory may not overlap source or generated inputs")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {output}")

    modified_doc, modified_manifests = prepare_migrated_inputs(
        source_doc, source_manifests, report,
    )
    output.mkdir(parents=True, exist_ok=False)
    staged_rules = output / "data/curated/rules"
    shutil.copytree(curated_path.parent, staged_rules)
    staged_curated = staged_rules / curated_path.name
    staged_curated.write_text(
        insert_citations_without_reformatting(
            curated_path.read_text(encoding="utf-8"), report["pending"], modified_doc,
        ),
        encoding="utf-8", newline="\n",
    )
    for name, path in paths.items():
        target = output / "config/validation" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            remove_review_metadata_without_reformatting(
                path.read_text(encoding="utf-8"),
                [entry for entry in report["pending"] if entry["reviewManifest"] == name],
                modified_manifests[name],
            ),
            encoding="utf-8", newline="\n",
        )

    generated = output / "data/generated"
    generated.mkdir(parents=True, exist_ok=True)
    rules_db = generated / "rules.db"
    export_rules_database(load_curated_directory(staged_rules), rules_db)
    published = build_publication(
        army_db, rules_db, staged_curated, DELIVERY, CANDIDATES,
    )
    if len(published["objects"]) != 17:
        raise ValueError("Staged publication changed reviewed object count")
    publication = generated / "deployed-objects.json"
    expected = publication_bytes(published)
    publication.write_bytes(expected)
    if publication.read_bytes() != expected:
        raise ValueError("Staged publication bytes differ after write")
    checksums = {
        "rulesDatabase": hashlib.sha256(rules_db.read_bytes()).hexdigest(),
        "deployedObjects": hashlib.sha256(expected).hexdigest(),
    }
    if published["sourceSnapshot"]["rulesDatabaseSha256"] != checksums["rulesDatabase"]:
        raise ValueError("Staged publication fingerprint does not match rules database")
    staging_report = {
        "scope": "staged-artifacts-only-not-applied-or-committed",
        "migratedCount": 14,
        "countsByManifest": report["countsByManifest"],
        "sourceHashes": report["reviewManifestSha256"],
        "curatedSourceSha256": report["curatedSourceSha256"],
        "verifiedPdfSha256": report["verifiedPdfSha256"],
        "stagedSha256": checksums,
        "reviewedObjects": len(published["objects"]),
        "stagedPaths": [
            f"data/curated/rules/{curated_path.name}",
            *(f"config/validation/{p.name}" for p in paths.values()),
            "data/generated/rules.db",
            "data/generated/deployed-objects.json",
        ],
    }
    (output / "migration-report.json").write_text(
        canonical_json(staging_report, indent=2), encoding="utf-8", newline="\n",
    )
    return staging_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, help="Optional exact excerpt validation")
    args = parser.parse_args()
    report = stage_citation_migration(args.output_dir, pdf=args.pdf)
    print(f"Staged {report['migratedCount']} citations and both generated artifacts.")
    print(f"Staging report: {args.output_dir / 'migration-report.json'}")
    print("Original working-tree source and generated artifacts were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
