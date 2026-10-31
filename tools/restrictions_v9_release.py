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
from contextlib import closing
from pathlib import Path
from typing import Any

from infinity_db.curated import discover_curated_documents, load_curated_directory
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
INITIAL_MOVEMENT_DISTANCE = {
    ("n5-core-v5.3", "skill:jump"): 263,
    ("n5-core-v5.3", "skill:climb"): 271,
}
MOVEMENT_DISTANCE_VARIANT = {
    "inheritance": "family",
    "occurrenceParameters": [{
        "source": "army-extra", "kind": "distance", "positiveSign": "omit",
    }],
}
TINBOT_FIREWALL = ("n5-core-v5.3", "equipment:tinbot-firewall")
TINBOT_FIREWALL_BASE = {
    "inheritance": "source", "sourceVariant": {"kind": "named", "label": "Firewall"},
}
TINBOT_FIREWALL_VARIANT = {
    **TINBOT_FIREWALL_BASE,
    "occurrenceParameters": [{
        "source": "army-extra",
        "kind": "reviewed-extra",
        "extraValues": [
            {
                "extraId": extra_id,
                "extraType": "TEXT",
                "rawValue": str(modifier),
                "effect": {
                    "kind": "enemy-comms-attack-mod",
                    "appliesTo": "comms-attack-targeting-tinbot-owner",
                    "modifier": modifier,
                },
            }
            for extra_id, modifier in ((6, -3), (7, -6))
        ],
    }],
}
TINBOT_OTHER_SOURCES = {
    ("n5-core-v5.3", "equipment:tinbot-discover"): {
        "sourceId": 244, "name": "TinBot: Discover", "count": 2, "label": "Discover",
        "signatures": [
            {"extras": [[277, "TEXT", "ReRoll"]], "reviewed": False, "count": 2},
        ],
        "values": [{
            "extraId": 277, "extraType": "TEXT", "rawValue": "ReRoll",
            "effect": {"kind": "reroll-one-die", "appliesTo": "tinbot-discover-roll"},
        }],
    },
    ("n5-core-v5.3", "equipment:tinbot-ecm-guided"): {
        "sourceId": 247, "name": "TinBot: ECM Guided", "count": 4,
        "label": "ECM Guided",
        "signatures": [
            {"extras": [[7, "TEXT", "-6"]], "reviewed": False, "count": 2},
            {"extras": [[259, "TEXT", "-9"]], "reviewed": False, "count": 2},
        ],
        "values": [
            {
                "extraId": extra_id, "extraType": "TEXT", "rawValue": str(modifier),
                "effect": {
                    "kind": "enemy-guided-attack-mod",
                    "appliesTo": "guided-attack-targeting-tinbot-owner",
                    "modifier": modifier,
                },
            }
            for extra_id, modifier in ((7, -6), (259, -9))
        ],
    },
}
TINBOT_OTHER_VARIANTS = {
    key: {
        "inheritance": "source",
        "sourceVariant": {"kind": "named", "label": source["label"]},
        "occurrenceParameters": [{
            "source": "army-extra", "kind": "reviewed-extra",
            "extraValues": source["values"],
        }],
    }
    for key, source in TINBOT_OTHER_SOURCES.items()
}


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
    *, backup_prefix: str = "restrictions-v8-recovery-",
) -> Path:
    """Retain both original binaries; recover them on any failed write/check."""
    backup = Path(tempfile.mkdtemp(prefix=backup_prefix, dir=root / "local"))
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


def refresh_isolated_context_v9_release(*, root: Path = ROOT) -> Path:
    """Synchronize only the two reviewed Isolated contextual links into a v9 pair.

    Refuse a stale/unpaired current release or unexpected legacy graph changes.
    Build and verify everything in ignored local/ before guarded replacement.
    """
    root = root.resolve()
    current_rules = root / RULES
    current_publication = root / PUBLICATION
    army = root / ARMY
    if not (root / "local").is_dir():
        raise ValueError("Ignored local/ recovery directory is required")
    git = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(RULES)],
        cwd=root, capture_output=True, check=False,
    )
    if git.returncode != 0:
        raise ValueError("Tracked release rules.db differs from HEAD")
    current = RulesDatabase(current_rules)
    current.validate()
    with closing(sqlite3.connect(current_rules)) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] != 9:
            raise ValueError("Contextual refresh requires the promoted v9 release")
    before = load_deployed_object_publication(current_publication, army, current_rules)
    if before is None:
        raise ValueError("Existing v9 publication does not match its release databases")
    chart = _checked_chart(root)
    documents = load_curated_directory(root / "data/curated/rules")
    source = next(
        document for _, document in documents
        if document["collection"]["id"] == "n5-core-v5.3"
    )
    isolated = next(row for row in source["records"] if row["id"] == "state:isolated")
    expected_links = (
        ("prevents-membership-in", "rule:fireteam-general"),
        ("prevents-participation-in", "rule:coordinated-orders"),
    )
    if [
        (edge["type"], edge["recordId"])
        for edge in isolated["relations"][-2:]
    ] != list(expected_links):
        raise ValueError("Isolated contextual links differ from reviewed scope")

    with tempfile.TemporaryDirectory(prefix="isolated-v9-stage-", dir=root / "local") as tmp:
        stage = Path(tmp)
        next_rules = stage / "rules.db"
        next_publication = stage / "deployed-objects.json"
        export_rules_database(documents, next_rules, restrictions_manifest=chart)
        generated = RulesDatabase(next_rules)
        generated.validate()
        if (
            generated.restrictions_payload() != current.restrictions_payload()
            or not generated.restrictions_payload()["available"]
        ):
            raise ValueError("Reviewed N5.3 typed Restrictions changed during refresh")
        relation_sql = (
            "SELECT collection_id, record_id, position, relation_type, related_record_id "
            "FROM record_relations ORDER BY collection_id, record_id, position"
        )
        with closing(sqlite3.connect(current_rules)) as old, closing(
            sqlite3.connect(next_rules)
        ) as new:
            previous_edges = set(old.execute(relation_sql).fetchall())
            next_edges = set(new.execute(relation_sql).fetchall())
            old_position = max(
                position for collection, record, position, _, _ in previous_edges
                if (collection, record) == ("n5-core-v5.3", "state:isolated")
            )
            expected_added = {
                ("n5-core-v5.3", "state:isolated", old_position + index,
                 edge_type, target)
                for index, (edge_type, target) in enumerate(expected_links, start=1)
            }
            if previous_edges - next_edges or next_edges - previous_edges != expected_added:
                raise ValueError("Unexpected legacy graph delta in isolated context refresh")
        proposed = build_publication(
            army, next_rules, root / CURATED, root / DELIVERY, root / CANDIDATES,
        )
        # The maintained source file changed, so its publication provenance
        # advances alongside the rules hash. The reviewed 17 object payloads,
        # delivery decisions and all other fingerprints must remain identical.
        expected_publication = json.loads(json.dumps(before))
        expected_publication["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(next_rules)
        expected_publication["sourceSnapshot"]["curatedSourceSha256"] = _sha(root / CURATED)
        if expected_publication != proposed:
            raise ValueError(
                "Isolated contextual refresh altered deployed-object content "
                "or unrelated provenance"
            )
        next_publication.write_bytes(publication_bytes(proposed))
        if load_deployed_object_publication(next_publication, army, next_rules) != proposed:
            raise ValueError("Staged contextual publication does not match v9 rules")

        payloads = {
            RULES: next_rules.read_bytes(),
            PUBLICATION: next_publication.read_bytes(),
        }

        def post_validate() -> None:
            refreshed = RulesDatabase(current_rules)
            refreshed.validate()
            if refreshed.restrictions_payload() != current.restrictions_payload():
                raise ValueError("Promoted contextual links changed typed Restrictions")
            if load_deployed_object_publication(current_publication, army, current_rules) != (
                proposed
            ):
                raise ValueError("Promoted contextual publication differs from staged source")
            state = refreshed.composed_record("state:isolated")
            if state is None or not all(
                any(
                    item["type"] == edge_type and item["record_id"] == target
                    and item["direction"] == "outbound"
                    for item in state["display_relations"]
                )
                for edge_type, target in expected_links
            ):
                raise ValueError("Promoted v9 lost Isolated contextual navigation")

        return _replace_with_rollback(
            root, payloads, post_validate, backup_prefix="isolated-v9-recovery-",
        )


def _check_source_pin_delta(
    previous: Path, proposed: Path, source_id: str, digest: str,
    expected_collections: set[str],
) -> None:
    """Compatibility wrapper for the original single-source guarded refresh."""
    _check_source_pins_delta(previous, proposed, {
        (collection, source_id): digest for collection in expected_collections
    })


def _check_source_pins_delta(
    previous: Path, proposed: Path, pins: dict[tuple[str, str], str],
) -> None:
    """Allow only the declared NULL-to-hash source cells; preserve every other row."""
    with closing(sqlite3.connect(previous)) as old, closing(sqlite3.connect(proposed)) as new:
        for pragma in ("application_id", "user_version"):
            if old.execute(f"PRAGMA {pragma}").fetchone() != new.execute(
                f"PRAGMA {pragma}",
            ).fetchone():
                raise ValueError("Source pin refresh changed database identity")
        schema_sql = "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        schema = old.execute(schema_sql).fetchall()
        if schema != new.execute(schema_sql).fetchall():
            raise ValueError("Source pin refresh changed the table schema")
        changed: set[tuple[str, str]] = set()
        for kind, name, _ in schema:
            if kind != "table":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [row[1] for row in old.execute(f"PRAGMA table_info({quoted})")]
            order = ",".join(str(index + 1) for index in range(len(columns)))
            query = f"SELECT * FROM {quoted} ORDER BY {order}"
            rows = old.execute(query).fetchall()
            if name == "sources":
                collection_column, id_column, hash_column = (
                    columns.index(key) for key in ("collection_id", "id", "sha256")
                )
                expected_rows = []
                for row in rows:
                    expected = list(row)
                    key = (row[collection_column], row[id_column])
                    if key in pins:
                        if row[hash_column] is not None:
                            raise ValueError(
                                "Source pin refresh requires exact unpinned declarations"
                            )
                        expected[hash_column] = pins[key]
                        changed.add(key)
                    expected_rows.append(tuple(expected))
                rows = expected_rows
            if rows != new.execute(query).fetchall():
                raise ValueError(f"Source pin refresh changed unrelated rows: {name}")
        if not pins or changed != set(pins):
            raise ValueError("Source pin refresh did not cover the expected declarations")


def refresh_core_pdf_pin_v9_release(*, root: Path = ROOT) -> Path:
    """Publish the reviewed English N5.3 byte pin without changing rules or objects."""
    return _refresh_metadata_v9_release(
        root=root, source_ids={"n5-core-v5.3-pdf"}, expected_count=2,
    )


def refresh_pdf_source_pins_v9_release(*, root: Path = ROOT) -> Path:
    """Publish missing pins for already-cataloged PDFs, verifying their local bytes."""
    return _refresh_metadata_v9_release(root=root)


def _check_variant_semantics_delta(
    previous: Path, proposed: Path, variants: dict[tuple[str, str], str],
    *, initialize_movement_distance: bool = False, tinbot_firewall: bool = False,
    tinbot_other: bool = False,
) -> None:
    """Guard exact parameter additions; preserve other records and source identity."""
    initial = INITIAL_MOVEMENT_DISTANCE if initialize_movement_distance else {}
    if initial and set(variants) != set(initial):
        raise ValueError("Movement distance refresh requires exactly Jump and Climb")
    if tinbot_firewall and (initial or tinbot_other or set(variants) != {TINBOT_FIREWALL}):
        raise ValueError("TinBot refresh requires its exact source record")
    if tinbot_other and (initial or set(variants) != set(TINBOT_OTHER_SOURCES)):
        raise ValueError("TinBot additional variants require exactly Discover and ECM Guided")
    with closing(sqlite3.connect(previous)) as old, closing(sqlite3.connect(proposed)) as new:
        for pragma in ("user_version", "application_id"):
            if old.execute(f"PRAGMA {pragma}").fetchone() != new.execute(
                f"PRAGMA {pragma}",
            ).fetchone():
                raise ValueError("Variant refresh changed database identity")
        schema_sql = "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        schema = old.execute(schema_sql).fetchall()
        if schema != new.execute(schema_sql).fetchall():
            raise ValueError("Variant refresh changed database schema")
        changed: set[tuple[str, str]] = set()
        for kind, name, _ in schema:
            if kind != "table":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [row[1] for row in old.execute(f"PRAGMA table_info({quoted})")]
            order = ",".join(str(index + 1) for index in range(len(columns)))
            query = f"SELECT * FROM {quoted} ORDER BY {order}"
            rows = old.execute(query).fetchall()
            if name == "records":
                rows = [list(row) for row in rows]
                for row in rows:
                    key = (row[columns.index("collection_id")], row[columns.index("id")])
                    if key not in variants:
                        continue
                    index = columns.index("variant_json")
                    after = json.loads(variants[key])
                    if key in initial:
                        if row[index] is not None or after != MOVEMENT_DISTANCE_VARIANT:
                            raise ValueError(
                                "Initial movement distance requires exact new metadata"
                            )
                    elif key == TINBOT_FIREWALL and tinbot_firewall:
                        if (
                            row[index] is None
                            or json.loads(row[index]) != TINBOT_FIREWALL_BASE
                            or after != TINBOT_FIREWALL_VARIANT
                        ):
                            raise ValueError("TinBot refresh changed named source identity")
                    elif key in TINBOT_OTHER_SOURCES and tinbot_other:
                        base = {
                            "inheritance": "source",
                            "sourceVariant": {
                                "kind": "named", "label": TINBOT_OTHER_SOURCES[key]["label"],
                            },
                        }
                        if (
                            row[index] is None
                            or json.loads(row[index]) != base
                            or after != TINBOT_OTHER_VARIANTS[key]
                        ):
                            raise ValueError("TinBot refresh changed additional named source")
                    else:
                        if row[index] is None:
                            raise ValueError("Variant refresh requires existing family metadata")
                        before = json.loads(row[index])
                        prior = before.pop("occurrenceParameters", [])
                        additions = after.pop("occurrenceParameters", [])
                        if (before != after or before.get("inheritance") != "family"
                                or len(additions) <= len(prior) or additions[:len(prior)] != prior):
                            raise ValueError("Variant refresh must only append reviewed parameters")
                    row[index] = variants[key]
                    changed.add(key)
                rows = [tuple(row) for row in rows]
            elif name == "record_army_links" and initial:
                column_keys = ("collection_id", "record_id", "position", "entity",
                               "external_id", "external_name")
                if set(columns) != set(column_keys):
                    raise ValueError("Unexpected record army link schema")
                if any((row[columns.index("collection_id")],
                        row[columns.index("record_id")]) in initial for row in rows):
                    raise ValueError("Initial movement records already have Army links")
                for (collection, record_id), source_id in initial.items():
                    expected = dict(zip(column_keys, (
                        collection, record_id, 0, "skill", str(source_id), None,
                    ), strict=True))
                    rows.append(tuple(expected[key] for key in columns))
                rows = sorted(rows)
            elif name == "sqlite_stat1" and initial:
                # ANALYZE refreshes cardinality estimates for the two added
                # Army links. Other tables' index statistics must remain exact.
                stat_table = columns.index("tbl")
                after_stats = new.execute(query).fetchall()
                before_others = [
                    row for row in rows if row[stat_table] != "record_army_links"
                ]
                after_others = [
                    row for row in after_stats
                    if row[stat_table] != "record_army_links"
                ]
                if before_others != after_others:
                    raise ValueError("Movement refresh changed unrelated index statistics")
                rows = after_stats
            if rows != new.execute(query).fetchall():
                raise ValueError(f"Variant refresh changed unrelated rows: {name}")
        if not variants or changed != set(variants):
            raise ValueError("Variant refresh did not cover the exact requested records")


def refresh_variant_semantics_v9_release(
    record_ids: set[str], *, root: Path = ROOT,
) -> Path:
    """Synchronize reviewed occurrence metadata without changing other rule content."""
    if not record_ids:
        raise ValueError("Variant refresh requires explicit record IDs")
    return _refresh_metadata_v9_release(root=root, variant_records=record_ids)


def refresh_movement_distance_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only the pinned Jump/Climb family links and distance parameters."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    for source_id, name, expected_count in ((263, "Jump", 26), (271, "Climb", 6)):
        matches = [
            item for item in report["catalogs"]["skills"]["items"]
            if item["id"] == source_id
        ]
        if (
            len(matches) != 1
            or matches[0]["name"] != name
            or matches[0]["applicationId"] != source_id
            or matches[0]["occurrences"] != expected_count
            or matches[0]["status"] != "unresolved-occurrence-parameter"
            or matches[0]["extraSignatures"] != [{
                "extras": [[372, "DISTANCE", "7.5"]],
                "reviewed": False,
                "count": expected_count,
            }]
            or matches[0]["rawValues"]
        ):
            raise ValueError(f"Unreviewed Jump/Climb source drift: {source_id}")
    return _refresh_metadata_v9_release(
        root=root, variant_records={key[1] for key in INITIAL_MOVEMENT_DISTANCE},
        initialize_movement_distance=True,
    )


def refresh_tinbot_firewall_v9_release(*, root: Path = ROOT) -> Path:
    """Promote exact source 169 Firewall modifiers without publishing inferred uses."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["equipment"]["items"]
        if row["id"] == 169
    ]
    if len(rows) != 1:
        raise ValueError("Missing exact TinBot Firewall source")
    item = rows[0]
    if (
        item["name"] != "TinBot: Firewall"
        or item["applicationId"] != 235
        or item["occurrences"] != 147
        or item["status"] != "unresolved-occurrence-parameter"
        or item["reviewedVariant"] != {"kind": "named", "label": "Firewall"}
        or item["reviewedExtra"] is not None
        or item["rawValues"]
        or item["extraSignatures"] != [
            {"extras": [[6, "TEXT", "-3"]], "reviewed": False, "count": 92},
            {"extras": [[7, "TEXT", "-6"]], "reviewed": False, "count": 55},
        ]
    ):
        raise ValueError("Unreviewed TinBot Firewall source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={TINBOT_FIREWALL[1]}, tinbot_firewall=True,
    )


def refresh_tinbot_other_v9_release(*, root: Path = ROOT) -> Path:
    """Promote exact Discover reroll and Guided attack MODs in a matched v9 pair."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {
        row["id"]: row for row in report["catalogs"]["equipment"]["items"]
    }
    for source in TINBOT_OTHER_SOURCES.values():
        item = items.get(source["sourceId"])
        if (
            item is None
            or item["name"] != source["name"]
            or item["applicationId"] != 235
            or item["occurrences"] != source["count"]
            or item["status"] != "unresolved-occurrence-parameter"
            or item["reviewedVariant"] != {
                "kind": "named", "label": source["label"],
            }
            or item["reviewedExtra"] is not None
            or item["extraSignatures"] != source["signatures"]
            or item["rawValues"]
        ):
            raise ValueError(f"Unreviewed TinBot source drift: {source['sourceId']}")
    return _refresh_metadata_v9_release(
        root=root,
        variant_records={key[1] for key in TINBOT_OTHER_SOURCES},
        tinbot_other=True,
    )


def _refresh_metadata_v9_release(
    *, root: Path, source_ids: set[str] | None = None, expected_count: int | None = None,
    variant_records: set[str] | None = None,
    initialize_movement_distance: bool = False, tinbot_firewall: bool = False,
    tinbot_other: bool = False,
) -> Path:
    root = root.resolve()
    current_rules, current_publication, army = (root / path for path in (RULES, PUBLICATION, ARMY))
    if not (root / "local").is_dir():
        raise ValueError("Ignored local/ recovery directory is required")
    git = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(RULES)],
        cwd=root, capture_output=True, check=False,
    )
    if git.returncode != 0:
        raise ValueError("Tracked release rules.db differs from HEAD")
    current = RulesDatabase(current_rules)
    current.validate()
    with closing(sqlite3.connect(current_rules)) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] != 9:
            raise ValueError("Source pin refresh requires the promoted v9 release")
        previous_pins = {
            (collection, source_id): digest for collection, source_id, digest in connection.execute(
                "SELECT collection_id, id, sha256 FROM sources WHERE kind = 'pdf'",
            )
        }
    before = load_deployed_object_publication(current_publication, army, current_rules)
    if before is None:
        raise ValueError("Existing v9 publication does not match its release databases")
    input_paths = set(discover_curated_documents(root / "data/curated/rules")) | {
        root / path for path in (ARMY, CHART, CURATED, DELIVERY, CANDIDATES)
    }
    input_hashes = {path: _sha(path) for path in input_paths}
    chart = _checked_chart(root)
    input_hashes[root / PDF] = chart["sourcePdfSha256"]
    documents = load_curated_directory(root / "data/curated/rules")
    pins: dict[tuple[str, str], str] = {}
    variants = {
        (document["collection"]["id"], row["id"]): json.dumps(
            row["variantSemantics"], ensure_ascii=False, separators=(",", ":"),
        )
        for _, document in documents for row in document["records"]
        if variant_records is not None and row["id"] in variant_records
        and row.get("review", {}).get("status") == "reviewed"
        and row.get("variantSemantics", {}).get("occurrenceParameters")
    }
    for _, document in documents:
        for source in document["sources"]:
            key = (document["collection"]["id"], source["id"])
            if (variant_records is not None or source["kind"] != "pdf" or key not in previous_pins
                    or previous_pins[key] is not None
                    or (source_ids is not None and source["id"] not in source_ids)):
                continue
            digest = source.get("sha256")
            if not isinstance(digest, str):
                continue
            path = (root / source["localPath"]).resolve()
            if not path.is_relative_to(root):
                raise ValueError("Source pin refresh requires checkout-local research inputs")
            actual = _sha(path)
            if actual != digest.lower():
                raise ValueError(f"Source pin refresh PDF hash mismatch: {source['id']}")
            input_hashes[path] = actual
            pins[key] = digest
    if variant_records is not None:
        if {record for _, record in variants} != variant_records or len(variants) != len(
            variant_records
        ):
            raise ValueError("Variant refresh requires exact reviewed family records")
    elif not pins or (expected_count is not None and len(pins) != expected_count):
        raise ValueError("Source pin refresh requires the expected missing PDF declarations")
    originals = {path: (root / path).read_bytes() for path in ARTIFACTS}
    with tempfile.TemporaryDirectory(prefix="pdf-source-pin-v9-stage-", dir=root / "local") as tmp:
        stage = Path(tmp)
        next_rules = stage / "rules.db"
        export_rules_database(documents, next_rules, restrictions_manifest=chart)
        repeat = stage / "repeat.db"
        export_rules_database(documents, repeat, restrictions_manifest=chart)
        if _sha(next_rules) != _sha(repeat):
            raise ValueError("Source pin export is not byte deterministic")
        generated = RulesDatabase(next_rules)
        generated.validate()
        if variant_records is not None:
            _check_variant_semantics_delta(
                current_rules, next_rules, variants,
                initialize_movement_distance=initialize_movement_distance,
                tinbot_firewall=tinbot_firewall,
                tinbot_other=tinbot_other,
            )
        else:
            _check_source_pins_delta(current_rules, next_rules, pins)
        if generated.restrictions_payload() != current.restrictions_payload():
            raise ValueError("Source pin refresh changed typed Restrictions")
        proposed = build_publication(
            army, next_rules, root / CURATED, root / DELIVERY, root / CANDIDATES,
        )
        expected = json.loads(json.dumps(before))
        expected["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(next_rules)
        expected["sourceSnapshot"]["curatedSourceSha256"] = _sha(root / CURATED)
        if proposed != expected:
            raise ValueError("Source pin refresh changed deployed objects or unrelated provenance")
        if any((root / path).read_bytes() != data for path, data in originals.items()):
            raise ValueError("Release pair changed during source pin staging")
        if any(_sha(path) != digest for path, digest in input_hashes.items()):
            raise ValueError("Reviewed inputs changed during source pin staging")

        def post_validate() -> None:
            RulesDatabase(current_rules).validate()
            if load_deployed_object_publication(current_publication, army, current_rules) != (
                proposed
            ):
                raise ValueError("Promoted source pin publication differs from staged source")

        return _replace_with_rollback(
            root, {RULES: next_rules.read_bytes(), PUBLICATION: publication_bytes(proposed)},
            post_validate, backup_prefix=(
                "variant-semantics-v9-recovery-" if variant_records is not None
                else "pdf-source-pin-v9-recovery-"
            ),
        )
