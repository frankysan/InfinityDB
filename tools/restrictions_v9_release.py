"""Stage, verify and optionally promote the paired N5.3 Restrictions v9 artifacts.

Staging never edits tracked files. Promotion validates exact source and
staging fingerprints, preserves v8 recovery artifacts and rolls back failed
post-publication checks. It does not commit, deploy or change legacy relations.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import RulesDatabase, export_rules_database
from tools.audit_restrictions_source_chart import verify_pinned_pdf
from tools.build_deployed_object_publication import build_publication, publication_bytes

ROOT = Path(__file__).resolve().parents[1]
GENERATED = Path("data/generated")
RULES = GENERATED / "rules.db"
PUBLICATION = GENERATED / "deployed-objects.json"
ARMY = GENERATED / "infinity.db"
CHART = Path("config/validation/restrictions-source-chart.json")
CURATED = Path("data/curated/rules/n5-core-v5.3.json")
DELIVERY = Path("config/validation/deployed-object-delivery-reviews.json")
CANDIDATES = Path("config/validation/deployed-object-candidate-reviews.json")
PDF = Path("data/pdf/rules/n5-rules-v5-3-en.pdf")
ARTIFACTS = (RULES, PUBLICATION)
INPUTS = (ARMY, RULES, PUBLICATION, CHART, CURATED, DELIVERY, CANDIDATES, PDF)
STAGING_SCOPE = "restrictions-v9-source-verified-paired-staging"


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _stage_path(root: Path, stage: Path) -> Path:
    root = root.resolve()
    stage = (root / stage).resolve()
    if not stage.is_relative_to(root / "local") or stage == root / "local":
        raise ValueError("Restrictions staging must be beneath ignored local/")
    if stage.is_symlink():
        raise ValueError("Symlinked staging path is not allowed")
    return stage


def _fingerprints(root: Path) -> dict[str, str]:
    if any(not (root / relative).is_file() or (root / relative).is_symlink()
           for relative in INPUTS):
        raise ValueError("Reviewed source, PDF and release-pair inputs are required")
    return {path.as_posix(): _sha(root / path) for path in INPUTS}


def _checked_chart(root: Path) -> dict[str, Any]:
    chart = json.loads((root / CHART).read_text(encoding="utf-8"))
    if verify_pinned_pdf(root / PDF, chart) != chart["sourcePdfSha256"]:
        raise ValueError("Verified N5.3 PDF hash differs from reviewed manifest")
    return chart


def _expected_publication_delta(
    previous: dict[str, Any], proposed: dict[str, Any], rules_sha: str,
) -> None:
    """The v9 migration must change only the pinned rules database hash."""
    expected = json.loads(json.dumps(previous))
    previous_hash = expected["sourceSnapshot"]["rulesDatabaseSha256"]
    if not isinstance(previous_hash, str) or len(previous_hash) != 64:
        raise ValueError("Existing publication lacks rules database fingerprint")
    expected["sourceSnapshot"]["rulesDatabaseSha256"] = rules_sha
    if proposed != expected:
        raise ValueError(
            "Restrictions migration unexpectedly changed reviewed deployed objects or provenance"
        )


def stage_restrictions_v9(output_dir: Path, *, root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    output = _stage_path(root, output_dir)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {output}")
    source = _fingerprints(root)
    old_rules = root / RULES
    old_pub = root / PUBLICATION
    RulesDatabase(old_rules).validate()
    with sqlite3.connect(old_rules) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] != 8:
            raise ValueError("Restrictions staging requires the original v8 release database")
    previous = load_deployed_object_publication(old_pub, root / ARMY, old_rules)
    if previous is None:
        raise ValueError("Matched v8 deployed-object publication required")
    chart = _checked_chart(root)

    output.mkdir(parents=True, exist_ok=False)
    generated = output / GENERATED
    generated.mkdir(parents=True)
    rules = generated / "rules.db"
    docs = load_curated_directory(root / "data/curated/rules")
    export_rules_database(docs, rules, restrictions_manifest=chart)
    database = RulesDatabase(rules)
    database.validate()
    typed = database.restrictions_payload()
    if not typed["available"] or len(typed["items"]) != 14:
        raise ValueError("Staged v9 database lacks the 14 reviewed restrictions")
    from infinity_db.restriction_conditions import compile_restriction_conditions

    current = next(
        document for _, document in docs
        if document["collection"]["id"] == "n5-core-v5.3"
    )
    records = {row["id"]: row for row in current["records"]}
    constraints = compile_restriction_conditions(chart, records)
    if [(item["subject"], item["action"]) for item in typed["items"]] != [
        (row.subject, row.action) for row in constraints
    ]:
        raise ValueError("Staged restrictions changed reviewed source order")
    with sqlite3.connect(old_rules) as old, sqlite3.connect(rules) as new:
        relation_sql = (
            "SELECT collection_id, record_id, position, relation_type, related_record_id "
            "FROM record_relations ORDER BY collection_id, record_id, position"
        )
        if old.execute(relation_sql).fetchall() != new.execute(relation_sql).fetchall():
            raise ValueError("v9 staging modified the legacy relation graph")

    proposed = build_publication(
        root / ARMY, rules, root / CURATED, root / DELIVERY, root / CANDIDATES,
    )
    _expected_publication_delta(previous, proposed, _sha(rules))
    published = generated / "deployed-objects.json"
    published.write_bytes(publication_bytes(proposed))
    if load_deployed_object_publication(published, root / ARMY, rules) != proposed:
        raise ValueError("Staged publication does not bind to the v9 release database")
    report = {
        "scope": STAGING_SCOPE,
        "source": source,
        "staged": {path.as_posix(): _sha(output / path) for path in ARTIFACTS},
        "reviewedPdfSha256": chart["sourcePdfSha256"],
        "reviewedConditions": 14,
        "reviewedObjects": len(proposed["objects"]),
        "targetPaths": [path.as_posix() for path in ARTIFACTS],
    }
    (output / "staging-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        newline="\n",
    )
    return report


def _atomic_write(path: Path, raw: bytes) -> None:
    fd, name = tempfile.mkstemp(prefix=".restrictions-v9-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _replace_with_rollback(
    root: Path, payloads: dict[Path, bytes], post_validate: Any,
) -> Path:
    """Retain both original binaries; recover them on any failed write/check."""
    backup = Path(tempfile.mkdtemp(prefix="restrictions-v8-recovery-", dir=root / "local"))
    originals = {relative: (root / relative).read_bytes() for relative in payloads}
    for relative, data in originals.items():
        saved = backup / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(data)
        if saved.read_bytes() != data:
            raise ValueError(f"v8 recovery copy failed verification: {relative}")
    try:
        if any((root / path).read_bytes() != originals[path] for path in payloads):
            raise ValueError("Release target changed while backing up")
        # Replace the data and publication in one guarded batch; the immutable
        # release image is only built from both matching artifacts afterwards.
        for relative, data in payloads.items():
            _atomic_write(root / relative, data)
        if any((root / path).read_bytes() != data for path, data in payloads.items()):
            raise ValueError("Promoted artifacts differ from reviewed staging bytes")
        post_validate()
    except Exception as failure:
        errors = []
        for relative, data in originals.items():
            try:
                _atomic_write(root / relative, data)
                if (root / relative).read_bytes() != data:
                    raise ValueError("Recovery bytes mismatch")
            except Exception as rollback_failure:
                errors.append(f"{relative}: {rollback_failure}")
        if errors:
            raise RuntimeError(
                f"v8 recovery incomplete; restore from {backup}: {'; '.join(errors)}"
            ) from failure
        raise RuntimeError(f"v9 promotion rolled back; recovery retained: {backup}") from failure
    return backup


def promote_restrictions_v9(stage_dir: Path, *, root: Path = ROOT) -> Path:
    """Apply only a previously reviewed, unchanged v9 pair to the local checkout."""
    root = root.resolve()
    stage = _stage_path(root, stage_dir)
    report = json.loads((stage / "staging-report.json").read_text(encoding="utf-8"))
    if (report.get("scope") != STAGING_SCOPE
        or report.get("reviewedConditions") != 14
        or report.get("targetPaths") != [p.as_posix() for p in ARTIFACTS]
    ):
        raise ValueError("Unexpected Restrictions v9 staging report")
    if _fingerprints(root) != report["source"]:
        raise ValueError("Release inputs changed since v9 staging")
    git = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(RULES)],
        cwd=root, capture_output=True, check=False,
    )
    if git.returncode != 0:
        raise ValueError("Tracked rules.db differs from HEAD; refusing to promote")

    proposed = {}
    for path in ARTIFACTS:
        source = stage / path
        if (
            not source.is_file() or source.is_symlink()
            or _sha(source) != report["staged"][path.as_posix()]
        ):
            raise ValueError(f"Staged v9 artifact changed: {path}")
        proposed[path] = source.read_bytes()

    original_pub = load_deployed_object_publication(
        root / PUBLICATION, root / ARMY, root / RULES,
    )
    staged_pub = load_deployed_object_publication(
        stage / PUBLICATION, root / ARMY, stage / RULES,
    )
    if original_pub is None or staged_pub is None:
        raise ValueError("Missing release-matched deployed-object publication")
    _expected_publication_delta(original_pub, staged_pub, _sha(stage / RULES))
    _checked_chart(root)
    RulesDatabase(stage / RULES).validate()
    expected = publication_bytes(build_publication(
        root / ARMY, stage / RULES, root / CURATED, root / DELIVERY, root / CANDIDATES,
    ))
    if proposed[PUBLICATION] != expected:
        raise ValueError("Staged publication is stale or not deterministic")

    def post_validate() -> None:
        if any(
            _sha(root / relative) != report["staged"][relative.as_posix()]
            for relative in ARTIFACTS
        ):
            raise ValueError("Promoted artifact fingerprints changed")
        current = RulesDatabase(root / RULES)
        current.validate()
        if not current.restrictions_payload()["available"] or len(
            current.restrictions_payload()["items"]
        ) != 14:
            raise ValueError("Promoted v9 reference incomplete")
        published = load_deployed_object_publication(
            root / PUBLICATION, root / ARMY, root / RULES,
        )
        if published != staged_pub:
            raise ValueError("Promoted deployed-object publication differs from verified staging")
        from infinity_db.web import create_app

        application = create_app(root / ARMY, rules_database_path=root / RULES)
        if application.deployed_objects is None or len(application.deployed_objects["objects"]) != (
            report["reviewedObjects"]
        ):
            raise ValueError("Co-located release application did not load deployed objects")
        # Version-aware application continues to accept the stored rollback v8
        # artifact, verified separately before promotion and retained in backups.

    return _replace_with_rollback(root, proposed, post_validate)
