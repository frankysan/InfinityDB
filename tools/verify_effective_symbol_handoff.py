"""Independently verify an intermediate effective-SVG override-stage handoff.

This verifies raw and effective identities. It does not certify font
conversion, deduplication, compression or publication readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file
from tools.verify_raw_symbol_handoff import verify_raw_handoff

LOOKUP_FORMAT = "InfinityDB symbol override lookup plan"
EFFECTIVE_FORMAT = "InfinityDB effective symbol processing report"
_RAW_SOURCE_ROOT = "https://assets.corvusbelli.net/army/img/"
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_PORTABLE = re.compile(r"[a-z0-9][a-z0-9._/-]*\.svg\Z")
_PENDING_STAGES = {
    "overrides": "completed",
    "fontAudit": "pending",
    "deduplication": "pending",
    "textConversion": "pending",
    "compression": "pending",
}


class EffectiveHandoffError(ValueError):
    """Intermediate symbol source evidence failed independent validation."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EffectiveHandoffError(f"Cannot read JSON from {path}: {exc}") from exc


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise EffectiveHandoffError(f"{label} must contain exactly {sorted(fields)}")
    return value


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise EffectiveHandoffError(f"{label} must be a lowercase SHA-256")
    return value


def _member(value: Any) -> str:
    if (
        not isinstance(value, str)
        or _PORTABLE.fullmatch(value) is None
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise EffectiveHandoffError(f"Invalid portable SVG path: {value!r}")
    return value


def verify_effective_symbol_handoff(
    plan_path: Path,
    lookup_path: Path,
    army_archive: Path,
    raw_archive: Path,
    raw_manifest: Path,
    raw_report: Path,
    effective_archive: Path,
    effective_manifest: Path,
    effective_report: Path,
    *,
    override_root: Path | None = None,
) -> dict[str, int]:
    """Verify exact raw and effective contents, source decisions and provenance."""
    verify_raw_handoff(plan_path, army_archive, raw_archive, raw_manifest, raw_report)
    plan = _json(plan_path)
    source_urls = [row["url"] for row in plan["requests"]]
    raw_rows = _json(raw_report)
    raw_available = {
        row["url"]: (row["sha256"], row["archivePath"]) for row in raw_rows["assets"]
    }
    raw_missing = {
        row["url"]: row["archivePath"] for row in raw_rows["unavailableAssets"]
    }

    lookup = _object(
        _json(lookup_path),
        {"format", "formatVersion", "sourcePlanSha256", "lookups"},
        "override lookup plan",
    )
    if lookup["format"] != LOOKUP_FORMAT or lookup["formatVersion"] != 1:
        raise EffectiveHandoffError("Unexpected override lookup format/version")
    source_hash = hashlib.sha256(_canonical(plan)).hexdigest()
    if lookup["sourcePlanSha256"] != source_hash:
        raise EffectiveHandoffError("Override lookup source-plan hash mismatch")
    lookups: dict[str, str] = {}
    if not isinstance(lookup["lookups"], list):
        raise EffectiveHandoffError("Override lookups are not an array")
    for index, row in enumerate(lookup["lookups"]):
        entry = _object(row, {"url", "overridePath"}, f"override lookup {index}")
        if not isinstance(entry["url"], str) or entry["url"] in lookups:
            raise EffectiveHandoffError("Duplicate override lookup URL")
        lookups[entry["url"]] = _member(entry["overridePath"])
    if (
        list(lookups) != source_urls
        or len({p.casefold() for p in lookups.values()}) != len(lookups)
    ):
        raise EffectiveHandoffError("Override lookups differ from source URL/path identity")

    report = _object(
        _json(effective_report),
        {
            "format", "formatVersion", "processingStages", "inputArtifact",
            "sourcePlanSha256", "overrideLookupPlanSha256",
            "rawSourceReportSha256", "rawSnapshot", "snapshot",
            "assets", "unavailableAssets", "rawUnavailableAssets",
            "unusedOverrides", "overrideSummary",
        },
        "effective symbol report",
    )
    if report["format"] != EFFECTIVE_FORMAT or report["formatVersion"] != 1:
        raise EffectiveHandoffError("Unexpected effective report format/version")
    if report["processingStages"] != _PENDING_STAGES:
        raise EffectiveHandoffError(
            "Intermediate report must mark only override resolution as completed"
        )
    if (
        report["inputArtifact"] != plan["inputArtifact"]
        or report["sourcePlanSha256"] != source_hash
        or report["overrideLookupPlanSha256"] != hashlib.sha256(
            _canonical(lookup)
        ).hexdigest()
        or report["rawSourceReportSha256"] != sha256_file(raw_report)
    ):
        raise EffectiveHandoffError("Effective report input/source hash mismatch")
    raw_pin = _object(
        report["rawSnapshot"],
        {"archiveName", "sha256", "manifestName", "manifestSha256"},
        "rawSnapshot",
    )
    if (
        raw_pin["archiveName"] != raw_archive.name
        or raw_pin["sha256"] != sha256_file(raw_archive)
        or raw_pin["manifestName"] != raw_manifest.name
        or raw_pin["manifestSha256"] != sha256_file(raw_manifest)
    ):
        raise EffectiveHandoffError("Raw snapshot binding differs from supplied bytes")
    snap = _object(
        report["snapshot"],
        {
            "archiveName", "sha256", "manifestName", "manifestSha256",
            "documentCount", "processedAt",
        },
        "effective snapshot",
    )
    if (
        not effective_archive.name.startswith("EFFECTIVE-SYMBOLS ")
        or snap["archiveName"] != effective_archive.name
        or snap["sha256"] != sha256_file(effective_archive)
        or snap["manifestName"] != effective_manifest.name
        or snap["manifestSha256"] != sha256_file(effective_manifest)
    ):
        raise EffectiveHandoffError("Effective ZIP/manifest/report hash mismatch")
    provenance = load_snapshot_manifest(effective_manifest, archive=effective_archive)
    if (
        provenance["formatVersion"] != 3
        or provenance["snapshot"]["type"] != "symbols"
        or provenance["source"]["url"] != _RAW_SOURCE_ROOT
        or provenance.get("inputArtifact", {}).get("name") != army_archive.name
        or provenance.get("inputArtifact", {}).get("sha256") != sha256_file(army_archive)
        or provenance["snapshot"]["acquiredAt"] != snap["processedAt"]
    ):
        raise EffectiveHandoffError("Effective provenance differs from pinned Army/output")

    effective_rows = report["assets"]
    unavailable_rows = report["unavailableAssets"]
    raw_missing_rows = report["rawUnavailableAssets"]
    if any(not isinstance(items, list) for items in (
        effective_rows, unavailable_rows, raw_missing_rows,
    )):
        raise EffectiveHandoffError("Effective source outcomes must be arrays")
    if raw_missing_rows != [
        {"url": url, "archivePath": raw_missing[url], "httpStatus": 404}
        for url in source_urls if url in raw_missing
    ]:
        raise EffectiveHandoffError("Effective report raw 404 coverage differs")
    effective: dict[str, tuple[str, str]] = {}
    paths: set[str] = set()
    direct = propagated = 0
    with zipfile.ZipFile(effective_archive) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if len(names) != len(set(names)):
            raise EffectiveHandoffError("Duplicate effective ZIP members")
        for index, value in enumerate(effective_rows):
            row = _object(
                value,
                {
                    "url", "archivePath", "sourceMethod", "upstreamSha256",
                    "sha256", "overridePath", "overrideSha256",
                },
                f"effective asset {index}",
            )
            url = row["url"]
            if (
                not isinstance(url, str)
                or url not in source_urls
                or url in effective
                or row["archivePath"] != dict(
                    (entry["url"], entry["archivePath"]) for entry in plan["requests"]
                )[url]
            ):
                raise EffectiveHandoffError(f"Unapproved effective URL/path at row {index}")
            relative = _member(row["archivePath"])
            if relative.casefold() in paths:
                raise EffectiveHandoffError("Effective output case-insensitive path collision")
            paths.add(relative.casefold())
            raw_sha = raw_available[url][0] if url in raw_available else None
            if row["upstreamSha256"] != raw_sha:
                raise EffectiveHandoffError(f"Effective upstream identity mismatch: {url}")
            expected = _sha(row["sha256"], "effective asset hash")
            try:
                body = archive.read(relative)
            except KeyError as exc:
                raise EffectiveHandoffError(
                    f"Missing effective ZIP member: {relative}"
                ) from exc
            if hashlib.sha256(body).hexdigest() != expected:
                raise EffectiveHandoffError(f"Effective SVG member digest mismatch: {relative}")
            try:
                svg = ElementTree.fromstring(body)
            except ElementTree.ParseError as exc:
                raise EffectiveHandoffError(f"Invalid effective SVG member: {relative}") from exc
            if svg.tag.rsplit("}", 1)[-1].casefold() != "svg":
                raise EffectiveHandoffError(f"Effective member is not SVG: {relative}")
            if row["sourceMethod"] == "network":
                if (
                    raw_sha is None or expected != raw_sha
                    or row["overridePath"] is not None
                    or row["overrideSha256"] is not None
                ):
                    raise EffectiveHandoffError("Raw source method/identity contradiction")
            elif row["sourceMethod"] == "override":
                override_path = _member(row["overridePath"])
                if row["overrideSha256"] != expected:
                    raise EffectiveHandoffError("Override content hash mismatch")
                if override_path not in lookups.values():
                    raise EffectiveHandoffError("Override path is not from approved lookups")
                donor = next(
                    (
                        candidate for candidate, candidate_path in lookups.items()
                        if candidate_path == override_path
                    ),
                    None,
                )
                if donor is None:
                    raise EffectiveHandoffError("Override donor is unapproved")
                if (
                    override_path != lookups[url]
                    and (
                        raw_sha is None
                        or raw_sha != raw_available.get(donor, (None, ""))[0]
                        or Path(override_path).parent
                        != Path(lookups[url]).parent
                    )
                ):
                    raise EffectiveHandoffError("Illegal override propagation identity")
                if override_path == lookups[url]:
                    direct += 1
                else:
                    propagated += 1
                if override_root is not None:
                    file = override_root / override_path
                    if not file.is_file() or file.is_symlink():
                        raise EffectiveHandoffError(f"Required override SVG missing: {file}")
                    if sha256_file(file) != expected:
                        raise EffectiveHandoffError(f"Local override input hash mismatch: {file}")
            else:
                raise EffectiveHandoffError("Unknown effective source method")
            effective[url] = (relative, expected)
    if set(names) != {entry[0] for entry in effective.values()}:
        raise EffectiveHandoffError("Effective ZIP members differ from reported assets")
    missing: set[str] = set()
    for index, value in enumerate(unavailable_rows):
        row = _object(value, {"url", "archivePath", "httpStatus"}, f"unavailable asset {index}")
        url = row["url"]
        if (
            not isinstance(url, str)
            or url not in raw_missing
            or url in effective
            or url in missing
            or row["archivePath"] != raw_missing[url]
            or row["httpStatus"] != 404
        ):
            raise EffectiveHandoffError("Effective unavailable source is not a verified raw 404")
        missing.add(url)
    if set(source_urls) != set(effective) | missing:
        raise EffectiveHandoffError("Effective report does not cover every reviewed URL")
    if (
        type(snap["documentCount"]) is not int
        or snap["documentCount"] != len(effective)
        or provenance["snapshot"]["documentCount"] != len(effective)
        or report["overrideSummary"] != {"direct": direct, "propagated": propagated}
    ):
        raise EffectiveHandoffError("Effective asset counts or override summary mismatch")
    unused = report["unusedOverrides"]
    if (
        not isinstance(unused, list)
        or unused != sorted(set(unused))
        or any(not isinstance(path, str) for path in unused)
    ):
        raise EffectiveHandoffError("Invalid unused override declarations")
    return {
        "requested": len(source_urls),
        "effective": len(effective),
        "overridden": direct + propagated,
        "unavailable": len(missing),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-plan", type=Path, required=True)
    parser.add_argument("--override-lookups", type=Path, required=True)
    parser.add_argument("--army", type=Path, required=True)
    parser.add_argument("--raw-archive", type=Path, required=True)
    parser.add_argument("--raw-manifest", type=Path, required=True)
    parser.add_argument("--raw-report", type=Path, required=True)
    parser.add_argument("--effective-archive", type=Path, required=True)
    parser.add_argument("--effective-manifest", type=Path, required=True)
    parser.add_argument("--effective-report", type=Path, required=True)
    parser.add_argument("--overrides", type=Path)
    args = parser.parse_args(argv)
    try:
        counts = verify_effective_symbol_handoff(
            args.source_plan, args.override_lookups, args.army,
            args.raw_archive, args.raw_manifest, args.raw_report,
            args.effective_archive, args.effective_manifest, args.effective_report,
            override_root=args.overrides,
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(
        "Intermediate effective source verified: "
        f"{counts['effective']} SVGs, {counts['overridden']} overridden, "
        f"{counts['unavailable']} missing; font/conversion/compression not complete"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
