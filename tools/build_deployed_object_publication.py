"""Legacy source-projection adapter retained for migration/source tests.

Current builders embed the reviewed model in Rules SQLite via
`infinity_db.deployed_object_builder`. The JSON CLI is retired; remaining
programmatic consumers are historical evidence pending P5 cleanup.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from infinity_db.deployed_object_builder import build_deployed_objects


def _digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def build_publication(
    army_db: Path,
    rules_db: Path,
    curated_source: Path,
    delivery_reviews: Path,
    candidate_reviews: Path,
) -> dict[str, Any]:
    """Project only validated review evidence; pin both shipped databases."""
    publication = build_deployed_objects(
        army_db, curated_source, delivery_reviews, candidate_reviews,
    )
    publication["sourceSnapshot"]["rulesDatabaseSha256"] = _digest(rules_db)
    return publication


def publication_bytes(publication: dict[str, Any]) -> bytes:
    return (json.dumps(
        publication, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ) + "\n").encode("utf-8")


def main() -> int:
    """Reject the retired JSON publishing/migration interface explicitly."""
    raise SystemExit(
        "The deployed-object JSON publisher and v8/v9 migration commands are retired. "
        "Validate the selected embedded runtime set with "
        "'infinity-db database-health --db-dir data/generated'."
    )


if __name__ == "__main__":
    raise SystemExit(main())
