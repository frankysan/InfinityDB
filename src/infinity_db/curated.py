"""Load human-reviewed reference facts prepared from external documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CURATED_FORMAT = "InfinityDB curated reference"
CURATED_FORMAT_VERSION = 2
REQUIRED_COLLECTION_FIELDS = frozenset(
    {"id", "title", "domain", "status", "effectiveFrom", "authority"}
)
REQUIRED_SOURCE_FIELDS = frozenset({"id", "kind", "title", "version", "authority"})
REQUIRED_RECORD_FIELDS = frozenset({"id", "kind", "name", "summary", "citations"})


def _require_string(value: Any, field: str, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: '{field}' must be a non-empty string")


def load_curated_document(path: Path) -> dict[str, Any]:
    """Load and validate one curated JSON document.

    This loader intentionally accepts only the intermediary JSON format. Raw
    PDFs, wiki snapshots, and arbitrary JSON are not valid ingestion sources.
    """
    if path.suffix.casefold() != ".json":
        raise ValueError(f"Curated source must be a .json file: {path}")

    try:
        document = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read curated source {path}: {exc}") from exc

    if not isinstance(document, dict):
        raise ValueError("Curated source must contain a top-level object")
    if document.get("format") != CURATED_FORMAT:
        raise ValueError(f"Curated source must declare format '{CURATED_FORMAT}'")
    if document.get("formatVersion") != CURATED_FORMAT_VERSION:
        raise ValueError(f"Unsupported curated format version: {document.get('formatVersion')!r}")

    collection = document.get("collection")
    sources = document.get("sources")
    records = document.get("records")
    if not isinstance(collection, dict):
        raise ValueError("Curated source must contain a collection object")
    missing = REQUIRED_COLLECTION_FIELDS - collection.keys()
    if missing:
        raise ValueError(f"collection: missing fields {sorted(missing)}")
    for field in REQUIRED_COLLECTION_FIELDS:
        _require_string(collection[field], field, "collection")
    if not isinstance(sources, list) or not isinstance(records, list):
        raise ValueError("Curated source must contain 'sources' and 'records' arrays")

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        context = f"sources[{index}]"
        if not isinstance(source, dict):
            raise ValueError(f"{context}: must be an object")
        missing = REQUIRED_SOURCE_FIELDS - source.keys()
        if missing:
            raise ValueError(f"{context}: missing fields {sorted(missing)}")
        for field in REQUIRED_SOURCE_FIELDS:
            _require_string(source[field], field, context)
        if source["kind"] not in {"pdf", "wiki"}:
            raise ValueError(f"{context}: 'kind' must be 'pdf' or 'wiki'")
        if not isinstance(source.get("localPath"), str) and not isinstance(source.get("url"), str):
            raise ValueError(f"{context}: requires a 'localPath' or 'url'")
        if source["kind"] == "pdf":
            _require_string(source.get("publishedDate"), "publishedDate", context)
            if type(source.get("pageCount")) is not int or source["pageCount"] < 1:
                raise ValueError(f"{context}: PDF 'pageCount' must be a positive integer")
        elif source["kind"] == "wiki":
            _require_string(source.get("snapshotDate"), "snapshotDate", context)
        source_id = source["id"]
        if source_id in source_ids:
            raise ValueError(f"{context}: duplicate source id {source_id!r}")
        source_ids.add(source_id)

    record_ids: set[str] = set()
    for index, record in enumerate(records):
        context = f"records[{index}]"
        if not isinstance(record, dict):
            raise ValueError(f"{context}: must be an object")
        missing = REQUIRED_RECORD_FIELDS - record.keys()
        if missing:
            raise ValueError(f"{context}: missing fields {sorted(missing)}")
        for field in ("id", "kind", "name", "summary"):
            _require_string(record[field], field, context)
        if not isinstance(record["citations"], list) or not record["citations"]:
            raise ValueError(f"{context}: 'citations' must be a non-empty array")
        for optional_list in ("aliases", "relatedRecords"):
            if optional_list in record and (
                not isinstance(record[optional_list], list)
                or any(not isinstance(value, str) for value in record[optional_list])
            ):
                raise ValueError(f"{context}: '{optional_list}' must be an array of strings")
        for optional_object in ("scope", "facts", "review"):
            if optional_object in record and not isinstance(record[optional_object], dict):
                raise ValueError(f"{context}: '{optional_object}' must be an object")
        if "armyLinks" in record and not isinstance(record["armyLinks"], list):
            raise ValueError(f"{context}: 'armyLinks' must be an array")
        if record["id"] in record_ids:
            raise ValueError(f"{context}: duplicate record id {record['id']!r}")
        record_ids.add(record["id"])
        for citation_index, citation in enumerate(record["citations"]):
            ref_context = f"{context}.citations[{citation_index}]"
            if not isinstance(citation, dict):
                raise ValueError(f"{ref_context}: must be an object")
            if "sourceId" not in citation:
                raise ValueError(f"{ref_context}: requires 'sourceId'")
            source_id = citation["sourceId"]
            if source_id not in source_ids:
                raise ValueError(f"{ref_context}: unknown source id {source_id!r}")
            source_kind = next(source["kind"] for source in sources if source["id"] == source_id)
            if source_kind == "pdf":
                if not isinstance(citation.get("page"), int) or citation["page"] < 1:
                    raise ValueError(f"{ref_context}: PDF 'page' must be a positive integer")
            elif source_kind == "wiki":
                _require_string(citation.get("path"), "path", ref_context)
                _require_string(citation.get("snapshotDate"), "snapshotDate", ref_context)

        for link_index, link in enumerate(record.get("armyLinks", [])):
            link_context = f"{context}.armyLinks[{link_index}]"
            if not isinstance(link, dict):
                raise ValueError(f"{link_context}: must be an object")
            _require_string(link.get("entity"), "entity", link_context)
            if "id" not in link and "name" not in link:
                raise ValueError(f"{link_context}: requires 'id' or 'name'")

    return document
