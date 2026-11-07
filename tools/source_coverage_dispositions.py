"""Validate fingerprinted, clause-scoped V1S-082 review evidence.

This is a maintained evidence gate, not a semantic reviewer or a source inventory.
Missing or stale evidence never becomes accepted automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_document
from tools.report_reference_baseline import (
    CURRENT_EXPLANATION_COLLECTIONS,
    PROJECT_ROOT,
    reconcile_explanation_inventory,
)

DEFAULT_MANIFEST = PROJECT_ROOT / "config/validation/source-coverage-dispositions-v1.json"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
_SEMANTIC = {
    "pending", "accepted", "accepted-with-disclosure", "excluded-with-rationale",
    "blocked-source-conflict", "confirmed-defect",
}
_BROWSER = {"pending", "accepted", "accepted-with-disclosure", "blocked"}


class DispositionError(ValueError):
    """A review claim is malformed, ungrounded or stale."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record_hash(record: dict[str, Any]) -> str:
    return _sha(json.dumps(
        record, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8"))


def _exact_keys(value: Any, allowed: set[str], required: set[str], label: str) -> None:
    if not isinstance(value, dict) or not required <= value.keys():
        raise DispositionError(f"{label}: missing mandatory fields")
    if set(value) - allowed:
        raise DispositionError(f"{label}: unexpected fields {sorted(set(value) - allowed)}")


def _nonempty(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise DispositionError(f"{label}: nonempty text required")


def _hash(value: Any, label: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise DispositionError(f"{label}: lowercase SHA-256 required")


def _signed_off(value: dict[str, Any], label: str) -> None:
    for field in ("reviewer", "reviewedOn", "evidenceRef"):
        _nonempty(value.get(field), f"{label}.{field}")
    try:
        if date.fromisoformat(value["reviewedOn"]).isoformat() != value["reviewedOn"]:
            raise ValueError("noncanonical date")
    except ValueError as exc:
        raise DispositionError(f"{label}.reviewedOn: ISO date required") from exc


def current_evidence_inputs() -> tuple[dict[str, str], dict[str, str | None],
                                        dict[str, set[tuple[str, int | None, str | None]]]]:
    """Use maintained curated identities and declared source pins, without opening PDFs."""
    report = reconcile_explanation_inventory()
    ids = {row["id"] for row in report["currentRecords"]}
    records: dict[str, str] = {}
    sources: dict[str, str | None] = {}
    citations: dict[str, set[tuple[str, int | None, str | None]]] = {}
    for path in CURRENT_EXPLANATION_COLLECTIONS:
        doc = load_curated_document(path)
        for record in doc["records"]:
            identity = record["id"]
            if identity in records:
                raise DispositionError(f"Duplicate current identity: {identity}")
            records[identity] = _record_hash(record)
            citations[identity] = {
                (item["sourceId"], item.get("page"), item.get("member"))
                for item in record.get("citations", [])
            }
        for src in doc.get("sources", []):
            source_id = src["id"]
            pin = src.get("sha256")
            if pin is not None:
                _hash(pin, f"source {source_id}")
            if source_id in sources and sources[source_id] != pin:
                raise DispositionError(f"Conflicting declared source pins: {source_id}")
            sources[source_id] = pin
    if ids != set(records):
        raise DispositionError("Current curated records differ from reconciliation inventory")
    return records, sources, citations


def validate_dispositions(
    manifest: dict[str, Any], *, record_hashes: dict[str, str],
    source_pins: dict[str, str | None],
    citations: dict[str, set[tuple[str, int | None, str | None]]],
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Validate tracked scoped evidence; never infer semantic or browser approval."""
    _exact_keys(manifest, {"format", "formatVersion", "owner", "reviews"},
                {"format", "formatVersion", "owner", "reviews"}, "manifest")
    if (manifest["format"] != "InfinityDB source-coverage dispositions"
            or type(manifest["formatVersion"]) is not int
            or manifest["formatVersion"] != 1
            or manifest["owner"] != "V1S-082"
            or not isinstance(manifest["reviews"], list)):
        raise DispositionError("Disposition manifest format, version or owner mismatch")
    seen_ids: set[str] = set()
    seen_clauses: set[tuple[str, int | None, str | None, str]] = set()
    dependencies: dict[str, list[str]] = {}
    counts = {
        "reviews": 0, "pending": 0, "semanticAccepted": 0,
        "browserAccepted": 0, "excluded": 0, "blocked": 0, "defects": 0,
        "sourceFirst": 0,
    }
    for review in manifest["reviews"]:
        _exact_keys(
            review,
            {"id", "origin", "clauseKey", "source", "recordIds", "recordSha256",
             "scope", "semantic", "browser", "dependsOn"},
            {"id", "origin", "clauseKey", "source", "recordIds", "recordSha256",
             "scope", "semantic", "browser", "dependsOn"},
            "review",
        )
        identity = review["id"]
        _nonempty(identity, "review.id")
        if identity in seen_ids:
            raise DispositionError(f"Duplicate review ID: {identity}")
        seen_ids.add(identity)
        if review["origin"] not in ("record", "source-first"):
            raise DispositionError(f"{identity}: invalid origin")
        if not isinstance(review["clauseKey"], str) or not _SLUG.fullmatch(review["clauseKey"]):
            raise DispositionError(f"{identity}: invalid stable clauseKey")
        _nonempty(review["scope"], f"{identity}.scope")
        source = review["source"]
        _exact_keys(source, {"sourceId", "page", "heading", "member", "sha256"},
                    {"sourceId", "page", "heading", "sha256"}, f"{identity}.source")
        source_id = source["sourceId"]
        _nonempty(source_id, f"{identity}.sourceId")
        if source_id not in source_pins:
            raise DispositionError(f"{identity}: source ID absent from curated declarations")
        page = source["page"]
        if page is not None and (type(page) is not int or page <= 0):
            raise DispositionError(f"{identity}: invalid printed page")
        heading = source["heading"]
        _nonempty(heading, f"{identity}.heading")
        member = source.get("member")
        if member is not None:
            _nonempty(member, f"{identity}.member")
        if page is None and not member and "-oldid-" not in source_id:
            raise DispositionError(f"{identity}: source lacks an addressable page/member")
        pin = source["sha256"]
        if pin is not None:
            _hash(pin, f"{identity}.source.sha256")
            if pin != source_pins[source_id]:
                raise DispositionError(f"{identity}: stale source fingerprint")
        clause = (source_id, page, member, review["clauseKey"])
        if clause in seen_clauses:
            raise DispositionError(f"{identity}: duplicate source-clause key")
        seen_clauses.add(clause)

        ids = review["recordIds"]
        hashes = review["recordSha256"]
        if (not isinstance(ids, list) or any(not isinstance(item, str) for item in ids)
                or len(ids) != len(set(ids)) or not isinstance(hashes, dict)
                or set(hashes) - set(ids)):
            raise DispositionError(f"{identity}: malformed record owners/fingerprints")
        if review["origin"] == "record" and not ids:
            raise DispositionError(f"{identity}: record-first clause must have owners")
        for record_id in ids:
            if record_id not in record_hashes:
                raise DispositionError(f"{identity}: unknown record {record_id}")
            if record_id in hashes:
                _hash(hashes[record_id], f"{identity}.{record_id}")
                if hashes[record_id] != record_hashes[record_id]:
                    raise DispositionError(f"{identity}: stale record fingerprint {record_id}")

        semantic = review["semantic"]
        browser = review["browser"]
        _exact_keys(semantic,
                    {"status", "reviewer", "reviewedOn", "evidenceRef", "reason"},
                    {"status"}, f"{identity}.semantic")
        _exact_keys(browser,
                    {"status", "reviewer", "reviewedOn", "evidenceRef", "appGitSha",
                     "armyDbSha256", "rulesDbSha256", "testSelectors", "contractFiles"},
                    {"status"}, f"{identity}.browser")
        semantic_status = semantic["status"]
        browser_status = browser["status"]
        if semantic_status not in _SEMANTIC or browser_status not in _BROWSER:
            raise DispositionError(f"{identity}: unsupported disposition")
        accepted = semantic_status in ("accepted", "accepted-with-disclosure")
        excluded = semantic_status == "excluded-with-rationale"
        if accepted or excluded:
            _signed_off(semantic, f"{identity}.semantic")
            if pin is None or source_pins[source_id] is None:
                raise DispositionError(f"{identity}: accepted claim requires declared source SHA")
            if set(hashes) != set(ids):
                raise DispositionError(f"{identity}: accepted claim has unpinned record owners")
            if accepted and not ids:
                raise DispositionError(
                    f"{identity}: accepted source-first claim has no record owner"
                )
            if review["origin"] == "record" and accepted:
                if not all(any(
                    cited_source == source_id and cited_page == page
                    and (member is None or cited_member == member)
                    for cited_source, cited_page, cited_member in citations[record_id]
                ) for record_id in ids):
                    raise DispositionError(
                        f"{identity}: accepted record lacks cited source locator"
                    )
        if semantic_status in ("accepted-with-disclosure", "excluded-with-rationale",
                               "blocked-source-conflict", "confirmed-defect"):
            _nonempty(semantic.get("reason"), f"{identity}.semantic.reason")
        if browser_status in ("accepted", "accepted-with-disclosure"):
            _signed_off(browser, f"{identity}.browser")
            if not accepted:
                raise DispositionError(
                    f"{identity}: browser acceptance without semantic acceptance"
                )
            if not isinstance(browser.get("appGitSha"), str) or not _GIT_SHA.fullmatch(
                browser["appGitSha"]
            ):
                raise DispositionError(f"{identity}.browser.appGitSha: Git SHA-1 required")
            for field in ("armyDbSha256", "rulesDbSha256"):
                _hash(browser.get(field), f"{identity}.browser.{field}")
            selectors = browser.get("testSelectors")
            if (not isinstance(selectors, list) or not selectors
                    or any(not isinstance(item, str) or not item.startswith("tests/test_")
                           for item in selectors)
                    or len(set(selectors)) != len(selectors)):
                raise DispositionError(f"{identity}: browser selectors required")
            contract = browser.get("contractFiles")
            if not isinstance(contract, dict) or not contract:
                raise DispositionError(f"{identity}: browser contract file fingerprints required")
            for name, value in contract.items():
                if (not isinstance(name, str) or "\\" in name or name.startswith("/")
                        or ".." in Path(name).parts or not name.startswith(("src/", "tests/"))):
                    raise DispositionError(f"{identity}: unsafe browser contract path")
                _hash(value, f"{identity}.browser.contractFiles")
                target = (root / name).resolve()
                if not target.is_relative_to(root.resolve()) or not target.is_file():
                    raise DispositionError(f"{identity}: browser contract file unavailable: {name}")
                if _sha(target.read_bytes()) != value:
                    raise DispositionError(f"{identity}: stale browser contract: {name}")
            counts["browserAccepted"] += 1
        elif browser_status == "blocked":
            _nonempty(browser.get("evidenceRef"), f"{identity}.browser.evidenceRef")
        counts["semanticAccepted"] += int(accepted)
        counts["excluded"] += int(excluded)
        counts["blocked"] += int(semantic_status == "blocked-source-conflict")
        counts["defects"] += int(semantic_status == "confirmed-defect")
        counts["pending"] += int(semantic_status == "pending")
        counts["sourceFirst"] += int(review["origin"] == "source-first")
        counts["reviews"] += 1
        deps = review["dependsOn"]
        if (not isinstance(deps, list) or any(not isinstance(item, str) for item in deps)
                or len(deps) != len(set(deps)) or identity in deps):
            raise DispositionError(f"{identity}: invalid dependencies")
        dependencies[identity] = deps
    for identity, deps in dependencies.items():
        if any(dependency not in seen_ids for dependency in deps):
            raise DispositionError(f"{identity}: dangling review dependency")
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(identity: str) -> None:
        if identity in visiting:
            raise DispositionError(f"Cyclic review dependency: {identity}")
        if identity in visited:
            return
        visiting.add(identity)
        for dependency in dependencies[identity]:
            visit(dependency)
        visiting.remove(identity)
        visited.add(identity)

    for identity in sorted(dependencies):
        visit(identity)
    return {
        "format": "InfinityDB source-coverage disposition validation",
        "formatVersion": 1,
        "status": "fingerprints-and-evidence-shape-only-not-semantic-approval",
        "counts": counts,
        "wholeRecordApprovalsIssued": 0,
        "sourceWideCompletenessApproved": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        records, sources, citations = current_evidence_inputs()
        result = validate_dispositions(
            manifest, record_hashes=records, source_pins=sources,
            citations=citations,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Source coverage dispositions: FAIL: {exc}\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
