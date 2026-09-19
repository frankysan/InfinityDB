import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import infinity_db.symbol_manifest as symbol_manifest
from infinity_db.symbol_manifest import (
    SymbolManifestError,
    add_compression,
    add_duplicate_detection,
    add_font_audit,
    add_publication,
    add_svg_preflight,
    add_text_conversion,
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


def assert_svg_preflight_rejects_later_state(
    document: dict[str, object],
    *,
    report: Path,
    project_root: Path,
) -> None:
    with pytest.raises(
        SymbolManifestError,
        match="SVG preflight requires version-2 acquisition state or failed version-3",
    ):
        add_svg_preflight(
            document,
            status="passed",
            summary={
                "svgCount": 0,
                "parseErrorCount": 0,
                "activeTextAssetCount": 0,
                "noActiveTextAssetCount": 0,
                "fontDeclaredAssetCount": 0,
                "uniqueDeclaredFontCount": 0,
            },
            report=report,
            project_root=project_root,
        )


def assert_text_conversion_rejects_later_state(
    document: dict[str, object],
    *,
    report: Path,
    summary_report: Path,
    project_root: Path,
) -> None:
    with pytest.raises(
        SymbolManifestError,
        match="Text conversion requires version-5 duplicate-detected state",
    ):
        add_text_conversion(
            document,
            status="passed",
            summary={
                "canonicalAssetCount": 0,
                "conversionCandidateCount": 0,
                "convertedAssetCount": 0,
                "carriedForwardAssetCount": 0,
                "failedAssetCount": 0,
            },
            report=report,
            summary_report=summary_report,
            converter="inkscape-shell",
            converter_version="test",
            jobs=4,
            project_root=project_root,
        )


def assert_compression_rejects_later_state(
    document: dict[str, object],
    *,
    report: Path,
    candidates_report: Path,
    run_report: Path,
    project_root: Path,
) -> None:
    with pytest.raises(
        SymbolManifestError,
        match="Compression requires version-6 text-converted state",
    ):
        add_compression(
            document,
            status="passed",
            summary={
                "assetCount": 0,
                "compressedAssetCount": 0,
                "retainedAssetCount": 0,
                "sourceBytes": 0,
                "outputBytes": 0,
                "reclaimedBytes": 0,
            },
            report=report,
            candidates_report=candidates_report,
            run_report=run_report,
            profile="balanced",
            renderer="resvg",
            target_sizes=[32, 64],
            dprs=[1.0, 2.0],
            balanced_precisions=[2, 3],
            max_rms=0.01,
            max_changed_fraction=0.01,
            pixel_diff_threshold=8,
            jobs=4,
            project_root=project_root,
        )


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



def test_authoritative_reference_may_target_recorded_http_404(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    url = "https://assets.corvusbelli.net/army/img/logo/units/missing.svg"
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 18, 20, 0, tzinfo=UTC),
        **army_source_kwargs(1),
        assets=[],
        unavailable_assets=[
            {
                "url": url,
                "sourceFilename": "missing.svg",
                "archivePath": "units/missing.svg",
                "sourceMethod": "network",
                "httpStatus": 404,
            }
        ],
        references=[
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-a.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
                "assetUrl": url,
                "unitId": 1,
            }
        ],
        audit={
            "unitProfileReferenceCount": 1,
            "uniqueUnitUrlCount": 1,
            "factionReferenceCount": 0,
            "uniqueFactionUrlCount": 0,
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

    validate_symbol_manifest(document)
    assert document["unavailableAssets"][0]["httpStatus"] == 404


def test_unavailable_asset_must_be_http_404_network_source(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    url = "https://assets.corvusbelli.net/army/img/logo/units/missing.svg"
    document = build_symbol_manifest(
        army_artifact=army,
        symbol_artifact=symbols,
        acquired_at=datetime(2026, 9, 18, 20, 0, tzinfo=UTC),
        **army_source_kwargs(1),
        assets=[],
        unavailable_assets=[
            {
                "url": url,
                "sourceFilename": "missing.svg",
                "archivePath": "units/missing.svg",
                "sourceMethod": "network",
                "httpStatus": 404,
            }
        ],
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
    document["unavailableAssets"][0]["httpStatus"] = 500

    with pytest.raises(SymbolManifestError, match="httpStatus must be 404"):
        validate_symbol_manifest(document)

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
        assets=[
            {
                "url": "https://assets.corvusbelli.net/army/img/logo/units/example.svg",
                "sourceFilename": "example.svg",
                "archivePath": "units/example.svg",
                "sha256": "1" * 64,
                "sourceMethod": "network",
            }
        ],
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
            "uniqueDownloadedUrlCount": 1,
            "unknownReferenceCount": 0,
        },
        project_root=tmp_path,
    )
    summary = {
        "svgCount": 1,
        "parseErrorCount": 0,
        "activeTextAssetCount": 0,
        "noActiveTextAssetCount": 1,
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

    with pytest.raises(
        SymbolManifestError,
        match="SVG preflight rerun requires a failed version-3 SVG preflight state",
    ):
        add_svg_preflight(
            promoted,
            status="passed",
            summary=summary,
            report=report,
            project_root=tmp_path,
        )

    failed = add_svg_preflight(
        document,
        status="failed",
        summary={
            **summary,
            "parseErrorCount": 1,
            "noActiveTextAssetCount": 0,
        },
        report=report,
        project_root=tmp_path,
    )
    retried = add_svg_preflight(
        failed,
        status="passed",
        summary=summary,
        report=report,
        project_root=tmp_path,
    )

    assert retried["formatVersion"] == 3
    assert retried["processing"]["svgPreflight"]["status"] == "passed"


def test_font_audit_promotes_preflight_manifest_to_version_4(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    preflight_report = artifact(tmp_path / "svg-preflight.json", b"{}")
    font_report = artifact(tmp_path / "font-audit.json", b"{}")
    aliases = artifact(tmp_path / "font-aliases.json", b"{}")
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
    preflight = add_svg_preflight(
        document,
        status="passed",
        summary={
            "svgCount": 0,
            "parseErrorCount": 0,
            "activeTextAssetCount": 0,
            "noActiveTextAssetCount": 0,
            "fontDeclaredAssetCount": 0,
            "uniqueDeclaredFontCount": 0,
        },
        report=preflight_report,
        project_root=tmp_path,
    )
    summary = {
        "svgCount": 0,
        "fontAvailableAssetCount": 0,
        "fontMissingAssetCount": 0,
        "noActiveTextAssetCount": 0,
        "implicitDefaultAssetCount": 0,
        "effectiveFontReferenceCount": 0,
        "availableFontReferenceCount": 0,
        "missingFontReferenceCount": 0,
        "ambiguousFontReferenceCount": 0,
        "genericFontReferenceCount": 0,
        "normalizedAliasReferenceCount": 0,
        "unusedDeclarationCount": 0,
    }

    promoted = add_font_audit(
        preflight,
        status="passed",
        summary=summary,
        report=font_report,
        aliases=aliases,
        project_root=tmp_path,
    )

    assert promoted["formatVersion"] == 4
    font_audit = promoted["processing"]["fontAudit"]
    assert font_audit["aliases"]["path"] == "font-aliases.json"
    assert font_audit["report"]["path"] == "font-audit.json"
    validate_symbol_manifest(promoted)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        (
            {"uniqueByteSetCount": 1, "rendersAvoidedExactCount": 2},
            "rendersAvoidedExactCount cannot exceed redundantAssetCount",
        ),
        (
            {"exactGroupCount": 2},
            "duplicate group count cannot exceed redundantAssetCount",
        ),
        (
            {"renderErrorCount": 4},
            "renderErrorCount cannot exceed sourceAssetCount",
        ),
    ],
)
def test_duplicate_detection_rejects_impossible_summary_counts(
    updates: dict[str, int],
    message: str,
) -> None:
    summary = {
        "sourceAssetCount": 3,
        "uniqueByteSetCount": 2,
        "rendersAvoidedExactCount": 1,
        "exactGroupCount": 1,
        "visualGroupCount": 0,
        "redundantAssetCount": 1,
        "canonicalAssetCount": 2,
        "renderErrorCount": 0,
        **updates,
    }
    report = {"name": "report.csv", "sha256": "0" * 64}
    record = {
        "status": "passed",
        "summary": summary,
        "renderer": {"name": "resvg", "renderSize": 512, "jobs": 4},
        "canonicalByArchivePath": {
            "units/a.svg": "units/a.svg",
            "units/b.svg": "units/a.svg",
            "units/c.svg": "units/c.svg",
        },
        "groupsReport": report,
        "errorsReport": report,
        "summaryReport": report,
    }

    with pytest.raises(SymbolManifestError, match=message):
        symbol_manifest._duplicate_detection(
            record,
            {"units/a.svg", "units/b.svg", "units/c.svg"},
            "duplicateDetection",
        )


def test_publication_promotes_compressed_manifest_to_version_8(tmp_path: Path) -> None:
    army = artifact(tmp_path / "army.zip", b"army")
    symbols = artifact(tmp_path / "symbols.zip", b"symbols")
    preflight_report = artifact(tmp_path / "svg-preflight.json", b"{}")
    font_report = artifact(tmp_path / "font-audit.json", b"{}")
    aliases = artifact(tmp_path / "font-aliases.json", b"{}")
    duplicate_groups = artifact(tmp_path / "duplicate-groups.csv", b"x")
    duplicate_errors = artifact(tmp_path / "duplicate-errors.csv", b"x")
    duplicate_summary = artifact(tmp_path / "duplicate-summary.csv", b"x")
    conversion_report = artifact(tmp_path / "conversion.csv", b"x")
    conversion_summary = artifact(tmp_path / "conversion-summary.csv", b"x")
    compression_report = artifact(tmp_path / "compression.csv", b"x")
    compression_candidates = artifact(tmp_path / "compression-candidates.csv", b"x")
    compression_run = artifact(tmp_path / "compression-run.json", b"{}")
    publication_report = artifact(tmp_path / "publication-map.json", b"{}")
    inventory = artifact(tmp_path / "symbol-inventory.json", b"{}")
    army_map = artifact(tmp_path / "army-symbols.js", b"map")
    unit_map = artifact(tmp_path / "unit-symbol-map.js", b"map")

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
    document = add_svg_preflight(
        document,
        status="passed",
        summary={
            "svgCount": 0,
            "parseErrorCount": 0,
            "activeTextAssetCount": 0,
            "noActiveTextAssetCount": 0,
            "fontDeclaredAssetCount": 0,
            "uniqueDeclaredFontCount": 0,
        },
        report=preflight_report,
        project_root=tmp_path,
    )
    document = add_font_audit(
        document,
        status="passed",
        summary={
            "svgCount": 0,
            "fontAvailableAssetCount": 0,
            "fontMissingAssetCount": 0,
            "noActiveTextAssetCount": 0,
            "implicitDefaultAssetCount": 0,
            "effectiveFontReferenceCount": 0,
            "availableFontReferenceCount": 0,
            "missingFontReferenceCount": 0,
            "ambiguousFontReferenceCount": 0,
            "genericFontReferenceCount": 0,
            "normalizedAliasReferenceCount": 0,
            "unusedDeclarationCount": 0,
        },
        report=font_report,
        aliases=aliases,
        project_root=tmp_path,
    )
    assert_svg_preflight_rejects_later_state(
        document, report=preflight_report, project_root=tmp_path
    )
    document = add_duplicate_detection(
        document,
        summary={
            "sourceAssetCount": 0,
            "canonicalAssetCount": 0,
            "redundantAssetCount": 0,
            "sourceAssetBytes": 0,
            "canonicalAssetBytes": 0,
            "reclaimedAssetBytes": 0,
            "uniqueByteSetCount": 0,
            "rendersAvoidedExactCount": 0,
            "exactGroupCount": 0,
            "visualGroupCount": 0,
            "renderErrorCount": 0,
        },
        canonical_by_archive_path={},
        groups_report=duplicate_groups,
        errors_report=duplicate_errors,
        summary_report=duplicate_summary,
        renderer="resvg",
        renderer_version="test",
        render_size=512,
        jobs=4,
        project_root=tmp_path,
    )
    assert_svg_preflight_rejects_later_state(
        document, report=preflight_report, project_root=tmp_path
    )
    document = add_text_conversion(
        document,
        status="passed",
        summary={
            "canonicalAssetCount": 0,
            "conversionCandidateCount": 0,
            "convertedAssetCount": 0,
            "carriedForwardAssetCount": 0,
            "failedAssetCount": 0,
        },
        report=conversion_report,
        summary_report=conversion_summary,
        converter="inkscape-shell",
        converter_version="test",
        jobs=4,
        project_root=tmp_path,
    )
    assert_text_conversion_rejects_later_state(
        document,
        report=conversion_report,
        summary_report=conversion_summary,
        project_root=tmp_path,
    )
    assert_svg_preflight_rejects_later_state(
        document, report=preflight_report, project_root=tmp_path
    )
    document = add_compression(
        document,
        status="passed",
        summary={
            "assetCount": 0,
            "compressedAssetCount": 0,
            "retainedAssetCount": 0,
            "sourceBytes": 0,
            "outputBytes": 0,
            "reclaimedBytes": 0,
        },
        report=compression_report,
        candidates_report=compression_candidates,
        run_report=compression_run,
        profile="balanced",
        renderer="resvg",
        target_sizes=[32, 64],
        dprs=[1.0, 2.0],
        balanced_precisions=[2, 3],
        max_rms=0.01,
        max_changed_fraction=0.01,
        pixel_diff_threshold=8,
        jobs=4,
        project_root=tmp_path,
    )
    assert document["formatVersion"] == 7
    assert_compression_rejects_later_state(
        document,
        report=compression_report,
        candidates_report=compression_candidates,
        run_report=compression_run,
        project_root=tmp_path,
    )
    assert_text_conversion_rejects_later_state(
        document,
        report=conversion_report,
        summary_report=conversion_summary,
        project_root=tmp_path,
    )
    assert_svg_preflight_rejects_later_state(
        document, report=preflight_report, project_root=tmp_path
    )

    published = add_publication(
        document,
        summary={
            "sourceAssetCount": 0,
            "canonicalAssetCount": 0,
            "publishedAssetCount": 0,
            "factionMappingCount": 0,
            "unitMappingCount": 0,
            "staticMappingCount": 0,
            "publishedBytes": 0,
        },
        mapping_report=publication_report,
        inventory=inventory,
        army_map=army_map,
        unit_map=unit_map,
        project_root=tmp_path,
    )

    assert published["formatVersion"] == 8
    assert published["processing"]["publication"]["status"] == "passed"
    assert published["processing"]["publication"]["inventory"]["path"] == "symbol-inventory.json"
    with pytest.raises(SymbolManifestError, match="version-7 compressed state"):
        add_publication(
            published,
            summary=published["processing"]["publication"]["summary"],
            mapping_report=publication_report,
            inventory=inventory,
            army_map=army_map,
            unit_map=unit_map,
            project_root=tmp_path,
        )
    published["processing"]["publication"]["summary"]["publishedBytes"] = 1
    with pytest.raises(
        SymbolManifestError, match="publishedBytes must equal compression outputBytes"
    ):
        validate_symbol_manifest(published)
    published["processing"]["publication"]["summary"]["publishedBytes"] = 0
    legacy_published = json.loads(json.dumps(published))
    legacy_published["processing"]["publication"].pop("inventory")
    validate_symbol_manifest(legacy_published)
    assert_compression_rejects_later_state(
        published,
        report=compression_report,
        candidates_report=compression_candidates,
        run_report=compression_run,
        project_root=tmp_path,
    )
    assert_text_conversion_rejects_later_state(
        published,
        report=conversion_report,
        summary_report=conversion_summary,
        project_root=tmp_path,
    )
    assert_svg_preflight_rejects_later_state(
        published, report=preflight_report, project_root=tmp_path
    )
    validate_symbol_manifest(published)
