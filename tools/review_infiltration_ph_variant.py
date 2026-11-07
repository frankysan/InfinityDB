"""Review N5.3 Infiltration PH=X Army extras and guard matched v9 promotion.

Only the five exact fixed-PH signatures from source Skill 47 are typed.
The plain ReRoll extra lacks the printed ReRoll PH=X parameter and stays
unreviewed. The rulebook's PH-3 still applies; none changes a Unit's PH.

Default is read-only; --promote refreshes the guarded rules/publication pair.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import (
    INFILTRATION_PH_SOURCE_SPECS,
    INFILTRATION_PH_VARIANT,
    load_curated_directory,
)
from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import RulesDatabase
from tools.audit_source_variant_inputs import (
    inventory_source_variants,
    select_source_variants,
    source_extra_owner_context,
)
from tools.build_deployed_object_publication import build_publication
from tools.release_rules_export import export_release_rules
from tools.restrictions_v9_release import (
    _check_variant_semantics_delta,
    refresh_variant_semantics_v9_release,
)
from tools.review_lieutenant_variant import verify_equivalent_rules_content

ROOT = Path(__file__).resolve().parents[1]
KEY = ("n5-core-v5.3", "skill:infiltration")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    generated = root / "data/generated"
    army, raw = generated / "infinity.db", generated / "infinity.raw.db"
    rules, objects = generated / "rules.db", generated / "deployed-objects.json"
    curated = root / "data/curated/rules/n5-core-v5.3.json"
    pdf = root / "data/pdf/rules/n5-rules-v5.3-en.pdf"
    manifest = root / "config/validation/weaponry-family-clauses.json"
    if _sha(pdf) != json.loads(manifest.read_text(encoding="utf-8"))["corePdfSha256"]:
        raise ValueError("N5.3 Infiltration PDF pin differs")

    docs = load_curated_directory(root / "data/curated/rules")
    matches = [
        row for _, doc in docs for row in doc["records"]
        if (doc["collection"]["id"], row["id"]) == KEY
    ]
    if (
        len(matches) != 1
        or matches[0].get("review", {}).get("status") != "reviewed"
        or matches[0].get("armyLinks") != [{"entity": "skill", "id": "infiltration"}]
        or matches[0].get("variantSemantics") != INFILTRATION_PH_VARIANT
        or not any(
            citation.get("sourceId") == "n5-core-v5.3-pdf"
            and citation.get("page") == 97
            for citation in matches[0].get("citations", [])
        )
    ):
        raise ValueError("N5.3 Infiltration curated p.97 source contract changed")

    before = load_deployed_object_publication(objects, army, rules)
    if before is None:
        raise ValueError("Existing Infiltration release/publication pair not matched")
    published = RulesDatabase(rules).skill_reviewed_extra_semantics().get("infiltration")
    [source] = select_source_variants(
        inventory_source_variants(army, raw, rules), "skills", [47],
    )["items"]
    raw_signatures = [
        (extra_id, f"PH={ph}", count, published is not None)
        for extra_id, ph, count in INFILTRATION_PH_SOURCE_SPECS
    ] + [(277, "ReRoll", 5, False)]
    expected = [
        {"extras": [[extra_id, "TEXT", text]], "reviewed": reviewed, "count": count}
        for extra_id, text, count, reviewed in sorted(raw_signatures)
    ]
    if (
        (source["name"], source["applicationId"], source["occurrences"])
        != ("Infiltration", 47, 216)
        or source["status"] != "unresolved-occurrence-parameter"
        or source["reviewedExtra"] != published
        or source["extraSignatures"] != expected
        or source["rawValues"]
        or sum(count for _, _, count, _ in raw_signatures) != 22
    ):
        raise ValueError("Infiltration source-47 signature/occurrence drift")
    for extra_id, text, count, _reviewed in raw_signatures:
        owners = source_extra_owner_context(
            raw, catalog="skills", source_id=47, extra_id=extra_id,
        )
        if len(owners) != count or any(
            owner["extra_id"] != extra_id
            or owner["extra_position"] != 1
            or owner["extra_type"] != "TEXT"
            or owner["extra_raw"] != text
            or owner["source_raw"] is not None
            for owner in owners
        ):
            raise ValueError(f"Infiltration owner signature drift: {extra_id}")

    with tempfile.TemporaryDirectory(prefix="infiltration-ph-review-", dir=root / "local") as temp:
        candidate = Path(temp) / "rules.db"
        export_release_rules(docs, candidate, baseline=rules)
        if published is None:
            _check_variant_semantics_delta(
                rules, candidate, {
                    KEY: json.dumps(
                        INFILTRATION_PH_VARIANT,
                        ensure_ascii=False, separators=(",", ":"),
                    ),
                },
            )
        else:
            verify_equivalent_rules_content(rules, candidate)
        typed = RulesDatabase(candidate).skill_reviewed_extra_semantics()["infiltration"]
        expected_typed = {
            "source": "army-extra", "kind": "reviewed-extra",
            "extra_values": [
                {
                    "extra_id": extra_id, "extra_type": "TEXT",
                    "raw_value": f"PH={ph}",
                    "effect": {
                        "kind": "infiltration-roll-ph-value",
                        "applies_to": "infiltration-ph-minus-three-roll",
                        "attribute": "PH", "value": ph,
                    },
                }
                for extra_id, ph, _count in INFILTRATION_PH_SOURCE_SPECS
            ],
        }
        if typed != expected_typed or (published is not None and published != typed):
            raise ValueError("Infiltration candidate contains unexpected typed effects")
        proposed = build_publication(
            army, candidate, curated,
            root / "config/validation/deployed-object-delivery-reviews.json",
            root / "config/validation/deployed-object-candidate-reviews.json",
        )
        expected_objects = json.loads(json.dumps(before))
        expected_objects["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(candidate)
        expected_objects["sourceSnapshot"]["curatedSourceSha256"] = _sha(curated)
        if proposed != expected_objects:
            raise ValueError("Infiltration refresh changed unrelated deployed objects")
        return {
            "scope": ("infiltration-ph-v9-verified-published" if published
                      else "infiltration-ph-v9-candidate-not-promoted"),
            "qualifiedPHOccurrences": 17,
            "unreviewedReRollOccurrences": 5,
            "unqualifiedOccurrences": 194,
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
        if report["scope"] != "infiltration-ph-v9-candidate-not-promoted":
            raise ValueError("Infiltration fixed PH extras already published")
        rollback = refresh_variant_semantics_v9_release({KEY[1]})
        print(f"Promoted N5.3 Infiltration PH extras; rollback: {rollback}")
        check_candidate()
    else:
        print(json.dumps(report, indent=2))
        print("Verified source/release candidate; no tracked changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
