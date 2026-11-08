"""Pin exact Combat Jump Army extras and verify/promote its matched v9 release pair.

N5.3 p. 89 gives the landing PH Roll and one-use Explosion attack.
The script never interprets a fixed landing PH as a permanent Unit stat.
Default is read-only. --promote invokes the guarded paired release refresh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import (
    COMBAT_JUMP_SOURCE_SPECS,
    COMBAT_JUMP_VARIANT,
    load_curated_directory,
)
from infinity_db.rules_database import RulesDatabase
from tools.audit_source_variant_inputs import (
    inventory_source_variants,
    select_source_variants,
    source_extra_owner_context,
)
from tools.build_deployed_object_publication import build_publication
from tools.release_rules_export import export_release_rules, load_release_deployed_objects
from tools.restrictions_v9_release import (
    _check_variant_semantics_delta,
    refresh_variant_semantics_v9_release,
)
from tools.review_lieutenant_variant import verify_equivalent_rules_content

ROOT = Path(__file__).resolve().parents[1]
KEY = ("n5-core-v5.3", "skill:combat-jump")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    gen = root / "data/generated"
    rules, army, raw = (gen / name for name in (
        "rules.db", "infinity.db", "infinity.raw.db",
    ))
    objects = gen / "deployed-objects.json"
    curated = root / "data/curated/rules/n5-core-v5.3.json"
    pdf = root / "data/pdf/rules/n5-rules-v5.3-en.pdf"
    manifest = root / "config/validation/weaponry-family-clauses.json"
    if _sha(pdf) != json.loads(manifest.read_text(encoding="utf-8"))["corePdfSha256"]:
        raise ValueError("N5.3 Combat Jump PDF pin differs")
    docs = load_curated_directory(root / "data/curated/rules")
    matching = [
        rec for _, doc in docs for rec in doc["records"]
        if (doc["collection"]["id"], rec["id"]) == KEY
    ]
    if (
        len(matching) != 1
        or matching[0].get("review", {}).get("status") != "reviewed"
        or matching[0].get("armyLinks") != [{"entity": "skill", "id": "combat-jump"}]
        or matching[0].get("variantSemantics") != COMBAT_JUMP_VARIANT
        or not any(
            c.get("sourceId") == "n5-core-v5.3-pdf" and c.get("page") == 89
            for c in matching[0].get("citations", [])
        )
    ):
        raise ValueError("Combat Jump curated p.89 source contract changed")
    before = load_release_deployed_objects(objects, army, rules)
    if before is None:
        raise ValueError("Combat Jump release/deployed-object pair not matched")
    published = RulesDatabase(rules).skill_reviewed_extra_semantics().get("combat-jump")
    [source] = select_source_variants(
        inventory_source_variants(army, raw, rules), "skills", [35],
    )["items"]
    signatures = [
        {"extras": [[extra_id, "TEXT", label]], "reviewed": published is not None,
         "count": count}
        for extra_id, label, count in COMBAT_JUMP_SOURCE_SPECS
    ]
    if (
        source["name"] != "Combat Jump"
        or source["applicationId"] != 35
        or source["occurrences"] != 211
        or source["status"] != (
            "reviewed-extra-parameter" if published else "unresolved-occurrence-parameter"
        )
        or source["reviewedExtra"] != published
        or source["extraSignatures"] != signatures
        or source["rawValues"]
        or sum(count for _, _, count in COMBAT_JUMP_SOURCE_SPECS) != 121
    ):
        raise ValueError("Combat Jump Army signature/occurrence count drift")
    for extra_id, label, count in COMBAT_JUMP_SOURCE_SPECS:
        owners = source_extra_owner_context(
            raw, catalog="skills", source_id=35, extra_id=extra_id,
        )
        if len(owners) != count or any(
            row["extra_id"] != extra_id or row["extra_type"] != "TEXT"
            or row["extra_raw"] != label or row["extra_position"] != 1
            or row["source_raw"] is not None
            for row in owners
        ):
            raise ValueError(f"Combat Jump owner signature drift: {extra_id}")
    with tempfile.TemporaryDirectory(prefix="combat-jump-review-", dir=root / "local") as temp:
        candidate = Path(temp) / "rules.db"
        export_release_rules(docs, candidate, baseline=rules)
        if published is None:
            _check_variant_semantics_delta(rules, candidate, {
                KEY: json.dumps(
                    COMBAT_JUMP_VARIANT, ensure_ascii=False, separators=(",", ":"),
                ),
            })
        else:
            verify_equivalent_rules_content(rules, candidate)
        typed = RulesDatabase(candidate).skill_reviewed_extra_semantics()["combat-jump"]
        expected = {
            "source": "army-extra", "kind": "reviewed-extra",
            "extra_values": [{
                "extra_id": extra["extraId"], "extra_type": "TEXT",
                "raw_value": extra["rawValue"],
                "effect": {
                    ("applies_to" if key == "appliesTo" else key): value
                    for key, value in extra["effect"].items()
                },
            } for extra in COMBAT_JUMP_VARIANT["occurrenceParameters"][0]["extraValues"]],
        }
        if typed != expected or (published is not None and typed != published):
            raise ValueError("Combat Jump typed candidate effects mismatch")
        proposed = build_publication(
            army, candidate, curated,
            root / "config/validation/deployed-object-delivery-reviews.json",
            root / "config/validation/deployed-object-candidate-reviews.json",
        )
        expected_objects = json.loads(json.dumps(before))
        expected_objects["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(candidate)
        expected_objects["sourceSnapshot"]["curatedSourceSha256"] = _sha(curated)
        if proposed != expected_objects:
            raise ValueError("Combat Jump refresh changed unrelated deployed objects")
        return {
            "scope": ("combat-jump-v9-verified-published" if published
                      else "combat-jump-v9-candidate-not-promoted"),
            "qualifiedOccurrences": 121,
            "unqualifiedOccurrences": 90,
            "sourceVariants": 6,
            "previousRulesSha256": _sha(rules),
            "candidateRulesSha256": _sha(candidate),
            "logicalContentVerified": published is not None,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    report = check_candidate()
    if args.promote:
        if report["scope"] != "combat-jump-v9-candidate-not-promoted":
            raise ValueError("Combat Jump source extras already published")
        rollback = refresh_variant_semantics_v9_release({KEY[1]})
        print(f"Promoted N5.3 Combat Jump extras; rollback: {rollback}")
        check_candidate()
    else:
        print(json.dumps(report, indent=2))
        print("Verified source/release candidate; no tracked changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
