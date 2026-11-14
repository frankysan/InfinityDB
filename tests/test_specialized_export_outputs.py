"""Specialized immutable export/candidate boundaries for the L2 path policy."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools import build_variant_usage as variants
from tools.data import audit_deployed_object_inventory as deployed
from tools.symbols import export_symbol_source_plan as symbols

ROOT = Path(__file__).resolve().parents[1]

VARIANT_RESULT: dict[str, Any] = {
    "scope": "read-only-candidate-not-published",
    "variants": [],
    "familyOnlyUniqueUnitCounts": {},
    "unresolvedSourceRows": [],
    "diagnosticCounts": {},
    "sourceSnapshot": {"name": "fixture"},
    "relationships": {
        "includes": [],
        "includePaths": [],
        "peripheralAttachments": [],
        "peripheralControllerEdges": [],
    },
}


def _deployed(
    monkeypatch: pytest.MonkeyPatch, *,
    destination: Path | None = None,
) -> int:
    args = ["audit_deployed_object_inventory"]
    if destination is not None:
        args += ["--json-output", str(destination)]
    monkeypatch.setattr(sys, "argv", args)
    return deployed.main()


def test_deployed_inventory_refuses_existing_before_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "prior.json"
    previous = b"earlier reviewed deployed objects\n"
    target.write_bytes(previous)
    monkeypatch.setattr(
        deployed, "audit_inventory",
        lambda *_args: pytest.fail("Existing output must block audit"),
    )
    with pytest.raises(SystemExit) as exc:
        _deployed(monkeypatch, destination=target)
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert target.read_bytes() == previous


def test_deployed_inventory_preserves_json_and_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = {"z": "café", "a": 2}
    monkeypatch.setattr(deployed, "audit_inventory", lambda *_args: report)
    target = tmp_path / "nested" / "deployed.json"
    assert _deployed(monkeypatch, destination=target) == 0
    expected = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert target.read_bytes() == expected
    assert capsys.readouterr().out == ""
    assert _deployed(monkeypatch) == 0
    assert capsys.readouterr().out == expected.decode("utf-8")


def test_deployed_inventory_late_claim_preserves_prior_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "receipt.json"
    previous = b"other writer finished first\n"

    def competing_audit(*_args: Any) -> dict[str, Any]:
        target.write_bytes(previous)
        return {"new": True}

    monkeypatch.setattr(deployed, "audit_inventory", competing_audit)
    with pytest.raises(SystemExit) as exc:
        _deployed(monkeypatch, destination=target)
    assert exc.value.code == 1
    assert target.read_bytes() == previous


def test_deployed_inventory_input_alias_is_immutable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source.json"
    original = b"source reviews are not reports\n"
    source.write_bytes(original)
    monkeypatch.setattr(
        deployed, "audit_inventory",
        lambda *_args: pytest.fail("Input source must remain untouched"),
    )
    args = ["audit_deployed_object_inventory", "--curated-source", str(source),
            "--json-output", str(source)]
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as exc:
        deployed.main()
    assert exc.value.code == 1
    assert source.read_bytes() == original


def test_deployed_inventory_dangling_symlink_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "dangling.json"
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink",
        lambda path: path == target or original_is_symlink(path),
    )
    monkeypatch.setattr(
        deployed, "audit_inventory",
        lambda *_args: pytest.fail("Symlink output must block audit"),
    )
    with pytest.raises(SystemExit) as exc:
        _deployed(monkeypatch, destination=target)
    assert exc.value.code == 1


def _variant(
    monkeypatch: pytest.MonkeyPatch, root: Path, filename: str,
    *, normalized: bool = True,
) -> None:
    monkeypatch.setattr(variants, "ROOT", root)
    command = ["build_variant_usage"]
    if normalized:
        command += ["--normalized", str(root / "normalized.json")]
    else:
        command += ["--raw-db", str(root / "raw.db")]
    command += ["--output", filename]
    monkeypatch.setattr(sys, "argv", command)
    variants.main()


def test_variant_candidate_preflight_prevents_expensive_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    local = tmp_path / "local"
    local.mkdir()
    prior = local / "variant-usage-existing.json"
    previous = b"reviewed candidate\n"
    prior.write_bytes(previous)
    monkeypatch.setattr(
        variants, "build_variant_usage_from_normalized",
        lambda *_args: pytest.fail("Candidate collision must block projection"),
    )
    with pytest.raises(SystemExit) as exc:
        _variant(monkeypatch, tmp_path, "local/variant-usage-existing.json")
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert prior.read_bytes() == previous


@pytest.mark.parametrize("output_name", (
    "local/variant-usage-r1.json",
    "local/candidates/variant-usage/variant-usage-r1.json",
))
def test_variant_candidate_fresh_is_canonical_and_staged_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], output_name: str,
) -> None:
    (tmp_path / "local").mkdir()
    result = json.loads(json.dumps(VARIANT_RESULT))
    monkeypatch.setattr(
        variants, "build_variant_usage_from_normalized",
        lambda *_args: result,
    )
    _variant(monkeypatch, tmp_path, output_name)
    output = tmp_path / output_name
    expected = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    assert output.read_bytes() == expected
    assert not output.with_suffix(".json.tmp").exists()
    summary = json.loads(capsys.readouterr().out)
    assert summary["scope"] == result["scope"]
    assert summary["output"].replace("\\", "/") == output_name


def test_variant_candidate_race_does_not_replace_other_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "local").mkdir()
    target = tmp_path / "local/variant-usage-race.json"
    previous = b"other candidate completed\n"
    monkeypatch.setattr(
        variants, "build_variant_usage_from_normalized",
        lambda *_args: VARIANT_RESULT,
    )
    original_link = variants.os.link

    def competing_link(source: Path, destination: Path) -> None:
        assert destination == target
        target.write_bytes(previous)
        original_link(source, destination)

    monkeypatch.setattr(variants.os, "link", competing_link)
    with pytest.raises(SystemExit) as exc:
        _variant(monkeypatch, tmp_path, "local/variant-usage-race.json")
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert target.read_bytes() == previous
    assert not target.with_suffix(".json.tmp").exists()


def test_variant_candidate_staging_is_not_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "local").mkdir()
    staging = tmp_path / "local/variant-usage-run.json.tmp"
    staging.write_bytes(b"another writer's staging")
    monkeypatch.setattr(
        variants, "build_variant_usage_from_normalized",
        lambda *_args: VARIANT_RESULT,
    )
    with pytest.raises(SystemExit) as exc:
        _variant(monkeypatch, tmp_path, "local/variant-usage-run.json")
    assert exc.value.code == 1
    assert staging.read_bytes() == b"another writer's staging"
    assert not staging.with_suffix("").exists()


def test_variant_candidate_rejects_outside_local_before_projection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        variants, "build_variant_usage_from_normalized",
        lambda *_args: pytest.fail("Unsafe output must block source processing"),
    )
    with pytest.raises(SystemExit) as exc:
        _variant(monkeypatch, tmp_path, "reports/variant-usage-run.json")
    assert exc.value.code == 2
    assert not (tmp_path / "reports").exists()


def test_variant_candidate_symlink_preflight_blocks_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "local").mkdir()
    target = tmp_path / "local/variant-usage-link.json"
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink",
        lambda path: path == target or original_is_symlink(path),
    )
    monkeypatch.setattr(
        variants, "build_variant_usage_from_normalized",
        lambda *_args: pytest.fail("Symlink must block projection"),
    )
    with pytest.raises(SystemExit) as exc:
        _variant(monkeypatch, tmp_path, "local/variant-usage-link.json")
    assert exc.value.code == 1


@pytest.mark.parametrize("same_bytes", (True, False))
def test_symbol_plan_concurrent_publication_is_idempotent_or_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, same_bytes: bool,
) -> None:
    plan = {"format": "test", "key": "café"}
    target = tmp_path / "new" / "source-plan.json"
    expected = (json.dumps(
        plan, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ) + "\n").encode("utf-8")
    prior = expected if same_bytes else b"competing export with different source pins\n"
    original_link = symbols.os.link

    def competing_link(source: Path, destination: Path) -> None:
        assert destination == target
        target.write_bytes(prior)
        original_link(source, destination)

    monkeypatch.setattr(symbols.os, "link", competing_link)
    if same_bytes:
        assert symbols.write_source_plan(target, plan) == target
    else:
        with pytest.raises(ValueError, match="differs"):
            symbols.write_source_plan(target, plan)
    assert target.read_bytes() == prior
    assert not target.with_suffix(".json.tmp").exists()


def test_symbol_plan_symlink_is_not_treated_as_same_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "link.json"
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink",
        lambda path: path == target or original_is_symlink(path),
    )
    with pytest.raises(ValueError, match="symlink"):
        symbols.write_source_plan(target, {"format": "test"})
    assert not target.exists()


def test_symbol_plan_existing_mismatched_content_is_immutable(
    tmp_path: Path,
) -> None:
    target = tmp_path / "source-plan.json"
    prior = b'{"plan": "earlier"}\n'
    target.write_bytes(prior)
    with pytest.raises(ValueError, match="differs"):
        symbols.write_source_plan(target, {"plan": "later"})
    assert target.read_bytes() == prior


@pytest.mark.parametrize(("module", "flag", "direct_script"), (
    ("data/audit_deployed_object_inventory", "--json-output", True),
    ("build_variant_usage", "--output", True),
    ("symbols.export_symbol_source_plan", "--output", False),
    ("symbols.export_symbol_override_lookups", "--output", False),
))
def test_export_and_inventory_documented_launch_contract(
    module: str, flag: str, direct_script: bool,
) -> None:
    command = (
        [sys.executable, str(ROOT / "tools" / (module + ".py"))]
        if direct_script else [sys.executable, "-m", "tools." + module]
    )
    result = subprocess.run(
        [*command, "--help"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert flag in result.stdout


@pytest.mark.parametrize("module", [
    "export_symbol_source_plan",
    "export_symbol_override_lookups",
    "verify_raw_symbol_handoff",
    "verify_effective_symbol_handoff",
    "verify_symbol_duplicate_handoff",
    "verify_processed_symbol_handoff",
    "prepare_symbol_publication",
    "promote_symbol_publication",
    "build_symbol_artwork_review",
])
def test_symbol_command_module_entrypoint_help(module: str) -> None:
    process = subprocess.run(
        [sys.executable, "-m", f"tools.symbols.{module}", "--help"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert process.returncode == 0, process.stderr
    assert "usage:" in process.stdout.lower()
