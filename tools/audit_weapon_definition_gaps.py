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
FORMAT_VERSION = 3
SHARED_REVIEWS_PATH = Path("data/curated/weapon-shared-effect-reviews.json")
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
    reviewed_shared: dict[int, dict[str, Any]] | None = None,
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
            if reviewed_shared is not None and weapon_id in reviewed_shared:
                evidence = reviewed_shared[weapon_id]
                coverage = (shared_effect_coverage or {}).get(weapon_id)
                if (
                    kind != "shared-effects-review"
                    or coverage is None
                    or evidence["chartPage"] not in {r["page"] for r in row_candidates}
                    or any(r["differences"] for r in row_candidates)
                ):
                    raise WeaponGapTriageError(
                        f"Reviewed shared Weapon source conditions changed: {weapon_id}"
                    )
                kind = "reviewed-shared-effects"
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
                {"sharedReview": reviewed_shared[weapon_id]}
                if reviewed_shared is not None and weapon_id in reviewed_shared
                else {}
            ),
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
                        r.get("requiresModeReview", False)
                        and r["disposition"] != "reviewed-shared-effects"
                        for r in results
                    ),
                    "reviewedSharedEffects": sum(
                        r["disposition"] == "reviewed-shared-effects" for r in results
                    ),
                    "remainingSourceReviews": sum(
                        r["disposition"] not in {
                            "reviewed-shared-effects", "reviewed-historical-citation",
                        }
                        for r in results
                    ),
                }
                if shared_effect_coverage is not None
                else {}
            ),
        },
        "batches": batches,
        "items": results,
    }


def load_shared_reviews(
    db: Database, enrichment: dict[str, Any], policy_path: Path,
    *, rules: RulesDatabase | None = None,
) -> dict[int, dict[str, Any]]:
    """Pin shared-effect decisions, including those superseded by a published rule."""
    policy = _load(policy_path)
    if (
        policy.get("format") != "InfinityDB Weapon shared-effects source reviews"
        or policy.get("version") != 1
        or policy.get("sourceId") != "n5-core-v5.3-pdf"
    ):
        raise WeaponGapTriageError("Unsupported reviewed Weapon source policy")
    reviews = policy.get("reviews")
    if not isinstance(reviews, list):
        raise WeaponGapTriageError("Reviewed Weapon source policy lacks reviews")
    unresolved = {
        row["name"]: row
        for row in enrichment.get("domains", {}).get("weapons", {}).get("items", [])
    }
    catalogue = {row["name"]: row for row in db.list_catalog_items("weapons")}
    accepted: dict[int, dict[str, Any]] = {}
    for review in reviews:
        if not isinstance(review, dict):
            raise WeaponGapTriageError("Reviewed Weapon entry must be an object")
        slug = review.get("slug")
        name = review.get("name")
        digest = review.get("profileSha256")
        note = review.get("reason")
        page = review.get("chartPage")
        if (
            not isinstance(slug, str) or not slug
            or not isinstance(name, str) or not name
            or not isinstance(digest, str)
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(page, int) or page <= 0
            or not isinstance(note, str) or not note.strip()
        ):
            raise WeaponGapTriageError(f"Incomplete reviewed Weapon entry: {name!r}")
        entry = catalogue.get(name)
        pending = unresolved.get(name)
        if entry is None or db.application_slug("weapons", int(entry["id"])) != slug:
            raise WeaponGapTriageError(f"Reviewed Weapon identity changed: {name}")
        weapon_id = int(entry["id"])
        if pending is not None:
            if (pending["id"] != weapon_id or pending["slug"] != slug
                    or pending["gapCodes"] != ["missing_rule_definition"]):
                raise WeaponGapTriageError(f"Reviewed Weapon gap classification changed: {name}")
        elif rules is None or not any(
            record["id"] == f"weapon:{slug}" and record["kind"] == "weapon"
            and (record.get("variant_semantics") or {}).get("inheritance") != "source"
            for record in rules.composed_records_for_army_link("weapon", slug)
        ):
            # An absent unresolved row is only acceptable when that exact Weapon
            # acquired a published family definition, not merely shared effects.
            raise WeaponGapTriageError(f"Reviewed Weapon has no verified definition: {name}")
        if weapon_id in accepted:
            raise WeaponGapTriageError(f"Duplicate reviewed Weapon: {name}")
        details = db.get_catalog_item("weapons", weapon_id)
        if details is None:
            raise WeaponGapTriageError(f"Reviewed Weapon cannot be resolved: {name}")
        profiles = details["profiles"]
        actual = hashlib.sha256(
            json.dumps(
                profiles, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if actual != digest:
            raise WeaponGapTriageError(f"Reviewed Weapon profile changed: {name}")
        accepted[weapon_id] = {
            "sourceId": policy["sourceId"],
            "chartPage": page,
            "reviewedOn": review.get("reviewedOn"),
            "reason": note,
        }
    return accepted


def assess_1_0_enrichment(
    enrichment: dict[str, Any], triage: dict[str, Any],
) -> dict[str, Any]:
    """Interpret current gaps for 1.0 without rewriting historical classifications.

    A reviewed shared effect is not a missing Weapon definition, but neither it
    nor this source triage certifies full rules or browser completeness.
    """
    if (
        enrichment.get("format") != ENRICHMENT_FORMAT
        or enrichment.get("formatVersion") != 3
        or enrichment.get("database", {}).get("sha256") != triage["armySha256"]
        or enrichment.get("rulesDatabase", {}).get("sha256") != triage["rulesSha256"]
    ):
        raise WeaponGapTriageError("1.0 assessment needs matching enrichment evidence")
    domains = enrichment.get("domains", {})
    weapons = domains.get("weapons", {})
    weapon_rows = weapons.get("items", [])
    if len(weapon_rows) != weapons.get("gapCount"):
        raise WeaponGapTriageError("1.0 assessment requires gap-only Weapon enrichment")
    triaged = {row["id"]: row for row in triage["items"]}
    if len(triaged) != len(triage["items"]) or set(triaged) != {
        row["id"] for row in weapon_rows
    }:
        raise WeaponGapTriageError("1.0 Weapon triage identities differ from enrichment")

    pending: list[dict[str, Any]] = []
    reviewed_shared = 0
    reviewed_historical = 0
    for item in weapon_rows:
        row = triaged[item["id"]]
        if (row["name"] != item["name"] or row["gapCodes"] != item["gapCodes"]):
            raise WeaponGapTriageError("1.0 Weapon triage classification drift")
        disposition = row["disposition"]
        if disposition == "reviewed-shared-effects":
            if not row.get("sharedReview"):
                raise WeaponGapTriageError("Reviewed Weapon lacks source review")
            reviewed_shared += 1
        elif (disposition == "reviewed-historical-citation"
                and item.get("gapClassifications")
                and all(
                    decision["classification"] == "intentional-omission"
                    and decision["source"] == "override"
                    for decision in item["gapClassifications"]
                )):
            reviewed_historical += 1
        else:
            pending.append({
                "catalog": "weapons", "id": item["id"], "name": item["name"],
                "gapCodes": item["gapCodes"], "disposition": disposition,
            })
    for catalog in sorted(set(domains) - {"weapons"}):
        for item in domains[catalog]["items"]:
            if item["gapCodes"]:
                pending.append({
                    "catalog": catalog, "id": item["id"], "name": item["name"],
                    "gapCodes": item["gapCodes"],
                    "disposition": (
                        "unverified-n5-reinforcements-authority"
                        if catalog == "skills" and item["name"] == "Commlink"
                        else "unresolved-catalog-gap"
                    ),
                })
    for link in enrichment.get("relationCoverage", {}).get("unresolved", []):
        pending.append({
            "catalog": "relations", "id": link["recordId"],
            "name": link["targetRecordId"], "gapCodes": ["unresolved_related_item_link"],
            "disposition": link["reason"],
        })
    return {
        "targetRelease": "1.0.0",
        "status": "pending" if pending else "source-triage-clear-not-release-acceptance",
        "historicalPolicyReleaseBlockerCount": enrichment["summary"]["releaseBlockerCount"],
        "reviewedSharedWeaponCount": reviewed_shared,
        "reviewedHistoricalCitationCount": reviewed_historical,
        "resolvedHistoricalWeaponReviewCount": triage["summary"]["resolvedSharedReviewCount"],
        "pendingCount": len(pending), "pending": pending,
    }


def build_report(
    army_db: Path, enrichment_path: Path, chart_path: Path,
    *, assess_release: str | None = None,
) -> dict[str, Any]:
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
    rules = RulesDatabase(rules_path)
    rules.validate()
    references = WeaponAmmunitionReferences(rules)
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
    reviews = load_shared_reviews(db, enrichment, SHARED_REVIEWS_PATH, rules=rules)
    chart = _load(chart_path)
    report = reconcile(
        enrichment, chart, categories, _sha256(army_db),
        shared_effect_coverage=coverage, reviewed_shared=reviews,
    )
    unresolved_ids = set(coverage)
    names = {int(row["id"]): str(row["name"])
             for row in db.list_catalog_items("weapons")}
    report["resolvedSharedReviews"] = [
        {"id": weapon_id, "name": names[weapon_id], "sourceReview": review}
        for weapon_id, review in sorted(reviews.items())
        if weapon_id not in unresolved_ids
    ]
    report["summary"]["resolvedSharedReviewCount"] = len(report["resolvedSharedReviews"])
    for resolved in report["resolvedSharedReviews"]:
        rows = [
            row for row in chart["comparison"]["compared"]
            if _identity(str(row["name"])) == _identity(resolved["name"])
        ]
        if (not rows
                or resolved["sourceReview"]["chartPage"] not in {row["page"] for row in rows}
                or any(row["differences"] for row in rows)):
            raise WeaponGapTriageError(
                f"Resolved shared Weapon chart conditions changed: {resolved['name']}"
            )
    if assess_release == "1.0.0":
        report["releaseAssessment"] = assess_1_0_enrichment(enrichment, report)
    return report


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
                f"- Explicitly reviewed without a standalone Weapon definition: "
                f"**{summary['reviewedSharedEffects']}**.",
                f"- Still requiring source/effect/mode review: "
                f"**{summary['remainingSourceReviews']}**.",
            ]
            if "reviewedSharedEffects" in summary else []
        ),
        *(
            [f"- Historical shared-effect reviews now backed by a published definition: "
             f"**{summary['resolvedSharedReviewCount']}**."]
            if "resolvedSharedReviewCount" in summary else []
        ),
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
    if "releaseAssessment" in report:
        release = report["releaseAssessment"]
        lines += [
            "## 1.0 enrichment source-triage assessment", "",
            "This assessment does not certify full rules, gameplay or browser completeness.", "",
            f"- Historical-policy blocker count (not a 1.0 verdict): "
            f"**{release['historicalPolicyReleaseBlockerCount']}**.",
            f"- Reviewed shared-effect omissions: **{release['reviewedSharedWeaponCount']}**.",
            f"- Accepted historical citations: **{release['reviewedHistoricalCitationCount']}**.",
            f"- Historical approvals with current definitions: "
            f"**{release['resolvedHistoricalWeaponReviewCount']}**.",
            f"- Pending for 1.0: **{release['pendingCount']}**.", "",
        ]
        for item in release["pending"]:
            lines.append(
                f"- {item['catalog']}: {item['name']} ({item['id']}) — "
                f"{item['disposition']} ({', '.join(item['gapCodes'])})"
            )
        lines.append("")
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
    parser.add_argument("--assess-release", choices=["1.0.0"])
    parser.add_argument("--require-release", choices=["1.0.0"])
    args = parser.parse_args()
    try:
        report = build_report(
            args.army_db, args.enrichment, args.chart,
            assess_release=args.require_release or args.assess_release,
        )
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
    if args.require_release and report["releaseAssessment"]["pendingCount"]:
        print(
            f"Release {args.require_release} enrichment triage has "
            f"{report['releaseAssessment']['pendingCount']} pending gaps; "
            "historical classification deferrals do not clear the release gate"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
