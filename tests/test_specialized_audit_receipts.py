"""Specialized L2 outputs: immutable receipts vs intentional published files."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tools import audit_pdf_revision_deltas as pdf_delta
from tools import audit_restrictions_source_chart as restrictions
from tools import audit_rules_interactions as interactions
from tools.research.report_output import write_audit_bytes_or_exit

ROOT = Path(__file__).resolve().parents[1]


def test_pdf_revision_inventory_uses_categorized_research_input() -> None:
    assert pdf_delta.PIN_PATH == ROOT / "local/research/pdf/revision-inventory.json"


def _pdf_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, bytes, list[str]]:
    root = tmp_path
    monkeypatch.setattr(pdf_delta, "ROOT", root)
    before, after, skip = pdf_delta.PAIRS["faq-en"]
    pins = root / "pinned-pdfs.json"
    contents = json.dumps({
        "artifacts": [
            {"path": "data/pdf/" + before, "sha256": "old-sha"},
            {"path": "data/pdf/" + after, "sha256": "new-sha"},
        ],
    }).encode("utf-8")
    pins.write_bytes(contents)
    monkeypatch.setattr(pdf_delta, "PIN_PATH", pins)
    examined: list[str] = []

    def select_source(
        selected_root: Path, label: str, digest: str, *, layout: str,
    ) -> Path:
        assert selected_root == root
        assert label in {"data/pdf/" + before, "data/pdf/" + after}
        assert digest == ("old-sha" if label.endswith(before) else "new-sha")
        prefix = "data/pdf" if layout == "legacy" else "local/data/pdf"
        return root / prefix / label.removeprefix("data/pdf/")

    monkeypatch.setattr(pdf_delta, "pinned_pdf_path", select_source)

    def extracted(
        relative: str, skipped: int, *, source_path: Path | None = None,
    ) -> pdf_delta.Extracted:
        examined.append(relative)
        assert skipped == skip
        assert source_path is not None
        return pdf_delta.Extracted(
            path=relative,
            sha256="old-sha" if relative == before else "new-sha",
            pages=2, starts=[0], words=["café"],
        )

    monkeypatch.setattr(pdf_delta, "extract", extracted)
    return pins, contents, examined


def _pdf_result(
    pair: str, old: pdf_delta.Extracted, new: pdf_delta.Extracted, skip: int,
) -> dict[str, Any]:
    return {
        "pair": pair,
        "old": {"pdf_pages": old.pages, "audited_words": len(old.words)},
        "new": {"pdf_pages": new.pages, "audited_words": len(new.words)},
        "candidate_spans": 0, "added_phrases": [], "omitted_phrases": [],
        "largest_candidates": [], "review": "café",
    }


def _pdf_main(monkeypatch: pytest.MonkeyPatch, *arguments: str) -> int:
    monkeypatch.setattr(sys, "argv", ["audit_pdf_revision_deltas", *arguments])
    return pdf_delta.main()


def test_pdf_revision_report_preflight_blocks_existing_before_pin_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(pdf_delta, "ROOT", tmp_path)
    monkeypatch.setattr(pdf_delta, "PIN_PATH", tmp_path / "missing-pins.json")
    output = tmp_path / "local/audits/preserved.json"
    output.parent.mkdir(parents=True)
    previous = b"accepted prior PDF diff evidence\n"
    output.write_bytes(previous)
    with pytest.raises(SystemExit) as exc:
        _pdf_main(monkeypatch, "--pairs", "faq-en", "--output", "local/audits/preserved.json")
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == previous


def test_pdf_revision_default_is_new_run_scoped_and_descriptive() -> None:
    now = datetime(2026, 11, 14, 12, 13, 14, 123456, tzinfo=UTC)
    assert pdf_delta.default_output_path(["faq-en"], now=now) == Path(
        "local/audits/pdf-revision-deltas/"
        "20261114T121314123456Z-faq-en/report.json"
    )
    assert pdf_delta.default_output_path(["faq-en", "faq-es"], now=now) == Path(
        "local/audits/pdf-revision-deltas/"
        "20261114T121314123456Z-2-pairs/report.json"
    )


def test_pdf_revision_dynamic_default_refuses_collision_before_reading_pins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf_delta, "ROOT", tmp_path)
    monkeypatch.setattr(pdf_delta, "PIN_PATH", tmp_path / "missing-pins.json")
    relative = Path("local/audits/pdf-revision-deltas/pinned-run/report.json")
    monkeypatch.setattr(pdf_delta, "default_output_path", lambda pairs: relative)
    output = tmp_path / relative
    output.parent.mkdir(parents=True)
    output.write_bytes(b"accepted prior run")
    with pytest.raises(SystemExit) as exc:
        _pdf_main(monkeypatch, "--pairs", "faq-en")
    assert exc.value.code == 1
    assert output.read_bytes() == b"accepted prior run"


def test_pdf_revision_dynamic_default_creates_new_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pins, _original, examined = _pdf_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(pdf_delta, "summarize", _pdf_result)
    relative = Path("local/audits/pdf-revision-deltas/new-run/report.json")
    monkeypatch.setattr(pdf_delta, "default_output_path", lambda pairs: relative)
    assert _pdf_main(monkeypatch, "--pairs", "faq-en") == 0
    output = tmp_path / relative
    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8"))["pairs"][0]["pair"] == "faq-en"
    assert len(examined) == 2


def test_pdf_revision_rejects_misplaced_local_segment_before_pin_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf_delta, "ROOT", tmp_path)
    monkeypatch.setattr(pdf_delta, "PIN_PATH", tmp_path / "missing-pins.json")
    with pytest.raises(SystemExit) as exc:
        _pdf_main(
            monkeypatch, "--pairs", "faq-en",
            "--output", "other/local/misplaced.json",
        )
    assert exc.value.code == 2
    assert not (tmp_path / "other").exists()


def test_pdf_revision_report_fresh_preserves_serialization_and_pins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pins, original, examined = _pdf_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(pdf_delta, "summarize", _pdf_result)
    path = tmp_path / "local/audits/fresh/run.json"
    assert _pdf_main(
        monkeypatch, "--pairs", "faq-en", "--output", "local/audits/fresh/run.json",
    ) == 0
    document = {
        "method": (
            "version-locked PDF text extraction and nine-word sequence alignment; "
            "candidates are not rulings"
        ),
        "pairs": [_pdf_result("faq-en", pdf_delta.Extracted("", "", 2, [], ["café"]),
                              pdf_delta.Extracted("", "", 2, [], ["café"]), 1)],
    }
    assert path.read_bytes() == (
        json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    assert len(examined) == 2
    assert pins.read_bytes() == original
    assert "Report: local/audits/fresh/run.json" in (
        capsys.readouterr().out.replace("\\", "/")
    )


def test_pdf_revision_local_layout_uses_exact_pinned_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, examined = _pdf_setup(tmp_path, monkeypatch)
    monkeypatch.setattr(pdf_delta, "summarize", _pdf_result)
    selected: list[tuple[str, str, str]] = []

    def select_source(root: Path, label: str, digest: str, *, layout: str) -> Path:
        assert root == tmp_path
        selected.append((label, digest, layout))
        return root / "local/data/pdf" / label.removeprefix("data/pdf/")

    monkeypatch.setattr(pdf_delta, "pinned_pdf_path", select_source)
    assert _pdf_main(
        monkeypatch, "--pairs", "faq-en", "--source-layout", "local",
        "--output", "local/audits/local.json",
    ) == 0
    before, after, _ = pdf_delta.PAIRS["faq-en"]
    assert examined == [before, after]
    assert selected == [
        (f"data/pdf/{before}", "old-sha", "local"),
        (f"data/pdf/{after}", "new-sha", "local"),
    ]
    assert (tmp_path / "local/audits/local.json").is_file()


def test_pdf_revision_selected_hash_failure_does_not_create_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, examined = _pdf_setup(tmp_path, monkeypatch)

    def reject(*args: Any, **kwargs: Any) -> Path:
        raise pdf_delta.SourcePathError("Source hash mismatch")

    monkeypatch.setattr(pdf_delta, "pinned_pdf_path", reject)
    with pytest.raises(SystemExit, match="Source hash mismatch"):
        _pdf_main(
            monkeypatch, "--pairs", "faq-en", "--source-layout", "local",
            "--output", "local/audits/rejected.json",
        )
    assert not examined
    assert not (tmp_path / "local/audits/rejected.json").exists()


def test_pdf_revision_real_pdfs_are_layout_equivalent_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf_delta, "ROOT", tmp_path)
    before, after, _ = pdf_delta.PAIRS["faq-en"]
    pins = []
    for relative, phrase in ((before, "Original rules phrase"), (after, "Updated rules phrase")):
        with pdf_delta.fitz.open() as doc:
            doc.new_page()
            doc.new_page().insert_text((72, 72), phrase)
            payload = doc.tobytes()
        for root in ("data/pdf", "local/data/pdf"):
            destination = tmp_path / root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        pins.append({
            "path": "data/pdf/" + relative,
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    pin_path = tmp_path / "pins.json"
    pin_path.write_text(json.dumps({"artifacts": pins}), encoding="utf-8")
    monkeypatch.setattr(pdf_delta, "PIN_PATH", pin_path)
    assert _pdf_main(
        monkeypatch, "--pairs", "faq-en", "--source-layout", "legacy",
        "--output", "local/validation/legacy.json",
    ) == 0
    assert _pdf_main(
        monkeypatch, "--pairs", "faq-en", "--source-layout", "local",
        "--output", "local/validation/local.json",
    ) == 0
    assert (tmp_path / "local/validation/legacy.json").read_bytes() == (
        tmp_path / "local/validation/local.json"
    ).read_bytes()
    # A corrupt selected source must not fall back to the intact legacy sibling.
    (tmp_path / "local/data/pdf" / after).write_bytes(b"bad pdf")
    rejected = tmp_path / "local/validation/rejected.json"
    with pytest.raises(SystemExit, match="Source hash mismatch"):
        _pdf_main(
            monkeypatch, "--pairs", "faq-en", "--source-layout", "local",
            "--output", "local/validation/rejected.json",
        )
    assert not rejected.exists()
    assert _pdf_main(
        monkeypatch, "--pairs", "faq-en", "--source-layout", "legacy",
        "--output", "local/validation/legacy-again.json",
    ) == 0


def test_pdf_revision_late_collision_does_not_clobber_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pins, original, _ = _pdf_setup(tmp_path, monkeypatch)
    output = tmp_path / "local/audits/late.json"
    prior = b"another completed report\n"

    def competitor(*args: Any) -> dict[str, Any]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(prior)
        return _pdf_result(*args)

    monkeypatch.setattr(pdf_delta, "summarize", competitor)
    with pytest.raises(SystemExit) as exc:
        _pdf_main(monkeypatch, "--pairs", "faq-en", "--output", "local/audits/late.json")
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == prior
    assert pins.read_bytes() == original


def test_pdf_revision_still_rejects_destinations_outside_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(pdf_delta, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as exc:
        _pdf_main(monkeypatch, "--output", "reports/new.json")
    assert exc.value.code == 2
    assert "inside repository local/" in capsys.readouterr().err


def _restrictions_main(
    monkeypatch: pytest.MonkeyPatch, *args: str,
) -> int:
    monkeypatch.setattr(sys, "argv", ["audit_restrictions_source_chart", *args])
    return restrictions.main()


def test_restrictions_existing_output_is_rejected_before_reading_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(restrictions, "ROOT", tmp_path)
    output = tmp_path / "local/review.json"
    output.parent.mkdir()
    original = b"reviewed earlier candidate\n"
    output.write_bytes(original)
    with pytest.raises(SystemExit) as exc:
        _restrictions_main(
            monkeypatch, "--manifest", str(tmp_path / "missing-manifest"),
            "--curated", str(tmp_path / "missing-curated"),
            "--output", str(output),
        )
    assert exc.value.code == 2
    assert "must name a new file" in capsys.readouterr().err
    assert output.read_bytes() == original


def test_restrictions_fresh_publication_bytes_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(restrictions, "ROOT", tmp_path)
    path = tmp_path / "local/reviews/new/restrictions.json"
    source_manifest = restrictions.MANIFEST.read_bytes()
    source_curated = restrictions.CURATED.read_bytes()
    assert _restrictions_main(
        monkeypatch,
        "--manifest", str(restrictions.MANIFEST),
        "--curated", str(restrictions.CURATED),
        "--output", str(path),
    ) == 0
    assert path.read_bytes() == restrictions.PUBLICATION.read_bytes()
    assert restrictions.MANIFEST.read_bytes() == source_manifest
    assert restrictions.CURATED.read_bytes() == source_curated


def test_restrictions_late_collision_preserves_other_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(restrictions, "ROOT", tmp_path)
    path = tmp_path / "local/reviews/candidate.json"
    prior = b"concurrent publication candidate\n"
    real_project = restrictions.project_public_restrictions

    def competing_projection(*args: Any, **kwargs: Any) -> dict[str, Any]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(prior)
        return real_project(*args, **kwargs)

    monkeypatch.setattr(restrictions, "project_public_restrictions", competing_projection)
    with pytest.raises(SystemExit) as exc:
        _restrictions_main(
            monkeypatch, "--output", str(path),
            "--manifest", str(restrictions.MANIFEST),
            "--curated", str(restrictions.CURATED),
        )
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert path.read_bytes() == prior


def test_restrictions_dangling_symlink_does_not_target_another_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(restrictions, "ROOT", tmp_path)
    output = tmp_path / "local/dangling.json"
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == output)
    with pytest.raises(SystemExit) as exc:
        _restrictions_main(monkeypatch, "--output", str(output))
    assert exc.value.code == 2
    assert not output.exists()


def test_restrictions_check_publication_remains_exclusive_with_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(restrictions, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as exc:
        _restrictions_main(
            monkeypatch, "--check-publication",
            "--output", str(tmp_path / "local/candidate.json"),
        )
    assert exc.value.code == 2


def test_binary_helper_refuses_late_competitor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "candidate.bin"
    prior = b"previous bytes\n"
    original_open = Path.open

    def occupied_open(
        target: Path, mode: str = "r", buffering: int = -1,
        encoding: str | None = None, errors: str | None = None,
        newline: str | None = None,
    ):
        if target == path and mode == "xb":
            path.write_bytes(prior)
        return original_open(
            target, mode, buffering=buffering,
            encoding=encoding, errors=errors, newline=newline,
        )

    monkeypatch.setattr(Path, "open", occupied_open)
    with pytest.raises(SystemExit) as exc:
        write_audit_bytes_or_exit(argparse.ArgumentParser(), path, b"new bytes")
    assert exc.value.code == 1
    assert path.read_bytes() == prior


def test_rules_interaction_receipt_refuses_occupied_before_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "prior.md"
    prior = b"previous reviewed interaction checklist\n"
    output.write_bytes(prior)

    def forbidden(*args: Any) -> dict[str, Any]:
        pytest.fail("Audit must not run after receipt collision")

    monkeypatch.setattr(interactions, "audit_rules_interactions", forbidden)
    with pytest.raises(SystemExit) as exc:
        interactions.main(["--receipt-output", str(output)])
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == prior


def test_rules_interaction_receipt_new_preserves_check_and_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "run" / "interactions.md"
    original_policy = interactions.DEFAULT_POLICY_PATH.read_bytes()
    original_scope = interactions.DEFAULT_CATALOG_SCOPE_PATH.read_bytes()
    original_checklist = interactions.DEFAULT_CHECKLIST_PATH.read_bytes()

    assert interactions.main([
        "--receipt-output", str(output),
        "--check-output", str(interactions.DEFAULT_CHECKLIST_PATH),
        "--require-release", "1.0.0",
    ]) == 0
    assert output.read_bytes() == original_checklist
    assert interactions.DEFAULT_POLICY_PATH.read_bytes() == original_policy
    assert interactions.DEFAULT_CATALOG_SCOPE_PATH.read_bytes() == original_scope
    assert interactions.DEFAULT_CHECKLIST_PATH.read_bytes() == original_checklist
    assert "Rules interaction receipt written" in capsys.readouterr().out


def test_rules_interaction_failing_release_gate_still_writes_new_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    receipt = tmp_path / "failed-review" / "interaction-review.md"
    source = interactions.DEFAULT_CHECKLIST_PATH.read_bytes()
    assert interactions.main([
        "--receipt-output", str(receipt),
        "--require-primary-release", "1.0.0",
    ]) == 1
    assert receipt.read_bytes() == source
    assert interactions.DEFAULT_CHECKLIST_PATH.read_bytes() == source
    assert "Primary catalog does not target 1.0.0" in capsys.readouterr().out


def test_rules_interaction_receipt_rejects_maintained_policy_alias() -> None:
    path = interactions.DEFAULT_POLICY_PATH
    original = path.read_bytes()
    with pytest.raises(SystemExit) as exc:
        interactions.main(["--receipt-output", str(path)])
    assert exc.value.code == 1
    assert path.read_bytes() == original


@pytest.mark.parametrize("arguments", [
    ["--output", "docs/rules-interaction-checklist.md"],
    ["--refresh-catalog-scope"],
    ["--report-catalog-scope-drift"],
])
def test_rules_interaction_receipt_excludes_intentional_rewrites(
    arguments: list[str], tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "receipt.md"
    assert interactions.main(["--receipt-output", str(output), *arguments]) == 2
    assert not output.exists()
    assert "cannot be combined" in capsys.readouterr().out


def test_rules_interaction_late_collision_preserves_prior_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "late.md"
    prior = b"other job completed\n"
    original = interactions.audit_rules_interactions

    def competitor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output.write_bytes(prior)
        return original(*args, **kwargs)

    monkeypatch.setattr(interactions, "audit_rules_interactions", competitor)
    with pytest.raises(SystemExit) as exc:
        interactions.main(["--receipt-output", str(output)])
    assert exc.value.code == 1
    assert output.read_bytes() == prior


@pytest.mark.parametrize("alias", ("policy", "catalog-scope", "curated-rule"))
@pytest.mark.parametrize("refresh", (False, True))
def test_rules_interaction_checklist_regeneration_cannot_replace_source_inputs(
    alias: str, refresh: bool, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    rules = tmp_path / "rules"
    rules.mkdir()
    curated = rules / "source-rule.json"
    policy = tmp_path / "reviews.json"
    scope = tmp_path / "catalog-scope.json"
    originals = {
        curated: b"retained curated rules source",
        policy: b"retained review policy",
        scope: b"retained primary catalog scope",
    }
    for path, data in originals.items():
        path.write_bytes(data)
    output = {
        "policy": policy,
        "catalog-scope": scope,
        "curated-rule": curated,
    }[alias]

    def no_audit(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Output alias must not run an audit or refresh")

    monkeypatch.setattr(interactions, "audit_rules_interactions", no_audit)
    args = [
        "--rules", str(rules),
        "--policy", str(policy),
        "--catalog-scope", str(scope),
        "--output", str(output),
    ]
    if refresh:
        args += [
            "--refresh-catalog-scope",
            "--database", "unused-army.db", "--rules-database", "unused-rules.db",
        ]
    assert interactions.main(args) == 2
    assert "cannot replace" in capsys.readouterr().out
    for path, data in originals.items():
        assert path.read_bytes() == data


def test_rules_interaction_explicit_checklist_regeneration_still_allowed(
    tmp_path: Path,
) -> None:
    output = tmp_path / "maintained-checklist.md"
    output.write_bytes(b"old checklist content")
    assert interactions.main(["--output", str(output)]) == 0
    assert output.read_bytes() == interactions.DEFAULT_CHECKLIST_PATH.read_bytes()


def test_rules_interaction_catalog_scope_refresh_remains_intentional(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scope = tmp_path / "catalog-scope.json"
    original = interactions.DEFAULT_CATALOG_SCOPE_PATH.read_bytes()
    scope.write_bytes(original)
    expected = interactions._load_catalog_scope(scope)
    projections: list[tuple[str, str]] = []

    def fake_scope(
        database: Path, rules_database: Path, *,
        target_release: str,
        release_exceptions: list[dict[str, str]],
    ) -> dict[str, Any]:
        projections.append((str(database), str(rules_database)))
        assert target_release == expected["targetRelease"]
        assert release_exceptions == expected["releaseExceptions"]
        return expected

    monkeypatch.setattr(interactions, "_catalog_scope_from_databases", fake_scope)
    assert interactions.main([
        "--catalog-scope", str(scope),
        "--database", "unused-army.db", "--rules-database", "unused-rules.db",
        "--refresh-catalog-scope",
    ]) == 0
    assert projections == [("unused-army.db", "unused-rules.db")]
    assert json.loads(scope.read_text(encoding="utf-8")) == expected
    assert interactions.DEFAULT_CATALOG_SCOPE_PATH.read_bytes() == original
    assert "Rules interaction catalog scope written" in capsys.readouterr().out


def test_rules_interaction_check_mode_stays_read_only() -> None:
    original = interactions.DEFAULT_CHECKLIST_PATH.read_bytes()
    assert interactions.main([
        "--check-output", str(interactions.DEFAULT_CHECKLIST_PATH),
    ]) == 0
    assert interactions.DEFAULT_CHECKLIST_PATH.read_bytes() == original


@pytest.mark.parametrize("filename", [
    "audit_rules_interactions.py",
    "audit_restrictions_source_chart.py",
    "audit_pdf_revision_deltas.py",
])
def test_specialized_audit_direct_script_help_still_works(filename: str) -> None:
    process = subprocess.run(
        [sys.executable, str(ROOT / "tools" / filename), "--help"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert "--output" in process.stdout
