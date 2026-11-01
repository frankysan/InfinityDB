"""Stage, verify and optionally promote the paired N5.3 Restrictions v9 artifacts.

Staging never edits tracked files. Promotion validates exact source and
staging fingerprints, preserves v8 recovery artifacts and rolls back failed
post-publication checks. It does not commit, deploy or change legacy relations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from infinity_db.curated import (
    BANGBOMB_SKILL_PARAMETERS,
    CHART_REROLL_VARIANTS,
    DECOY_VARIANT,
    FT_MASTER_UNIT_SIGNATURES,
    FT_MASTER_VARIANT,
    GIZMOKIT_TARGET_PH_PARAMETERS,
    HACKER_SOURCE_VARIANT,
    KILLER_HACKING_VARIANT,
    MEDIKIT_TARGET_PH_PARAMETERS,
    REGENERATION_VARIANT,
    REMDRIVER_COMBINATIONS,
    TAGCOM_COMBINATIONS,
    VULNERABILITY_VIRAL_VARIANT,
    discover_curated_documents,
    load_curated_directory,
    reviewed_hacking_combinations,
)
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
EVO_HACKING_DEVICE = ("n5-core-v5.3", "equipment:evo-hacking-device")
EVO_TRINITY_VARIANT = {
    "inheritance": "family",
    "occurrenceParameters": [{
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [{
            "extraId": 352, "extraType": "TEXT",
            "rawValue": "UPGRADE: Trinity (SR-2)",
            "effect": {
                "kind": "hacking-program-upgrade",
                "program": "hacking-program:trinity",
                "grantsProgram": True,
                "appliesTo": "target-saving-roll-against-program",
                "modifier": -2,
            },
        }],
    }],
}
MEDIKIT = ("n5-core-v5.3", "equipment:medikit")
MEDIKIT_VARIANT = {
    "inheritance": "family",
    "occurrenceParameters": [{
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [{
            "extraId": 8, "extraType": "TEXT", "rawValue": "+1B",
            "effect": {
                "kind": "equipment-burst-mod",
                "appliesTo": "ranged-medikit-bs-attack",
                "modifier": 1,
            },
        }],
    }],
}
MEDIKIT_TARGET_PH_VARIANT = {
    **MEDIKIT_VARIANT,
    "sourceCatalogParameters": MEDIKIT_TARGET_PH_PARAMETERS,
}
GIZMOKIT = ("n5-core-v5.3", "equipment:gizmokit")
GIZMOKIT_VARIANT = {
    "inheritance": "family",
    "occurrenceParameters": [{
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [{
            "extraId": 8, "extraType": "TEXT", "rawValue": "+1B",
            "effect": {
                "kind": "equipment-burst-mod",
                "appliesTo": "ranged-gizmokit-bs-attack",
                "modifier": 1,
            },
        }],
    }],
}
GIZMOKIT_TARGET_PH_VARIANT = {
    **GIZMOKIT_VARIANT,
    "sourceCatalogParameters": GIZMOKIT_TARGET_PH_PARAMETERS,
}
REGENERATION = ("n5-core-v5.3", "skill:regeneration")
CHART_REROLLS = {
    ("n5-core-v5.3", f"skill:{skill}"): variant
    for skill, variant in CHART_REROLL_VARIANTS.items()
}
HACKER_SKILL = ("n5-core-v5.3", "skill:hacker")
VULNERABILITY = ("n5-core-v5.3", "skill:vulnerability")
DECOY = ("n5-core-v5.3", "skill:decoy")
FT_MASTER = ("n5-core-v5.3", "skill:ft-master")
TAGCOM = ("n5-core-v5.3", "skill:tagcom")
TAGCOM_VARIANT = {
    "inheritance": "family",
    "occurrenceCombinations": TAGCOM_COMBINATIONS,
}
REMDRIVER = ("n5-core-v5.3", "skill:remdriver")
REMDRIVER_VARIANT = {
    "inheritance": "family",
    "occurrenceCombinations": REMDRIVER_COMBINATIONS,
}
IMPERSONATION = ("n5-core-v5.3", "skill:impersonation")
IMPERSONATION_VARIANT = {
    "inheritance": "family",
    "occurrenceParameters": [{
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [{
            "extraId": 268, "extraType": "TEXT", "rawValue": "IMP-2",
            "effect": {
                "kind": "impersonation-state-restriction",
                "state": "state:impersonation-2",
                "appliesTo": "deployment-and-activation",
                "only": True,
            },
        }],
    }],
}
KILLER_HACKING_DEVICE = ("n5-core-v5.3", "equipment:killer-hacking-device")
DEACTIVATOR = ("n5-core-v5.3", "equipment:deactivator")
DEACTIVATOR_VARIANT = {
    "inheritance": "family",
    "occurrenceParameters": [{
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [
            {
                "extraId": 8, "extraType": "TEXT", "rawValue": "+1B",
                "effect": {
                    "kind": "equipment-burst-mod",
                    "appliesTo": "deactivator-wip-attack",
                    "modifier": 1,
                },
            },
            {
                "extraId": 277, "extraType": "TEXT", "rawValue": "ReRoll",
                "effect": {
                    "kind": "reroll-one-die",
                    "appliesTo": "deactivator-wip-roll",
                },
            },
        ],
    }],
}
BANGBOMB = ("n5-core-v5.3", "equipment:bangbomb")
BANGBOMB_VARIANT = {
    "inheritance": "family",
    "occurrenceParameters": [{
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [{
            "extraId": 310, "extraType": "TEXT", "rawValue": "+4",
            "effect": {
                "kind": "dodge-roll-mod",
                "appliesTo": "dodge-vs-enemy-in-lof-or-zoc-excluding-template-weapons",
                "modifier": 4,
            },
        }],
    }],
}
BANGBOMB_SKILL_VARIANT = {
    **BANGBOMB_VARIANT,
    "sourceCatalogParameters": BANGBOMB_SKILL_PARAMETERS,
}
ECM_SOURCES = {
    ("n5-core-v5.3", "equipment:ecm-guided"): {
        "sourceId": 239, "name": "ECM:\u00a0Guided",
        "recordName": "ECM: Guided", "count": 181,
        "label": "Guided", "scope": "guided-attack-targeting-ecm-owner",
        "signatures": ((6, -3, 2), (7, -6, 176),
                       (51, -8, 1), (251, -8, 2)),
    },
    ("n5-core-v5.3", "equipment:ecm-hacker"): {
        "sourceId": 241, "name": "ECM: Hacker",
        "recordName": "ECM: Hacker", "count": 161,
        "label": "Hacker", "scope": "hacking-program-targeting-ecm-owner",
        "signatures": ((6, -3, 158), (7, -6, 3)),
    },
}


def _ecm_variant(key: tuple[str, str]) -> dict[str, Any]:
    spec = ECM_SOURCES[key]
    return {
        "inheritance": "source",
        "sourceVariant": {"kind": "named", "label": spec["label"]},
        "occurrenceParameters": [{
            "source": "army-extra", "kind": "reviewed-extra",
            "extraValues": [
                {
                    "extraId": extra_id, "extraType": "TEXT",
                    "rawValue": str(modifier),
                    "effect": {
                        "kind": "enemy-ecm-attack-mod",
                        "appliesTo": spec["scope"],
                        "modifier": modifier,
                    },
                }
                for extra_id, modifier, _count in spec["signatures"]
            ],
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


# Only unmodified program-grant UPGRADE values have been reviewed here.
# Other Hacking Device program overrides, Firewall, and combinations remain opaque.
HACKING_GRANT_SOURCES = {
    100: {
        "record": "equipment:hacking-device",
        "name": "Hacking Device",
        "occurrences": 653,
        "singles": {
            12: ("UPGRADE:\u00a0Trinity", 17),
            20: ("UPGRADE:\u00a0White Noise", 12),
            25: ("UPGRADE: Cybermask", 1),
            287: ("UPGRADE: Zero Pain", 120),
        },
        "combined": [
            {"extras": [[25, "TEXT", "UPGRADE: Cybermask"],
                        [12, "TEXT", "UPGRADE:\u00a0Trinity"]],
             "reviewed": False, "count": 1},
        ],
    },
    101: {
        "record": "equipment:hacking-device-plus",
        "name": "Hacking Device Plus",
        "occurrences": 126,
        "singles": {17: ("UPGRADE:\u00a0Fairy Dust", 46)},
        "combined": [],
    },
}


# Pinned single-extra program modifiers only; saving-roll and compound
# signatures remain unreviewed until their exact effects are established.
HACKING_MOD_SOURCES = {
    100: [
        (269, "UPGRADE: Oblivion (+1B)", "oblivion", "program-burst-mod", "modifier", 1, 7),
        (278, "UPGRADE: Total Control (+1B)", "total-control",
             "program-burst-mod", "modifier", 1, 46),
        (285, "UPGRADE: Carbonite (+1 B)", "carbonite", "program-burst-mod", "modifier", 1, 7),
        (290, "UPGRADE: Trinity (+1B)", "trinity", "program-burst-mod", "modifier", 1, 3),
        (363, "UPGRADE: Carbonite (PS=6)", "carbonite", "program-ps-replacement", "value", 6, 8),
        (378, "UPGRADE: Trinity (+1SD)", "trinity", "program-special-die", "count", 1, 1),
        (383, "UPGRADE: Carbonite (+1SD)", "carbonite", "program-special-die", "count", 1, 3),
    ],
    101: [
        (269, "UPGRADE: Oblivion (+1B)", "oblivion", "program-burst-mod", "modifier", 1, 3),
        (378, "UPGRADE: Trinity (+1SD)", "trinity", "program-special-die", "count", 1, 3),
    ],
}


def _hacking_mod_values(source_id: int) -> list[dict[str, Any]]:
    return [
        {
            "extraId": extra_id, "extraType": "TEXT", "rawValue": raw,
            "effect": {
                "kind": kind, "program": f"hacking-program:{program}",
                field: value,
            },
        }
        for extra_id, raw, program, kind, field, value, _count
        in HACKING_MOD_SOURCES[source_id]
    ]


# Single-source Saving Roll penalties against the specified program.
# Unqualified SR-1 and combined extras are intentionally not certified.
HACKING_SR_SOURCES = {
    100: [
        (331, "UPGRADE: Carbonite (SR-2)", "carbonite", -2, 1),
        (339, "UPGRADE: Trinity (SR-1)", "trinity", -1, 2),
        (352, "UPGRADE: Trinity (SR-2)", "trinity", -2, 4),
    ],
    101: [
        (314, "UPGRADE: Total Control (SR-2)", "total-control", -2, 46),
        (339, "UPGRADE: Trinity (SR-1)", "trinity", -1, 2),
    ],
}


def _hacking_sr_values(source_id: int) -> list[dict[str, Any]]:
    return [
        {
            "extraId": extra_id, "extraType": "TEXT", "rawValue": raw,
            "effect": {
                "kind": "program-saving-roll-mod",
                "program": f"hacking-program:{program}",
                "appliesTo": "target-saving-roll-against-program",
                "modifier": modifier,
            },
        }
        for extra_id, raw, program, modifier, _count
        in HACKING_SR_SOURCES[source_id]
    ]


# Standalone Hacking Device Firewall effects are distinct from TinBot
# and from the target-program SR upgrades. Both forms impose +3 SR.
HACKING_FIREWALL_SOURCES = {
    100: [
        (326, "Firewall -6", -6, 2),
        (334, "UPGRADE: Firewall (-3)", -3, 13),
        (376, "UPGRADE: Firewall (-6)", -6, 1),
    ],
}


def _hacking_firewall_values(source_id: int) -> list[dict[str, Any]]:
    return [
        {
            "extraId": extra_id, "extraType": "TEXT", "rawValue": raw,
            "effect": {
                "kind": "firewall-comms-defense",
                "rule": "equipment:firewall",
                "appliesTo": "comms-attack-targeting-device-owner",
                "attackerWipMod": modifier,
                "defenderSavingRollMod": 3,
            },
        }
        for extra_id, raw, modifier, _count in HACKING_FIREWALL_SOURCES[source_id]
    ]


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


def _check_ecm_source_additions(
    previous: Path, proposed: Path, variants: dict[tuple[str, str], str],
) -> None:
    """Allow only two exact source records and their owned relational rows."""
    from collections import Counter

    if set(variants) != set(ECM_SOURCES):
        raise ValueError("ECM source refresh requires precisely Guided and Hacker")
    for key, payload in variants.items():
        if json.loads(payload) != _ecm_variant(key):
            raise ValueError(f"ECM source variant drift: {key[1]}")
    with closing(sqlite3.connect(previous)) as old, closing(sqlite3.connect(proposed)) as new:
        for pragma in ("user_version", "application_id"):
            if old.execute(f"PRAGMA {pragma}").fetchone() != new.execute(
                f"PRAGMA {pragma}"
            ).fetchone():
                raise ValueError("ECM refresh changed database identity")
        schema_sql = "SELECT type, name, sql FROM sqlite_master ORDER BY type, name"
        schema = old.execute(schema_sql).fetchall()
        if schema != new.execute(schema_sql).fetchall():
            raise ValueError("ECM refresh changed database schema")
        additions: dict[str, list[dict[str, Any]]] = {}
        for kind, name, _ in schema:
            if kind != "table":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [row[1] for row in old.execute(f"PRAGMA table_info({quoted})")]
            order = ",".join(str(index + 1) for index in range(len(columns)))
            query = f"SELECT * FROM {quoted} ORDER BY {order}"
            before = old.execute(query).fetchall()
            after = new.execute(query).fetchall()
            if name == "sqlite_stat1":
                # New definitions legitimately change optimizer estimates.
                index = columns.index("tbl")
                touched = {"records", "record_army_links", "record_citations",
                           "record_relations"}
                before = [row for row in before if row[index] not in touched]
                after = [row for row in after if row[index] not in touched]
            missing = Counter(before) - Counter(after)
            if missing:
                raise ValueError(f"ECM refresh changed existing rows: {name}")
            extra = Counter(after) - Counter(before)
            additions[name] = []
            for values, multiplicity in extra.items():
                entry = dict(zip(columns, values, strict=True))
                key = (entry.get("collection_id"),
                       entry.get("id") if name == "records" else entry.get("record_id"))
                if key not in ECM_SOURCES or name not in {
                    "records", "record_army_links", "record_citations",
                    "record_relations",
                }:
                    raise ValueError(f"ECM refresh added unrelated rows: {name}")
                additions[name].extend([entry] * multiplicity)
        added_records = additions["records"]
        if {(row["collection_id"], row["id"]) for row in added_records} != set(
            ECM_SOURCES
        ) or len(added_records) != 2:
            raise ValueError("ECM refresh must add exactly two definition records")
        for row in added_records:
            key = (row["collection_id"], row["id"])
            if (
                row["kind"] != "equipment"
                or row["name"] != ECM_SOURCES[key]["recordName"]
                or row["composition_role"] != "definition"
                or json.loads(row["variant_json"]) != _ecm_variant(key)
            ):
                raise ValueError("ECM refresh changed new definition identity")
        links = additions["record_army_links"]
        if len(links) != 2 or {
            (row["collection_id"], row["record_id"], row["entity"],
             row["external_id"])
            for row in links
        } != {
            (*key, "equipment", str(spec["sourceId"]))
            for key, spec in ECM_SOURCES.items()
        }:
            raise ValueError("ECM refresh changed exact source links")
        citations = additions["record_citations"]
        relations = additions["record_relations"]
        if (
            { (row["collection_id"], row["record_id"]) for row in citations }
            != set(ECM_SOURCES)
            or {(row["collection_id"], row["record_id"]) for row in relations}
            != set(ECM_SOURCES)
            or any(row["related_record_id"] != "equipment:ecm"
                   or row["relation_type"] != "variant-of" for row in relations)
            or len(relations) != 2
        ):
            raise ValueError("ECM refresh changed source citations or family relations")


TRINITY_ACCESS_SINGLE_IDS = {
    100: (290, 378, 339, 352),
    101: (378, 339),
}
TRINITY_ACCESS_SIGNATURES = {
    100: ((290, 3), (378, 1), (339, 2), (352, 4)),
    101: ((378, 3), (339, 2)),
}


def _with_exact_trinity_access(
    previous: dict[str, Any], source_id: int,
) -> dict[str, Any]:
    """Add one access flag per reviewed Trinity variant; retain all other data."""
    if (
        set(previous) != {"inheritance", "occurrenceParameters", "occurrenceCombinations"}
        or previous["inheritance"] != "family"
        or len(previous["occurrenceParameters"]) != 1
    ):
        raise ValueError("Trinity access requires existing reviewed device metadata")
    result = json.loads(json.dumps(previous))
    entries = result["occurrenceParameters"][0]["extraValues"]
    selected = [
        entry for entry in entries if entry.get("extraId") in TRINITY_ACCESS_SINGLE_IDS[source_id]
    ]
    if (
        len(selected) != len(TRINITY_ACCESS_SINGLE_IDS[source_id])
        or {entry["extraId"] for entry in selected}
        != set(TRINITY_ACCESS_SINGLE_IDS[source_id])
    ):
        raise ValueError("Trinity access requires exact single extra identities")
    for entry in selected:
        effect = entry["effect"]
        if effect.get("program") != "hacking-program:trinity" or "grantsProgram" in effect:
            raise ValueError("Trinity access requires previously ungranted Trinity modifiers")
        effect["grantsProgram"] = True
    combinations = result["occurrenceCombinations"]
    selected_combinations = [
        combination for combination in combinations
        if any(entry["extraId"] == 343 for entry in combination["extras"])
    ]
    if len(selected_combinations) != 1:
        raise ValueError("Trinity access requires one approved exact compound signature")
    combination = selected_combinations[0]
    if (
        sum(entry["extraId"] == 343 for entry in combination["extras"]) != 1
        or len(combination["extras"]) != len(combination["effects"])
    ):
        raise ValueError("Trinity access compound identity changed")
    index = next(
        i for i, entry in enumerate(combination["extras"]) if entry["extraId"] == 343
    )
    effect = combination["effects"][index]
    if (
        effect != {
            "kind": "program-ps-replacement",
            "program": "hacking-program:trinity", "value": 5,
        }
    ):
        raise ValueError("Trinity access requires unmodified reviewed PS replacement")
    effect["grantsProgram"] = True
    return result


def _check_variant_semantics_delta(
    previous: Path, proposed: Path, variants: dict[tuple[str, str], str],
    *, initialize_movement_distance: bool = False, tinbot_firewall: bool = False,
    tinbot_other: bool = False, hacking_mods: bool = False,
    hacking_srs: bool = False, hacking_firewall: bool = False,
    hacking_combinations: bool = False, bangbomb: bool = False,
    medikit: bool = False, gizmokit: bool = False, deactivator: bool = False,
    evo_trinity: bool = False, hacking_trinity_access: bool = False,
    killer_hacking: bool = False, impersonation: bool = False,
    gizmokit_target_ph: bool = False, medikit_target_ph: bool = False,
    remdriver: bool = False, bangbomb_skill: bool = False,
    tagcom: bool = False, ft_master: bool = False,
    decoy: bool = False, vulnerability: bool = False,
    hacker_skill: bool = False, chart_rerolls: bool = False,
    regeneration: bool = False,
) -> None:
    """Guard exact parameter additions; preserve other records and source identity."""
    initial = INITIAL_MOVEMENT_DISTANCE if initialize_movement_distance else {}
    if regeneration and (
        initial or bangbomb or bangbomb_skill or medikit or gizmokit
        or deactivator or gizmokit_target_ph or medikit_target_ph
        or remdriver or ft_master or tagcom or decoy or vulnerability
        or hacker_skill or chart_rerolls or evo_trinity or killer_hacking
        or impersonation or tinbot_firewall or tinbot_other
        or hacking_mods or hacking_srs or hacking_firewall
        or hacking_combinations or hacking_trinity_access
        or set(variants) != {REGENERATION}
    ):
        raise ValueError("Regeneration refresh requires exactly Skill source 62")
    if chart_rerolls and (
        initial or bangbomb or bangbomb_skill or medikit or gizmokit
        or deactivator or gizmokit_target_ph or medikit_target_ph
        or remdriver or ft_master or tagcom or decoy or vulnerability
        or hacker_skill or evo_trinity or killer_hacking or impersonation
        or tinbot_firewall or tinbot_other or hacking_mods or hacking_srs
        or hacking_firewall or hacking_combinations or hacking_trinity_access
        or set(variants) != set(CHART_REROLLS)
    ):
        raise ValueError("Chart ReRoll refresh requires only both Skill records")
    if hacker_skill and (
        initial or bangbomb or bangbomb_skill or medikit or gizmokit
        or deactivator or gizmokit_target_ph or medikit_target_ph
        or remdriver or ft_master or tagcom or decoy or vulnerability
        or evo_trinity or killer_hacking or impersonation
        or tinbot_firewall or tinbot_other or hacking_mods or hacking_srs
        or hacking_firewall or hacking_combinations or hacking_trinity_access
        or set(variants) != {HACKER_SKILL}
    ):
        raise ValueError("Hacker Skill refresh requires only source 1000")
    if vulnerability and (
        initial or bangbomb or bangbomb_skill or medikit or gizmokit
        or deactivator or gizmokit_target_ph or medikit_target_ph or remdriver
        or ft_master or tagcom or decoy or evo_trinity or killer_hacking
        or impersonation or tinbot_firewall or tinbot_other
        or hacking_mods or hacking_srs or hacking_firewall
        or hacking_combinations or hacking_trinity_access
        or set(variants) != {VULNERABILITY}
    ):
        raise ValueError("Vulnerability refresh requires only Skill source 220")
    if decoy and (
        initial or bangbomb or bangbomb_skill or medikit or gizmokit
        or deactivator or gizmokit_target_ph or medikit_target_ph
        or remdriver or ft_master or tagcom or evo_trinity
        or killer_hacking or impersonation or tinbot_firewall or tinbot_other
        or hacking_mods or hacking_srs or hacking_firewall
        or hacking_combinations or hacking_trinity_access
        or set(variants) != {DECOY}
    ):
        raise ValueError("Decoy refresh requires exactly Skill source 215")
    if ft_master and (
        initial or bangbomb or bangbomb_skill or medikit or gizmokit
        or deactivator or gizmokit_target_ph or medikit_target_ph or remdriver
        or evo_trinity or killer_hacking or impersonation or tagcom
        or tinbot_firewall or tinbot_other or hacking_mods or hacking_srs
        or hacking_firewall or hacking_combinations or hacking_trinity_access
        or set(variants) != {FT_MASTER}
    ):
        raise ValueError("FT Master refresh requires exactly Skill source 261")
    if tagcom and (
        initial or bangbomb or bangbomb_skill or medikit or gizmokit
        or deactivator or gizmokit_target_ph or medikit_target_ph or remdriver
        or evo_trinity or killer_hacking or impersonation
        or tinbot_firewall or tinbot_other or hacking_mods or hacking_srs
        or hacking_firewall or hacking_combinations or hacking_trinity_access
        or set(variants) != {TAGCOM}
    ):
        raise ValueError("TAGCom refresh requires exactly Skill source 270")
    if bangbomb_skill and (
        initial or bangbomb or medikit or gizmokit or deactivator
        or gizmokit_target_ph or medikit_target_ph or remdriver
        or evo_trinity or killer_hacking or impersonation
        or tinbot_firewall or tinbot_other or hacking_mods or hacking_srs
        or hacking_firewall or hacking_combinations or hacking_trinity_access
        or set(variants) != {BANGBOMB}
    ):
        raise ValueError("Bangbomb Skill mapping requires exactly its Equipment record")
    if medikit_target_ph and (
        initial or medikit or gizmokit or gizmokit_target_ph or deactivator
        or bangbomb or evo_trinity or killer_hacking or impersonation
        or remdriver or tinbot_firewall or tinbot_other or hacking_mods
        or hacking_srs or hacking_firewall or hacking_combinations
        or hacking_trinity_access or set(variants) != {MEDIKIT}
    ):
        raise ValueError("MediKit target PH requires exactly its Equipment record")
    if remdriver and (
        initial or medikit or gizmokit or gizmokit_target_ph or deactivator
        or bangbomb or evo_trinity or killer_hacking or impersonation
        or tinbot_firewall or tinbot_other or hacking_mods or hacking_srs
        or hacking_firewall or hacking_combinations or hacking_trinity_access
        or set(variants) != {REMDRIVER}
    ):
        raise ValueError("RemDriver refresh requires exactly Skill source 255")
    if gizmokit_target_ph and (
        initial or gizmokit or medikit or deactivator or bangbomb
        or evo_trinity or killer_hacking or impersonation or tinbot_firewall
        or tinbot_other or hacking_mods or hacking_srs or hacking_firewall
        or hacking_combinations or hacking_trinity_access
        or set(variants) != {GIZMOKIT}
    ):
        raise ValueError("GizmoKit target PH requires exactly its Equipment record")
    if impersonation and (
        initial or killer_hacking or medikit or gizmokit or deactivator or bangbomb
        or evo_trinity or tinbot_firewall or tinbot_other or hacking_mods
        or hacking_srs or hacking_firewall or hacking_combinations
        or hacking_trinity_access or set(variants) != {IMPERSONATION}
    ):
        raise ValueError("Impersonation refresh requires exactly Skill source 249")
    if killer_hacking and (
        initial or medikit or gizmokit or deactivator or bangbomb or evo_trinity
        or tinbot_firewall or tinbot_other or hacking_mods or hacking_srs
        or hacking_firewall or hacking_combinations or hacking_trinity_access
        or set(variants) != {KILLER_HACKING_DEVICE}
    ):
        raise ValueError("Killer Hacking refresh requires exactly its Equipment record")
    if evo_trinity and (
        initial or medikit or gizmokit or bangbomb or deactivator
        or tinbot_firewall or tinbot_other
        or hacking_mods or hacking_srs or hacking_firewall or hacking_combinations
        or set(variants) != {EVO_HACKING_DEVICE}
    ):
        raise ValueError("EVO Trinity refresh requires exactly its Equipment record")
    if medikit and (
        initial or gizmokit or bangbomb or deactivator
        or tinbot_firewall or tinbot_other or hacking_mods
        or hacking_srs or hacking_firewall or hacking_combinations or evo_trinity
        or set(variants) != {MEDIKIT}
    ):
        raise ValueError("MediKit refresh requires exactly its Equipment record")
    if gizmokit and (
        initial or medikit or bangbomb or deactivator
        or tinbot_firewall or tinbot_other or hacking_mods
        or hacking_srs or hacking_firewall or hacking_combinations or evo_trinity
        or hacking_trinity_access or set(variants) != {GIZMOKIT}
    ):
        raise ValueError("GizmoKit refresh requires exactly its Equipment record")
    if deactivator and (
        initial or medikit or gizmokit or bangbomb or tinbot_firewall or tinbot_other
        or hacking_mods or hacking_srs or hacking_firewall or hacking_combinations
        or evo_trinity or hacking_trinity_access or set(variants) != {DEACTIVATOR}
    ):
        raise ValueError("Deactivator refresh requires exactly its Equipment record")
    if bangbomb and (
        initial or deactivator or tinbot_firewall or tinbot_other or hacking_mods
        or hacking_srs or hacking_firewall or hacking_combinations or medikit
        or set(variants) != {BANGBOMB}
    ):
        raise ValueError("Bangbomb refresh requires exactly its Equipment record")
    if initial and set(variants) != set(initial):
        raise ValueError("Movement distance refresh requires exactly Jump and Climb")
    if tinbot_firewall and (initial or tinbot_other or set(variants) != {TINBOT_FIREWALL}):
        raise ValueError("TinBot refresh requires its exact source record")
    if tinbot_other and (initial or set(variants) != set(TINBOT_OTHER_SOURCES)):
        raise ValueError("TinBot additional variants require exactly Discover and ECM Guided")
    hacking_keys = {
        ("n5-core-v5.3", source["record"]): source_id
        for source_id, source in HACKING_GRANT_SOURCES.items()
    }
    if (hacking_mods or hacking_srs) and (
        initial or tinbot_other or tinbot_firewall or hacking_firewall
        or hacking_mods == hacking_srs or set(variants) != set(hacking_keys)
    ):
        raise ValueError("Hacking modifiers require precisely the two device records")
    firewall_key = ("n5-core-v5.3", "equipment:hacking-device")
    if hacking_firewall and (
        initial or tinbot_other or tinbot_firewall or hacking_mods or hacking_srs
        or hacking_combinations or set(variants) != {firewall_key}
    ):
        raise ValueError("Hacking Firewall refresh requires its exact source record")
    if hacking_combinations and (
        initial or tinbot_other or tinbot_firewall or hacking_mods or hacking_srs
        or hacking_firewall or hacking_trinity_access
        or set(variants) != set(hacking_keys)
    ):
        raise ValueError("Hacking combinations require exactly the two device records")
    if hacking_trinity_access and (
        initial or tinbot_other or tinbot_firewall or hacking_mods or hacking_srs
        or hacking_firewall or hacking_combinations or evo_trinity
        or medikit or gizmokit or bangbomb or deactivator
        or set(variants) != set(hacking_keys)
    ):
        raise ValueError("Trinity access requires precisely two Hacking Device records")
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
                    elif key == REGENERATION:
                        if not regeneration:
                            raise ValueError("Regeneration requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != REGENERATION_VARIANT
                            or any(
                                type(item["extraId"]) is not int
                                or type(item["effect"]["value"]) is not int
                                for item in after["occurrenceParameters"][0]["extraValues"]
                            )
                        ):
                            raise ValueError("Regeneration changed source-only semantics")
                    elif key in CHART_REROLLS:
                        if not chart_rerolls:
                            raise ValueError("Chart ReRoll requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != CHART_REROLLS[key]
                            or type(after["occurrenceParameters"][0][
                                "extraValues"][0]["extraId"]) is not int
                        ):
                            raise ValueError("Chart ReRoll changed source-only semantics")
                    elif key == HACKER_SKILL:
                        if not hacker_skill:
                            raise ValueError("Hacker Skill requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != HACKER_SOURCE_VARIANT
                            or any(
                                type(item["extraId"]) is not int
                                for item in after["occurrenceParameters"][0]["extraValues"]
                            )
                            or any(
                                type(item["extraId"]) is not int
                                for combo in after["occurrenceCombinations"]
                                for item in combo["extras"]
                            )
                            or type(after["occurrenceParameters"][0]["extraValues"][1][
                                "effect"]["modifier"]) is not int
                            or type(after["occurrenceParameters"][0]["extraValues"][1][
                                "effect"]["grantsProgram"]) is not bool
                            or type(after["occurrenceParameters"][0]["extraValues"][2][
                                "effect"]["attackerWipMod"]) is not int
                            or type(after["occurrenceParameters"][0]["extraValues"][2][
                                "effect"]["defenderSavingRollMod"]) is not int
                        ):
                            raise ValueError("Hacker Skill refresh changed source-only semantics")
                    elif key == VULNERABILITY:
                        if not vulnerability:
                            raise ValueError("Vulnerability requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != VULNERABILITY_VIRAL_VARIANT
                            or any(
                                type(item["extraId"]) is not int
                                for item in after["occurrenceParameters"][0]["extraValues"]
                            )
                        ):
                            raise ValueError("Vulnerability refresh changed source-only semantics")
                    elif key == DECOY:
                        if not decoy:
                            raise ValueError("Decoy requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != DECOY_VARIANT
                            or any(
                                type(entry["extraId"]) is not int
                                or type(entry["effect"]["count"]) is not int
                                for entry in after["occurrenceParameters"][0]["extraValues"]
                            )
                        ):
                            raise ValueError("Decoy refresh changed source-only semantics")
                    elif key == FT_MASTER:
                        if not ft_master:
                            raise ValueError("FT Master requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != FT_MASTER_VARIANT
                        ):
                            raise ValueError("FT Master refresh changed source-only semantics")
                    elif key == TAGCOM:
                        if not tagcom:
                            raise ValueError("TAGCom requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != TAGCOM_VARIANT
                        ):
                            raise ValueError("TAGCom refresh changed source-only semantics")
                    elif key == REMDRIVER:
                        if not remdriver:
                            raise ValueError("RemDriver requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != REMDRIVER_VARIANT
                        ):
                            raise ValueError("RemDriver refresh changed source-only semantics")
                    elif key == IMPERSONATION:
                        if not impersonation:
                            raise ValueError("Impersonation requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != IMPERSONATION_VARIANT
                        ):
                            raise ValueError("Impersonation refresh changed source-only semantics")
                    elif key == KILLER_HACKING_DEVICE:
                        if not killer_hacking:
                            raise ValueError("Killer Hacking requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != KILLER_HACKING_VARIANT
                        ):
                            raise ValueError("Killer Hacking refresh changed source-only semantics")
                    elif key == EVO_HACKING_DEVICE:
                        if not evo_trinity:
                            raise ValueError("EVO Trinity requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != EVO_TRINITY_VARIANT
                        ):
                            raise ValueError("EVO Trinity refresh changed source-only semantics")
                    elif key == MEDIKIT and medikit_target_ph:
                        if (
                            row[index] is None
                            or json.loads(row[index]) != MEDIKIT_VARIANT
                            or after != MEDIKIT_TARGET_PH_VARIANT
                        ):
                            raise ValueError("MediKit target PH changed prior Equipment semantics")
                    elif key == MEDIKIT:
                        if not medikit:
                            raise ValueError("MediKit requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != MEDIKIT_VARIANT
                        ):
                            raise ValueError("MediKit refresh changed source-only semantics")
                    elif key == GIZMOKIT and gizmokit_target_ph:
                        if (
                            row[index] is None
                            or json.loads(row[index]) != GIZMOKIT_VARIANT
                            or after != GIZMOKIT_TARGET_PH_VARIANT
                        ):
                            raise ValueError("GizmoKit target PH changed prior Equipment semantics")
                    elif key == GIZMOKIT:
                        if not gizmokit:
                            raise ValueError("GizmoKit requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != GIZMOKIT_VARIANT
                        ):
                            raise ValueError("GizmoKit refresh changed source-only semantics")
                    elif key == DEACTIVATOR:
                        if not deactivator:
                            raise ValueError("Deactivator requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != DEACTIVATOR_VARIANT
                        ):
                            raise ValueError("Deactivator refresh changed source-only semantics")
                    elif key == BANGBOMB and bangbomb_skill:
                        if (
                            row[index] is None
                            or json.loads(row[index]) != BANGBOMB_VARIANT
                            or after != BANGBOMB_SKILL_VARIANT
                        ):
                            raise ValueError("Bangbomb Skill mapping changed prior Equipment scope")
                    elif key == BANGBOMB:
                        if not bangbomb:
                            raise ValueError("Bangbomb requires source-verified refresh")
                        if (
                            row[index] is None
                            or json.loads(row[index]) != {"inheritance": "family"}
                            or after != BANGBOMB_VARIANT
                        ):
                            raise ValueError("Bangbomb refresh changed source-only semantics")
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
                    elif hacking_trinity_access and key in hacking_keys:
                        if row[index] is None:
                            raise ValueError("Trinity access requires existing metadata")
                        previous_variant = json.loads(row[index])
                        expected = _with_exact_trinity_access(
                            previous_variant, hacking_keys[key],
                        )
                        if after != expected:
                            raise ValueError(
                                "Trinity access must preserve all prior reviewed effects"
                            )
                    elif hacking_combinations and key in hacking_keys:
                        if row[index] is None:
                            raise ValueError("Hacking combinations require existing variants")
                        before = json.loads(row[index])
                        expected = json.loads(json.dumps(before))
                        if (
                            before.get("inheritance") != "family"
                            or set(before) != {"inheritance", "occurrenceParameters"}
                            or len(before["occurrenceParameters"]) != 1
                        ):
                            raise ValueError(
                                "Hacking combinations require existing reviewed extras"
                            )
                        device = key[1].removeprefix("equipment:")
                        expected["occurrenceCombinations"] = reviewed_hacking_combinations(device)
                        if after != expected:
                            raise ValueError(
                                "Hacking combinations changed earlier reviewed semantics"
                            )
                    elif (hacking_mods or hacking_srs or hacking_firewall) and (
                        key in hacking_keys if not hacking_firewall else key == firewall_key
                    ):
                        if row[index] is None:
                            raise ValueError("Hacking modifier refresh requires existing grants")
                        before = json.loads(row[index])
                        source_id = hacking_keys[key]
                        if (
                            before.get("inheritance") != "family"
                            or set(before) != {"inheritance", "occurrenceParameters"}
                            or len(before["occurrenceParameters"]) != 1
                            or len(after.get("occurrenceParameters", [])) != 1
                        ):
                            raise ValueError(
                                "Hacking modifiers require existing single family parameter"
                            )
                        prior = before["occurrenceParameters"][0]
                        proposed_param = after["occurrenceParameters"][0]
                        expected = (
                            _hacking_mod_values(source_id) if hacking_mods
                            else _hacking_sr_values(source_id) if hacking_srs
                            else _hacking_firewall_values(source_id)
                        )
                        if hacking_srs and (
                            prior.get("extraValues", [])[
                                -len(HACKING_MOD_SOURCES[source_id]):
                            ] != _hacking_mod_values(source_id)
                        ):
                            raise ValueError(
                                "Saving Roll refresh changed previous program modifiers"
                            )
                        if hacking_firewall and (
                            prior.get("extraValues", [])[
                                -len(HACKING_SR_SOURCES[source_id]):
                            ] != _hacking_sr_values(source_id)
                        ):
                            raise ValueError("Firewall refresh changed previous SR modifiers")
                        if (
                            prior.get("kind") != "reviewed-extra"
                            or prior.get("source") != "army-extra"
                            or set(prior) != {"source", "kind", "extraValues"}
                            or set(proposed_param) != set(prior)
                            or proposed_param["source"] != prior["source"]
                            or proposed_param["kind"] != prior["kind"]
                            or proposed_param["extraValues"] != prior["extraValues"] + expected
                        ):
                            raise ValueError(
                                "Hacking modifiers must append only exact reviewed values"
                            )
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


def refresh_ecm_source_variants_v9_release(*, root: Path = ROOT) -> Path:
    """Promote the two exact source-specific ECM definitions as a matched pair."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {row["id"]: row for row in report["catalogs"]["equipment"]["items"]}
    for spec in ECM_SOURCES.values():
        source_id = spec["sourceId"]
        row = items.get(source_id)
        if (
            row is None or row["name"] != spec["name"]
            or row["applicationId"] != 239 or row["occurrences"] != spec["count"]
            or row["status"] != "unresolved-occurrence-parameter"
            or row["reviewedExtra"] is not None
            or row["reviewedVariant"] is not None
            or row["reviewedCombinations"] is not None
            or row["rawValues"]
            or row["extraSignatures"] != [
                {
                    "extras": [[extra_id, "TEXT", str(modifier)]],
                    "reviewed": False, "count": count,
                }
                for extra_id, modifier, count in spec["signatures"]
            ]
        ):
            raise ValueError(f"ECM source signature drift: {source_id}")
    return _refresh_metadata_v9_release(
        root=root,
        variant_records={key[1] for key in ECM_SOURCES},
        ecm_sources=True,
    )


def refresh_evo_trinity_v9_release(*, root: Path = ROOT) -> Path:
    """Promote the exact EVO Trinity grant with its SR-2 modifier."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    matches = [
        row for row in report["catalogs"]["equipment"]["items"]
        if row["id"] == 182
    ]
    if (
        len(matches) != 1
        or matches[0]["name"] != "EVO Hacking Device"
        or matches[0]["applicationId"] != 182
        or matches[0]["occurrences"] != 40
        or matches[0]["status"] != "unresolved-occurrence-parameter"
        or matches[0]["reviewedVariant"] is not None
        or matches[0]["reviewedExtra"] is not None
        or matches[0]["reviewedCombinations"] is not None
        or matches[0]["rawValues"]
        or matches[0]["extraSignatures"] != [{
            "extras": [[352, "TEXT", "UPGRADE: Trinity (SR-2)"]],
            "reviewed": False, "count": 2,
        }]
    ):
        raise ValueError("EVO Trinity source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={EVO_HACKING_DEVICE[1]}, evo_trinity=True,
    )


def refresh_medikit_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only the exact +1 Burst modifier for ranged MediKit use."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    matches = [
        row for row in report["catalogs"]["equipment"]["items"]
        if row["id"] == 106
    ]
    if (
        len(matches) != 1
        or matches[0]["name"] != "MediKit"
        or matches[0]["applicationId"] != 106
        or matches[0]["occurrences"] != 573
        or matches[0]["status"] != "unresolved-occurrence-parameter"
        or matches[0]["reviewedVariant"] is not None
        or matches[0]["reviewedExtra"] is not None
        or matches[0]["reviewedCombinations"] is not None
        or matches[0]["rawValues"]
        or matches[0]["extraSignatures"] != [{
            "extras": [[8, "TEXT", "+1B"]],
            "reviewed": False, "count": 38,
        }]
    ):
        raise ValueError("MediKit source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={MEDIKIT[1]}, medikit=True,
    )


def refresh_gizmokit_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only exact +1 Burst modifier for ranged GizmoKit use."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["equipment"]["items"]
        if row["id"] == 237
    ]
    if (
        len(rows) != 1
        or rows[0]["name"] != "GizmoKit"
        or rows[0]["applicationId"] != 237
        or rows[0]["occurrences"] != 544
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [{
            "extras": [[8, "TEXT", "+1B"]], "reviewed": False, "count": 16,
        }]
    ):
        raise ValueError("GizmoKit source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={GIZMOKIT[1]}, gizmokit=True,
    )


def refresh_regeneration_v9_release(*, root: Path = ROOT) -> Path:
    """Promote exact Regeneration States Phase PH replacements from source 62."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [item for item in report["catalogs"]["skills"]["items"]
            if item["id"] == 62]
    signatures = [
        {"extras": [[extra_id, "TEXT", f"PH={value}"]],
         "reviewed": False, "count": count}
        for extra_id, value, count in ((52, 13, 3), (244, 14, 3),
                                       (250, 12, 2), (353, 15, 8))
    ]
    if (
        len(rows) != 1 or rows[0]["name"] != "Regeneration"
        or rows[0]["applicationId"] != 62 or rows[0]["occurrences"] != 82
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"] or rows[0]["extraSignatures"] != signatures
    ):
        raise ValueError("Regeneration source-62 signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={REGENERATION[1]}, regeneration=True,
    )


def refresh_chart_rerolls_v9_release(*, root: Path = ROOT) -> Path:
    """Promote exactly Booty and MetaChemistry deployment chart ReRolls."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {
        row["id"]: row for row in report["catalogs"]["skills"]["items"]
        if row["id"] in (25, 55)
    }
    for source_id, name, occurrences, count in (
        (25, "Booty", 482, 108),
        (55, "MetaChemistry", 117, 60),
    ):
        row = items.get(source_id)
        if (
            row is None or row["name"] != name
            or row["applicationId"] != source_id
            or row["occurrences"] != occurrences
            or row["status"] != "unresolved-occurrence-parameter"
            or row["reviewedVariant"] is not None
            or row["reviewedDistance"] is not None
            or row["reviewedNumericMod"] is not None
            or row["reviewedExtra"] is not None
            or row["reviewedCombinations"] is not None
            or row["rawValues"]
            or row["extraSignatures"] != [{
                "extras": [[277, "TEXT", "ReRoll"]],
                "reviewed": False, "count": count,
            }]
        ):
            raise ValueError(f"Chart ReRoll source-{source_id} signature drift")
    return _refresh_metadata_v9_release(
        root=root,
        variant_records={key[1] for key in CHART_REROLLS},
        chart_rerolls=True,
    )


def refresh_hacker_skill_v9_release(*, root: Path = ROOT) -> Path:
    """Promote direct Hacker assignments without granting Device programs."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["skills"]["items"] if row["id"] == 1000
    ]
    expected = [
        {"extras": [[265, "TEXT", "Zero Pain"]], "reviewed": False, "count": 4},
        {"extras": [[314, "TEXT", "UPGRADE: Total Control (SR-2)"]],
         "reviewed": False, "count": 3},
        {"extras": [[334, "TEXT", "UPGRADE: Firewall (-3)"]],
         "reviewed": False, "count": 2},
        {"extras": [[386, "TEXT", "Carbonite"], [387, "TEXT", "Spotlight"]],
         "reviewed": False, "count": 12},
    ]
    if (
        len(rows) != 1 or rows[0]["name"] != "Hacker"
        or rows[0]["applicationId"] != 1000
        or rows[0]["occurrences"] != 1094
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"] or rows[0]["extraSignatures"] != expected
    ):
        raise ValueError("Hacker Skill source-1000 signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={HACKER_SKILL[1]}, hacker_skill=True,
    )


def refresh_vulnerability_viral_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only the name-scoped Viral Immunity restriction from source 220."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [item for item in report["catalogs"]["skills"]["items"]
            if item["id"] == 220]
    if (
        len(rows) != 1 or rows[0]["name"] != "Vulnerability"
        or rows[0]["applicationId"] != 220
        or rows[0]["occurrences"] != 2
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [{
            "extras": [[39, "TEXT", "Viral"]],
            "reviewed": False, "count": 2,
        }]
    ):
        raise ValueError("Vulnerability source-220 signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={VULNERABILITY[1]}, vulnerability=True,
    )


def refresh_decoy_v9_release(*, root: Path = ROOT) -> Path:
    """Certify only the exact Decoy (1)/(2) additional replica counts."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["skills"]["items"] if row["id"] == 215
    ]
    expected = [
        {"extras": [[44, "TEXT", "1"]], "reviewed": False, "count": 132},
        {"extras": [[267, "TEXT", "2"]], "reviewed": False, "count": 24},
    ]
    if (
        len(rows) != 1 or rows[0]["name"] != "Decoy"
        or rows[0]["applicationId"] != 215
        or rows[0]["occurrences"] != 162
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"] or rows[0]["extraSignatures"] != expected
    ):
        raise ValueError("Decoy source-215 signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={DECOY[1]}, decoy=True,
    )


def refresh_ft_master_v9_release(*, root: Path = ROOT) -> Path:
    """Promote exact FT Master listed-Unit cancellation triggers only."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [row for row in report["catalogs"]["skills"]["items"]
            if row["id"] == 261]
    signatures = [
        {
            "extras": [[extra_id, "TEXT", raw]], "reviewed": False,
            "count": count,
        }
        for (extra_id, raw, _names), count in zip(
            FT_MASTER_UNIT_SIGNATURES, (2, 47, 1, 2, 2, 2, 2, 1),
            strict=True,
        )
    ]
    if (
        len(rows) != 1 or rows[0]["name"] != "FT Master"
        or rows[0]["applicationId"] != 261
        or rows[0]["occurrences"] != 61
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"] or rows[0]["extraSignatures"] != signatures
    ):
        raise ValueError("FT Master source-261 signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={FT_MASTER[1]}, ft_master=True,
    )


def refresh_tagcom_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only three complete TAGCom profile-signature encodings."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["skills"]["items"] if row["id"] == 270
    ]
    expected = [
        {"extras": [[312, "TEXT", "Dodge (PH+3)"],
                    [313, "TEXT", "GizmoKit (PH+1)"]],
         "reviewed": False, "count": 2},
        {"extras": [[369, "TEXT", "Dodge (PH+3), GizmoKit (PH+1)"]],
         "reviewed": False, "count": 24},
        {"extras": [[370, "TEXT", "Dodge (PH+1), GizmoKit (PH+1)"]],
         "reviewed": False, "count": 2},
    ]
    if (
        len(rows) != 1 or rows[0]["name"] != "TAGCom"
        or rows[0]["applicationId"] != 270
        or rows[0]["occurrences"] != 28
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != expected
    ):
        raise ValueError("TAGCom source-270 signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={TAGCOM[1]}, tagcom=True,
    )


def refresh_remdriver_v9_release(*, root: Path = ROOT) -> Path:
    """Promote three complete ordered RemDriver recipient attribute signatures."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["skills"]["items"] if row["id"] == 255
    ]
    expected = [
        {"extras": [[271, "TEXT", "+1 BS"], [300, "TEXT", "+5 CC"]],
         "reviewed": False, "count": 3},
        {"extras": [[280, "TEXT", "CC=15"], [281, "TEXT", "BS=13"],
                    [282, "TEXT", "WIP=14"]],
         "reviewed": False, "count": 5},
        {"extras": [[281, "TEXT", "BS=13"], [52, "TEXT", "PH=13"],
                    [384, "TEXT", "BTS=6"]],
         "reviewed": False, "count": 4},
    ]
    if (
        len(rows) != 1 or rows[0]["name"] != "RemDriver"
        or rows[0]["applicationId"] != 255
        or rows[0]["occurrences"] != 12
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"] or rows[0]["extraSignatures"] != expected
    ):
        raise ValueError("RemDriver source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={REMDRIVER[1]}, remdriver=True,
    )


def refresh_bangbomb_skill_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only the existing restricted Dodge scope for Skill-listed Bangbomb."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["skills"]["items"] if row["id"] == 266
    ]
    if (
        len(rows) != 1
        or rows[0]["name"] != "Bangbomb"
        or rows[0]["applicationId"] != 266
        or rows[0]["occurrences"] != 4
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [{
            "extras": [[310, "TEXT", "+4"]], "reviewed": False, "count": 4,
        }]
    ):
        raise ValueError("Bangbomb Skill source-266 signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={BANGBOMB[1]}, bangbomb_skill=True,
    )


def refresh_medikit_target_ph_v9_release(*, root: Path = ROOT) -> Path:
    """Promote exact target-side MediKit PH replacements from Skill source 273."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["skills"]["items"] if row["id"] == 273
    ]
    signatures = (
        (52, "PH=13", 2),
        (244, "PH=14", 12),
        (250, "PH=12", 1),
        (340, "PH=16", 4),
        (353, "PH=15", 6),
        (382, "PH=17", 6),
    )
    if (
        len(rows) != 1
        or rows[0]["name"] != "MediKit"
        or rows[0]["applicationId"] != 273
        or rows[0]["occurrences"] != 31
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [
            {"extras": [[extra_id, "TEXT", raw]], "reviewed": False, "count": count}
            for extra_id, raw, count in signatures
        ]
    ):
        raise ValueError("MediKit target PH source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={MEDIKIT[1]}, medikit_target_ph=True,
    )


def refresh_gizmokit_target_ph_v9_release(*, root: Path = ROOT) -> Path:
    """Promote exact target-side PH replacements without inventing a Skill rule."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["skills"]["items"] if row["id"] == 254
    ]
    signatures = (
        (27, "PH=11", 131),
        (32, "PH=10", 53),
        (46, "PH=9", 57),
        (52, "PH=13", 33),
        (244, "PH=14", 4),
        (250, "PH=12", 10),
    )
    if (
        len(rows) != 1
        or rows[0]["name"] != "Gizmokit"
        or rows[0]["applicationId"] != 254
        or rows[0]["occurrences"] != 288
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [
            {"extras": [[extra_id, "TEXT", raw]], "reviewed": False, "count": count}
            for extra_id, raw, count in signatures
        ]
    ):
        raise ValueError("GizmoKit target PH source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={GIZMOKIT[1]}, gizmokit_target_ph=True,
    )


def refresh_impersonation_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only the exact Impersonation IMP-2 deployment/activation variant."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["skills"]["items"]
        if row["id"] == 249
    ]
    if (
        len(rows) != 1
        or rows[0]["name"] != "Impersonation"
        or rows[0]["applicationId"] != 249
        or rows[0]["occurrences"] != 14
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedDistance"] is not None
        or rows[0]["reviewedNumericMod"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [{
            "extras": [[268, "TEXT", "IMP-2"]],
            "reviewed": False, "count": 9,
        }]
    ):
        raise ValueError("Impersonation source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={IMPERSONATION[1]}, impersonation=True,
    )


def refresh_killer_hacking_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only the ten exact standalone KHD Army source signatures."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["equipment"]["items"]
        if row["id"] == 145
    ]
    signatures = (
        (13, "UPGRADE: Carbonite", 10),
        (14, "UPGRADE: Spotlight", 6),
        (20, "UPGRADE:\u00a0White Noise", 1),
        (21, "UPGRADE: Oblivion", 2),
        (270, "UPGRADE: Trinity (AP)", 2),
        (286, "UPGRADE: Trinity (-3)", 4),
        (334, "UPGRADE: Firewall (-3)", 14),
        (335, "UPGRADES: Carbonite, Firewall (-3)", 4),
        (339, "UPGRADE: Trinity (SR-1)", 1),
        (343, "UPGRADE: Trinity (PS=5)", 1),
    )
    if (
        len(rows) != 1
        or rows[0]["name"] != "Killer Hacking Device"
        or rows[0]["applicationId"] != 145
        or rows[0]["occurrences"] != 229
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [
            {"extras": [[extra_id, "TEXT", raw]], "reviewed": False, "count": count}
            for extra_id, raw, count in signatures
        ]
    ):
        raise ValueError("Killer Hacking source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={KILLER_HACKING_DEVICE[1]}, killer_hacking=True,
    )


def refresh_deactivator_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only two pinned standalone Deactivator WIP attack extras."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["equipment"]["items"]
        if row["id"] == 238
    ]
    if (
        len(rows) != 1
        or rows[0]["name"] != "Deactivator"
        or rows[0]["applicationId"] != 238
        or rows[0]["occurrences"] != 416
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [
            {"extras": [[8, "TEXT", "+1B"]], "reviewed": False, "count": 1},
            {"extras": [[277, "TEXT", "ReRoll"]], "reviewed": False, "count": 9},
        ]
    ):
        raise ValueError("Deactivator source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={DEACTIVATOR[1]}, deactivator=True,
    )


def refresh_bangbomb_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only the N5.3 Dodge-specific Bangbomb +4 Army extra."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    rows = [
        row for row in report["catalogs"]["equipment"]["items"]
        if row["id"] == 246
    ]
    if (
        len(rows) != 1
        or rows[0]["name"] != "Bangbomb"
        or rows[0]["applicationId"] != 246
        or rows[0]["occurrences"] != 125
        or rows[0]["status"] != "unresolved-occurrence-parameter"
        or rows[0]["reviewedVariant"] is not None
        or rows[0]["reviewedExtra"] is not None
        or rows[0]["reviewedCombinations"] is not None
        or rows[0]["rawValues"]
        or rows[0]["extraSignatures"] != [{
            "extras": [[310, "TEXT", "+4"]],
            "reviewed": False, "count": 125,
        }]
    ):
        raise ValueError("Bangbomb source signature drift")
    return _refresh_metadata_v9_release(
        root=root, variant_records={BANGBOMB[1]}, bangbomb=True,
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


def refresh_hacking_program_grants_v9_release(*, root: Path = ROOT) -> Path:
    """Review unmodified program grants only, never a compound UPGRADE signature."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {row["id"]: row for row in report["catalogs"]["equipment"]["items"]}
    for source_id, expected in HACKING_GRANT_SOURCES.items():
        item = items.get(source_id)
        if (
            item is None
            or item["name"] != expected["name"]
            or item["applicationId"] != source_id
            or item["occurrences"] != expected["occurrences"]
            or item["status"] != "unresolved-occurrence-parameter"
            or item["reviewedExtra"] is not None
            or item["rawValues"]
        ):
            raise ValueError(f"Unreviewed Hacking Device source drift: {source_id}")
        signatures = item["extraSignatures"]
        singles = {
            parts[0][0]: (parts[0][2], sig["count"])
            for sig in signatures
            if len(parts := sig["extras"]) == 1 and parts[0][0] in expected["singles"]
            and parts[0][1] == "TEXT" and sig["reviewed"] is False
        }
        combined = [
            sig for sig in signatures
            if len(sig["extras"]) > 1
            and any(part[0] in expected["singles"] for part in sig["extras"])
        ]
        if singles != expected["singles"] or combined != expected["combined"]:
            raise ValueError(f"Hacking Device grant signature drift: {source_id}")
    return _refresh_metadata_v9_release(
        root=root,
        variant_records={source["record"] for source in HACKING_GRANT_SOURCES.values()},
    )


def refresh_hacking_program_mods_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only pinned single-extra B/PS/SD program changes."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {row["id"]: row for row in report["catalogs"]["equipment"]["items"]}
    for source_id, specs in HACKING_MOD_SOURCES.items():
        item = items.get(source_id)
        source = HACKING_GRANT_SOURCES[source_id]
        if (
            item is None
            or item["name"] != source["name"]
            or item["applicationId"] != source_id
            or item["occurrences"] != source["occurrences"]
            or item["status"] != "unresolved-occurrence-parameter"
            or item["reviewedVariant"] is not None
            or item["reviewedDistance"] is not None
            or item["reviewedNumericMod"] is not None
            or item["rawValues"]
        ):
            raise ValueError(f"Hacking modifier source drift: {source_id}")
        reviewed = item["reviewedExtra"]
        if not isinstance(reviewed, dict):
            raise ValueError(f"Missing reviewed Hacking grants: {source_id}")
        old_values = reviewed.get("extra_values")
        if (
            not isinstance(old_values, list)
            or [(row["extra_id"], row["raw_value"]) for row in old_values]
            != [(extra_id, raw) for extra_id, (raw, _count) in source["singles"].items()]
        ):
            raise ValueError(f"Reviewed Hacking grants changed: {source_id}")
        signatures = item["extraSignatures"]
        selected = [
            sig for sig in signatures if len(sig["extras"]) == 1
            and sig["extras"][0][0] in {spec[0] for spec in specs}
        ]
        expected = [
            {"extras": [[extra_id, "TEXT", raw]], "reviewed": False, "count": count}
            for extra_id, raw, _program, _kind, _field, _value, count in specs
        ]
        combined = [
            sig for sig in signatures if len(sig["extras"]) > 1
            and any(part[0] in {spec[0] for spec in specs} for part in sig["extras"])
        ]
        if sorted(selected, key=str) != sorted(expected, key=str) or combined:
            raise ValueError(f"Hacking modifier signatures changed: {source_id}")
    return _refresh_metadata_v9_release(
        root=root,
        variant_records={source["record"] for source in HACKING_GRANT_SOURCES.values()},
        hacking_mods=True,
    )


def refresh_hacking_saving_rolls_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only exact named-program SR modifiers, excluding unqualified SR."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {row["id"]: row for row in report["catalogs"]["equipment"]["items"]}
    for source_id, specs in HACKING_SR_SOURCES.items():
        item = items.get(source_id)
        source = HACKING_GRANT_SOURCES[source_id]
        if (
            item is None
            or item["name"] != source["name"]
            or item["applicationId"] != source_id
            or item["occurrences"] != source["occurrences"]
            or item["status"] != "unresolved-occurrence-parameter"
            or item["reviewedVariant"] is not None
            or item["rawValues"]
        ):
            raise ValueError(f"Hacking SR source drift: {source_id}")
        reviewed = item["reviewedExtra"]
        previous = [
            (extra_id, raw)
            for extra_id, (raw, _count) in source["singles"].items()
        ] + [
            (extra_id, raw)
            for extra_id, raw, _program, _kind, _field, _value, _count
            in HACKING_MOD_SOURCES[source_id]
        ]
        if (
            not isinstance(reviewed, dict)
            or not isinstance(reviewed.get("extra_values"), list)
            or [
                (entry.get("extra_id"), entry.get("raw_value"))
                for entry in reviewed["extra_values"]
            ] != previous
        ):
            raise ValueError(f"Previously reviewed Hacking extras changed: {source_id}")
        signatures = item["extraSignatures"]
        desired = [
            {"extras": [[extra_id, "TEXT", raw]], "reviewed": False, "count": count}
            for extra_id, raw, _program, _modifier, count in specs
        ]
        selected = [
            sig for sig in signatures if len(sig["extras"]) == 1
            and sig["extras"][0][0] in {entry[0] for entry in specs}
        ]
        compound = [
            sig for sig in signatures if len(sig["extras"]) > 1
            and any(part[0] in {entry[0] for entry in specs} for part in sig["extras"])
        ]
        if sorted(selected, key=str) != sorted(desired, key=str) or compound:
            raise ValueError(f"Hacking SR signatures changed: {source_id}")
    return _refresh_metadata_v9_release(
        root=root,
        variant_records={source["record"] for source in HACKING_GRANT_SOURCES.values()},
        hacking_srs=True,
    )


def refresh_hacking_firewall_v9_release(*, root: Path = ROOT) -> Path:
    """Promote exact device Firewall profiles, never TinBot or combined extras."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {row["id"]: row for row in report["catalogs"]["equipment"]["items"]}
    source_id = 100
    item = items.get(source_id)
    source = HACKING_GRANT_SOURCES[source_id]
    if (
        item is None
        or item["name"] != source["name"]
        or item["applicationId"] != source_id
        or item["occurrences"] != source["occurrences"]
        or item["status"] != "unresolved-occurrence-parameter"
        or item["reviewedVariant"] is not None
        or item["rawValues"]
    ):
        raise ValueError("Hacking Firewall source drift")
    reviewed = item["reviewedExtra"]
    previous = [
        (extra_id, raw)
        for extra_id, (raw, _count) in source["singles"].items()
    ] + [
        (extra_id, raw)
        for extra_id, raw, _program, _kind, _field, _value, _count
        in HACKING_MOD_SOURCES[source_id]
    ] + [
        (extra_id, raw)
        for extra_id, raw, _program, _modifier, _count
        in HACKING_SR_SOURCES[source_id]
    ]
    if (
        not isinstance(reviewed, dict)
        or not isinstance(reviewed.get("extra_values"), list)
        or [
            (entry.get("extra_id"), entry.get("raw_value"))
            for entry in reviewed["extra_values"]
        ] != previous
    ):
        raise ValueError("Previous reviewed Hacking extras changed")
    specs = HACKING_FIREWALL_SOURCES[source_id]
    ids = {extra_id for extra_id, _raw, _mod, _count in specs}
    signatures = item["extraSignatures"]
    selected = [
        sig for sig in signatures if len(sig["extras"]) == 1
        and sig["extras"][0][0] in ids
    ]
    desired = [
        {"extras": [[extra_id, "TEXT", raw]], "reviewed": False, "count": count}
        for extra_id, raw, _modifier, count in specs
    ]
    combined = [
        sig for sig in signatures if len(sig["extras"]) > 1
        and any(part[0] in ids for part in sig["extras"])
    ]
    if sorted(selected, key=str) != sorted(desired, key=str) or combined:
        raise ValueError("Hacking Firewall signatures changed")
    return _refresh_metadata_v9_release(
        root=root, variant_records={source["record"]}, hacking_firewall=True,
    )


def refresh_hacking_trinity_access_v9_release(*, root: Path = ROOT) -> Path:
    """Add Trinity access only to eight existing exact reviewed Upgrade signatures."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {row["id"]: row for row in report["catalogs"]["equipment"]["items"]}
    raw_names = {
        290: "UPGRADE: Trinity (+1B)",
        378: "UPGRADE: Trinity (+1SD)",
        339: "UPGRADE: Trinity (SR-1)",
        352: "UPGRADE: Trinity (SR-2)",
    }
    compound_ids = {
        100: [[373, "TEXT", "UPGRADE: Total Control (PS=3)"],
              [343, "TEXT", "UPGRADE: Trinity (PS=5)"]],
        101: [[343, "TEXT", "UPGRADE: Trinity (PS=5)"],
              [287, "TEXT", "UPGRADE: Zero Pain"]],
    }
    total_occurrences = 0
    for source_id, source in HACKING_GRANT_SOURCES.items():
        item = items.get(source_id)
        if (
            item is None or item["name"] != source["name"]
            or item["applicationId"] != source_id
            or item["occurrences"] != source["occurrences"]
            or item["status"] != (
                "reviewed-extra-parameter" if source_id == 100
                else "unresolved-occurrence-parameter"
            )
            or item["reviewedVariant"] is not None
            or item["reviewedExtra"] is None
            or item["reviewedCombinations"] is None
            or item["rawValues"]
        ):
            raise ValueError(f"Trinity source family drift: {source_id}")
        selected_ids = {extra_id for extra_id, _ in TRINITY_ACCESS_SIGNATURES[source_id]}
        signatures = [
            sig for sig in item["extraSignatures"]
            if any(part[0] in selected_ids | {343} for part in sig["extras"])
        ]
        expected = [
            {
                "extras": [[extra_id, "TEXT", raw_names[extra_id]]],
                "reviewed": True, "count": count,
            }
            for extra_id, count in TRINITY_ACCESS_SIGNATURES[source_id]
        ] + [{
            "extras": compound_ids[source_id], "reviewed": True, "count": 2,
        }]
        if sorted(signatures, key=str) != sorted(expected, key=str):
            raise ValueError(f"Trinity exact source signatures changed: {source_id}")
        total_occurrences += sum(count for _id, count in TRINITY_ACCESS_SIGNATURES[source_id])
        total_occurrences += 2
        if source_id == 101 and [
            sig for sig in item["extraSignatures"] if not sig["reviewed"]
        ] != [{
            "extras": [[344, "TEXT", "UPGRADE: SR-1"]],
            "reviewed": False, "count": 2,
        }]:
            raise ValueError("Unqualified Charontid SR source drift")
    if total_occurrences != 19:
        raise ValueError("Trinity grant audit expected 19 direct occurrences")
    return _refresh_metadata_v9_release(
        root=root,
        variant_records={source["record"] for source in HACKING_GRANT_SOURCES.values()},
        hacking_trinity_access=True,
    )


def refresh_hacking_combinations_v9_release(*, root: Path = ROOT) -> Path:
    """Promote only complete pinned compound signatures; leave bare SR-1 unresolved."""
    from tools.audit_source_variant_inputs import inventory_source_variants

    report = inventory_source_variants(
        root / ARMY, root / "data/generated/infinity.raw.db", root / RULES,
    )
    items = {row["id"]: row for row in report["catalogs"]["equipment"]["items"]}
    for source_id, source in HACKING_GRANT_SOURCES.items():
        item = items.get(source_id)
        if (
            item is None
            or item["name"] != source["name"]
            or item["applicationId"] != source_id
            or item["occurrences"] != source["occurrences"]
            or item["status"] != "unresolved-occurrence-parameter"
            or item["reviewedCombinations"] is not None
            or item["reviewedExtra"] is None
            or item["rawValues"]
        ):
            raise ValueError(f"Hacking compound source drift: {source_id}")
        expected = [
            {
                "extras": [[entry["extraId"], entry["extraType"], entry["rawValue"]]
                           for entry in combination["extras"]],
                "reviewed": False,
                "count": count,
            }
            for combination, count in zip(
                reviewed_hacking_combinations(
                    "hacking-device" if source_id == 100 else "hacking-device-plus"
                ),
                (1, 2) if source_id == 100 else (2,),
                strict=True,
            )
        ]
        if source_id == 101:
            expected.append({
                "extras": [[344, "TEXT", "UPGRADE: SR-1"]],
                "reviewed": False, "count": 2,
            })
        outstanding = [
            sig for sig in item["extraSignatures"] if not sig["reviewed"]
        ]
        if outstanding != expected:
            raise ValueError(f"Hacking compound source signatures changed: {source_id}")
    return _refresh_metadata_v9_release(
        root=root,
        variant_records={source["record"] for source in HACKING_GRANT_SOURCES.values()},
        hacking_combinations=True,
    )


def _refresh_metadata_v9_release(
    *, root: Path, source_ids: set[str] | None = None, expected_count: int | None = None,
    variant_records: set[str] | None = None,
    initialize_movement_distance: bool = False, tinbot_firewall: bool = False,
    tinbot_other: bool = False, hacking_mods: bool = False,
    hacking_srs: bool = False, hacking_firewall: bool = False,
    hacking_combinations: bool = False, bangbomb: bool = False,
    ecm_sources: bool = False, medikit: bool = False, gizmokit: bool = False,
    deactivator: bool = False,
    evo_trinity: bool = False, hacking_trinity_access: bool = False,
    killer_hacking: bool = False, impersonation: bool = False,
    gizmokit_target_ph: bool = False, medikit_target_ph: bool = False,
    remdriver: bool = False, bangbomb_skill: bool = False,
    tagcom: bool = False, ft_master: bool = False,
    decoy: bool = False, vulnerability: bool = False,
    hacker_skill: bool = False, chart_rerolls: bool = False,
    regeneration: bool = False,
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
        and (
            row.get("variantSemantics", {}).get("occurrenceParameters")
            or row.get("variantSemantics", {}).get("occurrenceCombinations")
        )
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
        if ecm_sources:
            _check_ecm_source_additions(current_rules, next_rules, variants)
        elif variant_records is not None:
            _check_variant_semantics_delta(
                current_rules, next_rules, variants,
                initialize_movement_distance=initialize_movement_distance,
                tinbot_firewall=tinbot_firewall,
                tinbot_other=tinbot_other,
                hacking_mods=hacking_mods,
                hacking_srs=hacking_srs,
                hacking_firewall=hacking_firewall,
                hacking_combinations=hacking_combinations,
                bangbomb=bangbomb,
                medikit=medikit,
                gizmokit=gizmokit,
                gizmokit_target_ph=gizmokit_target_ph,
                medikit_target_ph=medikit_target_ph,
                remdriver=remdriver,
                bangbomb_skill=bangbomb_skill,
                tagcom=tagcom,
                ft_master=ft_master,
                decoy=decoy,
                vulnerability=vulnerability,
                hacker_skill=hacker_skill,
                chart_rerolls=chart_rerolls,
                regeneration=regeneration,
                deactivator=deactivator,
                evo_trinity=evo_trinity,
                hacking_trinity_access=hacking_trinity_access,
                killer_hacking=killer_hacking,
                impersonation=impersonation,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    if args.promote_staged:
        print(f"Promoted v9 release pair; recovery: {promote_restrictions_v9(args.stage_dir)}")
    else:
        print(json.dumps(stage_restrictions_v9(args.stage_dir), indent=2))
        print("Staged only; release artifacts unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
