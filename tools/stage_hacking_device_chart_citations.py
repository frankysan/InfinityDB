"""Stage and optionally promote four N5.3 Hacking Device chart citations.

Staging is exclusive and never changes tracked files. Opt-in promotion verifies
all staged artifacts, retains recovery backups and rolls back failed validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
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


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    """Replace one file using a same-directory temporary file."""
    fd, name = tempfile.mkstemp(prefix=".n53-citation-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _replace_staged_batch(
    root: Path, payloads: dict[str, bytes], validate: Any,
) -> Path:
    """Replace all three files with verified rollback copies and post-checks.

    A filesystem cannot atomically replace three independent files. Backups are
    retained under ignored local/ for recovery from an interrupted process.
    """
    targets = {relative: root / relative for relative in STAGED_PATHS}
    originals = {relative: path.read_bytes() for relative, path in targets.items()}
    backup = Path(tempfile.mkdtemp(prefix="hacking-device-citation-backup-", dir=root / "local"))
    for relative, raw in originals.items():
        destination = backup / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        if destination.read_bytes() != raw:
            raise ValueError(f"Backup verification failed: {relative}")
    try:
        if any(path.read_bytes() != originals[relative] for relative, path in targets.items()):
            raise ValueError("Promotion target changed while backing up")
        for relative, path in targets.items():
            _atomic_write(path, payloads[relative])
        if any(_sha256(path) != hashlib.sha256(payloads[relative]).hexdigest()
               for relative, path in targets.items()):
            raise ValueError("Promoted artifact hash mismatch")
        validate()
    except Exception as error:
        failures = []
        for relative, path in targets.items():
            try:
                _atomic_write(path, originals[relative])
                if path.read_bytes() != originals[relative]:
                    raise ValueError("Restored bytes differ")
            except Exception as rollback_error:
                failures.append(f"{relative}: {rollback_error}")
        if failures:
            raise RuntimeError(
                f"Rollback incomplete; recover from {backup}: {'; '.join(failures)}"
            ) from error
        raise RuntimeError(
            f"Promotion rolled back; original artifacts restored; backup: {backup}"
        ) from error
    return backup


def promote_hacking_device_chart_citations(
    output_dir: Path, *, root: Path = ROOT,
) -> Path:
    """Guard and promote one staged citation bundle with recovery copies."""
    from tools.audit_hacking_device_program_source_chart import audit_source_files

    root = root.resolve()
    stage = (root / output_dir).resolve()
    if not stage.is_relative_to(root / "local") or stage.is_symlink():
        raise ValueError("Staged artifacts must be under the repository local/ directory")
    report = json.loads((stage / "staging-report.json").read_text(encoding="utf-8"))
    if (
        report.get("scope") != "staged-only-hacking-device-p58-citations-not-applied"
        or report.get("sourceId") != SOURCE_CITATION["sourceId"]
        or report.get("sourcePage") != 58
        or report.get("migratedDeviceIds") != [row[0] for row in PINNED]
        or report.get("stagedPaths") != list(STAGED_PATHS)
        or report.get("reviewedObjects") != 17
    ):
        raise ValueError("Unexpected staged N5.3 citation migration report")
    target_paths = [root / relative for relative in STAGED_PATHS]
    if any(not path.is_file() or path.is_symlink() for path in target_paths):
        raise ValueError("Missing or symlinked tracked promotion target")
    git = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *STAGED_PATHS],
        cwd=root, check=False, capture_output=True,
    )
    if git.returncode != 0:
        raise ValueError("Tracked promotion targets differ from HEAD or git check failed")
    if (
        _sha256(target_paths[0]) != report["sourceSha256"]
        or _sha256(root / "data/generated/infinity.db") != report["armySha256"]
    ):
        raise ValueError("Curated or Army source changed after staging")
    pdf = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if not pdf.is_file() or _sha256(pdf) != report["verifiedPdfSha256"]:
        raise ValueError("Verified N5.3 PDF fingerprint changed")
    keys = ("curated", "rulesDatabase", "deployedObjects")
    expected = dict(zip(STAGED_PATHS, (report["stagedSha256"][key] for key in keys),
                        strict=True))
    payloads = {}
    for relative, sha256 in expected.items():
        staged = stage / relative
        if not staged.is_file() or staged.is_symlink() or _sha256(staged) != sha256:
            raise ValueError(f"Missing or changed staged artifact: {relative}")
        payloads[relative] = staged.read_bytes()

    before = json.loads(target_paths[2].read_text(encoding="utf-8"))
    staged_publication = json.loads(payloads[STAGED_PATHS[2]])
    if (
        len(before["objects"]) != 17
        or staged_publication["objects"] != before["objects"]
        or before["sourceSnapshot"]["rulesDatabaseSha256"] != _sha256(target_paths[1])
        or staged_publication["sourceSnapshot"]["rulesDatabaseSha256"] != expected[STAGED_PATHS[1]]
    ):
        raise ValueError("Staged publication changes reviewed objects or mismatches database")
    if publication_bytes(build_publication(
        root / "data/generated/infinity.db",
        stage / STAGED_PATHS[1], stage / STAGED_PATHS[0],
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )) != payloads[STAGED_PATHS[2]]:
        raise ValueError("Staged publication is not reproducible")
    source_audit = audit_source_files(
        curated_path=stage / STAGED_PATHS[0],
        manifest_path=root / "config/validation/hacking-device-program-source-chart.json",
        programs_path=root / "data/curated/rules/n5-hacking-programs-v5.3.json",
    )
    if source_audit["missingMaintainedN53ChartCitations"]:
        raise ValueError("Staged Hacking Device citations remain incomplete")

    def post_validate() -> None:
        if any(_sha256(root / relative) != digest for relative, digest in expected.items()):
            raise ValueError("Promoted artifact hashes differ from staging report")
        current = audit_source_files(
            curated_path=root / STAGED_PATHS[0],
            manifest_path=root / "config/validation/hacking-device-program-source-chart.json",
            programs_path=root / "data/curated/rules/n5-hacking-programs-v5.3.json",
        )
        if current["missingMaintainedN53ChartCitations"]:
            raise ValueError("Promoted source citations remain incomplete")
        if publication_bytes(build_publication(
            root / "data/generated/infinity.db",
            root / STAGED_PATHS[1], root / STAGED_PATHS[0],
            root / "config/validation/deployed-object-delivery-reviews.json",
            root / "config/validation/deployed-object-candidate-reviews.json",
        )) != (root / STAGED_PATHS[2]).read_bytes():
            raise ValueError("Promoted deployed-object publication is stale")
        promoted_objects = json.loads(
            (root / STAGED_PATHS[2]).read_text(encoding="utf-8")
        )["objects"]
        if promoted_objects != before["objects"]:
            raise ValueError("Reviewed deployed object or delivery paths changed")

    return _replace_staged_batch(root, payloads, post_validate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    if args.promote_staged:
        if args.pdf is not None:
            parser.error("--pdf is only accepted when staging")
        backup = promote_hacking_device_chart_citations(args.output_dir)
        print("Promoted three N5.3 citation artifacts with matching SHA-256 hashes.")
        print(f"Recovery backup retained: {backup}")
        return 0
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
