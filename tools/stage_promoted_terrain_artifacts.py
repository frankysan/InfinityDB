"""Historical terrain/scenery staging helper for old source-review tests.

The standalone command is retired. Current builds publish embedded Rules
data instead of generating a redundant Rules/JSON staging pair.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory, load_curated_document
from tools.audit_terrain_scenery_source_gaps import (
    CURATED,
    PUBLICATION,
    audit_terrain_scenery_boundary,
)
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.release_rules_export import (
    RELEASE_RULES,
    export_release_rules,
    release_deployed_object_bytes,
)
from tools.stage_terrain_scenery_references import (
    ARMY,
    CANDIDATES,
    DELIVERY,
    EXPECTED_IDS,
    verify_additions,
)

ROOT = CURATED.parents[3]
ADDITIONS = ROOT / "config/validation/terrain-scenery-reference-additions.json"


def stage_promoted_terrain_artifacts(
    output_dir: Path,
    *,
    curated_path: Path = CURATED,
    army_path: Path = ARMY,
) -> dict[str, Any]:
    """Build the rules DB and dependent publication in one exclusive directory."""
    output = output_dir.resolve()
    inputs = (
        curated_path, army_path, PUBLICATION, DELIVERY, CANDIDATES, ADDITIONS,
        ROOT / "data/generated/rules.db",
    )
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {output}")
    if any(
        output == path.resolve()
        or path.resolve().is_relative_to(output)
        or output.is_relative_to(path.resolve().parent)
        for path in inputs
    ):
        raise ValueError("Staging must not overlap tracked source or generated inputs")

    proposal = verify_additions(json.loads(ADDITIONS.read_text(encoding="utf-8")))
    curated = load_curated_document(curated_path)
    records = {row["id"]: row for row in curated["records"]}
    # The insertion proposal is historical. Current definitions may gain reviewed
    # aliases, citations and the validated source-example table after promotion.
    # Retain the original definition contract without requiring whole-record equality.
    def baseline_matches(proposed: dict[str, Any]) -> bool:
        current = records.get(proposed["id"], {})
        return (
            all(current.get(key) == proposed[key] for key in (
                "id", "kind", "name", "summary", "composition", "scope", "relations",
            ))
            and all(current.get("facts", {}).get(key) == value
                    for key, value in proposed["facts"].items())
            and all(cite in current.get("citations", []) for cite in proposed["citations"])
        )

    if tuple(record["id"] for record in proposal) != EXPECTED_IDS or any(
        not baseline_matches(record) for record in proposal
    ):
        raise ValueError("Promoted terrain records differ from reviewed proposal")
    audit = audit_terrain_scenery_boundary(
        curated,
        json.loads(release_deployed_object_bytes(PUBLICATION).decode("utf-8")),
    )
    if (
        audit["reviewStatus"]["specialTerrainRule"] != "maintained"
        or audit["reviewStatus"]["accessWidthRule"] != "maintained"
        or audit["publishedDeployedObjectCount"] != 17
    ):
        raise ValueError("Promoted rule/reference boundary not fully maintained")
    if not army_path.is_file():
        raise ValueError(f"Matching Army database missing: {army_path}")

    generated = output / "data/generated"
    generated.mkdir(parents=True, exist_ok=False)
    rules_db = generated / "rules.db"
    export_release_rules(load_curated_directory(curated_path.parent), rules_db)
    published = build_publication(
        army_path, rules_db, curated_path, DELIVERY, CANDIDATES,
    )
    if len(published["objects"]) != 17:
        raise ValueError("Unexpected change to reviewed deployed object count")
    deployment = generated / "deployed-objects.json"
    payload = publication_bytes(published)
    deployment.write_bytes(payload)
    rules_hash = hashlib.sha256(rules_db.read_bytes()).hexdigest()
    if published["sourceSnapshot"]["rulesDatabaseSha256"] != rules_hash:
        raise ValueError("Regenerated publication contains stale rules fingerprint")

    report = {
        "scope": "post-promotion-binary-rebuild-not-applied",
        "releaseBaselineSha256": {
            "rulesDatabase": hashlib.sha256(RELEASE_RULES.read_bytes()).hexdigest(),
            "deployedObjects": hashlib.sha256(
                release_deployed_object_bytes(PUBLICATION),
            ).hexdigest(),
        },
        "sourceSha256": hashlib.sha256(curated_path.read_bytes()).hexdigest(),
        "reviewedRuleIds": list(EXPECTED_IDS),
        "reviewedObjects": len(published["objects"]),
        "stagedSha256": {
            "rulesDatabase": rules_hash,
            "deployedObjects": hashlib.sha256(payload).hexdigest(),
        },
        "stagedPaths": [
            "data/generated/rules.db",
            "data/generated/deployed-objects.json",
        ],
    }
    (output / "staging-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    return report


def main() -> int:
    """Disable superseded post-promotion Rules/JSON assembly."""
    raise SystemExit(
        "Historical terrain/scenery Rules/JSON staging is retired. "
        "Use the current complete database-set build and validation path."
    )


if __name__ == "__main__":
    raise SystemExit(main())
