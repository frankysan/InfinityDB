"""Verify a standalone raw-symbol source result against InfinityDB's pinned plan.

This is a read-only research/source handoff. It does not import the standalone
producer, apply overrides, build a symbol manifest, or publish application assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree

from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file

PLAN_FORMAT = "InfinityDB raw symbol acquisition requests"
PLAN_VERSION = 1
REPORT_FORMAT = "InfinityDB raw symbol acquisition report"
REPORT_VERSION = 1
SYMBOL_SOURCE_URL = "https://assets.corvusbelli.net/army/img/"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PORTABLE_SVG = re.compile(r"[a-z0-9][a-z0-9._/-]*\.svg\Z")


class RawHandoffError(ValueError):
    """An exported raw-symbol artifact is not an acceptable pinned source handoff."""


def _object(value: Any, keys: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise RawHandoffError(f"{context} must contain exactly {sorted(keys)}")
    return value


def _source_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RawHandoffError(f"Could not load raw-symbol source JSON {path}: {exc}") from exc


def _canonical_bytes(document: Any) -> bytes:
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def verify_raw_handoff(
    plan_path: Path,
    army_archive: Path,
    symbol_archive: Path,
    snapshot_manifest: Path,
    result_report: Path,
) -> dict[str, int]:
    """Verify plan, original Army, raw source ZIP, provenance, and all report rows."""
    plan = _object(
        _source_json(plan_path),
        {"format", "formatVersion", "inputArtifact", "sourceDocumentCount", "requests"},
        "source plan",
    )
    if plan["format"] != PLAN_FORMAT or plan["formatVersion"] != PLAN_VERSION:
        raise RawHandoffError("Unsupported raw-symbol source-plan version")
    input_record = _object(plan["inputArtifact"], {"name", "sha256"}, "inputArtifact")
    if (
        not isinstance(input_record["name"], str)
        or input_record["name"] != army_archive.name
        or not isinstance(input_record["sha256"], str)
        or _SHA256.fullmatch(input_record["sha256"]) is None
        or sha256_file(army_archive) != input_record["sha256"]
    ):
        raise RawHandoffError("Army source-plan artifact name/SHA-256 mismatch")

    if (
        type(plan["sourceDocumentCount"]) is not int
        or plan["sourceDocumentCount"] < 2
        or not isinstance(plan["requests"], list)
        or not plan["requests"]
    ):
        raise RawHandoffError("Invalid source-document count or empty symbol requests")
    requested: dict[str, str] = {}
    for index, value in enumerate(plan["requests"]):
        record = _object(value, {"url", "archivePath"}, f"requests[{index}]")
        url, member = record["url"], record["archivePath"]
        if not isinstance(url, str):
            raise RawHandoffError(f"Invalid source-plan request at index {index}")
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "assets.corvusbelli.net"
            or not parsed.path.startswith("/army/img/")
            or not isinstance(member, str)
            or _PORTABLE_SVG.fullmatch(member) is None
            or any(part in {"", ".", ".."} for part in member.split("/"))
            or url in requested
        ):
            raise RawHandoffError(f"Invalid source-plan request at index {index}")
        requested[url] = member
    if (
        list(requested) != sorted(requested)
        or len({value.casefold() for value in requested.values()}) != len(requested)
    ):
        raise RawHandoffError("Source-plan URL or archive paths are not uniquely ordered")

    report = _object(
        _source_json(result_report),
        {
            "format", "formatVersion", "inputArtifact", "sourcePlanSha256",
            "snapshot", "assets", "unavailableAssets",
        },
        "raw source report",
    )
    if report["format"] != REPORT_FORMAT or report["formatVersion"] != REPORT_VERSION:
        raise RawHandoffError("Unsupported raw-symbol acquisition report version")
    if report["inputArtifact"] != input_record:
        raise RawHandoffError("Raw report Army identity differs from source plan")
    if report["sourcePlanSha256"] != hashlib.sha256(_canonical_bytes(plan)).hexdigest():
        raise RawHandoffError("Raw report source-plan SHA-256 mismatch")

    snapshot = _object(
        report["snapshot"],
        {
            "archiveName", "sha256", "snapshotManifestName",
            "snapshotManifestSha256", "documentCount", "acquiredAt",
        },
        "raw source report snapshot",
    )
    if (
        snapshot["archiveName"] != symbol_archive.name
        or snapshot["sha256"] != sha256_file(symbol_archive)
        or snapshot["snapshotManifestName"] != snapshot_manifest.name
        or snapshot["snapshotManifestSha256"] != sha256_file(snapshot_manifest)
    ):
        raise RawHandoffError("Raw source report archive/provenance identity mismatch")

    provenance = load_snapshot_manifest(snapshot_manifest, archive=symbol_archive)
    if (
        provenance["snapshot"]["type"] != "symbols"
        or provenance.get("inputArtifact", {}).get("name") != army_archive.name
        or provenance.get("inputArtifact", {}).get("sha256") != input_record["sha256"]
        or provenance["source"].get("url") != SYMBOL_SOURCE_URL
        or snapshot["acquiredAt"] != provenance["snapshot"]["acquiredAt"]
    ):
        raise RawHandoffError("Raw symbol provenance is not bound to the pinned Army/source")
    assets, unavailable = report["assets"], report["unavailableAssets"]
    if not isinstance(assets, list) or not assets or not isinstance(unavailable, list):
        raise RawHandoffError("Raw report assets must be a nonempty array")
    if (
        type(snapshot["documentCount"]) is not int
        or snapshot["documentCount"] != len(assets)
        or provenance["snapshot"]["documentCount"] != len(assets)
    ):
        raise RawHandoffError("Raw ZIP document count differs from source report")

    covered: set[str] = set()
    published: dict[str, str] = {}
    for index, value in enumerate(assets):
        asset = _object(
            value, {"url", "archivePath", "sha256", "sourceMethod"},
            f"assets[{index}]",
        )
        url, member = asset["url"], asset["archivePath"]
        if (
            not isinstance(url, str) or url not in requested
            or member != requested[url] or url in covered
            or asset["sourceMethod"] != "network"
            or not isinstance(asset["sha256"], str)
            or _SHA256.fullmatch(asset["sha256"]) is None
        ):
            raise RawHandoffError(f"Unapproved raw-symbol asset at index {index}")
        covered.add(url)
        published[member] = asset["sha256"]

    for index, value in enumerate(unavailable):
        missing = _object(
            value, {"url", "archivePath", "httpStatus"},
            f"unavailableAssets[{index}]",
        )
        url = missing["url"]
        if (
            not isinstance(url, str) or url not in requested
            or missing["archivePath"] != requested[url]
            or missing["httpStatus"] != 404
            or url in covered
        ):
            raise RawHandoffError(f"Unapproved unavailable source at index {index}")
        covered.add(url)
    if covered != set(requested):
        raise RawHandoffError("Raw acquisition did not account for every requested URL")

    with zipfile.ZipFile(symbol_archive) as archive:
        members = [info.filename for info in archive.infolist() if not info.is_dir()]
        if sorted(members) != sorted(published):
            raise RawHandoffError("Raw ZIP members differ from approved source-result assets")
        for member, expected_sha256 in published.items():
            body = archive.read(member)
            if hashlib.sha256(body).hexdigest() != expected_sha256:
                raise RawHandoffError(f"Raw SVG member SHA-256 mismatch: {member}")
            try:
                root = ElementTree.fromstring(body)
            except ElementTree.ParseError as exc:
                raise RawHandoffError(f"Invalid raw SVG member {member}: {exc}") from exc
            if root.tag.rsplit("}", 1)[-1].casefold() != "svg":
                raise RawHandoffError(f"Raw member is not SVG: {member}")

    return {
        "requested": len(requested),
        "acquired": len(assets),
        "unavailable": len(unavailable),
    }


def load_verified_raw_upstream(
    plan_path: Path,
    army_archive: Path,
    symbol_archive: Path,
    snapshot_manifest: Path,
    result_report: Path,
    *,
    authoritative_paths: dict[str, str],
    source_document_count: int,
) -> dict[str, bytes | None]:
    """Return verified upstream bytes, including explicit missing-source entries.

    The independently valid handoff must also exactly match the consumer's
    *current* source discovery and archive-path decisions.
    """
    verify_raw_handoff(
        plan_path, army_archive, symbol_archive, snapshot_manifest, result_report,
    )
    plan = _source_json(plan_path)
    expected = [
        {"url": url, "archivePath": authoritative_paths[url]}
        for url in sorted(authoritative_paths)
    ]
    if (
        plan["requests"] != expected
        or plan["sourceDocumentCount"] != source_document_count
    ):
        raise RawHandoffError(
            "Raw symbol source plan differs from current authoritative discovery"
        )

    report = _source_json(result_report)
    upstream: dict[str, bytes | None] = {
        row["url"]: None for row in report["unavailableAssets"]
    }
    with zipfile.ZipFile(symbol_archive) as archive:
        for row in report["assets"]:
            body = archive.read(row["archivePath"])
            if hashlib.sha256(body).hexdigest() != row["sha256"]:
                raise RawHandoffError("Raw SVG upstream changed after verification")
            upstream[row["url"]] = body
    return upstream


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--army", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        counts = verify_raw_handoff(
            args.plan, args.army, args.archive, args.manifest, args.report,
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(
        "Raw symbol handoff verified: "
        f"{counts['acquired']} acquired, {counts['unavailable']} unavailable "
        f"of {counts['requested']} reviewed requests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
