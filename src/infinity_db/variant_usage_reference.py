"""Verified public read model for reviewed Rule/Variant usage."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, TypeGuard

PUBLICATION_FORMAT = "infinitydb-rule-variant-usage"
PUBLICATION_VERSION = 1
PUBLICATION_SCOPE = "exact-reviewed-source-variants"


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def publication_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Make the public exact-variant view, excluding candidate diagnostics."""
    if (
        candidate.get("format") != PUBLICATION_FORMAT
        or candidate.get("formatVersion") != 2
        or candidate.get("scope") != "read-only-candidate-not-published"
        or not isinstance(candidate.get("sourceSnapshot"), dict)
        or not isinstance(candidate.get("variants"), list)
    ):
        raise ValueError("Unsupported variant usage candidate")
    publication = {
        "format": PUBLICATION_FORMAT,
        "formatVersion": PUBLICATION_VERSION,
        "scope": PUBLICATION_SCOPE,
        # Raw SQLite bytes may differ across hosts even for the same validated
        # export pair. Keep the raw byte digest in build diagnostics, not in
        # the portable publication; runtime release artifacts remain byte-bound.
        "sourceSnapshot": {
            key: value for key, value in candidate["sourceSnapshot"].items()
            if key != "rawDatabaseSha256"
        },
        "variants": candidate["variants"],
    }
    return _validate_publication(publication)


def _is_positive_integer(value: Any) -> TypeGuard[int]:
    return type(value) is int and value > 0


def _is_nonnegative_integer(value: Any) -> TypeGuard[int]:
    return type(value) is int and value >= 0


def _sort_value(value: Any) -> int:
    if value is None:
        return -1
    if _is_nonnegative_integer(value):
        return value or -1
    raise ValueError("Invalid variant usage source ordering value")


def _validate_publication(document: Any) -> dict[str, Any]:
    if (
        not isinstance(document, dict)
        or document.get("format") != PUBLICATION_FORMAT
        or document.get("formatVersion") != PUBLICATION_VERSION
        or document.get("scope") != PUBLICATION_SCOPE
        or not isinstance(document.get("sourceSnapshot"), dict)
        or not isinstance(document.get("variants"), list)
    ):
        raise ValueError("Unsupported variant usage publication")

    snapshot = document["sourceSnapshot"]
    digest_fields = (
        "armyArchiveSha256",
        "armyDatabaseSha256",
        "rulesDatabaseSha256",
        "exportPairSha256",
        "deployedObjectPublicationSha256",
    )
    if any(
        not isinstance(snapshot.get(field), str)
        or len(snapshot[field]) != 64
        or any(char not in "0123456789abcdef" for char in snapshot[field])
        for field in digest_fields
    ):
        raise ValueError("Variant usage publication has invalid source fingerprints")

    seen_groups: set[str] = set()
    seen_rows: set[tuple[str, str, int]] = set()
    previous_group: str | None = None
    for group in document["variants"]:
        if not isinstance(group, dict):
            raise ValueError("Invalid variant usage group")
        key = group.get("variantKey")
        variant = group.get("variant")
        rows = group.get("sourceRows")
        if (
            not isinstance(key, str)
            or not isinstance(variant, dict)
            or not isinstance(rows, list)
            or key != _canonical(variant)
            or key in seen_groups
            or (previous_group is not None and key < previous_group)
        ):
            raise ValueError("Invalid, duplicate or unordered variant usage group")
        seen_groups.add(key)
        previous_group = key

        record_id = variant.get("recordId")
        catalog = (
            "skills" if isinstance(record_id, str)
            and re.fullmatch(r"skill:[a-z0-9][a-z0-9-]*", record_id)
            else "equipment" if isinstance(record_id, str)
            and re.fullmatch(r"equipment:[a-z0-9][a-z0-9-]*", record_id)
            else None
        )
        if catalog is None:
            raise ValueError("Variant usage group has an unsupported canonical record")

        unit_ids: set[int] = set()
        army_unit_ids: set[tuple[int, int]] = set()
        contexts: set[tuple[int, int, str, str]] = set()
        previous_row: tuple[int, ...] | None = None
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid variant usage source row")
            owner_kind = row.get("ownerKind")
            occurrence_id = row.get("occurrenceId")
            source_key = row.get("sourceKey")
            context = row.get("context")
            if (
                row.get("catalog") != catalog
                or not isinstance(owner_kind, str)
                or owner_kind not in {"profile", "option", "unit_option"}
                or not _is_positive_integer(occurrence_id)
                or source_key != [catalog, owner_kind, occurrence_id]
                or not _is_positive_integer(row.get("sourceId"))
                or not _is_positive_integer(row.get("applicationItemId"))
                or not _is_positive_integer(row.get("unitId"))
                or not _is_nonnegative_integer(row.get("position"))
                or not isinstance(context, dict)
                or context.get("ownerKind") != owner_kind
                or (catalog, owner_kind, occurrence_id) in seen_rows
            ):
                raise ValueError("Invalid or duplicate variant usage source identity")
            seen_rows.add((catalog, owner_kind, occurrence_id))

            source_unit_id = context.get("sourceUnitId")
            logical_unit_id = context.get("logicalUnitId")
            army_id = context.get("applicationArmyId")
            row_order = (
                _sort_value(army_id),
                _sort_value(logical_unit_id),
                _sort_value(row.get("armyId")),
                row["unitId"],
                ("profile", "option", "unit_option").index(owner_kind),
                _sort_value(row.get("groupId")),
                _sort_value(context.get("contextPosition")),
                _sort_value(row.get("displayOrder")),
                row["position"],
                occurrence_id,
            )
            if previous_row is not None and row_order < previous_row:
                raise ValueError("Variant usage source rows are not stably ordered")
            previous_row = row_order
            if not _is_positive_integer(source_unit_id):
                raise ValueError("Variant usage source row has no Unit context")
            if owner_kind == "unit_option":
                if army_id is not None or logical_unit_id is not None:
                    raise ValueError("Shared Unit option cannot claim Army ownership")
            else:
                payload_hash = context.get("payloadSha256")
                if (
                    not _is_positive_integer(army_id)
                    or not _is_positive_integer(logical_unit_id)
                    or not isinstance(payload_hash, str)
                    or not payload_hash
                ):
                    raise ValueError("Variant usage source row has incomplete owner context")
                unit_ids.add(logical_unit_id)
                army_unit_ids.add((army_id, logical_unit_id))
                contexts.add((army_id, logical_unit_id, owner_kind, payload_hash))

        expected_counts = {
            "uniqueUnits": len(unit_ids),
            "uniqueArmyUnits": len(army_unit_ids),
            "distinctContexts": len(contexts),
            "distinctProfileContexts": sum(item[2] == "profile" for item in contexts),
            "distinctLoadoutContexts": sum(item[2] == "option" for item in contexts),
            "sourceRelationshipRows": len(rows),
        }
        if any(
            type(group.get(name)) is not int or group[name] != count
            for name, count in expected_counts.items()
        ):
            raise ValueError("Variant usage group counts do not match source rows")

    return document


def load_variant_usage_publication(
    path: Path,
    army_database: Path,
    rules_database: Path | None,
    deployed_object_publication: Path,
) -> dict[str, Any] | None:
    """Load an exact-variant publication only when its release pair matches."""
    if not path.is_file():
        return None
    if rules_database is None:
        raise ValueError("Variant usage publication requires a rules database")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid variant usage publication JSON") from exc
    publication = _validate_publication(document)
    snapshot = publication["sourceSnapshot"]
    if (
        snapshot["armyDatabaseSha256"] != _sha256(army_database)
        or snapshot["rulesDatabaseSha256"] != _sha256(rules_database)
        or not deployed_object_publication.is_file()
        or snapshot["deployedObjectPublicationSha256"]
        != _sha256(deployed_object_publication)
    ):
        raise ValueError("Variant usage publication does not match release artifacts")
    return publication
