from datetime import UTC, datetime
from pathlib import Path

import pytest

from infinity_db.symbol_manifest import (
    SymbolManifestError,
    build_symbol_manifest,
    validate_symbol_manifest,
)


def artifact(path: Path, body: bytes) -> Path:
    path.write_bytes(body)
    return path


def test_symbol_manifest_separates_assets_from_many_references(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    url = "https://assets.corvusbelli.net/army/img/logo/units/shared.svg"
    assets = [
        {
            "url": url,
            "sourceFilename": "shared.svg",
            "archivePath": "units/shared.svg",
            "sha256": "1" * 64,
            "sourceMethod": "network",
        }
    ]
    references = [
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "101-a.json",
            "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
            "assetUrl": url,
            "unitId": 1,
        },
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "102-b.json",
            "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
            "assetUrl": url,
            "unitId": 1,
        },
    ]
    audit = {
        "unitProfileReferenceCount": 2,
        "uniqueUnitUrlCount": 1,
        "factionReferenceCount": 0,
        "uniqueFactionUrlCount": 0,
        "semanticReferenceCount": 2,
        "uniqueSemanticUrlCount": 1,
        "resumeReferenceCount": 0,
        "uniqueResumeUrlCount": 0,
        "staticReferenceCount": 0,
        "recursiveReferenceCount": 2,
        "uniqueRecursiveUrlCount": 1,
        "uniqueDownloadedUrlCount": 1,
        "unknownReferenceCount": 0,
    }

    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 17, 20, 0, tzinfo=UTC),
        source_document_count=2,
        assets=assets,
        references=references,
        audit=audit,
        project_root=tmp_path,
    )

    assert len(document["assets"]) == 1
    assert len(document["references"]) == 2
    assert document["snapshot"]["armyArtifact"]["path"] == "army.zip"
    assert document["snapshot"]["symbolArtifact"]["path"] == "symbols.zip"


def test_resume_audit_reference_may_point_to_non_downloaded_url(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 17, 20, 0, tzinfo=UTC),
        source_document_count=1,
        assets=[],
        references=[
            {
                "kind": "resume-audit",
                "authoritative": False,
                "sourceDocument": "101-a.json",
                "jsonPath": "$.resume[0].logo",
                "assetUrl": "https://assets.corvusbelli.net/army/img/logo/units/audit-only.svg",
            }
        ],
        audit={
            "unitProfileReferenceCount": 0,
            "uniqueUnitUrlCount": 0,
            "factionReferenceCount": 0,
            "uniqueFactionUrlCount": 0,
            "semanticReferenceCount": 0,
            "uniqueSemanticUrlCount": 0,
            "resumeReferenceCount": 1,
            "uniqueResumeUrlCount": 1,
            "staticReferenceCount": 0,
            "recursiveReferenceCount": 1,
            "uniqueRecursiveUrlCount": 1,
            "uniqueDownloadedUrlCount": 0,
            "unknownReferenceCount": 0,
        },
        project_root=tmp_path,
    )

    validate_symbol_manifest(document)


def test_authoritative_reference_must_point_to_downloaded_asset(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    with pytest.raises(SymbolManifestError, match="does not identify a downloaded asset"):
        build_symbol_manifest(
            army_artifact=army,
            symbol_artifact=symbols,
            acquired_at=datetime(2026, 9, 17, 20, 0, tzinfo=UTC),
            source_document_count=1,
            assets=[],
            references=[
                {
                    "kind": "faction",
                    "authoritative": True,
                    "sourceDocument": "metadata.json",
                    "jsonPath": "$.factions[0].logo",
                    "assetUrl": "https://assets.corvusbelli.net/army/img/logo/factions/test.svg",
                }
            ],
            audit={
                "unitProfileReferenceCount": 0,
                "uniqueUnitUrlCount": 0,
                "factionReferenceCount": 1,
                "uniqueFactionUrlCount": 1,
                "semanticReferenceCount": 1,
                "uniqueSemanticUrlCount": 1,
                "resumeReferenceCount": 0,
                "uniqueResumeUrlCount": 0,
                "staticReferenceCount": 0,
                "recursiveReferenceCount": 1,
                "uniqueRecursiveUrlCount": 1,
                "uniqueDownloadedUrlCount": 0,
                "unknownReferenceCount": 0,
            },
            project_root=tmp_path,
        )
