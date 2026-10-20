"""Published cross-domain rule-relation destinations must resolve in normal APIs."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

from infinity_db.database import Database
from infinity_db.domain_references import enrich_rule_relation_references
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app


def _get(app: Any, path: str) -> str:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any = None,
    ) -> None:
        statuses.append(status)

    response = app(environ, start_response)
    try:
        b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert len(statuses) == 1
    return statuses[0]


def test_published_cross_domain_relation_catalog_destinations_resolve() -> None:
    root = Path(__file__).resolve().parents[1]
    army_path = root / "data/generated/infinity.db"
    rules_path = root / "data/generated/rules.db"
    database = Database(army_path)
    rules = RulesDatabase(rules_path)
    app = create_app(army_path, rules_database_path=rules_path)

    kinds = ("ammunition", "equipment", "hacking-program", "rule", "skill",
             "state", "trait", "weapon")
    records = [
        record
        for kind in kinds
        for record in rules.composed_records_by_kind(kind)
    ]
    enriched = enrich_rule_relation_references(database, {"records": records})
    targets: dict[tuple[str, str], set[str]] = defaultdict(set)
    for owner in enriched["records"]:
        for relation in owner.get("display_relations", []):
            if "presentation" not in relation:
                continue  # Structural variants are not rendered as links.
            reference = relation["record"].get("public_reference", {})
            if "catalog" not in reference:
                continue  # Embedded and deliberately unlinked source variants.
            targets[(reference["catalog"], reference["id"])].add(owner["id"])

    assert len(targets) >= 40, len(targets)
    failures = {}
    for (catalog, slug), owners in sorted(targets.items()):
        status = _get(app, f"/api/{catalog}/{slug}")
        if status != "200 OK":
            failures[f"/api/{catalog}/{slug}"] = sorted(owners)
    assert not failures, failures
