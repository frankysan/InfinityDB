"""Bind a runtime Army database to the Army snapshot used for symbol publication."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .database import Database
from .database.schema import METADATA_TABLE, quote

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class DeploymentProvenanceError(ValueError):
    """Raised when runtime data and a promoted symbol publication are unrelated."""


def _database_snapshot_sha256(database_path: Path) -> str:
    Database(database_path).validate()
    try:
        connection = sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            row = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?", ("_meta",)
            ).fetchone()
        finally:
            connection.close()
        meta = json.loads(row[0]) if row is not None else None
    except (OSError, sqlite3.Error, json.JSONDecodeError, TypeError) as exc:
        raise DeploymentProvenanceError(
            f"Could not read runtime database snapshot provenance from {database_path}: {exc}"
        ) from exc
    value = meta.get("snapshotArchiveSha256") if isinstance(meta, dict) else None
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise DeploymentProvenanceError(
            "Runtime infinity.db has no validated snapshotArchiveSha256. Rebuild it from the "
            "same Army ZIP snapshot used for the promoted symbol publication."
        )
    return value


def validate_database_symbol_provenance(
    database_path: Path, symbol_manifest: dict[str, Any]
) -> str:
    """Fail closed unless database and terminal symbols name the same Army ZIP SHA-256."""

    snapshot = symbol_manifest.get("snapshot")
    artifact = snapshot.get("armyArtifact") if isinstance(snapshot, dict) else None
    expected = artifact.get("sha256") if isinstance(artifact, dict) else None
    if not isinstance(expected, str) or _SHA256_RE.fullmatch(expected) is None:
        raise DeploymentProvenanceError(
            "Promoted symbol manifest has no valid snapshot.armyArtifact.sha256"
        )
    actual = _database_snapshot_sha256(database_path)
    if actual != expected:
        raise DeploymentProvenanceError(
            "Runtime infinity.db snapshotArchiveSha256 does not match promoted symbol "
            "manifest snapshot.armyArtifact.sha256. Rebuild the database from the exact "
            "Army ZIP used for symbol publication, or promote symbols for this database snapshot."
        )
    return actual
