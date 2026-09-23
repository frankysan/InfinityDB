#!/usr/bin/env python3
"""Audit user-facing catalog coverage against the current curated rules snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from infinity_db.catalog_rules import CatalogRules
from infinity_db.catalog_slugs import attach_public_catalog_slug
from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.skill_catalog import SkillCatalog
from infinity_db.state_catalog import StateCatalog
from infinity_db.trait_catalog import TraitCatalog

REPORT_FORMAT = "InfinityDB rules enrichment coverage audit"
REPORT_FORMAT_VERSION = 3
CATALOGS = ("skills", "equipment", "weapons", "traits", "states")
CLASSIFICATION_FORMAT = "InfinityDB enrichment coverage classifications"
CLASSIFICATION_FORMAT_VERSION = 1
CLASSIFICATIONS = frozenset(
    {"release-blocker", "intentional-omission", "supporting-identity", "later-product-work"}
)
KNOWN_GAP_CODES = frozenset(
    {
        "ambiguous_family_mapping",
        "ambiguous_source_variant_mapping",
        "missing_citation",
        "missing_rule_definition",
        "stale_citation_source",
        "unresolved_related_item_link",
        "unresolved_surface_rule",
        "unreviewed_rule",
    }
)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLASSIFICATION_PATH = (
    PROJECT_ROOT / "data" / "curated" / "enrichment-coverage" / "classifications.json"
)
ENTITY_BY_CATALOG = {"skills": "skill", "equipment": "equipment", "weapons": "weapon"}
CATALOG_BY_KIND = {**{value: key for key, value in ENTITY_BY_CATALOG.items()}, "state": "states"}


class EnrichmentCoverageAuditError(ValueError):
    """Raised when the selected application/rules snapshots cannot be audited safely."""



def _classification_decision(value: object, context: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"classification", "reason"}:
        raise EnrichmentCoverageAuditError(
            f"{context} must contain exactly classification and reason"
        )
    classification = value.get("classification")
    reason = value.get("reason")
    if classification not in CLASSIFICATIONS:
        raise EnrichmentCoverageAuditError(
            f"{context}.classification must be one of {sorted(CLASSIFICATIONS)}"
        )
    if not isinstance(reason, str) or not reason.strip():
        raise EnrichmentCoverageAuditError(f"{context}.reason must be a non-empty string")
    return {"classification": str(classification), "reason": reason.strip()}


def _load_classification_policy(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise EnrichmentCoverageAuditError(
            f"Enrichment coverage classification policy does not exist: {path}"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EnrichmentCoverageAuditError(
            f"Cannot read enrichment coverage classification policy {path}: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise EnrichmentCoverageAuditError("Classification policy root must be an object")
    expected = {"format", "formatVersion", "gapCodes", "supportingIdentity", "overrides"}
    if set(document) != expected:
        raise EnrichmentCoverageAuditError(
            f"Classification policy must contain exactly {sorted(expected)}"
        )
    if document.get("format") != CLASSIFICATION_FORMAT:
        raise EnrichmentCoverageAuditError(
            f"Unsupported classification policy format: {document.get('format')!r}"
        )
    if document.get("formatVersion") != CLASSIFICATION_FORMAT_VERSION:
        raise EnrichmentCoverageAuditError(
            "Unsupported classification policy formatVersion: "
            f"{document.get('formatVersion')!r}"
        )

    raw_gap_codes = document.get("gapCodes")
    if not isinstance(raw_gap_codes, dict):
        raise EnrichmentCoverageAuditError("Classification policy gapCodes must be an object")
    actual_codes = set(raw_gap_codes)
    if actual_codes != KNOWN_GAP_CODES:
        missing = sorted(KNOWN_GAP_CODES - actual_codes)
        extra = sorted(actual_codes - KNOWN_GAP_CODES)
        raise EnrichmentCoverageAuditError(
            f"Classification policy gapCodes mismatch; missing={missing}, extra={extra}"
        )
    gap_codes = {
        code: _classification_decision(raw_gap_codes[code], f"gapCodes.{code}")
        for code in sorted(KNOWN_GAP_CODES)
    }
    supporting = _classification_decision(
        document.get("supportingIdentity"), "supportingIdentity"
    )
    if supporting["classification"] != "supporting-identity":
        raise EnrichmentCoverageAuditError(
            "supportingIdentity.classification must be supporting-identity"
        )

    raw_overrides = document.get("overrides")
    if not isinstance(raw_overrides, list):
        raise EnrichmentCoverageAuditError("Classification policy overrides must be an array")
    catalog_overrides: dict[tuple[str, str, str], dict[str, str]] = {}
    relation_overrides: dict[tuple[str, str, str], dict[str, str]] = {}
    override_keys: set[tuple[str, ...]] = set()
    for position, raw in enumerate(raw_overrides):
        context = f"overrides[{position}]"
        if not isinstance(raw, dict):
            raise EnrichmentCoverageAuditError(f"{context} must be an object")
        scope = raw.get("scope")
        if scope == "catalog":
            expected_override = {
                "scope", "catalog", "itemId", "gapCode", "classification", "reason"
            }
            if set(raw) != expected_override:
                raise EnrichmentCoverageAuditError(
                    f"{context} catalog override must contain exactly {sorted(expected_override)}"
                )
            catalog = raw.get("catalog")
            gap_code = raw.get("gapCode")
            item_id = raw.get("itemId")
            if catalog not in CATALOGS:
                raise EnrichmentCoverageAuditError(
                    f"{context}.catalog must be one of {list(CATALOGS)}"
                )
            if gap_code not in KNOWN_GAP_CODES - {"unresolved_related_item_link"}:
                raise EnrichmentCoverageAuditError(
                    f"{context}.gapCode is not a catalog gap code: {gap_code!r}"
                )
            if isinstance(item_id, bool) or not isinstance(item_id, (int, str)) or not str(item_id):
                raise EnrichmentCoverageAuditError(
                    f"{context}.itemId must be a non-empty string or integer"
                )
            decision = _classification_decision(
                {"classification": raw.get("classification"), "reason": raw.get("reason")},
                context,
            )
            key = (str(catalog), str(item_id), str(gap_code))
            if key in catalog_overrides:
                raise EnrichmentCoverageAuditError(f"Duplicate catalog override: {key}")
            catalog_overrides[key] = decision
            override_keys.add(("catalog", *key))
        elif scope == "relation":
            expected_override = {
                "scope", "recordId", "relationType", "targetRecordId",
                "classification", "reason"
            }
            if set(raw) != expected_override:
                raise EnrichmentCoverageAuditError(
                    f"{context} relation override must contain exactly {sorted(expected_override)}"
                )
            record_id = raw.get("recordId")
            relation_type = raw.get("relationType")
            target_id = raw.get("targetRecordId")
            if not all(
                isinstance(value, str) and value.strip()
                for value in (record_id, relation_type, target_id)
            ):
                raise EnrichmentCoverageAuditError(
                    f"{context} relation selectors must be non-empty strings"
                )
            decision = _classification_decision(
                {"classification": raw.get("classification"), "reason": raw.get("reason")},
                context,
            )
            key = (str(record_id), str(relation_type), str(target_id))
            if key in relation_overrides:
                raise EnrichmentCoverageAuditError(f"Duplicate relation override: {key}")
            relation_overrides[key] = decision
            override_keys.add(("relation", *key))
        else:
            raise EnrichmentCoverageAuditError(
                f"{context}.scope must be catalog or relation"
            )

    return {
        "gapCodes": gap_codes,
        "supportingIdentity": supporting,
        "catalogOverrides": catalog_overrides,
        "relationOverrides": relation_overrides,
        "overrideKeys": override_keys,
    }


def _catalog_gap_classification(
    policy: dict[str, Any],
    matched_overrides: set[tuple[str, ...]],
    catalog: str,
    item_id: object,
    gap_code: str,
) -> dict[str, str]:
    key = (catalog, str(item_id), gap_code)
    override = policy["catalogOverrides"].get(key)
    if override is not None:
        matched_overrides.add(("catalog", *key))
        return {"code": gap_code, **override, "source": "override"}
    return {"code": gap_code, **policy["gapCodes"][gap_code], "source": "gap-code"}


def _relation_gap_classification(
    policy: dict[str, Any],
    matched_overrides: set[tuple[str, ...]],
    gap: dict[str, Any],
) -> dict[str, str]:
    key = (str(gap["recordId"]), str(gap["relationType"]), str(gap["targetRecordId"]))
    override = policy["relationOverrides"].get(key)
    if override is not None:
        matched_overrides.add(("relation", *key))
        return {**override, "source": "override"}
    return {
        **policy["gapCodes"]["unresolved_related_item_link"],
        "source": "gap-code",
    }

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _rules_version(value: object) -> str | None:
    text = str(value or "").strip()
    match = re.search(r"(?:\bN|\bv)(\d+\.\d+)\b", text, re.IGNORECASE)
    if match:
        return match.group(1)
    if re.fullmatch(r"\d+\.\d+", text):
        return text
    return None


def _rules_index(path: Path) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], list[str]]]:
    records: dict[str, dict[str, Any]] = {}
    links: dict[tuple[str, str], list[str]] = {}
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT r.*, c.title AS collection_title FROM records AS r "
            "JOIN collections AS c ON c.id = r.collection_id "
            "WHERE c.status = 'current' "
            "ORDER BY r.id, CASE r.composition_role WHEN 'definition' THEN 0 ELSE 1 END, "
            "r.collection_id"
        ).fetchall()
        for row in rows:
            record = records.setdefault(
                row["id"],
                {
                    "id": row["id"],
                    "kind": row["kind"],
                    "name": row["name"],
                    "reviewContributions": [],
                    "variant": None,
                    "citations": [],
                    "relations": [],
                    "links": [],
                },
            )
            review = _json(row["review_json"], None)
            record["reviewContributions"].append(
                {
                    "collectionTitle": row["collection_title"],
                    "collectionVersion": _rules_version(row["collection_title"]),
                    "review": review,
                }
            )
            if row["composition_role"] == "definition":
                record["variant"] = _json(row["variant_json"], None)
            for citation in connection.execute(
                "SELECT s.id AS source_id, s.title AS source_title, s.version AS source_version, "
                "s.authority, c.page, c.member, c.heading, c.section "
                "FROM record_citations AS c JOIN sources AS s "
                "ON s.collection_id = c.collection_id AND s.id = c.source_id "
                "WHERE c.collection_id = ? AND c.record_id = ? ORDER BY c.position",
                (row["collection_id"], row["id"]),
            ):
                item = dict(citation)
                item["collection_version"] = _rules_version(row["collection_title"])
                record["citations"].append(item)
            for relation in connection.execute(
                "SELECT relation_type, related_record_id FROM record_relations "
                "WHERE collection_id = ? AND record_id = ? ORDER BY position",
                (row["collection_id"], row["id"]),
            ):
                item = {
                    "type": relation["relation_type"],
                    "recordId": relation["related_record_id"],
                }
                if item not in record["relations"]:
                    record["relations"].append(item)
            for link in connection.execute(
                "SELECT entity, external_id FROM record_army_links "
                "WHERE collection_id = ? AND record_id = ? ORDER BY position",
                (row["collection_id"], row["id"]),
            ):
                item = {"entity": link["entity"], "id": link["external_id"]}
                if item not in record["links"]:
                    record["links"].append(item)
                key = (str(link["entity"]), str(link["external_id"]))
                if row["id"] not in links.setdefault(key, []):
                    links[key].append(row["id"])
    return records, links


def _record_gap_codes(record: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    reviews = record.get("reviewContributions", [])
    if not reviews or any(
        not isinstance(item.get("review"), dict)
        or item["review"].get("status") != "reviewed"
        for item in reviews
    ):
        gaps.append("unreviewed_rule")
    if not record.get("citations"):
        gaps.append("missing_citation")
    for citation in record.get("citations", []):
        current_version = citation.get("collection_version")
        source_version = _rules_version(citation.get("source_version"))
        if current_version and source_version and source_version != current_version:
            gaps.append("stale_citation_source")
            break
    return gaps


def _surface_rule_ids(detail: dict[str, Any]) -> tuple[set[str], set[str]]:
    family = {str(record["id"]) for record in detail.get("rules", [])}
    exact: set[str] = set()
    for variant in detail.get("variants", []):
        exact.update(str(record["id"]) for record in variant.get("rules", []))
    return family, exact


def audit_coverage(
    database_path: Path,
    rules_path: Path,
    *,
    include_complete: bool = False,
    classification_path: Path = DEFAULT_CLASSIFICATION_PATH,
) -> dict[str, Any]:
    if not database_path.is_file():
        raise EnrichmentCoverageAuditError(f"Database does not exist: {database_path}")
    if not rules_path.is_file():
        raise EnrichmentCoverageAuditError(f"Rules database does not exist: {rules_path}")

    try:
        database = Database(database_path)
        database.validate()
        rules = RulesDatabase(rules_path)
        rules.validate()
        records, links = _rules_index(rules_path)
        classification_policy = _load_classification_policy(classification_path)
        matched_overrides: set[tuple[str, ...]] = set()
        skill_catalog = SkillCatalog(database, rules)
        catalog_rules = CatalogRules(rules)
        trait_catalog = TraitCatalog(database, rules)
        state_catalog = StateCatalog(rules)

        exposed_rule_ids: set[str] = set()
        exposed_trait_rule_ids: set[str] = set()
        domain_reports: dict[str, Any] = {}

        for catalog in CATALOGS:
            items: list[dict[str, Any]] = []
            if catalog == "traits":
                sources = trait_catalog.list_traits()
            elif catalog == "states":
                sources = state_catalog.list_states()
            elif catalog == "skills":
                sources = skill_catalog.list_skills()
            else:
                sources = database.list_catalog_items(catalog)

            for source in sources:
                if catalog == "skills":
                    source_ref = source["id"]
                    detail = skill_catalog.get_skill(source_ref) or {}
                    slug = str(source.get("slug") or "") or None
                    source_ids = [
                        int(value)
                        for value in source.get("source_ids", [])
                        if str(value).isdecimal()
                    ]
                    family_ids, exact_ids = _surface_rule_ids(detail)
                elif catalog in {"equipment", "weapons"}:
                    raw = database.get_catalog_item(catalog, int(source["id"])) or {}
                    if raw:
                        attach_public_catalog_slug(database, catalog, raw)
                    detail = catalog_rules.enrich_catalog_item(catalog, raw)
                    slug = database.application_slug(catalog, int(source["id"]))
                    source_ids = [int(value) for value in source.get("source_ids", [])]
                    family_ids, exact_ids = _surface_rule_ids(detail)
                elif catalog == "traits":
                    detail = trait_catalog.get_trait(str(source["id"])) or {}
                    slug = str(source["id"])
                    source_ids = []
                    family_ids, exact_ids = _surface_rule_ids(detail)
                    exposed_trait_rule_ids.update(family_ids)
                else:
                    detail = state_catalog.get_state(str(source["id"])) or {}
                    slug = str(source["id"])
                    source_ids = []
                    family_ids, exact_ids = _surface_rule_ids(detail)

                exposed_rule_ids.update(family_ids)
                exposed_rule_ids.update(exact_ids)
                gap_codes: set[str] = set()
                if not family_ids:
                    gap_codes.add("missing_rule_definition")

                for record_id in sorted(family_ids | exact_ids):
                    record = records.get(record_id)
                    if record is None:
                        gap_codes.add("unresolved_surface_rule")
                        continue
                    gap_codes.update(_record_gap_codes(record))

                mapping: dict[str, Any] = {}
                if catalog not in {"traits", "states"}:
                    entity = ENTITY_BY_CATALOG[catalog]
                    family_candidates: set[str] = set()
                    exact_candidates: dict[int, list[str]] = {}
                    refs: list[int | str] = [*source_ids]
                    if slug:
                        refs.append(slug)
                    for ref in refs:
                        for record_id in links.get((entity, str(ref)), []):
                            record = records[record_id]
                            if record["kind"] != entity:
                                continue
                            variant = record.get("variant") or {}
                            inheritance = (
                                variant.get("inheritance")
                                if isinstance(variant, dict)
                                else None
                            )
                            if inheritance == "source" and isinstance(ref, int):
                                exact_candidates.setdefault(ref, []).append(record_id)
                            elif inheritance != "source":
                                family_candidates.add(record_id)
                    if len(family_candidates) > 1:
                        gap_codes.add("ambiguous_family_mapping")
                    ambiguous_sources = {
                        source_id: sorted(set(record_ids))
                        for source_id, record_ids in exact_candidates.items()
                        if len(set(record_ids)) > 1
                    }
                    if ambiguous_sources:
                        gap_codes.add("ambiguous_source_variant_mapping")
                    mapping = {
                        "familyRecordIds": sorted(family_candidates),
                        "exactSourceRecordIds": {
                            str(source_id): sorted(set(record_ids))
                            for source_id, record_ids in sorted(exact_candidates.items())
                        },
                    }
                    if ambiguous_sources:
                        mapping["ambiguousSourceRecordIds"] = {
                            str(key): value for key, value in ambiguous_sources.items()
                        }

                sorted_gap_codes = sorted(gap_codes)
                item = {
                    "id": source["id"],
                    "name": source["name"],
                    "slug": slug,
                    "useCount": int(source.get("use_count", 0)),
                    "sourceIds": source_ids,
                    "familyRuleIds": sorted(family_ids),
                    "exactSourceRuleIds": sorted(exact_ids),
                    "gapCodes": sorted_gap_codes,
                    "gapClassifications": [
                        _catalog_gap_classification(
                            classification_policy,
                            matched_overrides,
                            catalog,
                            source["id"],
                            code,
                        )
                        for code in sorted_gap_codes
                    ],
                }
                if mapping:
                    item["mapping"] = mapping
                if gap_codes or include_complete:
                    items.append(item)

            all_count = len(sources)
            gap_count = len([item for item in items if item["gapCodes"]])
            complete_count = all_count - gap_count
            domain_reports[catalog] = {
                "exposedCount": all_count,
                "completeCount": complete_count,
                "gapCount": gap_count,
                "items": items,
            }

        relation_gaps: list[dict[str, Any]] = []
        supporting_targets: set[str] = set()
        for source_id in sorted(exposed_rule_ids):
            source_record = records.get(source_id)
            if source_record is None:
                continue
            for relation in source_record.get("relations", []):
                target_id = relation["recordId"]
                target = records.get(target_id)
                if target is None:
                    relation_gaps.append(
                        {
                            "recordId": source_id,
                            "relationType": relation["type"],
                            "targetRecordId": target_id,
                            "reason": "missing_target_record",
                        }
                    )
                    continue
                target_kind = target["kind"]
                target_catalog = CATALOG_BY_KIND.get(target_kind)
                if target_catalog is None:
                    if target_kind == "trait":
                        if target_id not in exposed_trait_rule_ids:
                            relation_gaps.append(
                                {
                                    "recordId": source_id,
                                    "relationType": relation["type"],
                                    "targetRecordId": target_id,
                                    "reason": "trait_target_not_exposed",
                                }
                            )
                    else:
                        supporting_targets.add(target_id)
                    continue
                if target_catalog == "states":
                    state_slug = str(target_id).removeprefix("state:")
                    resolved = state_catalog.get_state(state_slug) is not None
                else:
                    resolved = target_id in exposed_rule_ids
                    if not resolved:
                        for link in target.get("links", []):
                            if link["entity"] != target_kind:
                                continue
                            ref: int | str = (
                                int(link["id"])
                                if str(link["id"]).isdecimal()
                                else str(link["id"])
                            )
                            if database.application_catalog_id(target_catalog, ref) is not None:
                                resolved = True
                                break
                if not resolved:
                    relation_gaps.append(
                        {
                            "recordId": source_id,
                            "relationType": relation["type"],
                            "targetRecordId": target_id,
                            "reason": "catalog_target_not_exposed",
                        }
                    )

        for gap in relation_gaps:
            gap["gapCode"] = "unresolved_related_item_link"
            gap["classification"] = _relation_gap_classification(
                classification_policy, matched_overrides, gap
            )

        unmatched_overrides = classification_policy["overrideKeys"] - matched_overrides
        if unmatched_overrides:
            raise EnrichmentCoverageAuditError(
                "Classification policy contains overrides that do not match current gaps: "
                + ", ".join(str(value) for value in sorted(unmatched_overrides))
            )

        gap_counts: dict[str, int] = {}
        classification_counts: dict[str, int] = {}
        for domain in domain_reports.values():
            for item in domain["items"]:
                for code in item["gapCodes"]:
                    gap_counts[code] = gap_counts.get(code, 0) + 1
                for decision in item["gapClassifications"]:
                    classification = decision["classification"]
                    classification_counts[classification] = (
                        classification_counts.get(classification, 0) + 1
                    )
        if relation_gaps:
            gap_counts["unresolved_related_item_link"] = len(relation_gaps)
            for gap in relation_gaps:
                classification = gap["classification"]["classification"]
                classification_counts[classification] = (
                    classification_counts.get(classification, 0) + 1
                )

        supporting_decision = classification_policy["supportingIdentity"]
        supporting_items = [
            {"recordId": record_id, **supporting_decision}
            for record_id in sorted(supporting_targets)
        ]

        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {"path": str(database_path), "sha256": _sha256(database_path)},
            "rulesDatabase": {"path": str(rules_path), "sha256": _sha256(rules_path)},
            "classificationPolicy": {
                "path": str(classification_path),
                "sha256": _sha256(classification_path),
            },
            "summary": {
                "exposedCount": sum(item["exposedCount"] for item in domain_reports.values()),
                "completeCount": sum(item["completeCount"] for item in domain_reports.values()),
                "gapCount": sum(item["gapCount"] for item in domain_reports.values()),
                "gapCounts": dict(sorted(gap_counts.items())),
                "classifiedGapCount": sum(classification_counts.values()),
                "classificationCounts": dict(sorted(classification_counts.items())),
                "releaseBlockerCount": classification_counts.get("release-blocker", 0),
                "unresolvedRelatedItemLinkCount": len(relation_gaps),
                "supportingRelationTargetCount": len(supporting_targets),
            },
            "domains": domain_reports,
            "relationCoverage": {
                "unresolved": relation_gaps,
                "supportingRecordIds": sorted(supporting_targets),
                "supporting": supporting_items,
            },
        }
    except (OSError, ValueError, sqlite3.Error) as exc:
        if isinstance(exc, EnrichmentCoverageAuditError):
            raise
        raise EnrichmentCoverageAuditError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit user-facing catalog rules-enrichment coverage."
    )
    parser.add_argument("database", type=Path, help="Path to infinity.db")
    parser.add_argument("--rules", type=Path, required=True, help="Path to rules.db")
    parser.add_argument(
        "--include-complete",
        action="store_true",
        help="Include fully covered items in domain detail lists",
    )
    parser.add_argument(
        "--classifications",
        type=Path,
        default=DEFAULT_CLASSIFICATION_PATH,
        help="Path to the maintained gap-classification policy",
    )
    parser.add_argument("--output", type=Path, help="Write the JSON report to this path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_coverage(
            args.database,
            args.rules,
            include_complete=args.include_complete,
            classification_path=args.classifications,
        )
    except EnrichmentCoverageAuditError as exc:
        raise SystemExit(str(exc)) from exc
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Enrichment coverage audit written: {args.output}")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
