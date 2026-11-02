"""Stage and atomically promote the reviewed N5.3 Parachutist (Dep. Zone) extra.

Staging is ignored/local only. Promotion guards pinned source, exact curated
delta, all publication hashes, unchanged deployed objects and retains rollback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.rules_database import RulesDatabase
from tools.audit_source_variant_inputs import inventory_source_variants, select_source_variants
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.stage_hacking_device_chart_citations import (
    STAGED_PATHS,
    _replace_staged_batch,
    export_release_rules,
)

ROOT = Path(__file__).resolve().parents[1]
CURATED, RULES, OBJECTS = (ROOT / path for path in STAGED_PATHS)
ARMY = ROOT / "data/generated/infinity.db"
RAW = ROOT / "data/generated/infinity.raw.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PDF_MANIFEST = ROOT / "config/validation/weaponry-family-clauses.json"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"
CANDIDATES = ROOT / "config/validation/deployed-object-candidate-reviews.json"
RECORD = "skill:parachutist"
EXPECTED = {
    "source": "army-extra", "kind": "reviewed-extra",
    "extra_values": [{
        "extra_id": 48, "extra_type": "TEXT", "raw_value": "Dep. Zone",
        "effect": {
            "kind": "parachutist-entry-zone-permission",
            "applies_to": "parachutist-table-edge-entry",
            "zone": "enemy-deployment-zone",
            "permitted": True,
        },
    }],
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def verify_curated_delta() -> None:
    previous = json.loads(subprocess.run(
        ["git", "show", f"HEAD:{STAGED_PATHS[0]}"], cwd=ROOT,
        capture_output=True, check=True,
    ).stdout)
    current = load_curated_document(CURATED)
    earlier = {item["id"]: item for item in previous["records"]}
    now = {item["id"]: item for item in current["records"]}
    if set(earlier) != set(now) or earlier[RECORD]["variantSemantics"] != {
        "inheritance": "family"
    }:
        raise ValueError("Parachutist source baseline differs from reviewed HEAD")
    if now[RECORD]["variantSemantics"] != {
        "inheritance": "family",
        "occurrenceParameters": [{
            "source": "army-extra", "kind": "reviewed-extra",
            "extraValues": [{
                "extraId": 48, "extraType": "TEXT", "rawValue": "Dep. Zone",
                "effect": {
                    "kind": "parachutist-entry-zone-permission",
                    "appliesTo": "parachutist-table-edge-entry",
                    "zone": "enemy-deployment-zone",
                    "permitted": True,
                },
            }],
        }],
    }:
        raise ValueError("Parachutist parameter differs from reviewed scope")
    restored = json.loads(json.dumps(current))
    for item in restored["records"]:
        if item["id"] == RECORD:
            item["variantSemantics"] = earlier[RECORD]["variantSemantics"]
    if restored != previous:
        raise ValueError("Other curated content changed")
    if not any(c.get("sourceId") == "n5-core-v5.3-pdf" and c.get("page") == 105
               for c in now[RECORD]["citations"]):
        raise ValueError("Missing N5.3 p.105 provenance")
    if digest(PDF) != json.loads(PDF_MANIFEST.read_text(encoding="utf-8"))["corePdfSha256"]:
        raise ValueError("Pinned N5.3 PDF identity mismatch")


def verify_occurrences(path: Path) -> None:
    report = inventory_source_variants(ARMY, RAW, path)
    [item] = select_source_variants(report, "skills", [33])["items"]
    if (
        item["applicationId"] != 33 or item["occurrences"] != 305
        or item["status"] != "reviewed-extra-parameter"
        or item["reviewedExtra"] != EXPECTED or item["rawValues"]
        or item["extraSignatures"] != [{
            "extras": [[48, "TEXT", "Dep. Zone"]],
            "reviewed": True, "count": 17,
        }]
    ):
        raise ValueError("Pinned Parachutist source-33 signatures diverged")


def publish(rules: Path) -> bytes:
    return publication_bytes(build_publication(
        ARMY, rules, CURATED, DELIVERY, CANDIDATES,
    ))


def stage(relative: Path) -> dict[str, Any]:
    destination = (ROOT / relative).resolve()
    if not destination.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Staging must be under ignored local/")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite stage: {relative}")
    verify_curated_delta()
    baseline = json.loads(OBJECTS.read_text(encoding="utf-8"))
    if baseline["sourceSnapshot"]["rulesDatabaseSha256"] != digest(RULES):
        raise ValueError("Deployed-object publication and existing rules database differ")
    destination.mkdir(parents=True)
    staged_rules = destination / "rules.db"
    export_release_rules(load_curated_directory(ROOT / "data/curated/rules"), staged_rules)
    verify_occurrences(staged_rules)
    if RulesDatabase(staged_rules).skill_reviewed_extra_semantics()["parachutist"] != EXPECTED:
        raise ValueError("Staged rules database lacks exact Parachutist semantics")
    body = publish(staged_rules)
    proposed = json.loads(body)
    if (
        len(baseline["objects"]) != 17
        or proposed["objects"] != baseline["objects"]
        or proposed["sourceSnapshot"]["rulesDatabaseSha256"] != digest(staged_rules)
    ):
        raise ValueError("Staged publication differs beyond rules database identity")
    staged_objects = destination / "deployed-objects.json"
    staged_objects.write_bytes(body)
    report = {
        "scope": "n53-parachutist-deployment-zone-staged",
        "head": head(),
        "sha256": {
            str(path.relative_to(ROOT)): digest(path)
            for path in (CURATED, RULES, OBJECTS, ARMY, RAW, PDF)
        },
        "stagedRulesSha256": digest(staged_rules),
        "stagedObjectsSha256": digest(staged_objects),
        "reviewedObjects": 17,
    }
    (destination / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def promote(relative: Path) -> Path:
    destination = (ROOT / relative).resolve()
    if (not destination.is_relative_to((ROOT / "local").resolve())
            or destination.is_symlink()):
        raise ValueError("Promotion requires ignored local/ stage")
    report = json.loads((destination / "report.json").read_text(encoding="utf-8"))
    if report.get("scope") != "n53-parachutist-deployment-zone-staged" or (
        report.get("reviewedObjects") != 17 or head() != report.get("head")
    ):
        raise ValueError("Staging report or HEAD changed")
    if subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", STAGED_PATHS[1], STAGED_PATHS[2]],
        cwd=ROOT, check=False,
    ).returncode != 0:
        raise ValueError("Existing tracked database/publication changed")
    for name, expected in report["sha256"].items():
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise ValueError(f"Changed staging input: {name}")
    staged_rules = destination / "rules.db"
    staged_objects = destination / "deployed-objects.json"
    for path, expected in (
        (staged_rules, report["stagedRulesSha256"]),
        (staged_objects, report["stagedObjectsSha256"]),
    ):
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise ValueError(f"Changed staged output: {path.name}")
    verify_curated_delta()
    verify_occurrences(staged_rules)
    before = json.loads(OBJECTS.read_text(encoding="utf-8"))
    if publish(staged_rules) != staged_objects.read_bytes() or (
        json.loads(staged_objects.read_text(encoding="utf-8"))["objects"] != before["objects"]
    ):
        raise ValueError("Staged publication changed reviewed deployed objects")
    payloads = {
        STAGED_PATHS[0]: CURATED.read_bytes(),
        STAGED_PATHS[1]: staged_rules.read_bytes(),
        STAGED_PATHS[2]: staged_objects.read_bytes(),
    }

    def postcheck() -> None:
        verify_occurrences(RULES)
        if digest(RULES) != report["stagedRulesSha256"] or (
            digest(OBJECTS) != report["stagedObjectsSha256"]
        ) or publish(RULES) != OBJECTS.read_bytes():
            raise ValueError("Promoted artifacts differ from staged output")
        if json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"] != before["objects"]:
            raise ValueError("Deployed objects changed")

    return _replace_staged_batch(ROOT, payloads, postcheck)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    if args.promote_staged:
        print(f"Promoted with retained recovery backup: {promote(args.output_dir)}")
    else:
        print(json.dumps(stage(args.output_dir), indent=2))
        print("Staged only; no tracked artifact changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
