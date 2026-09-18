from datetime import UTC, datetime
from pathlib import Path

import pytest

from infinity_db.symbol_manifest import (
    SymbolManifestError,
    add_svg_preflight,
    build_symbol_manifest,
    validate_symbol_manifest,
)


def artifact(path: Path, body: bytes) -> Path:
    path.write_bytes(body)
    return path


def army_source_kwargs(source_document_count: int) -> dict[str, object]:
    revisions = {} if source_document_count == 1 else {"7.26246.158": source_document_count - 1}
    return {
        "army_acquired_at": datetime(2026, 9, 18, 8, 35, 9, tzinfo=UTC),
        "army_language": "en",
        "army_source_url": "https://api.corvusbelli.com/army",
        "source_document_count": source_document_count,
        "source_revisions": revisions,
    }


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
        **army_source_kwargs(2),
        assets=assets,
        references=references,
        audit=audit,
        project_root=tmp_path,
    )

    assert len(document["assets"]) == 1
    assert len(document["references"]) == 2
    assert document["snapshot"]["armyArtifact"]["path"] == "army.zip"
    assert document["snapshot"]["symbolArtifact"]["path"] == "symbols.zip"
    assert document["snapshot"]["armySource"] == {
        "acquiredAt": "2026-09-18T08:35:09+00:00",
        "language": "en",
        "url": "https://api.corvusbelli.com/army",
        "documentCount": 2,
        "sourceRevisions": {"7.26246.158": 1},
    }


def test_resume_audit_reference_may_point_to_non_downloaded_url(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 17, 20, 0, tzinfo=UTC),
        **army_source_kwargs(1),
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
            **army_source_kwargs(1),
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


def test_army_source_revisions_must_account_for_non_metadata_documents(
    tmp_path: Path,
) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    kwargs = army_source_kwargs(2)
    kwargs["source_revisions"] = {"7.26246.158": 2}

    with pytest.raises(SymbolManifestError, match="must account for every non-metadata"):
        build_symbol_manifest(
            army_artifact=army,
            symbol_artifact=symbols,
            acquired_at=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
            assets=[],
            references=[],
            audit={
                "unitProfileReferenceCount": 0,
                "uniqueUnitUrlCount": 0,
                "factionReferenceCount": 0,
                "uniqueFactionUrlCount": 0,
                "semanticReferenceCount": 0,
                "uniqueSemanticUrlCount": 0,
                "resumeReferenceCount": 0,
                "uniqueResumeUrlCount": 0,
                "staticReferenceCount": 0,
                "recursiveReferenceCount": 0,
                "uniqueRecursiveUrlCount": 0,
                "uniqueDownloadedUrlCount": 0,
                "unknownReferenceCount": 0,
            },
            project_root=tmp_path,
            **kwargs,
        )


def test_acquisition_manifest_remains_version_2_until_preflight(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
        **army_source_kwargs(1),
        assets=[],
        references=[],
        audit={
            "unitProfileReferenceCount": 0,
            "uniqueUnitUrlCount": 0,
            "factionReferenceCount": 0,
            "uniqueFactionUrlCount": 0,
            "semanticReferenceCount": 0,
            "uniqueSemanticUrlCount": 0,
            "resumeReferenceCount": 0,
            "uniqueResumeUrlCount": 0,
            "staticReferenceCount": 0,
            "recursiveReferenceCount": 0,
            "uniqueRecursiveUrlCount": 0,
            "uniqueDownloadedUrlCount": 0,
            "unknownReferenceCount": 0,
        },
        project_root=tmp_path,
    )

    assert document["formatVersion"] == 2
    validate_symbol_manifest(document)


def test_svg_preflight_promotes_manifest_to_version_3(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    report = artifact(tmp_path / "svg-preflight.json", b"{}")
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
        **army_source_kwargs(1),
        assets=[],
        references=[],
        audit={
            "unitProfileReferenceCount": 0,
            "uniqueUnitUrlCount": 0,
            "factionReferenceCount": 0,
            "uniqueFactionUrlCount": 0,
            "semanticReferenceCount": 0,
            "uniqueSemanticUrlCount": 0,
            "resumeReferenceCount": 0,
            "uniqueResumeUrlCount": 0,
            "staticReferenceCount": 0,
            "recursiveReferenceCount": 0,
            "uniqueRecursiveUrlCount": 0,
            "uniqueDownloadedUrlCount": 0,
            "unknownReferenceCount": 0,
        },
        project_root=tmp_path,
    )
    summary = {
        "svgCount": 0,
        "parseErrorCount": 0,
        "activeTextAssetCount": 0,
        "noActiveTextAssetCount": 0,
        "fontDeclaredAssetCount": 0,
        "uniqueDeclaredFontCount": 0,
    }

    promoted = add_svg_preflight(
        document,
        status="passed",
        summary=summary,
        report=report,
        project_root=tmp_path,
    )

    assert promoted["formatVersion"] == 3
    assert promoted["processing"]["svgPreflight"]["report"]["path"] == "svg-preflight.json"
    validate_symbol_manifest(promoted)
