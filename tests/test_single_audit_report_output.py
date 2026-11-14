"""Single JSON audit receipts must not replace retained source or prior evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tools.data import (
    audit_army_faction_semantics,
    audit_database_separation,
    audit_enrichment_coverage,
    audit_fireteam_semantics,
    audit_loadout_semantics,
    audit_normalization_links,
    audit_peripheral_semantics,
    audit_profile_semantics,
    audit_relationship_semantics,
    audit_runtime_database_surface,
    audit_semantic_deduplication,
    audit_source_presentation,
    audit_unit_semantics,
)
from tools.research import audit_trait_wiki_anchors

MODULES = (
    audit_army_faction_semantics,
    audit_database_separation,
    audit_enrichment_coverage,
    audit_fireteam_semantics,
    audit_loadout_semantics,
    audit_normalization_links,
    audit_peripheral_semantics,
    audit_profile_semantics,
    audit_relationship_semantics,
    audit_runtime_database_surface,
    audit_semantic_deduplication,
    audit_source_presentation,
    audit_trait_wiki_anchors,
    audit_unit_semantics,
)
UTF8_ESCAPED = (
    audit_runtime_database_surface,
    audit_source_presentation,
    audit_trait_wiki_anchors,
)
JSON_STDOUT = (
    audit_army_faction_semantics,
    audit_enrichment_coverage,
    audit_peripheral_semantics,
    audit_relationship_semantics,
    audit_runtime_database_surface,
)
FAILABLE_SUMMARIES = (audit_loadout_semantics, audit_profile_semantics)


def _report(module: Any) -> dict[str, Any]:
    report: dict[str, Any] = {"label": "café", "formatVersion": 1}
    if module is audit_database_separation:
        report["summary"] = {
            k: 0 for k in (
                "canonicalApplicationTableCount", "contextualApplicationTableCount",
                "sourceProvenanceOnlyTableCount", "foreignKeyBlockerCount",
                "validationSourceOnlyDependencyCount",
            )
        }
        report["rawArchive"] = {"status": "not-present"}
    elif module is audit_fireteam_semantics:
        report.update({
            "chartShape": {"sourceArmyCount": 0, "teamCount": 0, "memberCount": 0},
            "memberResolution": {"resolutionCounts": {}, "nonArmyResolutionCount": 0},
            "ftoEligibility": {"statusCounts": {}, "memberRowCount": 0, "unresolvedCount": 0},
            "reinforcementContext": {
                "parentEdgeCount": 0, "blockedByParentTypeLimitCount": 0,
            },
        })
    elif module in FAILABLE_SUMMARIES:
        prefix = "loadout" if module is audit_loadout_semantics else "profile"
        variation = (
            ("Points", "Swc") if module is audit_loadout_semantics else ("Ava", "Logo")
        )
        summary: dict[str, Any] = {
            prefix + "OccurrenceCount": 0,
            prefix + "PayloadCount": 0,
            "reusedPayloadCount": 0,
            "source" + prefix.title() + "KeysWithMultiplePayloads": 0,
            "status": "pass",
        }
        for key in variation:
            summary["source" + prefix.title() + "KeysWith" + key + "Variation"] = 0
        report["summary"] = summary
    elif module is audit_normalization_links:
        report.update({
            "sourceFilterCatalogLinks": {"tableCount": 0, "rowCount": 0},
            "optionWeaponTemplateIndirection": {
                "occurrenceRowCount": 0, "templateRowCount": 0,
                "danglingOccurrenceCount": 0,
            },
            "canonicalizationLinks": {"linkCount": 0},
        })
    elif module is audit_runtime_database_surface:
        report["summary"] = {
            "surfaceCount": 0, "runtimeTableCount": 0,
            "runtimeFieldCount": 0, "tableWithOpenIssueCount": 0,
        }
    elif module is audit_semantic_deduplication:
        group: dict[str, Any] = {
            "storedOccurrences": 0,
            "sourceUnit": {"distinctPayloads": 0, "repeatPercent": 0.0},
            "logicalUnit": {"distinctPayloads": 0, "repeatPercent": 0.0},
        }
        report.update({"profiles": group, "loadouts": group})
    elif module is audit_source_presentation:
        report["summary"] = {
            "sourceTableCount": 0, "sourceFieldCount": 0,
            "confirmedGapCount": 0, "deferredOutOfScopeCount": 0,
            "occupiedUnrepresentedFieldCount": 0,
            "fieldStatusCounts": {module.UNREPRESENTED: 0},
        }
    elif module is audit_trait_wiki_anchors:
        report.update({
            "matchedCount": 1, "mappingCount": 1, "headingCount": 1,
            "failures": [], "unmappedReview": [],
        })
    elif module is audit_unit_semantics:
        report["summary"] = {
            "sourceUnitCount": 0, "logicalUnitCount": 0, "repeatedLogicalUnitCount": 0,
        }
        report["representativeRule"] = {
            k: 0 for k in (
                "representativeReinforcementOrNonStandardCount",
                "nonRepresentativeReinforcementCount",
                "nonRepresentativeMercenaryVariantCount",
                "repeatedLogicalUnitsWithAlternateGeneralLabels",
                "logicalUnitsWithNonRepresentativeNoteDeltas",
            )
        }
        report["relationships"] = {
            "unit_options": {
                "rowCount": 0, "logicalUnitCount": 0,
                "variantRepeatedLogicalUnitCollectionCount": 0,
            },
        }
        report["candidateModel"] = {
            "canonicalLogicalUnit": {"rowCount": 0},
            "aliases": {"occurrenceCount": 0},
            "notes": {"occurrenceCount": 0},
            "spectables": {"occurrenceCount": 0},
        }
    return report


def _source(tmp_path: Path, module: Any) -> tuple[Path, bytes]:
    path = tmp_path / (
        "saved-official-traits.html" if module is audit_trait_wiki_anchors else "source.db"
    )
    original = (
        b"\xef\xbb\xbf<html>Saved snapshot</html>\n"
        if module is audit_trait_wiki_anchors else b"original source bytes\n"
    )
    path.write_bytes(original)
    return path, original


def _invoke(
    module: Any, source: Path, *,
    output: Path | None = None, more: list[str] | None = None,
) -> int:
    args = [str(source)]
    if module is audit_enrichment_coverage:
        args.extend(["--rules", str(source)])
    if output is not None:
        args.extend(["--output", str(output)])
    args.extend(more or [])
    return module.main(args)


def _stub(
    module: Any,
    monkeypatch: pytest.MonkeyPatch,
    report: dict[str, Any],
    before: Callable[[], object] | None = None,
) -> None:
    def fake_audit(*args: Any, **kwargs: Any) -> dict[str, Any]:
        if before is not None:
            before()
        return report

    if module is audit_trait_wiki_anchors:
        monkeypatch.setattr(module, "audit_html", fake_audit)
        monkeypatch.setattr(module, "load_trait_wiki_references", lambda: {})
    else:
        name = "audit_coverage" if module is audit_enrichment_coverage else "audit_database"
        monkeypatch.setattr(module, name, fake_audit)


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_existing_output_refused_before_source_work(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source, original = _source(tmp_path, module)
    output = tmp_path / "accepted.json"
    previous = b"accepted prior JSON report\n"
    output.write_bytes(previous)

    def forbidden() -> None:
        pytest.fail("Existing output must prevent source audit and read")

    _stub(module, monkeypatch, _report(module), forbidden)
    with pytest.raises(SystemExit) as exc:
        _invoke(module, source, output=output)
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == previous
    assert source.read_bytes() == original


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_existing_source_file_cannot_be_selected_as_output(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, original = _source(tmp_path, module)
    _stub(module, monkeypatch, _report(module), lambda: pytest.fail("Should not audit"))
    with pytest.raises(SystemExit) as exc:
        _invoke(module, source, output=source)
    assert exc.value.code == 1
    assert source.read_bytes() == original


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_fresh_output_uses_existing_serialization_and_summary(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source, original = _source(tmp_path, module)
    output = tmp_path / "new-run" / "audit.json"
    report = _report(module)
    _stub(module, monkeypatch, report)
    assert _invoke(module, source, output=output) == 0
    if module is audit_trait_wiki_anchors:
        report["sourceSha256"] = hashlib.sha256(original).hexdigest()
    expected = (
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=module in UTF8_ESCAPED)
        + "\n"
    ).encode("utf-8")
    assert output.read_bytes() == expected
    assert source.read_bytes() == original
    captured = capsys.readouterr().out
    if module is audit_army_faction_semantics:
        assert captured == ""
    else:
        assert captured.strip()


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_late_collision_never_truncates_prior_evidence(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source, original = _source(tmp_path, module)
    output = tmp_path / "late-claim.json"
    previous = b"another audit completed during source reading\n"
    _stub(module, monkeypatch, _report(module), lambda: output.write_bytes(previous))
    with pytest.raises(SystemExit) as exc:
        _invoke(module, source, output=output)
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == previous
    assert source.read_bytes() == original


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.__name__.split(".")[-1])
def test_stdout_only_remains_read_only(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source, original = _source(tmp_path, module)
    report = _report(module)
    _stub(module, monkeypatch, report)
    assert _invoke(module, source) == 0
    output = capsys.readouterr().out
    assert output
    if module in JSON_STDOUT:
        if module is audit_runtime_database_surface:
            output = output[:output.index("\nRuntime surface:")] + "\n"
        assert json.loads(output) == report
    assert list(tmp_path.iterdir()) == [source]
    assert source.read_bytes() == original


@pytest.mark.parametrize("module", FAILABLE_SUMMARIES, ids=lambda m: m.__name__.split(".")[-1])
def test_failed_semantic_status_still_writes_fresh_report(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, original = _source(tmp_path, module)
    report = _report(module)
    report["summary"]["status"] = "fail"
    _stub(module, monkeypatch, report)
    path = tmp_path / "failure.json"
    assert _invoke(module, source, output=path) == 1
    assert json.loads(path.read_text(encoding="utf-8")) == report
    assert source.read_bytes() == original


def test_failed_source_presentation_gate_retains_fresh_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, original = _source(tmp_path, audit_source_presentation)
    report = _report(audit_source_presentation)
    report["summary"]["occupiedUnrepresentedFieldCount"] = 1
    _stub(audit_source_presentation, monkeypatch, report)
    path = tmp_path / "source-gaps.json"
    assert _invoke(
        audit_source_presentation, source, output=path,
        more=["--require-no-occupied-gaps"],
    ) == 1
    assert json.loads(path.read_text(encoding="utf-8")) == report
    assert source.read_bytes() == original


def test_trait_wiki_unmatched_anchors_return_failure_with_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, original = _source(tmp_path, audit_trait_wiki_anchors)
    report = _report(audit_trait_wiki_anchors)
    report["failures"] = [{
        "traitId": "boost", "status": "missing",
        "fragment": "#Boost", "actualHeading": None,
    }]
    _stub(audit_trait_wiki_anchors, monkeypatch, report)
    path = tmp_path / "review.json"
    assert _invoke(audit_trait_wiki_anchors, source, output=path) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["failures"] == report["failures"]
    assert source.read_bytes() == original
