#!/usr/bin/env python3
"""Audit maintained outgoing rules-interaction review progress."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory

REPORT_FORMAT = "InfinityDB rules interaction review"
REPORT_FORMAT_VERSION = 1
POLICY_FORMAT = "InfinityDB rules interaction review policy"
POLICY_FORMAT_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES_DIRECTORY = PROJECT_ROOT / "data" / "curated" / "rules"
DEFAULT_POLICY_PATH = (
    PROJECT_ROOT / "data" / "curated" / "rules-interactions" / "reviews.json"
)
DEFAULT_CHECKLIST_PATH = PROJECT_ROOT / "docs" / "rules-interaction-checklist.md"
EXCLUDED_RECORD_KINDS = frozenset({"declaration-category"})
REVIEW_STATUSES = frozenset({"pending", "reviewed", "inherited"})
FUTURE_STATUSES = frozenset({"deferred", "planned", "blocked"})
COMPLETE_STATUSES = frozenset({"reviewed", "inherited"})


class RulesInteractionAuditError(ValueError):
    """Raised when the interaction-review policy is invalid or stale."""


def _require_string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RulesInteractionAuditError(f"{context} must be a non-empty string")
    return value.strip()


def _semantic_records(rules_directory: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path, document in load_curated_directory(rules_directory):
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
) -> dict[str, Any]:
    semantic = _semantic_records(rules_directory)
    policy_document = _load_policy(policy_path)
    policy = policy_document["records"]
    future_interactions = policy_document["futureInteractions"]
    missing = sorted(set(semantic) - set(policy))
    extra = sorted(set(policy) - set(semantic))
    if missing or extra:
        raise RulesInteractionAuditError(
            f"Interaction-review coverage mismatch; missing={missing}, extra={extra}"
        )

    items: list[dict[str, Any]] = []
    release_summary: dict[str, Counter[str]] = defaultdict(Counter)
    kind_summary: dict[str, Counter[str]] = defaultdict(Counter)
    future_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in future_interactions:
        future_by_source[candidate["sourceRecordId"]].append(candidate)
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
        items.append(
            {
                **record,
                **review,
                "futureInteractions": future_by_source.get(record_id, []),
            }
        )

    releases: dict[str, dict[str, int | float]] = {}
    for release, counts in sorted(release_summary.items()):
        total = sum(counts.values())
        complete = sum(counts[status] for status in COMPLETE_STATUSES)
        releases[release] = {
            "total": total,
            "complete": complete,
            "pending": counts["pending"],
            "reviewed": counts["reviewed"],
            "inherited": counts["inherited"],
            "percentComplete": round(100.0 * complete / total, 1) if total else 100.0,
        }
    kinds: dict[str, dict[str, int]] = {}
    for kind, counts in sorted(kind_summary.items()):
        total = sum(counts.values())
        kinds[kind] = {
            "total": total,
            "complete": sum(counts[status] for status in COMPLETE_STATUSES),
            "pending": counts["pending"],
        }

    return {
        "format": REPORT_FORMAT,
        "formatVersion": REPORT_FORMAT_VERSION,
        "summary": {
            "recordCount": len(items),
            "authoredOutgoingRelationCount": sum(len(item["relations"]) for item in items),
            "futureInteractionCount": len(future_interactions),
            "releases": releases,
            "kinds": kinds,
        },
        "items": items,
        "futureInteractions": future_interactions,
    }


def _record_label(record_id: str, semantic: dict[str, dict[str, Any]]) -> str:
    target = semantic.get(record_id)
    if target is None:
        return f"`{record_id}`"
    return f"{target['name']} (`{record_id}`)"


def render_markdown(report: dict[str, Any]) -> str:
    items = report["items"]
    semantic = {item["id"]: item for item in items}
    lines = [
        "# Rules interaction review checklist",
        "",
        "This file is generated from the maintained interaction-review policy and the current",
        "curated rules graph. Do not edit it by hand. Regenerate it with:",
        "",
        "```powershell",
        "python tools/audit_rules_interactions.py --output docs/rules-interaction-checklist.md",
        "```",
        "",
        "A checked entity means its **outgoing** interaction semantics have been reviewed for",
        "its target release. `inherited` means an exact source variant uses the reviewed family",
        "semantics unless a variant-specific exception is later identified. A checked entity may",
        "still have explicitly tracked future interactions; those stay in the future queue until",
        "their target release/model is ready.",
        "",
        "`declaration-category` projection records are excluded because they classify Skills/",
        "Equipment rather than representing independently reviewable gameplay identities.",
        "",
        "## Progress",
        "",
    ]
    summary = report["summary"]
    for release, values in summary["releases"].items():
        lines.append(
            f"- **{release}: {values['complete']}/{values['total']} complete "
            f"({values['percentComplete']:.1f}%), {values['pending']} pending.**"
        )
    lines.extend(
        [
            "- Current authored outgoing relations: "
            f"**{summary['authoredOutgoingRelationCount']}**.",
            "- Explicitly tracked future/deferred interactions: "
            f"**{summary['futureInteractionCount']}**.",
            "",
        ]
    )

    by_release: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_release[item["targetRelease"]].append(item)
    for release in sorted(by_release):
        lines.extend([f"## {release} entity review", ""])
        by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in by_release[release]:
            by_kind[item["kind"]].append(item)
        for kind in sorted(by_kind):
            kind_items = by_kind[kind]
            complete = sum(item["status"] in COMPLETE_STATUSES for item in kind_items)
            lines.extend([f"### {kind.title()} ({complete}/{len(kind_items)})", ""])
            for item in kind_items:
                checked = "x" if item["status"] in COMPLETE_STATUSES else " "
                suffix = f" — {item['status']}"
                if item.get("note"):
                    suffix += f": {item['note']}"
                lines.append(f"- [{checked}] **{item['name']}** (`{item['id']}`){suffix}")
                if item["relations"]:
                    for relation_type, target_id in item["relations"]:
                        lines.append(
                            f"  - `{relation_type}` → {_record_label(target_id, semantic)}"
                        )
                else:
                    lines.append("  - outgoing: none")
                for future in item["futureInteractions"]:
                    rel = future["relationType"] or "relation type TBD"
                    lines.append(
                        f"  - future [{future['targetRelease']}; {future['status']}]: "
                        f"`{rel}` → {_record_label(future['targetRecordId'], semantic)} — "
                        f"{future['reason']}"
                    )
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
                f"- [ ] {_record_label(future['sourceRecordId'], semantic)} → "
                f"{_record_label(future['targetRecordId'], semantic)}; `{rel}`; "
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
    parser.add_argument("--output", type=Path, help="Write the generated Markdown checklist.")
    parser.add_argument(
        "--check-output",
        type=Path,
        help="Fail if this committed Markdown checklist differs from generated output.",
    )
    parser.add_argument(
        "--require-release",
        help="Fail if the named release still has pending entity reviews.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_rules_interactions(args.rules, args.policy)
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

    releases = report["summary"]["releases"]
    for release, values in releases.items():
        print(
            f"{release}: {values['complete']}/{values['total']} complete "
            f"({values['percentComplete']:.1f}%), {values['pending']} pending"
        )
    print(
        f"Outgoing relations: {report['summary']['authoredOutgoingRelationCount']}; "
        f"future interactions: {report['summary']['futureInteractionCount']}"
    )
    if args.require_release is not None:
        release = releases.get(args.require_release)
        if release is None:
            print(f"Unknown tracked release: {args.require_release}")
            return 2
        if release["pending"]:
            print(
                f"Release {args.require_release} is not interaction-review complete: "
                f"{release['pending']} pending"
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
