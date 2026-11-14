"""Compatibility facade for the offline Army snapshot verifier.

The shared verifier now lives in the installed application package so normal
builds do not depend on developer-only tools modules.
"""

from infinity_db.army_snapshot_source import (
    ApiDownloadError,
    ArmySnapshotResult,
    resolve_army_snapshot,
    snapshot_source_revision_counts,
)

__all__ = [
    "ApiDownloadError",
    "ArmySnapshotResult",
    "resolve_army_snapshot",
    "snapshot_source_revision_counts",
]
