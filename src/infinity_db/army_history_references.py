"""Resolve historical reference occurrences against endpoint-specific catalogs.

These are source-backed comparison signatures, not canonical rule identities.
"""

from __future__ import annotations

from typing import Any

from infinity_db.army_history_characterization import fingerprint
from infinity_db.army_history_source import Document

CATALOGS = {"skills": "skills", "equip": "equips", "weapons": "weapons"}
CONTEXT_FLAGS = frozenset({"mercs", "specops", "teamops"})


def filter_catalog(data: Document, field: str) -> dict[int, Document]:
    """Reject duplicate keys; exclude only known army-list context flags."""
    filters = data.get("filters")
    if not isinstance(filters, dict) or not isinstance(filters.get(field), list):
        return {}
    result = {}
    duplicates = set()
    for row in filters[field]:
        if not isinstance(row, dict) or type(row.get("id")) is not int:
            continue
        identity = row["id"]
        if identity in result:
            duplicates.add(identity)
        result[identity] = {k: v for k, v in row.items() if k not in CONTEXT_FLAGS}
    return {
        k: v for k, v in result.items()
        if k not in duplicates and isinstance(v.get("name"), str) and v["name"]
    }


def resolve_references(
    value: Any, field: str, data: Document,
    contexts: list[dict[str, dict[int, tuple[str, ...]]]],
) -> tuple[list[Document] | None, str]:
    """Resolve a multiset, retaining quantities, extra definitions and unknown fields.

    Filter-only resolution is explicit; conflicting contexts are never chosen.
    Numeric IDs remain part of signatures (no inference of rekeys by name).
    """
    if not isinstance(value, list):
        return None, "referenceShape"
    if not value:
        return [], "empty"
    if not contexts:
        return None, "missingMetadataContext"
    filters = filter_catalog(data, field)
    extras = filter_catalog(data, "extras")
    result = []
    filter_only = False
    for row in value:
        if not isinstance(row, dict) or type(row.get("id")) is not int:
            return None, "referenceShape"
        identity = row["id"]
        definition = filters.get(identity)
        if definition is None:
            return None, "missingFactionDefinition"
        choices = {context.get(CATALOGS[field], {}).get(identity) for context in contexts}
        if len(choices) > 1:
            return None, "ambiguousMetadataDefinition"
        metadata = next(iter(choices), None)
        filter_only |= metadata is None
        occurrence = {k: v for k, v in row.items() if k not in {"id", "order"}}
        if "extra" in occurrence and occurrence["extra"] is not None:
            refs = occurrence["extra"]
            if not isinstance(refs, list) or any(type(i) is not int for i in refs):
                return None, "extraShape"
            if any(i not in extras for i in refs):
                return None, "missingExtraDefinition"
            occurrence["extra"] = [extras[i] for i in refs]
        result.append({
            "filter": definition,
            "metadataFingerprints": list(metadata) if metadata is not None else None,
            "occurrence": occurrence,
        })
    return sorted(result, key=fingerprint), "filterOnly" if filter_only else "withMetadata"
