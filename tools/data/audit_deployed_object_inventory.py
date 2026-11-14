"""Developer CLI wrapper around the maintained deployed-object inventory."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db import deployed_object_inventory as _inventory

if __package__ == "tools.data":
    from tools.research.report_output import (
        require_new_audit_outputs,
        write_audit_text_or_exit,
    )
else:  # Support direct execution from tools/data/.
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from research.report_output import (
        require_new_audit_outputs,
        write_audit_text_or_exit,
    )

# Preserve the developer audit's established Python import surface.
CHART_AUXILIARY = _inventory.CHART_AUXILIARY
REVIEW_CASES = _inventory.REVIEW_CASES
SOURCE_DOMAIN_CLASSIFICATIONS = _inventory.SOURCE_DOMAIN_CLASSIFICATIONS
SOURCE_DOMAIN_PDF_ONLY = _inventory.SOURCE_DOMAIN_PDF_ONLY
_profile_stats = _inventory._profile_stats
audit_inventory = _inventory.audit_inventory
source_domain_clause_leads = _inventory.source_domain_clause_leads
validate_candidate_reviews = _inventory.validate_candidate_reviews
validate_delivery_reviews = _inventory.validate_delivery_reviews
validate_source_domain_clause_reviews = _inventory.validate_source_domain_clause_reviews

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/army.db"))
    parser.add_argument(
        "--curated-source", type=Path,
        default=Path("data/curated/rules/n5-core-v5.3.json"),
    )
    parser.add_argument(
        "--delivery-reviews", type=Path,
        default=Path("config/validation/deployed-object-delivery-reviews.json"),
    )
    parser.add_argument(
        "--candidate-reviews", type=Path,
        default=Path("config/validation/deployed-object-candidate-reviews.json"),
    )
    parser.add_argument(
        "--source-clause-reviews", type=Path,
        default=Path(
            "config/validation/deployed-object-source-domain-clause-reviews.json"
        ),
    )
    parser.add_argument("--json-output", type=Path)
    arguments = parser.parse_args()
    require_new_audit_outputs(parser, arguments.json_output)
    report = audit_inventory(
        arguments.army_db, arguments.curated_source,
        arguments.delivery_reviews, arguments.candidate_reviews,
        arguments.source_clause_reviews,
    )
    result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if arguments.json_output is not None:
        write_audit_text_or_exit(parser, arguments.json_output, result)
    else:
        print(result, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

