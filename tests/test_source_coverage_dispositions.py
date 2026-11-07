from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tools.source_coverage_dispositions import (
    DEFAULT_MANIFEST,
    DispositionError,
    current_evidence_inputs,
    validate_dispositions,
)

RECORD_SHA = "a" * 64
SOURCE_SHA = "b" * 64
ARMY_SHA = "c" * 64
RULES_SHA = "d" * 64
GIT_SHA = "e" * 40


def _review() -> dict[str, Any]:
    return {
        "id": "test-clause",
        "origin": "record",
        "clauseKey": "target-condition",
        "source": {
            "sourceId": "n5-core-v5.3-pdf",
            "page": 59,
            "heading": "Program",
            "sha256": SOURCE_SHA,
        },
        "recordIds": ["hacking-program:test"],
        "recordSha256": {},
        "scope": "Selected target condition, not a whole-record review",
        "semantic": {"status": "pending"},
        "browser": {"status": "pending"},
        "dependsOn": [],
    }


def _manifest(*rows: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "InfinityDB source-coverage dispositions",
        "formatVersion": 1,
        "owner": "V1S-082",
        "reviews": list(rows),
    }


def _validate(data: dict[str, Any], tmp_path: Path) -> dict[str, Any]:
    return validate_dispositions(
        data,
        record_hashes={"hacking-program:test": RECORD_SHA},
        source_pins={"n5-core-v5.3-pdf": SOURCE_SHA},
        citations={"hacking-program:test": {("n5-core-v5.3-pdf", 59, None)}},
        root=tmp_path,
    )


def _approve(review: dict[str, Any]) -> dict[str, Any]:
    review["recordSha256"] = {"hacking-program:test": RECORD_SHA}
    review["semantic"] = {
        "status": "accepted",
        "reviewer": "source-reviewer",
        "reviewedOn": "2026-11-06",
        "evidenceRef": "docs/v1.0-source-coverage-audit.md#scoped-example",
    }
    return review


def test_tracked_disposition_manifest_pins_scoped_source_reviews_only() -> None:
    data = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    record_hashes, source_pins, citations = current_evidence_inputs()
    result = validate_dispositions(
        data, record_hashes=record_hashes,
        source_pins=source_pins, citations=citations,
    )
    reviewed = {
        (row["recordIds"][0], row["source"]["sourceId"])
        for row in data["reviews"]
    }
    assert {
        ("trait:deployable", "n5-core-v5.3-pdf"),
        ("trait:deployable", "n5-core-v5.3-es-pdf"),
        ("trait:target-attribute", "n5-core-v5.3-pdf"),
        ("trait:target-attribute", "n5-core-v5.3-es-pdf"),
    } <= reviewed
    assert result["counts"]["semanticAccepted"] >= 4
    assert result["counts"]["browserAccepted"] == 0
    assert all(
        row["browser"]["status"] == "pending"
        for row in data["reviews"]
        if row["id"] in {
            "deployable-en-n53", "deployable-es-n53",
            "target-attribute-en-n53", "target-attribute-es-n53",
        }
    )
    assert result["wholeRecordApprovalsIssued"] == 0
    assert result["sourceWideCompletenessApproved"] is False


def test_candidate_review_does_not_implicitly_approve_anything(tmp_path: Path) -> None:
    result = _validate(_manifest(_review()), tmp_path)
    assert result["counts"]["pending"] == 1
    assert result["counts"]["semanticAccepted"] == 0
    assert result["counts"]["browserAccepted"] == 0


def test_scoped_source_and_record_pin_can_be_accepted_independently_of_browser(
    tmp_path: Path,
) -> None:
    result = _validate(_manifest(_approve(_review())), tmp_path)
    assert result["counts"]["semanticAccepted"] == 1
    assert result["counts"]["browserAccepted"] == 0
    assert result["wholeRecordApprovalsIssued"] == 0


@pytest.mark.parametrize(
    "modify,error",
    [
        (lambda r: r["recordSha256"].update({"hacking-program:test": "f" * 64}),
         "stale record fingerprint"),
        (lambda r: r["source"].update({"sha256": "f" * 64}),
         "stale source fingerprint"),
        (lambda r: r["source"].update({"sha256": None}),
         "accepted claim requires declared source SHA"),
        (lambda r: r["recordSha256"].clear(), "unpinned record owners"),
        (lambda r: r["source"].update({"page": 60}), "lacks cited source locator"),
        (lambda r: r["semantic"].update({"reviewedOn": "yesterday"}), "ISO date"),
        (lambda r: r["semantic"].update({"reviewer": ""}), "nonempty text"),
    ],
)
def test_approval_rejects_stale_incomplete_or_unreviewed_inputs(
    tmp_path: Path, modify: Any, error: str,
) -> None:
    review = _approve(_review())
    modify(review)
    with pytest.raises(DispositionError, match=error):
        _validate(_manifest(review), tmp_path)


def test_source_first_exclusion_requires_scoped_signed_off_rationale(
    tmp_path: Path,
) -> None:
    row = _review()
    row["origin"] = "source-first"
    row["recordIds"] = []
    row["semantic"] = {
        "status": "excluded-with-rationale",
        "reviewer": "source-reviewer",
        "reviewedOn": "2026-11-06",
        "evidenceRef": "docs/v1.0-source-coverage-audit.md#scoped-example",
        "reason": "Outside the v1.0 reference definition",
    }
    result = _validate(_manifest(row), tmp_path)
    assert result["counts"]["excluded"] == 1
    assert result["counts"]["sourceFirst"] == 1
    row["semantic"].pop("reason")
    with pytest.raises(DispositionError, match="semantic.reason"):
        _validate(_manifest(row), tmp_path)


@pytest.mark.parametrize("bad", ["duplicate", "dangling", "cyclic"])
def test_review_identity_dependencies_fail_closed(tmp_path: Path, bad: str) -> None:
    row = _review()
    other = copy.deepcopy(row)
    other["id"] = "another-claim"
    other["clauseKey"] = "different-condition"
    if bad == "duplicate":
        other["id"] = row["id"]
    if bad == "dangling":
        row["dependsOn"] = ["missing-review"]
    if bad == "cyclic":
        row["dependsOn"] = [other["id"]]
        other["dependsOn"] = [row["id"]]
    with pytest.raises(DispositionError):
        _validate(_manifest(row, other), tmp_path)


def test_duplicate_source_clause_key_is_rejected(tmp_path: Path) -> None:
    a = _review()
    b = copy.deepcopy(a)
    b["id"] = "second-review"
    with pytest.raises(DispositionError, match="duplicate source-clause"):
        _validate(_manifest(a, b), tmp_path)


def test_browser_acceptance_requires_exact_revision_artifacts_and_contract(
    tmp_path: Path,
) -> None:
    review = _approve(_review())
    (tmp_path / "src").mkdir()
    file_path = tmp_path / "src" / "app.py"
    file_path.write_text("status = 'ok'\n", encoding="utf-8")
    file_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
    review["browser"] = {
        "status": "accepted",
        "reviewer": "browser-reviewer",
        "reviewedOn": "2026-11-06",
        "evidenceRef": "docs/v1.0-source-coverage-audit.md#browser-case",
        "appGitSha": GIT_SHA,
        "armyDbSha256": ARMY_SHA,
        "rulesDbSha256": RULES_SHA,
        "testSelectors": ["tests/test_browser.py::test_reference"],
        "contractFiles": {"src/app.py": file_sha},
    }
    result = _validate(_manifest(review), tmp_path)
    assert result["counts"]["browserAccepted"] == 1
    file_path.write_text("status = 'changed'\n", encoding="utf-8")
    with pytest.raises(DispositionError, match="stale browser contract"):
        _validate(_manifest(review), tmp_path)


def test_browser_acceptance_cannot_outpace_semantic_acceptance(tmp_path: Path) -> None:
    review = _review()
    review["browser"] = {"status": "accepted", "reviewer": "someone"}
    with pytest.raises(DispositionError):
        _validate(_manifest(review), tmp_path)


@pytest.mark.parametrize("path", ["../escape.py", "/tmp/escape.py", "src/../other.py",
                                  "docs/notes.md", "src\\app.py"])
def test_browser_contract_paths_are_restricted(tmp_path: Path, path: str) -> None:
    review = _approve(_review())
    review["browser"] = {
        "status": "accepted",
        "reviewer": "browser-reviewer",
        "reviewedOn": "2026-11-06",
        "evidenceRef": "docs/v1.0-source-coverage-audit.md#browser-case",
        "appGitSha": GIT_SHA,
        "armyDbSha256": ARMY_SHA,
        "rulesDbSha256": RULES_SHA,
        "testSelectors": ["tests/test_browser.py::test_reference"],
        "contractFiles": {path: "a" * 64},
    }
    with pytest.raises(DispositionError, match="unsafe browser contract path"):
        _validate(_manifest(review), tmp_path)


def test_unrecognized_review_fields_and_dispositions_are_rejected(
    tmp_path: Path,
) -> None:
    review = _review()
    review["sourceStatus"] = "approved"
    with pytest.raises(DispositionError, match="unexpected fields"):
        _validate(_manifest(review), tmp_path)
    review.pop("sourceStatus")
    review["semantic"]["status"] = "approved"
    with pytest.raises(DispositionError, match="unsupported disposition"):
        _validate(_manifest(review), tmp_path)
