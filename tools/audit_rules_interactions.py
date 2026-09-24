#!/usr/bin/env python3
"""Audit maintained outgoing rules-interaction review progress."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.skill_catalog import SkillCatalog
from infinity_db.trait_catalog import TraitCatalog

REPORT_FORMAT = "InfinityDB rules interaction review"
REPORT_FORMAT_VERSION = 2
POLICY_FORMAT = "InfinityDB rules interaction review policy"
POLICY_FORMAT_VERSION = 1
CATALOG_SCOPE_FORMAT = "InfinityDB rules interaction catalog scope"
CATALOG_SCOPE_FORMAT_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_DIRECTORY = PROJECT_ROOT / "data" / "curated" / "rules"
DEFAULT_POLICY_PATH = (
    PROJECT_ROOT / "data" / "curated" / "rules-interactions" / "reviews.json"
)
DEFAULT_CHECKLIST_PATH = PROJECT_ROOT / "docs" / "rules-interaction-checklist.md"
DEFAULT_CATALOG_SCOPE_PATH = (
    PROJECT_ROOT / "data" / "curated" / "rules-interactions" / "catalog-scope.json"
)
EXCLUDED_RECORD_KINDS = frozenset({"declaration-category"})
REVIEW_STATUSES = frozenset({"pending", "reviewed", "inherited"})
FUTURE_STATUSES = frozenset({"deferred", "planned", "blocked"})
COMPLETE_STATUSES = frozenset({"reviewed", "inherited"})
PRIMARY_CATALOGS = {"skills": "skill", "equipment": "equipment", "traits": "trait"}


class RulesInteractionAuditError(ValueError):
    """Raised when the interaction-review policy is invalid or stale."""


def _require_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RulesInteractionAuditError(f"{context} must be a non-empty string")
    return value.strip()


def _load_catalog_scope(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RulesInteractionAuditError(
            f"Cannot read interaction catalog scope {path}: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise RulesInteractionAuditError("Interaction catalog scope root must be an object")
    expected = {"format", "formatVersion", "targetRelease", "catalogs"}
    if set(document) != expected:
        raise RulesInteractionAuditError(
            f"Interaction catalog scope must contain exactly {sorted(expected)}"
        )
    if document.get("format") != CATALOG_SCOPE_FORMAT:
        raise RulesInteractionAuditError(
            f"Unsupported interaction catalog scope format: {document.get('format')!r}"
        )
    if document.get("formatVersion") != CATALOG_SCOPE_FORMAT_VERSION:
        raise RulesInteractionAuditError(
            "Unsupported interaction catalog scope formatVersion: "
            f"{document.get('formatVersion')!r}"
        )
    target_release = _require_string(document.get("targetRelease"), "targetRelease")
    raw_catalogs = document.get("catalogs")
    if not isinstance(raw_catalogs, dict) or set(raw_catalogs) != set(PRIMARY_CATALOGS):
        raise RulesInteractionAuditError(
            "Interaction catalog scope catalogs must contain exactly "
            f"{sorted(PRIMARY_CATALOGS)}"
        )
    catalogs: dict[str, list[dict[str, str]]] = {}
    for catalog in PRIMARY_CATALOGS:
        raw_items = raw_catalogs.get(catalog)
        if not isinstance(raw_items, list):
            raise RulesInteractionAuditError(f"catalogs.{catalog} must be an array")
        seen: set[str] = set()
        items: list[dict[str, str]] = []
        for index, raw in enumerate(raw_items):
            context = f"catalogs.{catalog}[{index}]"
            if not isinstance(raw, dict) or set(raw) != {"id", "name"}:
                raise RulesInteractionAuditError(
                    f"{context} must contain exactly id and name"
                )
            item_id = _require_string(raw.get("id"), f"{context}.id")
            name = _require_string(raw.get("name"), f"{context}.name")
            if item_id in seen:
                raise RulesInteractionAuditError(
                    f"Duplicate {catalog} catalog-scope id {item_id!r}"
                )
            seen.add(item_id)
            items.append({"id": item_id, "name": name})
        catalogs[catalog] = items
    return {
        "format": CATALOG_SCOPE_FORMAT,
        "formatVersion": CATALOG_SCOPE_FORMAT_VERSION,
        "targetRelease": target_release,
        "catalogs": catalogs,
    }


def _catalog_scope_from_databases(
    database_path: Path,
    rules_database_path: Path,
    *,
    target_release: str,
) -> dict[str, Any]:
    try:
        database = Database(database_path)
        database.validate()
        rules = RulesDatabase(rules_database_path)
        rules.validate()
        skills = SkillCatalog(database, rules).list_skills()
        traits = TraitCatalog(database, rules).list_traits()
        equipment: list[dict[str, str]] = []
        for item in database.list_catalog_items("equipment"):
            slug = database.application_slug("equipment", int(item["id"]))
            if slug is None:
                raise RulesInteractionAuditError(
                    f"Equipment catalog item {item['id']!r} has no public application slug"
                )
            equipment.append({"id": slug, "name": str(item["name"])})
    except (OSError, ValueError) as exc:
        if isinstance(exc, RulesInteractionAuditError):
            raise
        raise RulesInteractionAuditError(str(exc)) from exc

    def ordered(items: list[dict[str, str]]) -> list[dict[str, str]]:
        return sorted(items, key=lambda item: (item["name"].casefold(), item["id"]))

    return {
        "format": CATALOG_SCOPE_FORMAT,
        "formatVersion": CATALOG_SCOPE_FORMAT_VERSION,
        "targetRelease": target_release,
        "catalogs": {
            "skills": ordered(
                [{"id": str(item["slug"]), "name": str(item["name"])} for item in skills]
            ),
            "equipment": ordered(equipment),
            "traits": ordered(
                [{"id": str(item["slug"]), "name": str(item["name"])} for item in traits]
            ),
        },
    }


def _write_catalog_scope(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _semantic_records(rules_directory: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for _path, document in load_curated_directory(rules_directory):
        for raw in document["records"]:
            if raw["kind"] in EXCLUDED_RECORD_KINDS:
                continue
            record_id = str(raw["id"])
            existing = records.get(record_id)
            if existing is None:
                existing = {
                    "id": record_id,
                    "kind": str(raw["kind"]),
                    "name": str(raw["name"]),
                    "relations": [],
                    "sourceVariant": False,
                }
                records[record_id] = existing
            elif (existing["kind"], existing["name"]) != (raw["kind"], raw["name"]):
                raise RulesInteractionAuditError(
                    f"Semantic record {record_id!r} changes kind/name across contributions"
                )
            semantics = raw.get("variantSemantics")
            if isinstance(semantics, dict) and semantics.get("inheritance") == "source":
                existing["sourceVariant"] = True
            for relation in raw.get("relations", []):
                pair = (str(relation["type"]), str(relation["recordId"]))
                if pair not in existing["relations"]:
                    existing["relations"].append(pair)
    return records


def _load_policy(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RulesInteractionAuditError(
            f"Cannot read interaction-review policy {path}: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise RulesInteractionAuditError("Interaction-review policy root must be an object")
    expected_root = {"format", "formatVersion", "records", "futureInteractions"}
    if set(document) != expected_root:
        raise RulesInteractionAuditError(
            "Interaction-review policy must contain exactly "
            "format, formatVersion, records, and futureInteractions"
        )
    if document.get("format") != POLICY_FORMAT:
        raise RulesInteractionAuditError(
            "Unsupported interaction-review format: "
            f"{document.get('format')!r}"
        )
    if document.get("formatVersion") != POLICY_FORMAT_VERSION:
        raise RulesInteractionAuditError(
            f"Unsupported interaction-review formatVersion: {document.get('formatVersion')!r}"
        )
    raw_records = document.get("records")
    if not isinstance(raw_records, list):
        raise RulesInteractionAuditError("Interaction-review records must be an array")

    records: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_records):
        context = f"records[{index}]"
        if not isinstance(raw, dict):
            raise RulesInteractionAuditError(f"{context} must be an object")
        allowed = {
            "recordId",
            "targetRelease",
            "status",
            "reviewedOn",
            "note",
        }
        unknown = set(raw) - allowed
        missing = {"recordId", "targetRelease", "status"} - set(raw)
        if unknown or missing:
            raise RulesInteractionAuditError(
                f"{context} fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}"
            )
        record_id = _require_string(raw.get("recordId"), f"{context}.recordId")
        if record_id in records:
            raise RulesInteractionAuditError(f"Duplicate interaction-review record {record_id!r}")
        target_release = _require_string(raw.get("targetRelease"), f"{context}.targetRelease")
        status = raw.get("status")
        if status not in REVIEW_STATUSES:
            raise RulesInteractionAuditError(
                f"{context}.status must be one of {sorted(REVIEW_STATUSES)}"
            )
        reviewed_on = raw.get("reviewedOn")
        if status in COMPLETE_STATUSES:
            _require_string(reviewed_on, f"{context}.reviewedOn")
        elif reviewed_on is not None:
            raise RulesInteractionAuditError(
                f"{context}.reviewedOn is only valid for completed reviews"
            )
        note = raw.get("note")
        if note is not None:
            _require_string(note, f"{context}.note")
        records[record_id] = {
            "recordId": record_id,
            "targetRelease": target_release,
            "status": status,
            "reviewedOn": reviewed_on,
            "note": note,
        }

    raw_future = document.get("futureInteractions")
    if not isinstance(raw_future, list):
        raise RulesInteractionAuditError("futureInteractions must be an array")
    future: list[dict[str, Any]] = []
    seen_future: set[tuple[str, str, str]] = set()
    for index, candidate in enumerate(raw_future):
        context = f"futureInteractions[{index}]"
        if not isinstance(candidate, dict):
            raise RulesInteractionAuditError(f"{context} must be an object")
        expected = {
            "sourceRecordId",
            "targetRecordId",
            "relationType",
            "targetRelease",
            "status",
            "reason",
        }
        if set(candidate) != expected:
            raise RulesInteractionAuditError(
                f"{context} must contain exactly {sorted(expected)}"
            )
        source_id = _require_string(
            candidate.get("sourceRecordId"), f"{context}.sourceRecordId"
        )
        target_id = _require_string(
            candidate.get("targetRecordId"), f"{context}.targetRecordId"
        )
        relation_type = candidate.get("relationType")
        if relation_type is not None:
            relation_type = _require_string(relation_type, f"{context}.relationType")
        target_release = _require_string(
            candidate.get("targetRelease"), f"{context}.targetRelease"
        )
        status = candidate.get("status")
        if status not in FUTURE_STATUSES:
            raise RulesInteractionAuditError(
                f"{context}.status must be one of {sorted(FUTURE_STATUSES)}"
            )
        reason = _require_string(candidate.get("reason"), f"{context}.reason")
        key = (source_id, target_id, relation_type or "")
        if key in seen_future:
            raise RulesInteractionAuditError(f"{context} duplicates {key!r}")
        seen_future.add(key)
        future.append(
            {
                "sourceRecordId": source_id,
                "targetRecordId": target_id,
                "relationType": relation_type,
                "targetRelease": target_release,
                "status": status,
                "reason": reason,
            }
        )
    return {"records": records, "futureInteractions": future}


def audit_rules_interactions(
    rules_directory: Path = DEFAULT_RULES_DIRECTORY,
    policy_path: Path = DEFAULT_POLICY_PATH,
    catalog_scope_path: Path = DEFAULT_CATALOG_SCOPE_PATH,
) -> dict[str, Any]:
    semantic = _semantic_records(rules_directory)
    policy_document = _load_policy(policy_path)
    policy = policy_document["records"]
    future_interactions = policy_document["futureInteractions"]
    catalog_scope = _load_catalog_scope(catalog_scope_path)
    missing = sorted(set(semantic) - set(policy))
    extra = sorted(set(policy) - set(semantic))
    if missing or extra:
        raise RulesInteractionAuditError(
            f"Interaction-review coverage mismatch; missing={missing}, extra={extra}"
        )

    future_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in future_interactions:
        future_by_source[candidate["sourceRecordId"]].append(candidate)

    record_items: list[dict[str, Any]] = []
    release_summary: dict[str, Counter[str]] = defaultdict(Counter)
    kind_summary: dict[str, Counter[str]] = defaultdict(Counter)
    ordered_ids = sorted(
        semantic,
        key=lambda value: (
            semantic[value]["kind"],
            semantic[value]["name"].casefold(),
            value,
        ),
    )
    for record_id in ordered_ids:
        record = semantic[record_id]
        review = policy[record_id]
        if review["status"] == "inherited" and not record["sourceVariant"]:
            raise RulesInteractionAuditError(
                f"{record_id}: inherited review status requires a source-specific variant"
            )
        release_summary[review["targetRelease"]][review["status"]] += 1
        kind_summary[record["kind"]][review["status"]] += 1
        record_items.append(
            {
                **record,
                **review,
                "futureInteractions": future_by_source.get(record_id, []),
            }
        )

    primary_record_ids: set[str] = set()
    primary_items: list[dict[str, Any]] = []
    catalog_summary: dict[str, dict[str, int | float]] = {}
    target_release = catalog_scope["targetRelease"]
    for catalog, kind in PRIMARY_CATALOGS.items():
        catalog_items: list[dict[str, Any]] = []
        for scoped in catalog_scope["catalogs"][catalog]:
            record_id = f"{kind}:{scoped['id']}"
            primary_record_ids.add(record_id)
            record = semantic.get(record_id)
            if record is None:
                item = {
                    "id": record_id,
                    "catalog": catalog,
                    "catalogId": scoped["id"],
                    "kind": kind,
                    "name": scoped["name"],
                    "relations": [],
                    "sourceVariant": False,
                    "recordDefined": False,
                    "targetRelease": target_release,
                    "status": "pending",
                    "reviewedOn": None,
                    "note": "No curated rules definition yet.",
                    "futureInteractions": future_by_source.get(record_id, []),
                }
            else:
                review = policy[record_id]
                if review["targetRelease"] != target_release:
                    raise RulesInteractionAuditError(
                        f"{record_id}: primary {catalog} catalog review targets "
                        f"{review['targetRelease']!r}, expected {target_release!r}"
                    )
                if review["status"] == "inherited":
                    raise RulesInteractionAuditError(
                        f"{record_id}: primary catalog identities cannot use inherited status"
                    )
                item = {
                    **record,
                    **review,
                    "catalog": catalog,
                    "catalogId": scoped["id"],
                    "name": scoped["name"],
                    "recordDefined": True,
                    "futureInteractions": future_by_source.get(record_id, []),
                }
            catalog_items.append(item)
            primary_items.append(item)
        total = len(catalog_items)
        complete = sum(item["status"] in COMPLETE_STATUSES for item in catalog_items)
        defined = sum(bool(item["recordDefined"]) for item in catalog_items)
        catalog_summary[catalog] = {
            "total": total,
            "complete": complete,
            "pending": total - complete,
            "defined": defined,
            "missingRuleDefinition": total - defined,
            "percentComplete": round(100.0 * complete / total, 1) if total else 100.0,
        }

    primary_total = sum(int(values["total"]) for values in catalog_summary.values())
    primary_complete = sum(int(values["complete"]) for values in catalog_summary.values())
    supporting_items = [item for item in record_items if item["id"] not in primary_record_ids]
    supporting_complete = sum(
        item["status"] in COMPLETE_STATUSES for item in supporting_items
    )
    supporting_by_release: dict[str, Counter[str]] = defaultdict(Counter)
    supporting_by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    for item in supporting_items:
        supporting_by_release[item["targetRelease"]][item["status"]] += 1
        supporting_by_kind[item["kind"]][item["status"]] += 1

    def summarize_counts(counts: Counter[str]) -> dict[str, int | float]:
        total = sum(counts.values())
        complete = sum(counts[status] for status in COMPLETE_STATUSES)
        return {
            "total": total,
            "complete": complete,
            "pending": counts["pending"],
            "reviewed": counts["reviewed"],
            "inherited": counts["inherited"],
            "percentComplete": round(100.0 * complete / total, 1) if total else 100.0,
        }

    releases = {
        release: summarize_counts(counts)
        for release, counts in sorted(release_summary.items())
    }
    kinds = {
        kind: {
            "total": sum(counts.values()),
            "complete": sum(counts[status] for status in COMPLETE_STATUSES),
            "pending": counts["pending"],
        }
        for kind, counts in sorted(kind_summary.items())
    }
    supporting_releases = {
        release: summarize_counts(counts)
        for release, counts in sorted(supporting_by_release.items())
    }
    supporting_kinds = {
        kind: {
            "total": sum(counts.values()),
            "complete": sum(counts[status] for status in COMPLETE_STATUSES),
            "pending": counts["pending"],
        }
        for kind, counts in sorted(supporting_by_kind.items())
    }

    return {
        "format": REPORT_FORMAT,
        "formatVersion": REPORT_FORMAT_VERSION,
        "summary": {
            "recordCount": len(record_items),
            "authoredOutgoingRelationCount": sum(
                len(item["relations"]) for item in record_items
            ),
            "futureInteractionCount": len(future_interactions),
            "releases": releases,
            "kinds": kinds,
            "primaryCatalog": {
                "targetRelease": target_release,
                "total": primary_total,
                "complete": primary_complete,
                "pending": primary_total - primary_complete,
                "percentComplete": (
                    round(100.0 * primary_complete / primary_total, 1)
                    if primary_total
                    else 100.0
                ),
                "catalogs": catalog_summary,
            },
            "supporting": {
                "total": len(supporting_items),
                "complete": supporting_complete,
                "pending": len(supporting_items) - supporting_complete,
                "releases": supporting_releases,
                "kinds": supporting_kinds,
            },
        },
        "items": record_items,
        "primaryCatalogItems": primary_items,
        "supportingItems": supporting_items,
        "catalogScope": catalog_scope,
        "futureInteractions": future_interactions,
    }

def _record_label(record_id: str, labels: dict[str, str]) -> str:
    name = labels.get(record_id)
    if name is None:
        return f"`{record_id}`"
    return f"{name} (`{record_id}`)"


def _append_item(
    lines: list[str],
    item: dict[str, Any],
    labels: dict[str, str],
    *,
    show_missing_definition: bool = False,
) -> None:
    checked = "x" if item["status"] in COMPLETE_STATUSES else " "
    suffix = f" — {item['status']}"
    if item.get("note"):
        suffix += f": {item['note']}"
    lines.append(f"- [{checked}] **{item['name']}** (`{item['id']}`){suffix}")
    if show_missing_definition and not item.get("recordDefined", True):
        lines.append("  - rules definition: missing; outgoing interactions not yet reviewable")
    elif item["relations"]:
        for relation_type, target_id in item["relations"]:
            lines.append(f"  - `{relation_type}` → {_record_label(target_id, labels)}")
    else:
        lines.append("  - outgoing: none")
    for future in item["futureInteractions"]:
        rel = future["relationType"] or "relation type TBD"
        lines.append(
            f"  - future [{future['targetRelease']}; {future['status']}]: "
            f"`{rel}` → {_record_label(future['targetRecordId'], labels)} — "
            f"{future['reason']}"
        )


def render_markdown(report: dict[str, Any]) -> str:
    record_items = report["items"]
    primary_items = report["primaryCatalogItems"]
    supporting_items = report["supportingItems"]
    labels = {item["id"]: item["name"] for item in record_items}
    labels.update({item["id"]: item["name"] for item in primary_items})
    lines = [
        "# Rules interaction review checklist",
        "",
        "This file is generated from the maintained public-catalog scope, interaction-review",
        "policy, and current curated rules graph. Do not edit it by hand. Regenerate it with:",
        "",
        "```powershell",
        "python tools/audit_rules_interactions.py --output docs/rules-interaction-checklist.md",
        "```",
        "",
        "The **0.7.0 progress gate is catalog-based**: every public Skill, Equipment item, and",
        "Trait is listed, including entries that do not yet have a curated rules definition.",
        "A catalog item is complete only when its canonical rules identity exists and its",
        "outgoing interaction semantics have been reviewed. Missing rules definitions therefore",
        "remain visibly pending instead of disappearing from the denominator.",
        "",
        "Exact source variants plus independently modeled Rule, State, Training, supporting",
        "Trait, and curated Weapon identities are tracked separately as supporting semantics.",
        "Ordinary Weapon catalog rows are covered through their Skill/Trait behavior rather than",
        "audited one-by-one; a Weapon with its own curated rules definition remains in supporting",
        "review. `declaration-category` projection records are excluded.",
        "",
        "## Progress",
        "",
    ]
    summary = report["summary"]
    primary = summary["primaryCatalog"]
    lines.append(
        f"- **{primary['targetRelease']} primary catalog: {primary['complete']}/"
        f"{primary['total']} complete ({primary['percentComplete']:.1f}%), "
        f"{primary['pending']} pending.**"
    )
    domain_parts = []
    for catalog in PRIMARY_CATALOGS:
        values = primary["catalogs"][catalog]
        domain_parts.append(
            f"{PRIMARY_CATALOGS[catalog].title()} **{values['complete']}/{values['total']}**"
        )
    lines.append("- Primary domains: " + "; ".join(domain_parts) + ".")
    supporting = summary["supporting"]
    lines.append(
        f"- Supporting semantic identities: **{supporting['complete']}/"
        f"{supporting['total']}** complete, **{supporting['pending']}** pending."
    )
    lines.extend(
        [
            "- Current authored outgoing relations: "
            f"**{summary['authoredOutgoingRelationCount']}**.",
            "- Explicitly tracked future/deferred interactions: "
            f"**{summary['futureInteractionCount']}**.",
            "",
            f"## {primary['targetRelease']} primary catalog review",
            "",
        ]
    )

    by_catalog: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in primary_items:
        by_catalog[item["catalog"]].append(item)
    for catalog, kind in PRIMARY_CATALOGS.items():
        catalog_items = by_catalog[catalog]
        values = primary["catalogs"][catalog]
        lines.extend(
            [
                f"### {kind.title()} ({values['complete']}/{values['total']})",
                "",
            ]
        )
        for item in catalog_items:
            _append_item(lines, item, labels, show_missing_definition=True)
        lines.append("")

    lines.extend(["## Supporting rules-identity review", ""])
    by_release: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in supporting_items:
        by_release[item["targetRelease"]].append(item)
    for release in sorted(by_release):
        lines.extend([f"### {release}", ""])
        by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in by_release[release]:
            by_kind[item["kind"]].append(item)
        for kind in sorted(by_kind):
            kind_items = by_kind[kind]
            complete = sum(item["status"] in COMPLETE_STATUSES for item in kind_items)
            lines.extend([f"#### {kind.title()} ({complete}/{len(kind_items)})", ""])
            for item in kind_items:
                _append_item(lines, item, labels)
            lines.append("")

    future_items = report["futureInteractions"]
    lines.extend(["## Future interaction queue", ""])
    if not future_items:
        lines.append("No future interactions are currently tracked.")
    else:
        for future in sorted(
            future_items,
            key=lambda candidate: (
                candidate["targetRelease"],
                candidate["sourceRecordId"],
                candidate["targetRecordId"],
            ),
        ):
            rel = future["relationType"] or "relation type TBD"
            lines.append(
                f"- [ ] {_record_label(future['sourceRecordId'], labels)} → "
                f"{_record_label(future['targetRecordId'], labels)}; `{rel}`; "
                f"**{future['targetRelease']} / {future['status']}** — {future['reason']}"
            )
    lines.append("")
    return "\n".join(lines)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit and render outgoing rules-interaction review progress."
    )
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES_DIRECTORY)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--catalog-scope", type=Path, default=DEFAULT_CATALOG_SCOPE_PATH)
    parser.add_argument("--output", type=Path, help="Write the generated Markdown checklist.")
    parser.add_argument(
        "--check-output",
        type=Path,
        help="Fail if this committed Markdown checklist differs from generated output.",
    )
    parser.add_argument(
        "--require-release",
        help="Fail if the named release still has pending catalog/supporting reviews.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="Validate the maintained catalog scope against this application database.",
    )
    parser.add_argument(
        "--rules-database",
        type=Path,
        help="Rules database paired with --database for public Skill/Trait composition.",
    )
    parser.add_argument(
        "--refresh-catalog-scope",
        action="store_true",
        help="Rewrite --catalog-scope from --database and --rules-database before auditing.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if (
            args.refresh_catalog_scope
            or args.database is not None
            or args.rules_database is not None
        ):
            if args.database is None or args.rules_database is None:
                raise RulesInteractionAuditError(
                    "--database and --rules-database must be supplied together"
                )
            current_scope = _load_catalog_scope(args.catalog_scope)
            runtime_scope = _catalog_scope_from_databases(
                args.database,
                args.rules_database,
                target_release=current_scope["targetRelease"],
            )
            if args.refresh_catalog_scope:
                _write_catalog_scope(args.catalog_scope, runtime_scope)
                print(f"Rules interaction catalog scope written: {args.catalog_scope}")
            elif runtime_scope != current_scope:
                raise RulesInteractionAuditError(
                    "Maintained interaction catalog scope differs from the supplied runtime "
                    "catalogs; refresh it with --refresh-catalog-scope"
                )
        report = audit_rules_interactions(args.rules, args.policy, args.catalog_scope)
        markdown = render_markdown(report)
    except RulesInteractionAuditError as exc:
        print(f"Rules interaction audit failed: {exc}")
        return 2

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8", newline="\n")
        print(f"Rules interaction checklist written: {args.output}")
    if args.check_output is not None:
        try:
            current = args.check_output.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Rules interaction checklist check failed: {exc}")
            return 2
        if current.replace("\r\n", "\n") != markdown:
            print(
                "Rules interaction checklist is stale; regenerate with "
                "tools/audit_rules_interactions.py --output "
                f"{args.check_output}"
            )
            return 1

    primary = report["summary"]["primaryCatalog"]
    print(
        f"{primary['targetRelease']} primary catalog: {primary['complete']}/"
        f"{primary['total']} complete ({primary['percentComplete']:.1f}%), "
        f"{primary['pending']} pending"
    )
    supporting = report["summary"]["supporting"]
    print(
        f"Supporting identities: {supporting['complete']}/{supporting['total']} complete, "
        f"{supporting['pending']} pending"
    )
    print(
        f"Outgoing relations: {report['summary']['authoredOutgoingRelationCount']}; "
        f"future interactions: {report['summary']['futureInteractionCount']}"
    )
    if args.require_release is not None:
        if args.require_release != primary["targetRelease"]:
            releases = report["summary"]["supporting"]["releases"]
            release = releases.get(args.require_release)
            if release is None:
                print(f"Unknown tracked release: {args.require_release}")
                return 2
            if release["pending"]:
                print(
                    f"Release {args.require_release} is not interaction-review complete: "
                    f"{release['pending']} supporting identities pending"
                )
                return 1
        else:
            support_release = report["summary"]["supporting"]["releases"].get(
                args.require_release, {"pending": 0}
            )
            primary_pending = int(primary["pending"])
            supporting_pending = int(support_release["pending"])
            if primary_pending or supporting_pending:
                print(
                    f"Release {args.require_release} is not interaction-review complete: "
                    f"{primary_pending} primary catalog items and "
                    f"{supporting_pending} supporting identities pending"
                )
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
