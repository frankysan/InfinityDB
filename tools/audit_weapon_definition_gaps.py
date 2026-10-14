#!/usr/bin/env python3
"""Reconcile existing Weapon enrichment gaps with pinned N5 Weapon Chart evidence.

Consumes the maintained enrichment and PDF chart audits. A matched chart profile
is *profile evidence*, not a reviewed rules definition or browser-coverage claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_ammunition_references import WeaponAmmunitionReferences

FORMAT = "InfinityDB 1.0 weapon definition gap triage"
FORMAT_VERSION = 2
ENRICHMENT_FORMAT = "InfinityDB rules enrichment coverage audit"
CHART_FORMAT = "InfinityDB N5 Weapon Chart profile evidence"
MAX_BATCH_SIZE = 8


class WeaponGapTriageError(ValueError):
    """Incompatible or incomplete evidence prevents a reproducible comparison."""


def _identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKC", value).casefold())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WeaponGapTriageError(f"Cannot read evidence {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WeaponGapTriageError("Evidence root must be an object")
    return value


def reconcile(
    enrichment: dict[str, Any],
    chart: dict[str, Any],
    categories: dict[int, str],
    army_sha256: str,
    *,
    shared_effect_coverage: dict[int, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Join unresolved Army Weapon identities to chart rows without inferring rules."""
    if (enrichment.get("format"), enrichment.get("formatVersion")) != (
        ENRICHMENT_FORMAT, 3
    ):
        raise WeaponGapTriageError("Expected enrichment coverage report v3")
    if (chart.get("format"), chart.get("formatVersion")) != (CHART_FORMAT, 3):
        raise WeaponGapTriageError("Expected Weapon Chart profile report v3")
    if enrichment.get("database", {}).get("sha256") != army_sha256:
        raise WeaponGapTriageError("Enrichment report uses a different Army database")
    if chart.get("armyDatabaseSha256") != army_sha256:
        raise WeaponGapTriageError("Weapon Chart report uses a different Army database")
    pdf_sha = chart.get("corePdfSha256")
    if not isinstance(pdf_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", pdf_sha):
        raise WeaponGapTriageError("Weapon Chart report lacks a valid PDF SHA-256")

    comparison = chart.get("comparison")
    if not isinstance(comparison, dict):
        raise WeaponGapTriageError("Weapon Chart report has no comparison")
    compared = comparison.get("compared")
    if (not isinstance(compared, list)
            or len(compared) != comparison.get("unambiguousRowsCompared")
            or len(compared) != comparison.get("chartRowsLocated")
            or comparison.get("deferredRows") != 0):
        raise WeaponGapTriageError("Weapon Chart is incomplete or has deferred rows")
    names: dict[str, list[dict[str, Any]]] = {}
    for row in compared:
        key = _identity(str(row["name"]))
        names.setdefault(key, []).append(row)
    gaps = enrichment.get("domains", {}).get("weapons", {})
    items = gaps.get("items")
    if not isinstance(items, list) or len(items) != gaps.get("gapCount"):
        raise WeaponGapTriageError(
            "Enrichment report must include every unresolved Weapon (omit --include-complete)"
        )
    results: list[dict[str, Any]] = []
    seen: set[int] = set()
    for item in items:
        weapon_id = item["id"]
        if not isinstance(weapon_id, int) or weapon_id in seen:
            raise WeaponGapTriageError(f"Duplicate or invalid Weapon ID: {weapon_id}")
        seen.add(weapon_id)
        if weapon_id not in categories:
            raise WeaponGapTriageError(f"Weapon ID absent from Army catalog: {weapon_id}")
        row_candidates = names.get(_identity(str(item["name"])), [])
        codes = item["gapCodes"]
        if codes == ["missing_rule_definition"]:
            if not row_candidates:
                kind = "outside-chart-review"
            elif shared_effect_coverage is None:
                kind = "definition-review"
            else:
                coverage = shared_effect_coverage.get(weapon_id)
                if coverage is None or coverage["total"] <= 0:
                    raise WeaponGapTriageError(
                        f"Missing Weapon profile coverage for {weapon_id}"
                    )
                kind = (
                    "shared-effects-review"
                    if coverage["linked"] == coverage["total"]
                    else "missing-effect-links-review"
                )
        elif codes == ["ambiguous_family_mapping"]:
            kind = "ambiguous-rule-mapping"
        elif codes == ["stale_citation_source"]:
            accepted = any(
                decision["code"] == "stale_citation_source"
                and decision["classification"] == "intentional-omission"
                and decision["source"] == "override"
                for decision in item.get("gapClassifications", [])
            )
            kind = "reviewed-historical-citation" if accepted else "stale-rule-citation"
        else:
            raise WeaponGapTriageError(f"Unclassified gap codes for {weapon_id}: {codes}")
        results.append({
            "id": weapon_id,
            "name": item["name"],
            "slug": item["slug"],
            "sourceCategory": categories[weapon_id],
            "catalogUseCount": item["useCount"],
            "gapCodes": codes,
            "disposition": kind,
            "chart": {
                "status": "identity-present" if row_candidates else "identity-not-in-chart",
                "printedRows": len(row_candidates),
                "pages": sorted({row["page"] for row in row_candidates}),
                "modes": sorted({str(row["mode"]) for row in row_candidates}),
                "profileCandidates": sum(bool(row["differences"]) for row in row_candidates),
            },
            "familyRules": item["familyRuleIds"],
            "sourceRuleIds": item["exactSourceRuleIds"],
            **(
                {"sharedEffectCoverage": shared_effect_coverage[weapon_id],
                 "requiresModeReview": shared_effect_coverage[weapon_id]["total"] > 1}
                if shared_effect_coverage is not None
                and weapon_id in shared_effect_coverage
                else {}
            ),
        })
    results.sort(key=lambda row: (-row["catalogUseCount"], row["name"].casefold(), row["id"]))

    # Batches use the source catalog's category rather than inferring common
    # mechanics from weapon names. The cap keeps each review independently sized.
    batches: list[dict[str, Any]] = []
    for disposition in (
        "ambiguous-rule-mapping",
        "stale-rule-citation",
        "reviewed-historical-citation",
        "outside-chart-review",
        "missing-effect-links-review",
        "shared-effects-review",
        "definition-review",
    ):
        candidates = [item for item in results if item["disposition"] == disposition]
        by_category: dict[str, list[dict[str, Any]]] = {}
        for item in candidates:
            by_category.setdefault(item["sourceCategory"], []).append(item)
        groups = sorted(
            by_category.items(),
            key=lambda group: (
                -sum(item["catalogUseCount"] for item in group[1]),
                group[0].casefold(),
            ),
        )
        for category, group in groups:
            for offset in range(0, len(group), MAX_BATCH_SIZE):
                segment = group[offset:offset + MAX_BATCH_SIZE]
                batches.append({
                    "disposition": disposition,
                    "sourceCategory": category,
                    "weaponIds": [item["id"] for item in segment],
                    "weaponNames": [item["name"] for item in segment],
                    "catalogUseCount": sum(item["catalogUseCount"] for item in segment),
                    "evidenceRequirement": (
                        "Review conflicting rule mappings or citations and check visible links."
                        if disposition in {"ambiguous-rule-mapping", "stale-rule-citation"}
                        else "Historical comparison accepted for this source revision; preserve "
                        "the separate unresolved publication conflict and current "
                        "primary citations."
                        if disposition == "reviewed-historical-citation"
                        else "Find separately scoped primary source text before rule curation."
                        if disposition == "outside-chart-review"
                        else "Review missing or non-ammunition profile links and special rules; "
                        "do not manufacture Ammunition effects from notation."
                        if disposition == "missing-effect-links-review"
                        else "Canonical Ammunition effects are linked; review mode-specific "
                        "Traits, target conditions, exceptions and source coverage without "
                        "duplicating shared Ammunition prose."
                        if disposition == "shared-effects-review"
                        else "Compare chart profiles and applicable rules; verify existing "
                        "ammunition/trait links, then add only missing player-facing explanations."
                    ),
                })
    chart_candidates = [
        {"name": row["name"], "mode": row["mode"], "page": row["page"],
         "differences": row["differences"]}
        for row in compared if row["differences"]
    ]
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "status": "source-triage-only-not-rules-or-browser-completeness",
        "armySha256": army_sha256,
        "rulesSha256": enrichment["rulesDatabase"]["sha256"],
        "corePdfSha256": pdf_sha,
        "chartRowsCompared": len(compared),
        "chartProfileDiscrepancies": chart_candidates,
        "summary": {
            "unresolvedWeapons": len(results),
            "dispositions": dict(sorted(Counter(x["disposition"] for x in results).items())),
            "matchedChartIdentity": sum(x["chart"]["printedRows"] > 0 for x in results),
            "noChartIdentity": sum(x["chart"]["printedRows"] == 0 for x in results),
            "reviewBatches": len(batches),
            **(
                {
                    "sharedEffectCandidates": sum(
                        r["disposition"] == "shared-effects-review" for r in results
                    ),
                    "missingEffectLinkCandidates": sum(
                        r["disposition"] == "missing-effect-links-review" for r in results
                    ),
                    "modeReviewCandidates": sum(
                        r.get("requiresModeReview", False) for r in results
                    ),
                }
                if shared_effect_coverage is not None
                else {}
            ),
        },
        "batches": batches,
        "items": results,
    }


def build_report(army_db: Path, enrichment_path: Path, chart_path: Path) -> dict[str, Any]:
    if not army_db.is_file():
        raise WeaponGapTriageError(f"Army database is unavailable: {army_db}")
    db = Database(army_db)
    db.validate()
    categories = {int(item["id"]): str(item["category"])
                  for item in db.list_catalog_items("weapons")}
    enrichment = _load(enrichment_path)
    rules_info = enrichment.get("rulesDatabase")
    if not isinstance(rules_info, dict):
        raise WeaponGapTriageError("Enrichment report lacks rules database metadata")
    rules_path_text = rules_info.get("path")
    if not isinstance(rules_path_text, str) or not rules_path_text:
        raise WeaponGapTriageError("Enrichment report lacks a rules database path")
    rules_path = Path(rules_path_text)
    if not rules_path.is_file() or _sha256(rules_path) != rules_info.get("sha256"):
        raise WeaponGapTriageError("Enrichment report rules database fingerprint differs")
    references = WeaponAmmunitionReferences(RulesDatabase(rules_path))
    coverage: dict[int, dict[str, int]] = {}
    for item in enrichment.get("domains", {}).get("weapons", {}).get("items", []):
        details = db.get_catalog_item("weapons", item["id"])
        if details is None:
            raise WeaponGapTriageError(f"Weapon is absent from catalog: {item['id']}")
        profiles = details.get("profiles", [])
        if not profiles:
            profiles = [
                profile
                for variant in details.get("weapon_variants", [])
                for profile in variant.get("profiles", [])
            ]
        coverage[item["id"]] = {
            "total": len(profiles),
            "linked": sum(
                references.effects_for_profile(profile) is not None
                for profile in profiles
            ),
        }
    return reconcile(
        enrichment, _load(chart_path), categories, _sha256(army_db),
        shared_effect_coverage=coverage,
    )


def markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Weapon definitions — 1.0 source-to-reference triage", "",
        "This report joins existing audits; it does not infer Weapon rules from profiles.",
        "The numbered batches are review scopes, not missing-fact or browser-defect verdicts.", "",
        f"- Unresolved Weapon entries: **{summary['unresolvedWeapons']}**.",
        f"- With a printed chart identity: **{summary['matchedChartIdentity']}**.",
        f"- Without one: **{summary['noChartIdentity']}**.",
        f"- Independently sized review batches: **{summary['reviewBatches']}**.",
        *(
            [
                "- Weapons with linked reusable Ammunition effects (review still pending): "
                f"**{summary['sharedEffectCandidates']}**.",
                "- Weapons needing other/source-specific effect links: "
                f"**{summary['missingEffectLinkCandidates']}**.",
                f"- Multi-profile review candidates: **{summary['modeReviewCandidates']}**.",
            ]
            if "sharedEffectCandidates" in summary else []
        ),
        f"- N5 v5.3 PDF SHA-256: `{report['corePdfSha256']}`.", "",
        "## Reconciliation batches", "",
    ]
    for n, batch in enumerate(report["batches"], 1):
        lines += [
            f"### {n}. {batch['sourceCategory']} — {batch['disposition']}",
            f"Summed catalog use-count: {batch['catalogUseCount']}.",
            "Names: " + "; ".join(batch["weaponNames"]) + ".",
            batch["evidenceRequirement"], "",
        ]
    lines += ["## Chart-profile source differences", ""]
    for row in report["chartProfileDiscrepancies"]:
        lines += [f"- {row['name']} ({row['mode']}), chart p. {row['page']}: "
                  f"{row['differences']}"]
    if not report["chartProfileDiscrepancies"]:
        lines += ["- None in the input chart report."]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument("--enrichment", type=Path, required=True)
    parser.add_argument("--chart", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    try:
        report = build_report(args.army_db, args.enrichment, args.chart)
    except (WeaponGapTriageError, ValueError, OSError) as exc:
        parser.error(str(exc))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(
            markdown_report(report), encoding="utf-8", newline="\n"
        )
    print("Weapon gap triage written:", args.json_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
