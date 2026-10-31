"""Fail-closed source-evidence gates for historical Reinforcements annex rules."""

from __future__ import annotations

import copy
import json
from pathlib import Path

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


def test_pinned_current_references_do_not_authorize_n4_procedures_as_n5() -> None:
    report = audit_applicability()
    assert report["currentReferencesVerified"] == 2
    assert report["historicalN4PdfsVerified"] == 2
    assert report["historicalActionsReviewed"] == ["Commlink", "Request Reinforcements"]
    assert report["n5ExtraCurrentlyReferenced"] is True
    assert report["n5ProceduresAuthorized"] is False
    assert "N5-applicable annex" in report["nextGate"]


@pytest.mark.parametrize("defect", [
    "authorize-procedures", "authorize-commlink", "authorize-request",
    "wrong-its-page", "wrong-its-hash", "drop-current-source",
    "wrong-legacy-category", "drop-legacy-action", "source-quote",
    "duplicate-current-reference",
])
def test_source_review_rejects_unreviewed_authority_and_identity_drift(
    tmp_path: Path, defect: str,
) -> None:
    manifest = copy.deepcopy(json.loads(MANIFEST.read_text(encoding="utf-8")))
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
        audit_applicability(path, ROOT)


def test_unverified_annex_actions_do_not_leak_into_current_n5_rules() -> None:
    rules = RulesDatabase(ROOT / "data/generated/rules.db")
    army = Database(ROOT / "data/generated/infinity.db")
    for identity in ("skill:commlink", "skill:request-reinforcements"):
        assert rules.composed_record(identity) is None
    payload = core_declaration_matrix(army, rules)
    assert sum(len(section["items"]) for section in payload["sections"]) == 57
    assert not any(
        item["name"].casefold() in {"commlink", "request reinforcements"}
        for section in payload["sections"] for item in section["items"]
    )
