"""Deterministic input identity shared by the databases of one offline build."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

BUILD_PROVENANCE_KEY = "database_set_build"
MANIFEST_FORMAT = "InfinityDB database-set build inputs"
FAMILIES = ("army", "rules-n5")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build_input_fingerprints(root: Path) -> dict[str, str]:
    """Hash the maintained input envelope without requiring upstream archives."""
    paths = [
        path for directory in (
            "config/catalogs", "config/identity", "config/validation", "config/symbols",
            "data/curated",
        ) for path in (root / directory).rglob("*.json") if path.name != "example.json"
    ]
    paths.extend((root / "src").rglob("*.py"))
    paths.extend([
        root / "pyproject.toml", root / "data/manifests/symbol-publication.json",
        root / "src/infinity_db/web/static/restrictions-reference.json",
    ])
    result = {}
    for path in paths:
        name = path.relative_to(root).as_posix()
        data = path.read_bytes()
        if name.startswith("src/") and name.endswith(".py"):
            data = data.replace(b"\r\n", b"\n")
        result[name] = hashlib.sha256(data).hexdigest()
    return dict(sorted(result.items()))


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _validate_manifest(manifest: Any) -> None:
    if (
        not isinstance(manifest, dict)
        or set(manifest) != {"format", "formatVersion", "families", "builderRevision",
                             "source", "inputs"}
        or manifest["format"] != MANIFEST_FORMAT
        or type(manifest["formatVersion"]) is not int or manifest["formatVersion"] != 1
        or manifest["families"] != list(FAMILIES)
        or not _is_digest(manifest["builderRevision"])
        or not isinstance(manifest["inputs"], dict) or not manifest["inputs"]
    ):
        raise ValueError("Invalid database-set input manifest")
    for identity, digest in manifest["inputs"].items():
        if (
            not isinstance(identity, str) or not identity or "\\" in identity
            or identity.startswith("/") or ":" in identity
            or any(part in {"", ".", ".."} for part in identity.split("/"))
            or not _is_digest(digest)
        ):
            raise ValueError("Invalid database-set input identity or digest")
    source = manifest["source"]
    if (
        not isinstance(source, dict)
        or set(source) != {"archiveName", "archiveSha256", "metadataName", "metadataSha256"}
        or any(
            not isinstance(source[name], str) or not source[name]
            or any(char in source[name] for char in "/\\:")
            for name in ("archiveName", "metadataName")
        )
        or any(not _is_digest(source[key]) for key in ("archiveSha256", "metadataSha256"))
    ):
        raise ValueError("Invalid database-set source identity")


def build_set_id(manifest: dict[str, Any]) -> str:
    """Hash inputs before writing any output; never include final database hashes."""
    _validate_manifest(manifest)
    content = b"InfinityDB database-set build v1\0" + canonical_bytes(manifest)
    return hashlib.sha256(content).hexdigest()


def build_record(
    manifest: dict[str, Any], family: str, *, army_generation: str | None = None,
) -> dict[str, Any]:
    record = {
        "formatVersion": 1, "buildSetId": build_set_id(manifest),
        "family": family, "manifest": manifest,
    }
    if army_generation is not None:
        record["requiredArmyExportPairSha256"] = army_generation
    validate_build_record(record, family)
    return record


def validate_build_record(record: Any, family: str) -> dict[str, Any]:
    expected = {"formatVersion", "buildSetId", "family", "manifest"}
    if family == "rules-n5":
        expected.add("requiredArmyExportPairSha256")
    if (
        family not in FAMILIES or not isinstance(record, dict) or set(record) != expected
        or type(record["formatVersion"]) is not int or record["formatVersion"] != 1
        or record["family"] != family
        or record["buildSetId"] != build_set_id(record["manifest"])
        or (family == "rules-n5" and not _is_digest(record["requiredArmyExportPairSha256"]))
    ):
        raise ValueError("Invalid database-set build provenance")
    return record


def _metadata(path: Path, *, rules: bool = False) -> dict[str, Any]:
    from .database.schema import METADATA_TABLE
    from .rules_database import RULES_METADATA_TABLE

    table = RULES_METADATA_TABLE if rules else METADATA_TABLE
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        return {
            key: json.loads(value)
            for key, value in connection.execute(f"SELECT key,value FROM {table}")
        }


def validate_set_provenance(army: Path, rules: Path) -> dict[str, Any]:
    """Reject mixed/partial recorded generations; identify older unrecorded sets."""
    army_meta, rules_meta = _metadata(army), _metadata(rules, rules=True)
    records = army_meta.get(BUILD_PROVENANCE_KEY), rules_meta.get(BUILD_PROVENANCE_KEY)
    if BUILD_PROVENANCE_KEY not in army_meta and BUILD_PROVENANCE_KEY not in rules_meta:
        return {"status": "not-recorded"}
    army_record, rules_record = (
        validate_build_record(record, family)
        for record, family in zip(records, FAMILIES, strict=True)
    )
    if army_record["buildSetId"] != rules_record["buildSetId"]:
        raise ValueError("Database-set build generations do not match")
    generation = army_meta.get("export_pair_sha256")
    if not _is_digest(generation) or rules_record["requiredArmyExportPairSha256"] != generation:
        raise ValueError("Rules database requires a different Army export generation")
    if army_meta.get("_meta", {}).get("snapshotArchiveSha256") != (
        army_record["manifest"]["source"]["archiveSha256"]
    ):
        raise ValueError("Database-set manifest does not match the Army source archive")
    metadata = army_meta.get("armyMetadata", {})
    source = army_record["manifest"]["source"]
    if (
        metadata.get("sourceSha256") != source["metadataSha256"]
        or metadata.get("sourceFile") != source["metadataName"]
    ):
        raise ValueError("Database-set manifest does not match the Army metadata source")
    return {
        "status": "matched", "buildSetId": army_record["buildSetId"],
        "builderRevision": army_record["manifest"]["builderRevision"],
        "armyExportPairSha256": generation,
    }


def validate_build_input_freshness(army: Path, root: Path) -> None:
    """Release/source gate: require the maintained checkout inputs recorded by the build."""
    record = validate_build_record(_metadata(army).get(BUILD_PROVENANCE_KEY), "army")
    root = root.resolve()
    expected = record["manifest"]["inputs"]
    actual = build_input_fingerprints(root)
    changed = sorted(name for name in expected.keys() | actual.keys()
                     if expected.get(name) != actual.get(name))
    if changed:
        raise ValueError(f"Runtime databases require rebuilding after input change: {changed[0]}")
