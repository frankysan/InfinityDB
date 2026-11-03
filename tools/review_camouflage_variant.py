"""Review or promote exact N5 Camouflage (1 Use) Army/FAQ metadata.

Default is read-only. Promotion requires local pinned FAQ PDFs and uses the
guarded v9 variant-only release refresh, preserving unrelated records and
deployed-object publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import CAMOUFLAGE_ONE_USE_VARIANT, load_curated_directory
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
KEY = ("n5-core-v5.3", "skill:camouflage")
FAQ_ID = "faq-ruling:camouflage-one-use-infiltration-failure"
FAQ_SOURCES = frozenset({
    "n5-faq-v0.0-en-pdf", "n5-faq-v0.1-en-pdf", "n5-faq-v0.1-es-pdf",
})


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_candidate(root: Path = ROOT, *, require_pdfs: bool = False) -> dict[str, Any]:
    """Check source, exact Army extras, candidate delta and matched publication."""
    root = root.resolve()
    generated = root / "data/generated"
    active_rules, active_objects = generated / "rules.db", generated / "deployed-objects.json"
    army, raw = generated / "infinity.db", generated / "infinity.raw.db"
    curated = root / "data/curated/rules/n5-core-v5.3.json"
    docs = load_curated_directory(root / "data/curated/rules")
    records = {
        (doc["collection"]["id"], row["id"]): row
        for _, doc in docs for row in doc["records"]
    }
    camouflage = records[KEY]
    faq = records[("n5-faq-v0.1", FAQ_ID)]
    if (
        camouflage.get("review", {}).get("status") != "reviewed"
        or camouflage.get("armyLinks") != [{"entity": "skill", "id": "camouflage"}]
        or camouflage.get("variantSemantics") != CAMOUFLAGE_ONE_USE_VARIANT
        or not any(c.get("sourceId") == "n5-core-v5.3-pdf" and c.get("page") == 87
                   for c in camouflage.get("citations", []))
        or faq.get("review", {}).get("status") != "reviewed"
        or faq.get("facts", {}).get("topicIds") != [
            "skill:camouflage", "skill:infiltration",
        ]
        or "Deploying as a Model preserves" not in faq.get("facts", {}).get("answer", "")
        or "failing an Infiltration Roll uses up the one use" not in (
            faq.get("facts", {}).get("answer", "")
        )
        or {(c["sourceId"], c["page"]) for c in faq["citations"]} != {
            ("n5-faq-v0.0-en-pdf", 2),
            ("n5-faq-v0.1-en-pdf", 2),
            ("n5-faq-v0.1-es-pdf", 2),
        }
    ):
        raise ValueError("Reviewed Camouflage/FAQ source semantics changed")
    faq_doc = next(doc for _, doc in docs if doc["collection"]["id"] == "n5-faq-v0.1")
    source_pins = {s["id"]: s for s in faq_doc["sources"]}
    if not FAQ_SOURCES <= source_pins.keys():
        raise ValueError("Camouflage source FAQ identity pins changed")
    verified = []
    for source_id in sorted(FAQ_SOURCES):
        source = source_pins[source_id]
        file = root / source["localPath"]
        if file.is_file():
            if _sha(file) != source["sha256"]:
                raise ValueError(f"Camouflage FAQ PDF hash mismatch: {source_id}")
            verified.append(source_id)
        elif require_pdfs:
            raise ValueError(f"Camouflage FAQ PDF unavailable for promotion: {source_id}")

    before = load_deployed_object_publication(active_objects, army, active_rules)
    if before is None:
        raise ValueError("Existing Camouflage release/deployed-object pair is not matched")
    published = RulesDatabase(active_rules).skill_reviewed_extra_semantics().get(
        "camouflage"
    )
    audit = inventory_source_variants(army, raw, active_rules)
    [source] = select_source_variants(audit, "skills", [29])["items"]
    if (
        source["name"] != "Camouflage"
        or source["applicationId"] != 29
        or source["occurrences"] != 597
        or source["status"] != (
            "reviewed-extra-parameter" if published else "unresolved-occurrence-parameter"
        )
        or source["rawValues"]
        or source["reviewedExtra"] != published
        or source["extraSignatures"] != [{
            "extras": [[43, "TEXT", "1 Use"]],
            "reviewed": published is not None, "count": 223,
        }]
    ):
        raise ValueError("Camouflage source-29 occurrence signature changed")
    owners = source_extra_owner_context(
        raw, catalog="skills", source_id=29, extra_id=43,
    )
    if len(owners) != 223 or any(
        row["extra_position"] != 1 or row["extra_id"] != 43
        or row["extra_type"] != "TEXT" or row["extra_raw"] != "1 Use"
        or row["source_raw"] is not None
        for row in owners
    ):
        raise ValueError("Camouflage one-use owner scope changed")
    with tempfile.TemporaryDirectory(prefix="camouflage-review-", dir=root / "local") as tmp:
        candidate = Path(tmp) / "rules.db"
        export_release_rules(docs, candidate, baseline=active_rules)
        if published is None:
            _check_variant_semantics_delta(
                active_rules, candidate,
                {KEY: json.dumps(
                    CAMOUFLAGE_ONE_USE_VARIANT, ensure_ascii=False, separators=(",", ":"),
                )},
            )
        else:
            verify_equivalent_rules_content(active_rules, candidate)
        typed = RulesDatabase(candidate).skill_reviewed_extra_semantics()["camouflage"]
        expected = {
            "source": "army-extra", "kind": "reviewed-extra",
            "extra_values": [{
                "extra_id": 43, "extra_type": "TEXT", "raw_value": "1 Use",
                "effect": {
                    "kind": "camouflaged-state-one-use",
                    "applies_to": "camouflaged-state-entry",
                    "maxUses": 1,
                    "deploymentAsModelConsumesUse": False,
                    "failedInfiltrationMarkerDeploymentConsumesUse": True,
                },
            }],
        }
        if typed != expected or (published is not None and typed != published):
            raise ValueError("Camouflage one-use candidate effect changed")
        proposed = build_publication(
            army, candidate, curated,
            root / "config/validation/deployed-object-delivery-reviews.json",
            root / "config/validation/deployed-object-candidate-reviews.json",
        )
        expected_objects = json.loads(json.dumps(before))
        expected_objects["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(candidate)
        expected_objects["sourceSnapshot"]["curatedSourceSha256"] = _sha(curated)
        if proposed != expected_objects:
            raise ValueError("Camouflage refresh modified unrelated deployed objects")
        return {
            "scope": ("camouflage-one-use-v9-verified-published" if published is not None
                      else "camouflage-one-use-v9-candidate-not-promoted"),
            "qualifiedOccurrences": 223,
            "unqualifiedOccurrences": 374,
            "verifiedFaqPdfs": verified,
            "logicalContentVerified": published is not None,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    result = check_candidate(require_pdfs=args.promote)
    if args.promote:
        if result["scope"] != "camouflage-one-use-v9-candidate-not-promoted":
            raise ValueError("Camouflage one-use has already been promoted")
        backup = refresh_variant_semantics_v9_release({KEY[1]})
        print(f"Promoted N5.3 Camouflage one-use; rollback: {backup}")
        check_candidate()
    else:
        print(json.dumps(result, indent=2))
        print("Verified current release/candidate; no tracked files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
