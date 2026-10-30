"""Audit Reinforcements source applicability without publishing N4 rules as N5.

N5.3 p. 6 names a game mode and ITS18 p. 27 refers to an unversioned
Reinforcements Annex. Neither supplies the N5 procedural text or explicitly
adopts the historic N4 annex unchanged. This gate reports evidence and blocks
unsupported publication, rather than guessing declaration categories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.audit_1_0_reference_inputs import (
    SourceEvidenceError,
    verify_reinforcements_inputs,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/validation/reinforcements-n5-applicability-review.json"
EXPECTED_REFERENCES = {
    "n5-core-v5.3-pdf": (
        "N5", "5.3", "data/pdf/rules/n5-rules-v5-3-en.pdf",
        6, "game-mode-name-not-procedure", "n5-core-v5.3.json",
    ),
    "its-season-18-en-pdf": (
        "N5-ITS", "2026.09.01",
        "data/pdf/its/Its-rules-season-18-en.pdf", 27,
        "current-extra-refers-to-unversioned-annex",
        "n5-its-season-18-2026.09.01.json",
    ),
}
EXPECTED_LEGACY = {
    "Commlink": ("reinforcements-n4-en", 3, "automatic-skill"),
    "Request Reinforcements": (
        "reinforcements-n4-en", 3, "tactical-phase-step",
    ),
}
EXPECTED_GATE = {
    "n5ExtraCurrentlyReferenced": True,
    "specificN5AnnexTextVerified": False,
    "explicitUnchangedN4AdoptionVerified": False,
    "currentN5ProceduresAuthorized": False,
    "commlinkN5DefinitionAuthorized": False,
    "requestReinforcementsN5PhaseActionAuthorized": False,
}
EXPECTED_SOURCE_TEXT = {
    "n5-core-v5.3-pdf": frozenset({
        "GAME MODES", "GAMES WITH", "REINFORCEMENTS",
    }),
    "its-season-18-en-pdf": frozenset({
        "REINFORCEMENTS",
        "With this Extra, the Reinforcement Rules are used",
        "see the", "Reinforcements Annex",
    }),
}
EXPECTED_LEGACY_TEXT = {
    "Commlink": frozenset({"COMMLINK", "AUTOMATIC SKILL", "Obligatory"}),
    "Request Reinforcements": frozenset({
        "REQUEST REINFORCEMENTS", "ACTIVATION", "Tactical",
    }),
}
EXPECTED_SCOPE = "reinforcements-current-reference-evidence-not-n5-procedural-authority"


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SourceEvidenceError(f"Expected JSON object: {path.name}")
    return data


def _read_source_text(root: Path, relative: str, digest: str, page: int) -> str:
    from fitz import open as open_pdf

    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise SourceEvidenceError(f"Source unavailable or escapes root: {relative}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise SourceEvidenceError(f"Source hash mismatch: {relative}")
    with open_pdf(path) as pdf:
        if not 1 <= page <= len(pdf):
            raise SourceEvidenceError(f"Invalid PDF page {page}: {relative}")
        page_text = pdf[page - 1].get_text("text")
        if not isinstance(page_text, str):
            raise SourceEvidenceError(f"Non-text PDF page {page}: {relative}")
        return " ".join(page_text.casefold().split())


def _contains(text: str, required: object, *, context: str) -> None:
    if (
        not isinstance(required, list)
        or not required
        or any(not isinstance(item, str) or not item.strip() for item in required)
        or len(set(required)) != len(required)
    ):
        raise SourceEvidenceError(f"Invalid required source excerpts: {context}")
    for item in required:
        if not isinstance(item, str):
            raise SourceEvidenceError(f"Invalid source excerpt type: {context}")
        # PDF layout can separate words across line or column breaks; require
        # each distinctive phrase verbatim after whitespace normalization.
        phrase = " ".join(item.casefold().split())
        if phrase not in text:
            raise SourceEvidenceError(f"Source excerpt absent: {context}: {item!r}")


def audit_applicability(
    manifest_path: Path = MANIFEST,
    source_root: Path = ROOT,
) -> dict[str, Any]:
    """Verify official references and historical provenance; grant no N5 authority."""
    manifest = _load(manifest_path)
    if set(manifest) != {
        "formatVersion", "scope", "historicalInventory", "currentReferences",
        "reviewDecision", "legacyActionEvidence",
    } or manifest["formatVersion"] != 1 or type(manifest["formatVersion"]) is not int:
        raise SourceEvidenceError("Invalid Reinforcements applicability contract")
    if manifest["scope"] != EXPECTED_SCOPE or (
        manifest["historicalInventory"]
        != "config/validation/reinforcements-source-inputs.json"
    ):
        raise SourceEvidenceError("Reinforcements source scopes were changed")
    decision = manifest["reviewDecision"]
    if not isinstance(decision, dict) or (
        any(type(decision.get(key)) is not bool or decision[key] is not value
            for key, value in EXPECTED_GATE.items())
        or set(decision) != {*EXPECTED_GATE, "reason"}
        or not isinstance(decision["reason"], str)
        or len(decision["reason"].strip()) < 40
    ):
        raise SourceEvidenceError("N5 Reinforcements publication cannot be authorized")
    legacy = verify_reinforcements_inputs(
        source_root / manifest["historicalInventory"], source_root,
    )
    if legacy["verifiedCount"] != 2 or legacy["n5AuthorityVerified"] is not False:
        raise SourceEvidenceError("Pinned N4 Reinforcements sources not fully verified")
    english = next(source for source in legacy["items"] if source["language"] == "en")

    current = manifest["currentReferences"]
    if not isinstance(current, list) or len(current) != len(EXPECTED_REFERENCES):
        raise SourceEvidenceError("Missing official current-mode reference")
    found: set[str] = set()
    for row in current:
        if not isinstance(row, dict) or set(row) != {
            "sourceId", "edition", "version", "localPath", "sha256",
            "page", "evidenceKind", "requiredText",
        }:
            raise SourceEvidenceError("Invalid current-mode reference row")
        source_id = row["sourceId"]
        if source_id in found or source_id not in EXPECTED_REFERENCES:
            raise SourceEvidenceError("Duplicate or unreviewed current source identity")
        edition, version, relative, page, kind, curated_name = EXPECTED_REFERENCES[source_id]
        if any(row[field] != expected for field, expected in (
            ("edition", edition), ("version", version),
            ("localPath", relative), ("page", page), ("evidenceKind", kind),
        )):
            raise SourceEvidenceError(f"Current source identity drift: {source_id}")
        document = _load(source_root / "data/curated/rules" / curated_name)
        catalog = [s for s in document["sources"] if s["id"] == source_id]
        if len(catalog) != 1 or catalog[0].get("sha256") != row["sha256"]:
            raise SourceEvidenceError(
                f"Current source pin differs from curated catalog: {source_id}"
            )
        if not isinstance(row["requiredText"], list) or any(
            not isinstance(item, str) for item in row["requiredText"]
        ) or set(row["requiredText"]) != EXPECTED_SOURCE_TEXT[source_id]:
            raise SourceEvidenceError(f"Current source review excerpt drift: {source_id}")
        text = _read_source_text(source_root, relative, row["sha256"], page)
        _contains(text, row["requiredText"], context=source_id)
        found.add(source_id)
    if found != set(EXPECTED_REFERENCES):
        raise SourceEvidenceError("Incomplete current references")

    actions = manifest["legacyActionEvidence"]
    if not isinstance(actions, list) or len(actions) != len(EXPECTED_LEGACY):
        raise SourceEvidenceError("Historical N4 action review incomplete")
    seen_actions: set[str] = set()
    historic_text = _read_source_text(
        source_root, english["localPath"], english["sha256"], 3,
    )
    for row in actions:
        if not isinstance(row, dict) or set(row) != {
            "name", "sourceId", "pdfPage", "classification", "requiredText",
        }:
            raise SourceEvidenceError("Invalid historical N4 action")
        name = row["name"]
        if name in seen_actions or name not in EXPECTED_LEGACY:
            raise SourceEvidenceError("Duplicate or unsupported historical action")
        source_id, page, classification = EXPECTED_LEGACY[name]
        if (
            row["sourceId"], row["pdfPage"], row["classification"]
        ) != (source_id, page, classification):
            raise SourceEvidenceError("Historical action classification drift")
        if not isinstance(row["requiredText"], list) or any(
            not isinstance(item, str) for item in row["requiredText"]
        ) or set(row["requiredText"]) != EXPECTED_LEGACY_TEXT[name]:
            raise SourceEvidenceError(f"Historical N4 source review excerpt drift: {name}")
        _contains(historic_text, row["requiredText"], context=name)
        seen_actions.add(name)

    return {
        "scope": EXPECTED_SCOPE,
        "n5ExtraCurrentlyReferenced": True,
        "n5ProceduresAuthorized": False,
        "currentReferencesVerified": len(found),
        "historicalN4PdfsVerified": legacy["verifiedCount"],
        "historicalActionsReviewed": sorted(seen_actions),
        "nextGate": "Verified N5-applicable annex text or explicit unchanged N4 adoption",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_applicability(args.manifest)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"Current references: {report['currentReferencesVerified']}; "
            f"historic annex PDFs: {report['historicalN4PdfsVerified']}; "
            "N5 procedure publication: BLOCKED"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
