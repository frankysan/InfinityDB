from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.migrate_symbol_publication_provenance as migration
from tools.migrate_symbol_publication_provenance import (
    PublicationMigrationError,
    migrate_publication_provenance,
)


def _publication(path: Path) -> Path:
    document = {
        "format": "InfinityDB symbol publication mapping",
        "formatVersion": 2,
        "summary": {"publishedBytes": 0},
        "publishedSha256ByPath": {"orders/regular.svg": "a" * 64},
        "factionIdToPublishedPath": {},
        "unitSlugToPublishedPath": {},
        "unitProfileLogoToPublishedPath": {},
        "staticKeyToPublishedPath": {"regular": "orders/regular.svg"},
        "browserUsageSummary": {
            "browserReferencedAssetCount": 1,
            "unreferencedPublishedAssetCount": 0,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _build_manifest(publication: Path) -> dict:
    return {
        "formatVersion": 8,
        "snapshot": {
            "armyArtifact": {
                "name": "JSON 20260918-204434.zip",
                "sha256": "b" * 64,
            }
        },
        "processing": {
            "publication": {
                "status": "passed",
                "summary": {"publishedAssetCount": 1, "publishedBytes": 0},
                "publicationManifest": {
                    "name": publication.name,
                    "path": "data/manifests/symbol-publication.json",
                    "sha256": hashlib.sha256(publication.read_bytes()).hexdigest(),
                },
            }
        },
    }


def test_migration_promotes_snapshot_identity_and_refreshes_local_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication = _publication(tmp_path / "data" / "manifests" / "symbol-publication.json")
    build = _build_manifest(publication)
    monkeypatch.setattr(migration, "load_symbol_manifest", lambda _path: build)
    monkeypatch.setattr(migration, "validate_symbol_manifest", lambda _document: None)
    written: dict[str, object] = {}

    def capture(document: dict, path: Path) -> Path:
        written["document"] = document
        written["path"] = path
        return path

    monkeypatch.setattr(migration, "write_symbol_manifest", capture)

    assert migrate_publication_provenance(
        tmp_path / "data" / "manifests" / "army-symbol-build.json",
        publication,
        project_root=tmp_path,
    )
    document = json.loads(publication.read_text(encoding="utf-8"))
    assert document["sourceSnapshot"] == {
        "armyArtifact": {
            "name": "JSON 20260918-204434.zip",
            "sha256": "b" * 64,
        }
    }
    rebound = written["document"]
    assert isinstance(rebound, dict)
    assert rebound["processing"]["publication"]["publicationManifest"]["sha256"] == hashlib.sha256(
        publication.read_bytes()
    ).hexdigest()


def test_migration_is_idempotent_for_matching_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication = _publication(tmp_path / "data" / "manifests" / "symbol-publication.json")
    build = _build_manifest(publication)
    document = json.loads(publication.read_text(encoding="utf-8"))
    document["sourceSnapshot"] = {
        "armyArtifact": {
            "name": "JSON 20260918-204434.zip",
            "sha256": "b" * 64,
        }
    }
    publication.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    build["processing"]["publication"].pop("publicationManifest")
    monkeypatch.setattr(migration, "load_symbol_manifest", lambda _path: build)

    assert not migrate_publication_provenance(
        tmp_path / "army-symbol-build.json", publication, project_root=tmp_path
    )


def test_migration_rejects_conflicting_source_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication = _publication(tmp_path / "data" / "manifests" / "symbol-publication.json")
    build = _build_manifest(publication)
    document = json.loads(publication.read_text(encoding="utf-8"))
    document["sourceSnapshot"] = {
        "armyArtifact": {"name": "other.zip", "sha256": "c" * 64}
    }
    publication.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    build["processing"]["publication"].pop("publicationManifest")
    monkeypatch.setattr(migration, "load_symbol_manifest", lambda _path: build)

    with pytest.raises(PublicationMigrationError, match="different source snapshot"):
        migrate_publication_provenance(
            tmp_path / "army-symbol-build.json", publication, project_root=tmp_path
        )
