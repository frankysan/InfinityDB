"""Fail-closed source-evidence gates for historical Reinforcements annex rules."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from infinity_db.database.repository import Database
from infinity_db.declaration_matrix import core_declaration_matrix
from infinity_db.rules_database import RulesDatabase
from tools.audit_1_0_reference_inputs import SourceEvidenceError
from tools.audit_reinforcements_applicability import (
    MANIFEST,
    ROOT,
    audit_applicability,
)


def test_pinned_current_references_do_not_authorize_n4_procedures_as_n5(
    require_source_files,
) -> None:
    require_source_files(*(
        ROOT / path for path in (
            "data/pdf/rules/reinforcement-rules-en.pdf",
            "data/pdf/rules/reinforcement-rules-es.pdf",
            "data/pdf/rules/n5-rules-v5.3-en.pdf",
            "data/pdf/its/its-18-rules-v2026.09.01-en.pdf",
        )
    ))
    report = audit_applicability()
    assert report["currentReferencesVerified"] == 2
    assert report["historicalN4PdfsVerified"] == 2
    assert report["historicalActionsReviewed"] == ["Commlink", "Request Reinforcements"]
    assert report["n5ExtraCurrentlyReferenced"] is True
    assert report["n5ProceduresAuthorized"] is False
    assert "N5-applicable annex" in report["nextGate"]


@pytest.fixture
def synthetic_sources(tmp_path: Path) -> tuple[Path, Path]:
    """Exercise the evidence gate in CI with invented PDFs, never official bytes."""
    root = tmp_path / "sources"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    inventory = json.loads((ROOT / manifest["historicalInventory"]).read_text(encoding="utf-8"))

    def pdf(relative: str, page: int, text: str) -> str:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with pymupdf.open() as document:
            for _ in range(page):
                document.new_page()
            document[-1].insert_text((36, 36), "Synthetic test fixture only\n" + text)
            document.save(path)
        return hashlib.sha256(path.read_bytes()).hexdigest()

    for source in inventory["sources"]:
        source["sha256"] = pdf(source["localPath"], 3, (
            "COMMLINK\nAUTOMATIC SKILL\nObligatory\n"
            "REQUEST REINFORCEMENTS\nACTIVATION\nTactical"
        ))
    inventory_path = root / manifest["historicalInventory"]
    inventory_path.parent.mkdir(parents=True)
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    for row, catalog_name in zip(manifest["currentReferences"], (
        "n5-core-v5.3.json", "n5-its-season-18-2026.09.01.json",
    ), strict=True):
        row["sha256"] = pdf(row["localPath"], row["page"], "\n".join(row["requiredText"]))
        catalog = root / "data/curated/rules" / catalog_name
        catalog.parent.mkdir(parents=True, exist_ok=True)
        catalog.write_text(json.dumps({"sources": [{
            "id": row["sourceId"], "sha256": row["sha256"],
        }]}), encoding="utf-8")
    path = root / "review.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return root, path


def test_synthetic_source_gate_never_authorizes_n5_procedures(
    synthetic_sources: tuple[Path, Path],
) -> None:
    root, manifest = synthetic_sources
    report = audit_applicability(manifest, root)
    assert report["currentReferencesVerified"] == 2
    assert report["historicalN4PdfsVerified"] == 2
    assert report["n5ProceduresAuthorized"] is False


@pytest.mark.parametrize("defect", [
    "authorize-procedures", "authorize-commlink", "authorize-request",
    "wrong-its-page", "wrong-its-hash", "drop-current-source",
    "wrong-legacy-category", "drop-legacy-action", "source-quote",
    "duplicate-current-reference",
])
def test_source_review_rejects_unreviewed_authority_and_identity_drift(
    tmp_path: Path, defect: str, synthetic_sources: tuple[Path, Path],
) -> None:
    root, manifest_path = synthetic_sources
    manifest = copy.deepcopy(json.loads(manifest_path.read_text(encoding="utf-8")))
    if defect == "authorize-procedures":
        manifest["reviewDecision"]["currentN5ProceduresAuthorized"] = True
    elif defect == "authorize-commlink":
        manifest["reviewDecision"]["commlinkN5DefinitionAuthorized"] = True
    elif defect == "authorize-request":
        manifest["reviewDecision"]["requestReinforcementsN5PhaseActionAuthorized"] = True
    elif defect == "wrong-its-page":
        manifest["currentReferences"][1]["page"] = 26
    elif defect == "wrong-its-hash":
        manifest["currentReferences"][1]["sha256"] = "0" * 64
    elif defect == "drop-current-source":
        manifest["currentReferences"].pop()
    elif defect == "wrong-legacy-category":
        manifest["legacyActionEvidence"][1]["classification"] = "short-skill"
    elif defect == "drop-legacy-action":
        manifest["legacyActionEvidence"].pop()
    elif defect == "source-quote":
        manifest["currentReferences"][0]["requiredText"] = [
            "This is an invented N5 Reinforcements procedure"
        ]
    else:
        manifest["currentReferences"][1] = copy.deepcopy(
            manifest["currentReferences"][0]
        )
    path = tmp_path / "review.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(SourceEvidenceError):
        audit_applicability(path, root)


@pytest.mark.parametrize("defect", ["missing", "changed-bytes", "missing-clause"])
def test_source_gate_fails_closed_on_missing_or_changed_evidence(
    synthetic_sources: tuple[Path, Path], defect: str,
) -> None:
    root, manifest_path = synthetic_sources
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = root / manifest["currentReferences"][0]["localPath"]
    if defect == "missing":
        source.unlink()
    elif defect == "changed-bytes":
        source.write_bytes(b"unreviewed replacement")
    else:
        with pymupdf.open(source) as document:
            document[5].insert_text((36, 200), "Replacement without the required clauses")
            document[5].add_redact_annot(pymupdf.Rect(0, 0, 595, 150))
            document[5].apply_redactions()
            changed = document.tobytes()
        source.write_bytes(changed)
        pin = hashlib.sha256(changed).hexdigest()
        manifest["currentReferences"][0]["sha256"] = pin
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        catalog = root / "data/curated/rules/n5-core-v5.3.json"
        catalog.write_text(json.dumps({"sources": [{
            "id": "n5-core-v5.3-pdf", "sha256": pin,
        }]}), encoding="utf-8")
    with pytest.raises(SourceEvidenceError, match={
        "missing": "Source unavailable", "changed-bytes": "hash mismatch",
        "missing-clause": "Source excerpt absent",
    }[defect]):
        audit_applicability(manifest_path, root)


def test_optional_n4_annex_remains_separate_from_current_core_declarations() -> None:
    rules = RulesDatabase(ROOT / "data/generated/rules.db")
    army = Database(ROOT / "data/generated/infinity.db")
    for identity in ("skill:commlink", "skill:request-reinforcements"):
        record = rules.composed_record(identity)
        assert record is not None
        assert record["collection"]["id"] == "reinforcements-extra-n4-reference"
        assert "N4" in record["summary"]
    payload = core_declaration_matrix(army, rules)
    assert sum(len(section["items"]) for section in payload["sections"]) == 57
    assert not any(
        item["name"].casefold() in {"commlink", "request reinforcements"}
        for section in payload["sections"] for item in section["items"]
    )
