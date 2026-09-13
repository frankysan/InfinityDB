#!/usr/bin/env python3
"""Merge Infinity Army JSON datasets into one lossless master.json.

The merger uses unit ``id`` as the global unit identity. Fields that are stable
for a unit across army/sectorial files are stored once, while fields known to
vary by army list (``profileGroups`` and unit-level ``filters``) are stored in
``byArmy``.

The script validates that no other unit field varies for a repeated unit ID and
then reconstructs every source document from the merged structure to prove that
no source data was lost.

Input may be either:
  * a directory containing files named like 101-panoceania.json, or
  * a ZIP archive containing those JSON files.

Uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SOURCE_NAME_RE = re.compile(r"^(?P<id>\d+)-(?P<slug>.+)\.json$", re.IGNORECASE)
VARIANT_UNIT_FIELDS = frozenset({"profileGroups", "filters"})


@dataclass(frozen=True)
class SourceDocument:
    faction_id: int
    slug: str
    filename: str
    sha256: str
    data: dict[str, Any]


def parse_source_name(name: str) -> tuple[int, str] | None:
    """Return (numeric faction/list id, slug) for an Army source filename."""
    match = SOURCE_NAME_RE.match(Path(name).name)
    if not match:
        return None
    return int(match.group("id")), match.group("slug")


def decode_document(raw: bytes, filename: str) -> dict[str, Any]:
    try:
        decoded = raw.decode("utf-8-sig")
        data = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not parse {filename}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{filename}: top-level JSON value is not an object")
    if not isinstance(data.get("units"), list):
        raise ValueError(f"{filename}: missing or invalid top-level 'units' array")
    return data


def make_source(filename: str, raw: bytes) -> SourceDocument | None:
    parsed = parse_source_name(filename)
    if parsed is None:
        return None
    faction_id, slug = parsed
    return SourceDocument(
        faction_id=faction_id,
        slug=slug,
        filename=Path(filename).name,
        sha256=hashlib.sha256(raw).hexdigest(),
        data=decode_document(raw, filename),
    )


def load_sources(input_path: Path) -> tuple[list[SourceDocument], list[str]]:
    """Load matching Army JSON documents from a directory or ZIP file."""
    sources: list[SourceDocument] = []
    skipped: list[str] = []

    if input_path.is_dir():
        for path in sorted(input_path.glob("*.json")):
            raw = path.read_bytes()
            source = make_source(path.name, raw)
            if source is None:
                skipped.append(path.name)
            else:
                sources.append(source)
    elif input_path.is_file() and zipfile.is_zipfile(input_path):
        with zipfile.ZipFile(input_path) as archive:
            for member in sorted(archive.namelist()):
                if member.endswith("/") or not member.lower().endswith(".json"):
                    continue
                raw = archive.read(member)
                source = make_source(member, raw)
                if source is None:
                    skipped.append(member)
                else:
                    sources.append(source)
    else:
        raise ValueError("Input must be a directory of JSON files or a ZIP archive")

    if not sources:
        raise ValueError("No files matching '<numeric-id>-<slug>.json' were found")

    sources.sort(key=lambda s: s.faction_id)

    ids = [s.faction_id for s in sources]
    duplicates = sorted(fid for fid, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate source faction/list IDs: {duplicates}")

    return sources, skipped


def canonical_json(value: Any) -> str:
    """Stable representation used only for equality diagnostics."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def diff_keys(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    keys = set(a) | set(b)
    return sorted(k for k in keys if a.get(k, object()) != b.get(k, object()))


def merge_sources(sources: Iterable[SourceDocument]) -> dict[str, Any]:
    sources = list(sources)
    units: dict[str, dict[str, Any]] = {}
    army_lists: dict[str, dict[str, Any]] = {}

    for source in sources:
        faction_key = str(source.faction_id)
        data = source.data

        # Preserve every top-level source field except 'units'.  Metadata added by
        # the merger is kept under '_meta' to avoid collisions with source fields.
        army_record: dict[str, Any] = {
            "_meta": {
                "factionId": source.faction_id,
                "slug": source.slug,
                "sourceFile": source.filename,
                "sourceSha256": source.sha256,
                "kind": "army" if "reinforcements" in data else "reinforcement",
            }
        }
        for key, value in data.items():
            if key != "units":
                army_record[key] = value

        unit_ids: list[int] = []
        seen_in_this_source: set[int] = set()

        for unit in data["units"]:
            if not isinstance(unit, dict) or not isinstance(unit.get("id"), int):
                raise ValueError(
                    f"{source.filename}: every unit must be an object with integer 'id'"
                )

            unit_id = unit["id"]
            if unit_id in seen_in_this_source:
                raise ValueError(f"{source.filename}: duplicate unit id {unit_id}")
            seen_in_this_source.add(unit_id)
            unit_ids.append(unit_id)

            shared = {key: value for key, value in unit.items() if key not in VARIANT_UNIT_FIELDS}
            variant = {key: value for key, value in unit.items() if key in VARIANT_UNIT_FIELDS}

            unit_key = str(unit_id)
            if unit_key not in units:
                units[unit_key] = {
                    "shared": shared,
                    "byArmy": {faction_key: variant},
                }
            else:
                existing = units[unit_key]
                if existing["shared"] != shared:
                    changed = diff_keys(existing["shared"], shared)
                    details = ", ".join(changed) if changed else "unknown fields"
                    raise ValueError(
                        f"Unit id {unit_id} has army-dependent data outside "
                        f"{sorted(VARIANT_UNIT_FIELDS)}. Changed field(s): {details}. "
                        "Refusing to merge because this would lose information."
                    )
                if faction_key in existing["byArmy"]:
                    raise ValueError(
                        f"Unit id {unit_id} occurs more than once for faction/list "
                        f"{source.faction_id}"
                    )
                existing["byArmy"][faction_key] = variant

        army_record["unitIds"] = unit_ids
        army_lists[faction_key] = army_record

    versions = Counter(str(s.data.get("version")) for s in sources)
    regular_count = sum("reinforcements" in s.data for s in sources)
    reinforcement_count = len(sources) - regular_count

    return {
        "_meta": {
            "format": "Infinity Army merged JSON",
            "formatVersion": 1,
            "sourceFileCount": len(sources),
            "armyFileCount": regular_count,
            "reinforcementFileCount": reinforcement_count,
            "unitOccurrenceCount": sum(len(s.data["units"]) for s in sources),
            "distinctUnitCount": len(units),
            "sourceVersions": dict(sorted(versions.items())),
            "unitIdentityField": "id",
            "armyVariantFields": sorted(VARIANT_UNIT_FIELDS),
        },
        "armyLists": army_lists,
        "units": units,
    }


def reconstruct_source(master: dict[str, Any], faction_id: int) -> dict[str, Any]:
    """Reconstruct one original source object from master.json."""
    faction_key = str(faction_id)
    army_record = master["armyLists"][faction_key]

    reconstructed = {
        key: value for key, value in army_record.items() if key not in {"_meta", "unitIds"}
    }

    reconstructed_units: list[dict[str, Any]] = []
    for unit_id in army_record["unitIds"]:
        unit_record = master["units"][str(unit_id)]
        variant = unit_record["byArmy"][faction_key]
        reconstructed_units.append({**unit_record["shared"], **variant})

    # Put units back after version where possible. Object key order does not affect
    # JSON semantics, but this keeps the reconstructed shape close to the source.
    ordered: dict[str, Any] = {}
    if "version" in reconstructed:
        ordered["version"] = reconstructed.pop("version")
    ordered["units"] = reconstructed_units
    ordered.update(reconstructed)
    return ordered


def validate_master(master: dict[str, Any], sources: Iterable[SourceDocument]) -> None:
    """Prove that every parsed source object can be reconstructed exactly."""
    for source in sources:
        reconstructed = reconstruct_source(master, source.faction_id)
        if reconstructed != source.data:
            # Find a useful top-level diagnostic before failing.
            changed = diff_keys(reconstructed, source.data)
            raise ValueError(
                f"Lossless reconstruction failed for {source.filename}; "
                f"different top-level field(s): {', '.join(changed)}"
            )


def write_json(path: Path, data: Any, compact: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        if compact:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    temp_path.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge Infinity Army faction JSON files into one lossless master.json"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Directory containing Army JSON files, or a ZIP archive",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("master.json"),
        help="Output file (default: ./master.json)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Write minified JSON instead of pretty-printed JSON",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip reconstruction verification (not recommended)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        sources, skipped = load_sources(args.input)
        master = merge_sources(sources)
        if not args.no_verify:
            validate_master(master, sources)
        write_json(args.output, master, args.compact)
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    meta = master["_meta"]
    print(f"Merged {meta['sourceFileCount']} source files -> {args.output}")
    print(
        f"Units: {meta['unitOccurrenceCount']} occurrences, "
        f"{meta['distinctUnitCount']} distinct IDs"
    )
    print(
        f"Files: {meta['armyFileCount']} army/sectorial, "
        f"{meta['reinforcementFileCount']} reinforcement"
    )
    print(f"Verification: {'skipped' if args.no_verify else 'passed (lossless)'}")
    if skipped:
        print("Skipped non-Army JSON files: " + ", ".join(skipped), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
