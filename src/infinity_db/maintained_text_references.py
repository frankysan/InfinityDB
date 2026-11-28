"""Resolve maintained-text tokens into bounded player-facing API references."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from copy import deepcopy
from typing import Any

from infinity_db.build_provenance import canonical_bytes
from infinity_db.database.repository import Database
from infinity_db.domain_references import (
    local_rule_public_reference,
    rule_record_public_reference,
)
from infinity_db.maintained_text import MAINTAINED_REFERENCE_KINDS, parse_maintained_text
from infinity_db.rules_database import RULES_METADATA_TABLE, RulesDatabase
from infinity_db.weapon_properties import WeaponProperties


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


def collect_reference_targets(
    database: Database, rules_database: RulesDatabase,
) -> dict[str, Any]:
    """Prepare small context-neutral target descriptors from composed Rules rows."""
    records: dict[str, dict[str, Any]] = {}
    with rules_database._connect() as db:
        for record_id, scenario_id, body in db.execute(
            "SELECT record_id,scenario_id,body FROM composed_rule_records "
            "ORDER BY record_id,scenario_id"
        ):
            record = json.loads(body)
            if record_id.partition(":")[0] not in MAINTAINED_REFERENCE_KINDS:
                continue
            records.setdefault(record_id, {})[scenario_id] = {
                "name": record["name"],
                "contextual": bool((record.get("scope") or {}).get("scenarios")),
                "public_reference": rule_record_public_reference(
                    database, record, rules_database=rules_database,
                ),
                "summary_tokens": parse_maintained_text(record["summary"]),
            }
    properties = {
        entry["id"]: {
            "name": entry["name"], "public_reference": entry["public_reference"],
            "summary": entry["summary"],
        }
        for entry in WeaponProperties(rules_database, database=database).entries()
    }
    return {"records": records, "properties": properties}


def _target_fingerprint(db: sqlite3.Connection, body: str) -> str:
    row = db.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='searchIndex'"
    ).fetchone()
    if row is None:
        raise ValueError("Maintained reference targets require publication scope")
    return hashlib.sha256(canonical_bytes([json.loads(row[0])["scope"], body])).hexdigest()


def stage_reference_targets(db: sqlite3.Connection, targets: dict[str, Any]) -> None:
    body = canonical_bytes(targets).decode("utf-8")
    db.execute(
        "CREATE TABLE maintained_reference_targets (id INTEGER PRIMARY KEY CHECK(id=1), "
        "body TEXT NOT NULL)"
    )
    db.execute("INSERT INTO maintained_reference_targets VALUES (1,?)", (body,))
    db.execute(
        f"INSERT INTO {RULES_METADATA_TABLE} VALUES (?,?)",
        ("referenceTargetsSha256", json.dumps(_target_fingerprint(db, body))),
    )
    validate_reference_targets(db)


def read_reference_targets(db: sqlite3.Connection) -> dict[str, Any]:
    row = db.execute("SELECT body FROM maintained_reference_targets WHERE id=1").fetchone()
    if row is None:
        raise ValueError("Missing maintained reference targets")
    return json.loads(row[0])


def validate_reference_targets(db: sqlite3.Connection) -> None:
    body = db.execute("SELECT body FROM maintained_reference_targets WHERE id=1").fetchone()
    digest = db.execute(
        f"SELECT value FROM {RULES_METADATA_TABLE} WHERE key='referenceTargetsSha256'"
    ).fetchone()
    if body is None or digest is None or json.loads(digest[0]) != _target_fingerprint(db, body[0]):
        raise ValueError("Invalid maintained reference targets fingerprint")
    targets = json.loads(body[0])
    expected = {
        (record_id, context) for record_id, context in db.execute(
            "SELECT record_id,scenario_id FROM composed_rule_records"
        ) if record_id.partition(":")[0] in MAINTAINED_REFERENCE_KINDS
    }
    actual = {
        (record_id, context) for record_id, variants in targets["records"].items()
        for context in variants
    }
    if actual != expected:
        raise ValueError("Incomplete maintained reference target coverage")


class _Resolver:
    def __init__(
        self,
        database: Database,
        rules_database: RulesDatabase,
        scenario_id: str | None = None,
        *,
        local_rule_ids: frozenset[str] = frozenset(),
        additional_records: dict[str, dict[str, Any]] | None = None,
        reference_targets: dict[str, Any] | None = None,
    ) -> None:
        self.additional_records = additional_records or {}
        self.database = database
        self.rules_database = rules_database
        self.scenario_id = scenario_id
        self.local_rule_ids = local_rule_ids
        self.records: dict[str, dict[str, Any] | None] = {}
        projection = database.catalog_projection
        if (reference_targets is None and projection is not None
                and projection.path == rules_database.path):
            reference_targets = projection.reference_targets
        self.reference_targets = reference_targets
        self._properties: dict[str, dict[str, Any]] | None = (
            reference_targets["properties"] if reference_targets is not None else None
        )

    def record(self, record_id: str) -> dict[str, Any]:
        if record_id not in self.records:
            self.records[record_id] = self.rules_database.composed_record(
                record_id, include_army_links=True, scenario_id=self.scenario_id
            ) or self.additional_records.get(record_id)
        record = self.records[record_id]
        if record is None:
            raise ValueError(f"Maintained-text reference {record_id!r} is not current")
        return record

    def tokens(self, value: str, *, include_preview: bool = True) -> list[dict[str, Any]]:
        return self._resolve_tokens(parse_maintained_text(value), include_preview=include_preview)

    def _resolve_tokens(
        self, tokens: list[dict[str, Any]], *, include_preview: bool,
    ) -> list[dict[str, Any]]:
        resolved = []
        for token in tokens:
            if token["type"] != "reference":
                resolved.append(dict(token))
                continue
            if token["target"].startswith("weapon-property:"):
                if self._properties is None:
                    self._properties = {
                        entry["id"]: entry
                        for entry in WeaponProperties(
                            self.rules_database, database=self.database
                        ).entries()
                    }
                property_entry = self._properties.get(token["target"])
                if property_entry is None:
                    raise ValueError(
                        f"Maintained-text Weapon Property {token['target']!r} is not current"
                    )
                label = token.get("display_text") or property_entry["name"]
                item = {
                    "type": "reference",
                    "target": token["target"],
                    "label": label,
                    "public_reference": deepcopy(property_entry["public_reference"]),
                }
                if include_preview:
                    item["preview_tokens"] = [
                        {"type": "text", "text": property_entry["summary"]}
                    ]
                resolved.append(item)
                continue
            target = token["target"]
            prepared = None
            if self.reference_targets is not None:
                variants = self.reference_targets["records"].get(target, {})
                prepared = variants.get(self.scenario_id or "") or variants.get("")
            if prepared is not None:
                name = prepared["name"]
                contextual = prepared["contextual"]
                reference = prepared["public_reference"]
            else:
                record = self.record(target)
                name = record["name"]
                contextual = bool((record.get("scope") or {}).get("scenarios"))
                reference = None if contextual else (
                    local_rule_public_reference(record["id"], self.local_rule_ids)
                    or rule_record_public_reference(
                        self.database, record, rules_database=self.rules_database,
                    )
                )
            label = token.get("display_text") or name
            if token.get("display_form") == "plural" and not token.get("display_text"):
                label = _pluralize(label)
            if prepared is not None:
                reference = None if contextual else (
                    local_rule_public_reference(target, self.local_rule_ids) or reference
                )
            if reference is None and not contextual:
                raise ValueError(
                    f"Maintained-text reference {token['target']!r} has no public route"
                )
            item = {
                "type": "reference",
                "target": token["target"],
                "label": label,
                "public_reference": deepcopy(reference),
            }
            if include_preview:
                preview = (
                    prepared["summary_tokens"] if prepared is not None
                    else parse_maintained_text(record["summary"])
                )
                item["preview_tokens"] = self._resolve_tokens(preview, include_preview=False)
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
    for key in (
        "requirements", "effects", "restrictions", "clarifications", "rules", "sourceNotes"
    ):
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
    *,
    scenario_id: str | None = None,
) -> list[dict[str, Any]] | None:
    """Resolve one maintained-text value for a non-record reference surface."""

    if rules_database is None:
        return None
    return _Resolver(database, rules_database, scenario_id).tokens(value)


def maintained_text_tokens_batch(
    database: Database,
    rules_database: RulesDatabase | None,
    values: Iterable[str],
) -> list[list[dict[str, Any]] | None]:
    """Resolve a collection using one cache for repeated rule/property references."""

    if rules_database is None:
        return [None for _ in values]
    resolver = _Resolver(database, rules_database)
    return [resolver.tokens(value) for value in values]


def enrich_maintained_text_references(
    database: Database,
    rules_database: RulesDatabase | None,
    value: dict[str, Any],
    *,
    scenario_id: str | None = None,
    local_rule_ids: frozenset[str] = frozenset(),
    additional_records: dict[str, dict[str, Any]] | None = None,
    in_place: bool = False,
) -> dict[str, Any]:
    """Attach resolved inline-text tokens to nested rules records, copying by default."""

    result = value if in_place else deepcopy(value)
    if rules_database is None:
        return result
    resolver = _Resolver(
        database, rules_database, scenario_id, local_rule_ids=local_rule_ids,
        additional_records=additional_records,
    )

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("id"), str) and isinstance(node.get("summary"), str):
                _enrich_rule_record(node, resolver)
            elif (
                isinstance(node.get("record_id"), str)
                and node["record_id"].startswith("ammunition:")
                and isinstance(node.get("summary"), str)
            ):
                # Weapon profiles reuse canonical Ammunition text but publish
                # its identity as record_id, not as an embedded rules record.
                node["summary_tokens"] = resolver.tokens(node["summary"])
            for child in list(node.values()):
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(result)
    return result
