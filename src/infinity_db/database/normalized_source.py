"""Verify an Army export against its complete normalized source generation.

The base Army export fingerprint covers every normalized table and shared
metadata value, while later overlay publishers change only the compatibility
version and published-content hash. This permits source verification without
requiring a durable raw SQLite sibling.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .publication import (
    EXPORT_PAIR_SHA256_KEY,
    PUBLISHED_CONTENT_SHA256_KEY,
    export_pair_sha256,
    published_content_sha256,
    validate_database_pair,
)
from .schema import (
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    METADATA_TABLE,
    quote,
)


@dataclass(frozen=True, slots=True)
class VerifiedNormalizedSource:
    """Build-local receipt for an already validated normalized export.

    Every reuse still verifies the exact source bytes, base database content
    and shared metadata. No mutable document or global cache is retained.
    """

    path: Path
    source_sha256: str
    metadata_sha256: str
    generation: str

    def verify(self, application_path: Path) -> str:
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != self.source_sha256:
            raise ValueError("Verified normalized source bytes changed during build")
        _, base_metadata, generation = _base_export_metadata(application_path)
        if (
            generation != self.generation
            or export_pair_sha256({}, base_metadata) != self.metadata_sha256
        ):
            raise ValueError("Verified normalized source export generation changed during build")
        return generation


def _base_export_metadata(
    application_path: Path,
) -> tuple[list[tuple[str, str]], dict[str, Any], str]:
    with closing(sqlite3.connect(
        application_path.resolve().as_uri() + "?mode=ro", uri=True,
    )) as app:
        rows = [
            (str(key), str(value))
            for key, value in app.execute(
                f"SELECT key, value FROM {quote(METADATA_TABLE)} ORDER BY key"
            )
        ]
        try:
            metadata = {key: json.loads(value) for key, value in rows}
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid published Army export metadata") from exc
        generation = metadata.get(EXPORT_PAIR_SHA256_KEY)
        if (
            not isinstance(generation, str)
            or len(generation) != 64
            or any(char not in "0123456789abcdef" for char in generation)
        ):
            raise ValueError("Normalized source requires a pinned Army export")
        base_metadata = {
            **metadata,
            DATABASE_COMPATIBILITY_KEY: DATABASE_COMPATIBILITY_VERSION,
            PUBLISHED_CONTENT_SHA256_KEY: published_content_sha256(app),
        }
    return rows, base_metadata, generation


def _verify_document(
    application_path: Path, source_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, tuple[str, ...]], list[tuple[str, str]], str, dict[str, Any]]:
    document = json.loads(source_bytes.decode("utf-8"))
    # Keep build-time normalization imports out of runtime database/web startup.
    from .importer import validate_input

    table_columns = validate_input(document)
    rows, base_metadata, generation = _base_export_metadata(application_path)
    if export_pair_sha256(document, base_metadata) != generation:
        raise ValueError(
            "Normalized source does not match the published Army export generation"
        )
    return document, table_columns, rows, generation, base_metadata


def verified_normalized_document(
    application_path: Path, normalized_path: Path,
) -> tuple[dict[str, Any], dict[str, tuple[str, ...]], list[tuple[str, str]], str]:
    """Return the validated source, its columns, metadata and pinned generation."""
    document, columns, rows, generation, _ = _verify_document(
        application_path, normalized_path.read_bytes(),
    )
    return document, columns, rows, generation


def attest_normalized_source(
    application_path: Path, normalized_path: Path,
) -> VerifiedNormalizedSource:
    """Validate once for sequential generation-only consumers in a staged build."""
    source_bytes = normalized_path.read_bytes()
    _, _, _, generation, base_metadata = _verify_document(application_path, source_bytes)
    return VerifiedNormalizedSource(
        normalized_path.resolve(),
        hashlib.sha256(source_bytes).hexdigest(),
        export_pair_sha256({}, base_metadata),
        generation,
    )


def verified_normalized_generation(
    application_path: Path, normalized_path: Path | VerifiedNormalizedSource,
) -> str:
    """Verify normalized source provenance without materializing SQLite rows."""
    if isinstance(normalized_path, VerifiedNormalizedSource):
        return normalized_path.verify(application_path)
    return verified_normalized_document(application_path, normalized_path)[3]


def verified_army_export_generation(
    application_path: Path, raw_path: Path | None,
    normalized_path: Path | VerifiedNormalizedSource | None,
) -> str:
    """Accept exactly one explicit and verified Army source representation."""
    if (raw_path is None) == (normalized_path is None):
        raise ValueError("Select exactly one raw or normalized Army export source")
    if normalized_path is not None:
        return verified_normalized_generation(application_path, normalized_path)
    assert raw_path is not None
    generation = validate_database_pair(application_path, raw_path=raw_path)
    if generation is None:
        raise ValueError("Army overlay requires a pinned export generation")
    return generation
