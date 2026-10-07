"""Resolve maintained-text tokens into bounded player-facing API references."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.domain_references import rule_record_public_reference
from infinity_db.maintained_text import parse_maintained_text
from infinity_db.rules_database import RulesDatabase


def _pluralize(value: str) -> str:
    """Return a conservative English plural for optional display-form shorthand."""

    if not value:
        return value
    lower = value.casefold()
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return f"{value}es"
    if len(value) > 1 and lower.endswith("y") and lower[-2] not in "aeiou":
        return f"{value[:-1]}ies"
    return f"{value}s"


class _Resolver:
    def __init__(
        self, database: Database, rules_database: RulesDatabase, scenario_id: str | None = None
    ) -> None:
        self.database = database
        self.rules_database = rules_database
        self.scenario_id = scenario_id
        self.records: dict[str, dict[str, Any] | None] = {}

    def record(self, record_id: str) -> dict[str, Any]:
        if record_id not in self.records:
            self.records[record_id] = self.rules_database.composed_record(
                record_id, include_army_links=True, scenario_id=self.scenario_id
            )
        record = self.records[record_id]
        if record is None:
            raise ValueError(f"Maintained-text reference {record_id!r} is not current")
        return record

    def tokens(self, value: str, *, include_preview: bool = True) -> list[dict[str, Any]]:
        resolved = []
        for token in parse_maintained_text(value):
            if token["type"] != "reference":
                resolved.append(token)
                continue
            record = self.record(token["target"])
            label = token.get("display_text") or record["name"]
            if token.get("display_form") == "plural" and not token.get("display_text"):
                label = _pluralize(label)
            contextual = bool((record.get("scope") or {}).get("scenarios"))
            reference = None if contextual else rule_record_public_reference(self.database, record)
            if reference is None and not contextual:
                raise ValueError(
                    f"Maintained-text reference {token['target']!r} has no public route"
                )
            item = {
                "type": "reference",
                "target": token["target"],
                "label": label,
                "public_reference": reference,
            }
            if include_preview:
                item["preview_tokens"] = self.tokens(record["summary"], include_preview=False)
            resolved.append(item)
        return resolved


def _enrich_rule_record(record: dict[str, Any], resolver: _Resolver) -> None:
    summary = record.get("summary")
    if isinstance(summary, str):
        record["summary_tokens"] = resolver.tokens(summary)

    labels = record.get("labels")
    if isinstance(labels, list):
        for label in labels:
            if not isinstance(label, dict):
                continue
            description = label.get("description")
            if isinstance(description, str):
                label["description_tokens"] = resolver.tokens(description)

    facts = record.get("facts")
    if not isinstance(facts, dict):
        return
    fact_tokens: dict[str, Any] = {}
    for key in ("requirements", "effects", "restrictions", "rules"):
        values = facts.get(key)
        if isinstance(values, list) and all(isinstance(value, str) for value in values):
            fact_tokens[key] = [resolver.tokens(value) for value in values]
    specialists = facts.get("specialists")
    if isinstance(specialists, dict):
        fact_tokens["specialists"] = [
            resolver.tokens(f"[[{identifier}]]")
            for identifier in specialists.get("anyOfSkills", [])
        ]
    basis = facts.get("basis")
    if isinstance(basis, str):
        fact_tokens["basis"] = resolver.tokens(basis)
    terminology = facts.get("terminology")
    if isinstance(terminology, list):
        term_tokens = []
        for term in terminology:
            if not isinstance(term, dict) or not isinstance(term.get("meaning"), str):
                term_tokens.append(None)
                continue
            term_tokens.append(resolver.tokens(term["meaning"]))
        if any(tokens is not None for tokens in term_tokens):
            fact_tokens["terminology"] = term_tokens
    levels = facts.get("levels")
    if isinstance(levels, list):
        level_tokens = []
        for level in levels:
            if not isinstance(level, dict):
                level_tokens.append(None)
                continue
            level_item: dict[str, Any] = {}
            requirement = level.get("requirement")
            if isinstance(requirement, str):
                level_item["requirement"] = resolver.tokens(requirement)
            for key in ("bonuses", "effects"):
                values = level.get(key)
                if isinstance(values, list) and all(isinstance(value, str) for value in values):
                    level_item[key] = [resolver.tokens(value) for value in values]
            level_tokens.append(level_item or None)
        if any(tokens is not None for tokens in level_tokens):
            fact_tokens["levels"] = level_tokens
    if fact_tokens:
        record["fact_tokens"] = fact_tokens


def maintained_text_tokens(
    database: Database,
    rules_database: RulesDatabase | None,
    value: str,
) -> list[dict[str, Any]] | None:
    """Resolve one maintained-text value for a non-record reference surface."""

    if rules_database is None:
        return None
    return _Resolver(database, rules_database).tokens(value)


def enrich_maintained_text_references(
    database: Database,
    rules_database: RulesDatabase | None,
    value: dict[str, Any],
    *,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """Attach resolved inline-text tokens to nested current rules records."""

    result = deepcopy(value)
    if rules_database is None:
        return result
    resolver = _Resolver(database, rules_database, scenario_id)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("id"), str) and isinstance(node.get("summary"), str):
                _enrich_rule_record(node, resolver)
            for child in list(node.values()):
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(result)
    return result
