"""Load human-reviewed reference facts prepared from external documents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from infinity_db.domain_slugs import validate_typed_domain_id

CURATED_FORMAT = "InfinityDB curated reference"
CURATED_FORMAT_VERSION = 3
REQUIRED_COLLECTION_FIELDS = frozenset(
    {"id", "title", "domain", "status", "effectiveFrom", "authority"}
)
REQUIRED_SOURCE_FIELDS = frozenset({"id", "kind", "title", "version", "authority"})
REQUIRED_RECORD_FIELDS = frozenset({"id", "kind", "name", "summary", "citations"})
REQUIRED_SKILL_TYPE_FIELDS = frozenset({"id", "name", "labels", "descriptions"})
REQUIRED_LABEL_FIELDS = frozenset({"id", "name", "description"})
EXCLUDED_CURATED_FILENAMES = frozenset({"example.json"})


def _require_string(value: Any, field: str, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}: '{field}' must be a non-empty string")


def _require_positive_int(value: Any, field: str, context: str) -> None:
    if type(value) is not int or value < 1:
        raise ValueError(f"{context}: '{field}' must be a positive integer")


def _validate_reference(
    reference: dict[str, Any],
    source: dict[str, Any],
    context: str,
    *,
    require_heading: bool = False,
) -> None:
    deprecated = reference.keys() & {"path", "snapshotDate"}
    if deprecated:
        raise ValueError(f"{context}: unsupported legacy fields {sorted(deprecated)}")
    if require_heading:
        _require_string(reference.get("heading"), "heading", context)

    if source["kind"] == "pdf":
        _require_positive_int(reference.get("page"), "page", context)
        if "member" in reference:
            raise ValueError(f"{context}: PDF references must not contain 'member'")
        return

    if source.get("localPath"):
        _require_string(reference.get("member"), "member", context)
        if "page" in reference:
            raise ValueError(f"{context}: archived wiki references must not contain 'page'")
        return

    if "page" in reference or "member" in reference:
        raise ValueError(f"{context}: URL-backed wiki references use the source URL directly")


def _validate_source(source: dict[str, Any], context: str) -> None:
    missing = REQUIRED_SOURCE_FIELDS - source.keys()
    if missing:
        raise ValueError(f"{context}: missing fields {sorted(missing)}")
    for field in REQUIRED_SOURCE_FIELDS:
        _require_string(source[field], field, context)
    if source["kind"] not in {"pdf", "wiki"}:
        raise ValueError(f"{context}: 'kind' must be 'pdf' or 'wiki'")

    _require_string(source.get("url"), "url", context)
    if source["kind"] == "pdf":
        _require_string(source.get("publishedDate"), "publishedDate", context)
        _require_string(source.get("localPath"), "localPath", context)
        _require_positive_int(source.get("pageCount"), "pageCount", context)
        return

    if source.get("localPath") is not None:
        _require_string(source.get("localPath"), "localPath", context)
        _require_string(source.get("acquiredAt"), "acquiredAt", context)
        _require_string(source.get("sha256"), "sha256", context)
        sha256 = source["sha256"]
        if len(sha256) != 64 or any(char not in "0123456789abcdefABCDEF" for char in sha256):
            raise ValueError(f"{context}: 'sha256' must be a 64-character hexadecimal digest")
        _require_string(source.get("language"), "language", context)
        _require_positive_int(source.get("documentCount"), "documentCount", context)
    else:
        _require_string(source.get("retrievedDate"), "retrievedDate", context)


def discover_curated_documents(directory: Path) -> list[Path]:
    """Return curated rules collections, excluding non-rule curated categories.

    Passing the common ``data/curated`` parent remains supported, but once a
    dedicated ``rules/`` subtree exists only that subtree is an input to this
    rules-reference loader.
    """
    if not directory.is_dir():
        raise ValueError(f"Curated source directory does not exist: {directory}")
    rules_directory = directory / "rules"
    search_root = rules_directory if rules_directory.is_dir() else directory
    return sorted(
        path
        for path in search_root.rglob("*.json")
        if path.is_file() and path.name.casefold() not in EXCLUDED_CURATED_FILENAMES
    )


def load_curated_directory(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Load every curated collection below a directory except example templates."""
    documents = [
        (path, load_curated_document(path)) for path in discover_curated_documents(directory)
    ]
    if not documents:
        raise ValueError(f"No curated collection JSON files found in {directory}")
    return documents


def _validate_weapon_special_profile(profile: object, context: str) -> None:
    if not isinstance(profile, dict):
        raise ValueError(f"{context}: must be an object")
    required = {"stats", "equipment", "skills", "ccWeapon"}
    missing = required - profile.keys()
    unknown = profile.keys() - required
    if missing:
        raise ValueError(f"{context}: missing fields {sorted(missing)}")
    if unknown:
        raise ValueError(f"{context}: unsupported fields {sorted(unknown)}")

    stats = profile["stats"]
    if not isinstance(stats, list) or not stats:
        raise ValueError(f"{context}.stats: must be a non-empty array")
    seen_stats: set[str] = set()
    for index, stat in enumerate(stats):
        stat_context = f"{context}.stats[{index}]"
        if (
            not isinstance(stat, list)
            or len(stat) != 2
            or not all(isinstance(value, str) and value.strip() for value in stat)
        ):
            raise ValueError(f"{stat_context}: must be [name, value] strings")
        if stat[0] in seen_stats:
            raise ValueError(f"{stat_context}: duplicate stat name {stat[0]!r}")
        seen_stats.add(stat[0])

    for field in ("equipment", "skills"):
        values = profile[field]
        if not isinstance(values, list) or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError(f"{context}.{field}: must be an array of non-empty strings")
    _require_string(profile["ccWeapon"], "ccWeapon", context)


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
    skill_types = document.get("skillTypes")
    labels = document.get("labels")
    vocabulary_sources = document.get("vocabularySources")
    if not isinstance(collection, dict):
        raise ValueError("Curated source must contain a collection object")
    missing = REQUIRED_COLLECTION_FIELDS - collection.keys()
    if missing:
        raise ValueError(f"collection: missing fields {sorted(missing)}")
    for field in REQUIRED_COLLECTION_FIELDS:
        _require_string(collection[field], field, "collection")
    if not isinstance(sources, list) or not isinstance(records, list):
        raise ValueError("Curated source must contain 'sources' and 'records' arrays")
    if not isinstance(skill_types, list):
        raise ValueError("Curated source must contain a 'skillTypes' array")
    if not isinstance(labels, list):
        raise ValueError("Curated source must contain a 'labels' array")
    if not isinstance(vocabulary_sources, dict):
        raise ValueError("Curated source must contain a 'vocabularySources' object")
    skill_type_ids: set[str] = set()
    for index, skill_type in enumerate(skill_types):
        context = f"skillTypes[{index}]"
        if not isinstance(skill_type, dict):
            raise ValueError(f"{context}: must be an object")
        missing = REQUIRED_SKILL_TYPE_FIELDS - skill_type.keys()
        if missing:
            raise ValueError(f"{context}: missing fields {sorted(missing)}")
        for field in ("id", "name"):
            _require_string(skill_type[field], field, context)
        skill_type_labels = skill_type["labels"]
        if (
            not isinstance(skill_type_labels, list)
            or len(skill_type_labels) != 2
            or any(not isinstance(label, str) or not label.strip() for label in skill_type_labels)
        ):
            raise ValueError(f"{context}: 'labels' must contain singular and plural strings")
        descriptions = skill_type["descriptions"]
        if not isinstance(descriptions, dict):
            raise ValueError(f"{context}: 'descriptions' must be an object")
        for form in ("singular", "plural"):
            _require_string(descriptions.get(form), f"descriptions.{form}", context)
        if skill_type["id"] in skill_type_ids:
            raise ValueError(f"{context}: duplicate skill type id {skill_type['id']!r}")
        skill_type_ids.add(skill_type["id"])

    label_ids: set[str] = set()
    for index, label in enumerate(labels):
        context = f"labels[{index}]"
        if not isinstance(label, dict):
            raise ValueError(f"{context}: must be an object")
        missing = REQUIRED_LABEL_FIELDS - label.keys()
        if missing:
            raise ValueError(f"{context}: missing fields {sorted(missing)}")
        for field in REQUIRED_LABEL_FIELDS:
            _require_string(label[field], field, context)
        if label["id"] in label_ids:
            raise ValueError(f"{context}: duplicate label id {label['id']!r}")
        label_ids.add(label["id"])

    source_ids: set[str] = set()
    source_by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        context = f"sources[{index}]"
        if not isinstance(source, dict):
            raise ValueError(f"{context}: must be an object")
        _validate_source(source, context)
        source_id = source["id"]
        if source_id in source_ids:
            raise ValueError(f"{context}: duplicate source id {source_id!r}")
        source_ids.add(source_id)
        source_by_id[source_id] = source

    for vocabulary_name in ("skillTypes", "labels"):
        source_list = vocabulary_sources.get(vocabulary_name)
        if not isinstance(source_list, list):
            raise ValueError(f"vocabularySources.{vocabulary_name} must be an array")
        for index, reference in enumerate(source_list):
            context = f"vocabularySources.{vocabulary_name}[{index}]"
            if not isinstance(reference, dict):
                raise ValueError(f"{context}: must be an object")
            _require_string(reference.get("sourceId"), "sourceId", context)
            source_id = reference["sourceId"]
            if source_id not in source_by_id:
                raise ValueError(f"{context}: unknown source id {source_id!r}")
            _validate_reference(
                reference, source_by_id[source_id], context, require_heading=True
            )

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
        validate_typed_domain_id(
            record["id"], expected_domain=record["kind"], context=f"{context}.id"
        )
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
        if record["kind"] == "skill":
            facts = record.get("facts")
            if not isinstance(facts, dict) or facts.get("typeId") not in skill_type_ids:
                raise ValueError(f"{context}: skill 'facts.typeId' must reference skillTypes")
            parameter_semantics = facts.get("parameterSemantics")
            if parameter_semantics is not None:
                if not isinstance(parameter_semantics, dict):
                    raise ValueError(
                        f"{context}: skill 'facts.parameterSemantics' must be an object"
                    )
                if set(parameter_semantics) != {"kind", "positiveSign"}:
                    raise ValueError(
                        f"{context}: skill 'facts.parameterSemantics' must contain only "
                        "'kind' and 'positiveSign'"
                    )
                if parameter_semantics["kind"] != "distance":
                    raise ValueError(
                        f"{context}: skill parameter semantics 'kind' must be 'distance'"
                    )
                if parameter_semantics["positiveSign"] not in {"preserve", "omit", "force"}:
                    raise ValueError(
                        f"{context}: skill parameter semantics 'positiveSign' must be one of "
                        "'preserve', 'omit', or 'force'"
                    )
        if record["kind"] == "trait":
            facts = record.get("facts")
            if facts is not None:
                source_identity = facts.get("sourceIdentity")
                if source_identity is not None:
                    if not isinstance(source_identity, dict):
                        raise ValueError(
                            f"{context}: trait 'facts.sourceIdentity' must be an object"
                        )
                    unknown = source_identity.keys() - {"prefixes"}
                    if unknown:
                        raise ValueError(
                            f"{context}: trait 'facts.sourceIdentity' has unsupported fields "
                            f"{sorted(unknown)}"
                        )
                    prefixes = source_identity.get("prefixes")
                    if not isinstance(prefixes, list) or not prefixes:
                        raise ValueError(
                            f"{context}: trait 'facts.sourceIdentity.prefixes' must be a "
                            "non-empty array"
                        )
                    for prefix_index, prefix in enumerate(prefixes):
                        _require_string(
                            prefix,
                            f"facts.sourceIdentity.prefixes[{prefix_index}]",
                            context,
                        )
        if record["kind"] == "weapon":
            facts = record.get("facts")
            if not isinstance(facts, dict):
                raise ValueError(f"{context}: weapon 'facts' must be an object")
            if "specialProfile" in facts:
                _validate_weapon_special_profile(
                    facts["specialProfile"], f"{context}.facts.specialProfile"
                )
        if record["kind"] == "skill-declaration-category":
            facts = record.get("facts")
            if not isinstance(facts, dict) or set(facts) != {"order"}:
                raise ValueError(
                    f"{context}: skill declaration category 'facts' must contain only 'order'"
                )
            if type(facts["order"]) is not int or facts["order"] < 0:
                raise ValueError(
                    f"{context}: skill declaration category 'facts.order' must be "
                    "a non-negative integer"
                )
            links = record.get("armyLinks")
            if not isinstance(links, list) or not links:
                raise ValueError(
                    f"{context}: skill declaration category requires non-empty 'armyLinks'"
                )
            for link in links:
                if (
                    not isinstance(link, dict)
                    or link.get("entity") != "skill"
                    or type(link.get("id")) is not int
                ):
                    raise ValueError(
                        f"{context}: skill declaration category armyLinks must reference "
                        "integer skill ids"
                    )
            if len(record["citations"]) != 1:
                raise ValueError(
                    f"{context}: skill declaration category requires exactly one citation"
                )
            citation_source = record["citations"][0].get("sourceId")
            citation_kind = next(
                (source["kind"] for source in sources if source["id"] == citation_source),
                None,
            )
            if citation_kind != "pdf":
                raise ValueError(
                    f"{context}: skill declaration category citation must reference a PDF"
                )
        if record["kind"] in {"skill", "state"}:
            record_labels = record.get("labelIds")
            if not isinstance(record_labels, list) or not record_labels:
                raise ValueError(f"{context}: '{record['kind']}' requires non-empty 'labelIds'")
            if any(label_id not in label_ids for label_id in record_labels):
                raise ValueError(f"{context}: 'labelIds' must reference labels")
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
            _validate_reference(citation, source_by_id[source_id], ref_context)

        for link_index, link in enumerate(record.get("armyLinks", [])):
            link_context = f"{context}.armyLinks[{link_index}]"
            if not isinstance(link, dict):
                raise ValueError(f"{link_context}: must be an object")
            _require_string(link.get("entity"), "entity", link_context)
            if "id" not in link and "name" not in link:
                raise ValueError(f"{link_context}: requires 'id' or 'name'")

    return document
