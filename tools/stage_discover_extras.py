"""Guarded N5.3 Discover (+3/+6/ReRoll) source-extra publication.

Stage under ignored local/; promote only the exact curated delta and matched
v9 rules/deployed-object pair with rollback on any failed postcheck.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.rules_database import RulesDatabase
from tools.audit_source_variant_inputs import (
    inventory_source_variants,
    select_source_variants,
    source_extra_owner_context,
)
from tools.stage_hacking_device_chart_citations import (
    STAGED_PATHS,
    _replace_staged_batch,
    export_release_rules,
)
from tools.stage_parachutist_deployment_zone import (
    ARMY,
    CURATED,
    OBJECTS,
    PDF,
    PDF_MANIFEST,
    RAW,
    ROOT,
    RULES,
    digest,
    head,
    publish,
)

RECORD = "skill:discover"
SOURCE_ID = 131
SIGNATURES = ((1, "+3", 24), (2, "+6", 13), (277, "ReRoll", 6))
EXPECTED_VALUES = [
    {
        "extraId": extra_id, "extraType": "TEXT", "rawValue": f"+{modifier}",
        "effect": {
            "kind": "discover-wip-roll-mod",
            "appliesTo": "discover-wip-roll", "modifier": modifier,
        },
    }
    for extra_id, modifier in ((1, 3), (2, 6))
] + [{
    "extraId": 277, "extraType": "TEXT", "rawValue": "ReRoll",
    "effect": {"kind": "reroll-one-die", "appliesTo": "discover-wip-roll"},
}]
EXPECTED = {
    "source": "army-extra", "kind": "reviewed-extra",
    "extra_values": [
        {
            "extra_id": value["extraId"],
            "extra_type": value["extraType"],
            "raw_value": value["rawValue"],
            "effect": {
                **{k: v for k, v in value["effect"].items() if k != "appliesTo"},
                "applies_to": value["effect"]["appliesTo"],
            },
        }
        for value in EXPECTED_VALUES
    ],
}
EXPECTED_OWNERS = {
    1: {4278, 6423, 16516, 41502, 41515, 48170, 48183, 50841,
        50920, 53448, 54720, 56674, 56893, 58393, 58426, 58524,
        60806, 66106, 68389, 69537, 80498, 80650, 82705, 84912},
    2: {25171, 26785, 31511, 34673, 38006, 41626, 46537, 49175,
        58340, 71102, 76097, 80980, 82136},
    277: {1309, 6622, 16348, 16879, 54571, 78075},
}


def verify_curated_delta() -> None:
    previous = json.loads(subprocess.run(
        ["git", "show", f"HEAD:{STAGED_PATHS[0]}"], cwd=ROOT,
        capture_output=True, check=True,
    ).stdout)
    current = load_curated_document(CURATED)
    before = {record["id"]: record for record in previous["records"]}
    now = {record["id"]: record for record in current["records"]}
    if set(before) != set(now) or before[RECORD]["variantSemantics"] != {
        "inheritance": "family"
    }:
        raise ValueError("Unexpected Discover HEAD baseline")
    if now[RECORD]["variantSemantics"] != {
        "inheritance": "family",
        "occurrenceParameters": [{
            "source": "army-extra", "kind": "reviewed-extra",
            "extraValues": EXPECTED_VALUES,
        }],
    }:
        raise ValueError("Discover variant differs from reviewed scope")
    restored = json.loads(json.dumps(current))
    for record in restored["records"]:
        if record["id"] == RECORD:
            record["variantSemantics"] = before[RECORD]["variantSemantics"]
    if restored != previous:
        raise ValueError("Unrelated curated records changed")
    citations = now[RECORD]["citations"]
    if not any(c.get("sourceId") == "n5-core-v5.3-pdf" and c.get("page") == 77
               for c in citations):
        raise ValueError("Missing Discover N5.3 p. 77 citation")
    if digest(PDF) != json.loads(
        PDF_MANIFEST.read_text(encoding="utf-8")
    )["corePdfSha256"]:
        raise ValueError("N5.3 PDF hash differs from pinned source")


def verify_occurrences(path: Path) -> None:
    report = inventory_source_variants(ARMY, RAW, path)
    [item] = select_source_variants(report, "skills", [SOURCE_ID])["items"]
    expected = [
        {"extras": [[extra_id, "TEXT", raw]], "reviewed": True, "count": count}
        for extra_id, raw, count in SIGNATURES
    ]
    if (
        item["applicationId"] != SOURCE_ID or item["occurrences"] != 43
        or item["rawValues"] or item["status"] != "reviewed-extra-parameter"
        or item["reviewedExtra"] != EXPECTED or item["extraSignatures"] != expected
        or report["catalogs"]["skills"]["summary"]["statuses"].get(
            "unresolved-occurrence-parameter"
        ) != 15
    ):
        raise ValueError("Pinned Discover signatures or source baseline differ")
    for extra_id, raw, count in SIGNATURES:
        owners = source_extra_owner_context(
            RAW, catalog="skills", source_id=SOURCE_ID, extra_id=extra_id,
        )
        if len(owners) != count or {
            owner["occurrence_id"] for owner in owners
        } != EXPECTED_OWNERS[extra_id] or any(
            owner["extra_position"] != 1
            or owner["extra_type"] != "TEXT"
            or owner["extra_raw"] != raw
            or owner["source_raw"] is not None
            for owner in owners
        ):
            raise ValueError(f"Discover extra {extra_id} owners changed")


def stage(relative: Path) -> dict:
    destination = (ROOT / relative).resolve()
    if not destination.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Only ignored local/ staging permitted")
    if destination.exists():
        raise FileExistsError(f"Refusing to replace stage {relative}")
    verify_curated_delta()
    before = json.loads(OBJECTS.read_text(encoding="utf-8"))
    if before["sourceSnapshot"]["rulesDatabaseSha256"] != digest(RULES):
        raise ValueError("Existing rules/publication fingerprints differ")
    destination.mkdir(parents=True)
    staged_rules = destination / "rules.db"
    export_release_rules(load_curated_directory(ROOT / "data/curated/rules"), staged_rules)
    verify_occurrences(staged_rules)
    if RulesDatabase(staged_rules).skill_reviewed_extra_semantics()["discover"] != EXPECTED:
        raise ValueError("Staged Discover mapping is missing")
    published = publish(staged_rules)
    after = json.loads(published)
    if (
        len(before["objects"]) != 17 or after["objects"] != before["objects"]
        or after["sourceSnapshot"]["rulesDatabaseSha256"] != digest(staged_rules)
    ):
        raise ValueError("Staged deployed-object content changed")
    staged_objects = destination / "deployed-objects.json"
    staged_objects.write_bytes(published)
    report = {
        "scope": "n53-discover-exact-extras-staged",
        "head": head(),
        "inputSha256": {
            str(p.relative_to(ROOT)): digest(p)
            for p in (CURATED, RULES, OBJECTS, ARMY, RAW, PDF)
        },
        "rulesSha256": digest(staged_rules),
        "objectsSha256": digest(staged_objects),
        "reviewedObjects": 17,
    }
    (destination / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    return report


def promote(relative: Path) -> Path:
    destination = (ROOT / relative).resolve()
    if not destination.is_relative_to((ROOT / "local").resolve()) or destination.is_symlink():
        raise ValueError("Only ignored local/ staged promotion permitted")
    report = json.loads((destination / "report.json").read_text(encoding="utf-8"))
    if (
        report.get("scope") != "n53-discover-exact-extras-staged"
        or report.get("reviewedObjects") != 17 or report.get("head") != head()
    ):
        raise ValueError("Invalid Discover stage metadata or changed HEAD")
    if subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", STAGED_PATHS[1], STAGED_PATHS[2]],
        cwd=ROOT, check=False,
    ).returncode != 0:
        raise ValueError("Publication target differs from HEAD")
    for name, sha in report["inputSha256"].items():
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or digest(path) != sha:
            raise ValueError(f"Changed source input: {name}")
    staged_rules, staged_objects = (destination / name for name in (
        "rules.db", "deployed-objects.json",
    ))
    for path, sha in ((staged_rules, report["rulesSha256"]),
                      (staged_objects, report["objectsSha256"])):
        if not path.is_file() or path.is_symlink() or digest(path) != sha:
            raise ValueError(f"Changed staged output: {path.name}")
    verify_curated_delta()
    verify_occurrences(staged_rules)
    old = json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
    if publish(staged_rules) != staged_objects.read_bytes() or (
        json.loads(staged_objects.read_text(encoding="utf-8"))["objects"] != old
    ):
        raise ValueError("Staged object publication is not reproducible")
    payloads = {
        STAGED_PATHS[0]: CURATED.read_bytes(),
        STAGED_PATHS[1]: staged_rules.read_bytes(),
        STAGED_PATHS[2]: staged_objects.read_bytes(),
    }

    def postcheck() -> None:
        verify_occurrences(RULES)
        if (
            digest(RULES) != report["rulesSha256"]
            or digest(OBJECTS) != report["objectsSha256"]
            or publish(RULES) != OBJECTS.read_bytes()
            or json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"] != old
        ):
            raise ValueError("Promoted Discover pair failed verification")

    return _replace_staged_batch(ROOT, payloads, postcheck)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    if args.promote_staged:
        print(f"Promoted with retained rollback backup: {promote(args.output_dir)}")
    else:
        print(json.dumps(stage(args.output_dir), indent=2))
        print("Staged only; tracked files unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
