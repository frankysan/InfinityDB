"""Verify or promote exact N5.3 Lieutenant (+1 Command Token / +1 Order) metadata.

The default check is read-only. --promote uses the existing deterministic v9
variant-only release gate with matching deployed-object publication and rollback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import LIEUTENANT_VARIANT, load_curated_directory
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

ROOT = Path(__file__).resolve().parents[1]
KEY = ("n5-core-v5.3", "skill:lieutenant")
SIGNATURES = [
    {"extras": [[245, "TEXT", "+1 Command Token"]], "reviewed": False, "count": 30},
    {"extras": [[246, "TEXT", "+1 Order"]], "reviewed": False, "count": 53},
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_candidate(root: Path = ROOT) -> dict[str, Any]:
    """Pin source, schema, two resource effects and unrelated publication bytes."""
    root = root.resolve()
    generated = root / "data/generated"
    active_rules = generated / "rules.db"
    active_objects = generated / "deployed-objects.json"
    army = generated / "infinity.db"
    raw = generated / "infinity.raw.db"
    curated = root / "data/curated/rules/n5-core-v5.3.json"
    manifest = root / "config/validation/weaponry-family-clauses.json"
    pdf = root / "data/pdf/rules/n5-rules-v5-3-en.pdf"
    if _sha(pdf) != json.loads(manifest.read_text(encoding="utf-8"))["corePdfSha256"]:
        raise ValueError("N5.3 source PDF differs from the pinned review")
    documents = load_curated_directory(root / "data/curated/rules")
    matching = [
        record for _, doc in documents for record in doc["records"]
        if (doc["collection"]["id"], record["id"]) == KEY
    ]
    if (
        len(matching) != 1
        or matching[0].get("review", {}).get("status") != "reviewed"
        or matching[0].get("armyLinks") != [{"entity": "skill", "id": "lieutenant"}]
        or matching[0].get("variantSemantics") != LIEUTENANT_VARIANT
        or not any(c.get("sourceId") == "n5-core-v5.3-pdf" and c.get("page") == 99
                   for c in matching[0].get("citations", []))
    ):
        raise ValueError("N5.3 Lieutenant curated source contract changed")
    baseline = load_deployed_object_publication(active_objects, army, active_rules)
    if baseline is None:
        raise ValueError("Existing published rules/deployed-object pair is not matched")
    current = RulesDatabase(active_rules)
    published = current.skill_reviewed_extra_semantics().get("lieutenant")
    report = inventory_source_variants(army, raw, active_rules)
    [source] = select_source_variants(report, "skills", [119])["items"]
    if (
        source["name"] != "Lieutenant"
        or source["applicationId"] != 119
        or source["occurrences"] != 438
        or source["status"] != (
            "reviewed-extra-parameter" if published else "unresolved-occurrence-parameter"
        )
        or source["rawValues"]
        or source["reviewedExtra"] != published
        or source["extraSignatures"] != [
            {**signature, "reviewed": published is not None}
            for signature in SIGNATURES
        ]
    ):
        raise ValueError("Lieutenant source occurrence signatures changed")
    for extra_id, count in ((245, 30), (246, 53)):
        owners = source_extra_owner_context(
            raw, catalog="skills", source_id=119, extra_id=extra_id,
        )
        if (
            len(owners) != count
            or {row["owner"] for row in owners} != {"option"}
            or any(
                row["extra_position"] != 1 or row["source_raw"] is not None
                for row in owners
            )
        ):
            raise ValueError(f"Lieutenant source owner scope changed: {extra_id}")
    with tempfile.TemporaryDirectory(prefix="lieutenant-review-", dir=root / "local") as tmp:
        candidate = Path(tmp) / "rules.db"
        export_release_rules(documents, candidate, baseline=active_rules)
        if published is None:
            _check_variant_semantics_delta(
                active_rules, candidate, {
                    KEY: json.dumps(
                        LIEUTENANT_VARIANT, ensure_ascii=False, separators=(",", ":"),
                    ),
                },
            )
        elif _sha(candidate) != _sha(active_rules):
            raise ValueError("Published Lieutenant release differs from a fresh v9 export")
        staged = RulesDatabase(candidate)
        typed = staged.skill_reviewed_extra_semantics()["lieutenant"]
        expected = LIEUTENANT_VARIANT["occurrenceParameters"][0]["extraValues"]
        if (
            len(typed["extra_values"]) != 2
            or [
                (row["extra_id"], row["raw_value"], row["effect"]["count"])
                for row in typed["extra_values"]
            ] != [
                (row["extraId"], row["rawValue"], row["effect"]["count"])
                for row in expected
            ]
            or (published is not None and typed != published)
        ):
            raise ValueError("Staged Lieutenant resources do not match reviewed extras")
        proposed = build_publication(
            army, candidate, curated,
            root / "config/validation/deployed-object-delivery-reviews.json",
            root / "config/validation/deployed-object-candidate-reviews.json",
        )
        expected_objects = json.loads(json.dumps(baseline))
        expected_objects["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(candidate)
        expected_objects["sourceSnapshot"]["curatedSourceSha256"] = _sha(curated)
        if proposed != expected_objects:
            raise ValueError("Lieutenant refresh changed unrelated deployed-object publication")
        return {
            "scope": (
                "lieutenant-resource-v9-verified-published" if published is not None
                else "lieutenant-resource-v9-candidate-not-promoted"
            ),
            "qualifiedOccurrences": 83,
            "unqualifiedOccurrences": 355,
            "previousRulesSha256": _sha(active_rules),
            "candidateRulesSha256": _sha(candidate),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--promote", action="store_true",
        help="replace tracked v9 pair with rollback",
    )
    args = parser.parse_args()
    report = check_candidate()
    if args.promote:
        if report["scope"] != "lieutenant-resource-v9-candidate-not-promoted":
            raise ValueError("Lieutenant variant has already been published")
        rollback = refresh_variant_semantics_v9_release({KEY[1]})
        print(f"Promoted exact N5.3 Lieutenant resources; rollback: {rollback}")
    else:
        print(json.dumps(report, indent=2))
        print("Verified current release/candidate; no tracked files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
