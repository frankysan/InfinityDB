"""Verify or promote reviewed N5.3 Terrain (source 58) occurrence types.

Read-only by default. Promotion uses the guarded matched-v9 refresh with
rollback; no Army source rows or unrelated rule effects are rewritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import (
    TERRAIN_SOURCE_SPECS,
    TERRAIN_VARIANT,
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
KEY = ("n5-core-v5.3", "skill:terrain")
COUNTS = (918, 164, 65, 29, 30, 19, 10)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_candidate(root: Path = ROOT) -> dict[str, Any]:
    """Pin the exact seven Terrain extras and preserve unrelated publication."""
    root = root.resolve()
    generated = root / "data/generated"
    rules = generated / "rules.db"
    objects = generated / "deployed-objects.json"
    army = generated / "infinity.db"
    raw = generated / "infinity.raw.db"
    curated = root / "data/curated/rules/n5-core-v5.3.json"
    pdf = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    manifest = root / "config/validation/weaponry-family-clauses.json"
    if _sha(pdf) != json.loads(manifest.read_text(encoding="utf-8"))["corePdfSha256"]:
        raise ValueError("N5.3 Terrain PDF differs from the pinned review")
    docs = load_curated_directory(root / "data/curated/rules")
    matching = [
        row for _, document in docs for row in document["records"]
        if (document["collection"]["id"], row["id"]) == KEY
    ]
    if (
        len(matching) != 1
        or matching[0].get("armyLinks") != [{"entity": "skill", "id": "terrain"}]
        or matching[0].get("review", {}).get("status") != "reviewed"
        or matching[0].get("variantSemantics") != TERRAIN_VARIANT
        or not any(c.get("sourceId") == "n5-core-v5.3-pdf" and c.get("page") == 116
                   for c in matching[0].get("citations", []))
    ):
        raise ValueError("N5.3 Terrain curated source contract changed")
    prior = load_deployed_object_publication(objects, army, rules)
    if prior is None:
        raise ValueError("Existing deployed-object/rules release pair is not matched")
    published = RulesDatabase(rules).skill_reviewed_extra_semantics().get("terrain")
    report = inventory_source_variants(army, raw, rules)
    [source] = select_source_variants(report, "skills", [58])["items"]
    signatures = [
        {
            "extras": [[extra_id, "TEXT", label]],
            "reviewed": published is not None, "count": count,
        }
        for (extra_id, label, _types, _selection), count
        in zip(TERRAIN_SOURCE_SPECS, COUNTS, strict=True)
    ]
    if (
        source["name"] != "Terrain"
        or source["applicationId"] != 58
        or source["occurrences"] != 1236
        or source["status"] != (
            "reviewed-extra-parameter" if published else "unresolved-occurrence-parameter"
        )
        or source["rawValues"]
        or source["reviewedExtra"] != published
        or source["extraSignatures"] != signatures
        or sum(COUNTS) != 1235
    ):
        raise ValueError("N5.3 Terrain source occurrence signatures changed")
    [religious] = select_source_variants(report, "skills", [83])["items"]
    if (
        religious["status"] != "unresolved-occurrence-parameter"
        or religious["extraSignatures"] != [{
            "extras": [[33, "TEXT", "Total"]], "reviewed": False, "count": 1,
        }]
    ):
        raise ValueError("SRC-028 Religious Troop source anomaly changed")
    for (extra_id, label, _types, _selection), count in zip(
        TERRAIN_SOURCE_SPECS, COUNTS, strict=True,
    ):
        owners = source_extra_owner_context(
            raw, catalog="skills", source_id=58, extra_id=extra_id,
        )
        if len(owners) != count or any(
            row["extra_id"] != extra_id or row["extra_type"] != "TEXT"
            or row["extra_raw"] != label or row["extra_position"] != 1
            or row["source_raw"] is not None
            for row in owners
        ):
            raise ValueError(f"Terrain source owner signature changed: {extra_id}")

    with tempfile.TemporaryDirectory(prefix="terrain-review-", dir=root / "local") as tmp:
        candidate = Path(tmp) / "rules.db"
        export_release_rules(docs, candidate, baseline=rules)
        if published is None:
            _check_variant_semantics_delta(
                rules, candidate, {
                    KEY: json.dumps(
                        TERRAIN_VARIANT, ensure_ascii=False, separators=(",", ":"),
                    ),
                },
            )
        else:
            verify_equivalent_rules_content(rules, candidate)
        typed = RulesDatabase(candidate).skill_reviewed_extra_semantics()["terrain"]
        expected = {
            "source": "army-extra", "kind": "reviewed-extra",
            "extra_values": [
                {
                    "extra_id": extra_id, "extra_type": "TEXT", "raw_value": label,
                    "effect": {
                        "kind": "terrain-type-applicability",
                        "applies_to": "terrain-movement-skill-effects",
                        "terrainTypes": list(types), "selection": selection,
                    },
                }
                for extra_id, label, types, selection in TERRAIN_SOURCE_SPECS
            ],
        }
        if typed != expected or (published is not None and typed != published):
            raise ValueError("Staged Terrain type effects differ from reviewed source")
        proposed = build_publication(
            army, candidate, curated,
            root / "config/validation/deployed-object-delivery-reviews.json",
            root / "config/validation/deployed-object-candidate-reviews.json",
        )
        expected_objects = json.loads(json.dumps(prior))
        expected_objects["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(candidate)
        expected_objects["sourceSnapshot"]["curatedSourceSha256"] = _sha(curated)
        if proposed != expected_objects:
            raise ValueError("Terrain refresh modified unrelated deployed objects")
        return {
            "scope": ("terrain-v9-verified-published" if published is not None
                      else "terrain-v9-candidate-not-promoted"),
            "qualifiedOccurrences": sum(COUNTS),
            "unqualifiedOccurrences": source["occurrences"] - sum(COUNTS),
            "sourceVariants": len(TERRAIN_SOURCE_SPECS),
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
        if report["scope"] != "terrain-v9-candidate-not-promoted":
            raise ValueError("Reviewed Terrain types are already published")
        rollback = refresh_variant_semantics_v9_release({KEY[1]})
        print(f"Promoted N5.3 Terrain type applicability; rollback: {rollback}")
        check_candidate()
    else:
        print(json.dumps(report, indent=2))
        print("Verified current release/candidate; no tracked files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
