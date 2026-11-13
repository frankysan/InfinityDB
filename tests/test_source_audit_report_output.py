"""Non-overwriting JSON/Markdown contracts for source- and weapon-audit CLIs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tools import (
    audit_1_0_reference_inputs,
    audit_auxiliary_silhouette_provenance,
    audit_weapon_chart_profiles,
    audit_weapon_definition_gaps,
    audit_weapon_trait_cross_sources,
    audit_weapon_traits_prose,
    audit_weaponry_family_clauses,
    audit_wiki_weapon_chart_names,
)
from tools.research.report_output import require_new_audit_outputs, write_audit_text_or_exit

MODULES = (
    audit_1_0_reference_inputs,
    audit_weapon_chart_profiles,
    audit_weapon_definition_gaps,
    audit_weapon_trait_cross_sources,
    audit_weapon_traits_prose,
    audit_weaponry_family_clauses,
    audit_wiki_weapon_chart_names,
    audit_auxiliary_silhouette_provenance,
)
MANDATORY_BOTH = (audit_wiki_weapon_chart_names, audit_auxiliary_silhouette_provenance)
MANDATORY_JSON = (audit_weapon_definition_gaps, *MANDATORY_BOTH)
AUDIT_FUNCTIONS = (
    "build_report", "audit_chart", "build_report", "audit_cross_sources",
    "audit_traits_and_prose", "audit_family_clauses", "audit", "audit",
)


def _base_args(module: Any, source: Path) -> list[str]:
    if module is audit_1_0_reference_inputs:
        return ["--wiki-history", str(source), "--core-pdf", str(source),
                "--faq-pdf", str(source)]
    if module is audit_weapon_chart_profiles:
        return ["--core-pdf", str(source)]
    if module is audit_weapon_definition_gaps:
        return ["--enrichment", str(source), "--chart", str(source)]
    if module is audit_weapon_trait_cross_sources:
        return ["--core-pdf", str(source), "--wiki-history", str(source)]
    if module is audit_weapon_traits_prose or module is audit_weaponry_family_clauses:
        return ["--core-pdf", str(source)]
    if module is audit_wiki_weapon_chart_names:
        return ["--wiki-en", str(source), "--army-db", str(source),
                "--curated-rules", str(source)]
    return ["--pdf-en", str(source), "--pdf-es", str(source),
            "--wiki-en", str(source), "--wiki-es", str(source),
            "--army-db", str(source)]


def _main(
    module: Any, monkeypatch: pytest.MonkeyPatch, source: Path,
    *, json_output: Path | None = None, markdown_output: Path | None = None,
) -> int:
    args = _base_args(module, source)
    if json_output is not None:
        args += ["--json-output", str(json_output)]
    if markdown_output is not None:
        args += ["--markdown-output", str(markdown_output)]
    monkeypatch.setattr(sys, "argv", [module.__name__, *args])
    return module.main()


def _patch_report(
    module: Any, monkeypatch: pytest.MonkeyPatch,
    *, on_audit: Any = None,
) -> dict[str, Any]:
    report = {"z": "café", "a": 1}
    def audited(*args: Any, **kwargs: Any) -> dict[str, Any]:
        if on_audit is not None:
            on_audit()
        return report
    name = AUDIT_FUNCTIONS[MODULES.index(module)]
    monkeypatch.setattr(module, name, audited)
    monkeypatch.setattr(
        module,
        "report_markdown" if module is audit_1_0_reference_inputs else "markdown_report",
        lambda document: "## Reviewed source evidence\n\nCafé.\n",
    )
    return report


def _expected_json(module: Any, report: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            report, indent=2,
            sort_keys=module not in MANDATORY_BOTH,
            ensure_ascii=module is audit_auxiliary_silhouette_provenance,
        ) + "\n"
    ).encode("utf-8")


@pytest.mark.parametrize("module", MODULES, ids=lambda x: x.__name__.split(".")[-1])
@pytest.mark.parametrize("occupied", ("json", "markdown"))
def test_occupied_output_blocks_source_audit_and_preserves_bytes(
    module: Any, occupied: str, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "official-source.pdf"
    source_bytes = b"private saved source bytes\n"
    source.write_bytes(source_bytes)
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    occupied_path = json_path if occupied == "json" else markdown_path
    prior = b"accepted audit evidence\n"
    occupied_path.write_bytes(prior)

    def forbidden() -> None:
        pytest.fail("Occupied receipt must stop private input investigation")

    _patch_report(module, monkeypatch, on_audit=forbidden)
    with pytest.raises(SystemExit) as exc:
        _main(module, monkeypatch, source,
              json_output=json_path, markdown_output=markdown_path)
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert occupied_path.read_bytes() == prior
    assert source.read_bytes() == source_bytes
    assert not (markdown_path if occupied == "json" else json_path).exists()


@pytest.mark.parametrize("module", MODULES, ids=lambda x: x.__name__.split(".")[-1])
def test_rejects_duplicate_json_markdown_path_before_audit(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"private source\n")
    duplicate = tmp_path / "new.json"
    def forbidden() -> None:
        pytest.fail("Duplicate output must stop audit")
    _patch_report(module, monkeypatch, on_audit=forbidden)
    with pytest.raises(SystemExit) as exc:
        _main(module, monkeypatch, source,
              json_output=duplicate, markdown_output=duplicate)
    assert exc.value.code == 1
    assert "duplicate destination" in capsys.readouterr().err
    assert not duplicate.exists()


@pytest.mark.parametrize("module", MODULES, ids=lambda x: x.__name__.split(".")[-1])
def test_json_markdown_rendering_and_source_bytes_stay_unchanged(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "saved-source.pdf"
    original = b"retained downloaded snapshot\n"
    source.write_bytes(original)
    json_path = tmp_path / "new-run" / "audit.json"
    markdown_path = tmp_path / "new-run" / "audit.md"
    report = _patch_report(module, monkeypatch)
    assert _main(module, monkeypatch, source,
                 json_output=json_path, markdown_output=markdown_path) == 0
    assert json_path.read_bytes() == _expected_json(module, report)
    assert markdown_path.read_bytes() == b"## Reviewed source evidence\n\nCaf\xc3\xa9.\n"
    assert source.read_bytes() == original
    stdout = capsys.readouterr().out
    if module in MANDATORY_BOTH:
        assert "Reviewed source evidence" in stdout
    elif module is audit_weapon_definition_gaps:
        assert "Weapon gap triage written:" in stdout
    else:
        assert stdout == ""


@pytest.mark.parametrize("module", MODULES, ids=lambda x: x.__name__.split(".")[-1])
def test_late_claim_does_not_replace_accepted_json_report(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"retained original bytes")
    json_path = tmp_path / "report.json"
    markdown_path = tmp_path / "report.md"
    prior = b"another audit finished first\n"
    _patch_report(module, monkeypatch, on_audit=lambda: json_path.write_bytes(prior))
    with pytest.raises(SystemExit) as exc:
        _main(module, monkeypatch, source,
              json_output=json_path, markdown_output=markdown_path)
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert json_path.read_bytes() == prior
    assert not markdown_path.exists()
    assert source.read_bytes() == b"retained original bytes"


@pytest.mark.parametrize(
    "module", tuple(x for x in MODULES if x not in MANDATORY_JSON),
    ids=lambda x: x.__name__.split(".")[-1],
)
def test_optional_stdout_json_remains_available(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"private original")
    report = _patch_report(module, monkeypatch)
    assert _main(module, monkeypatch, source) == 0
    assert capsys.readouterr().out == _expected_json(module, report).decode("utf-8")
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("module", MODULES, ids=lambda x: x.__name__.split(".")[-1])
def test_cannot_write_into_existing_source_pdf(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "source.pdf"
    original = b"official source is immutable\n"
    source.write_bytes(original)
    _patch_report(module, monkeypatch, on_audit=lambda: pytest.fail("source read"))
    with pytest.raises(SystemExit) as exc:
        _main(module, monkeypatch, source,
              json_output=source, markdown_output=tmp_path / "new.md")
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert source.read_bytes() == original


def test_helper_refuses_dangling_symlink_even_when_target_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import argparse

    path = tmp_path / "dangling.json"
    monkeypatch.setattr(Path, "is_symlink", lambda target: target == path)
    with pytest.raises(SystemExit) as exc:
        require_new_audit_outputs(argparse.ArgumentParser(), path)
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err


def test_helper_rejects_equivalent_relative_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    import argparse

    target = tmp_path / "report.json"
    alternate = tmp_path / "reports" / ".." / "report.json"
    with pytest.raises(SystemExit) as exc:
        require_new_audit_outputs(argparse.ArgumentParser(), target, alternate)
    assert exc.value.code == 1
    assert "duplicate destination" in capsys.readouterr().err


def test_helper_exclusive_create_prevents_post_preflight_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import argparse

    target = tmp_path / "report.json"
    previous = b"previous run\n"
    original_open = Path.open
    def colliding_open(
        path: Path, mode: str = "r", buffering: int = -1,
        encoding: str | None = None, errors: str | None = None,
        newline: str | None = None,
    ):
        if path == target and mode == "x":
            path.write_bytes(previous)
        return original_open(
            path, mode, buffering=buffering, encoding=encoding,
            errors=errors, newline=newline,
        )
    monkeypatch.setattr(Path, "open", colliding_open)
    with pytest.raises(SystemExit) as exc:
        write_audit_text_or_exit(argparse.ArgumentParser(), target, "new report\n")
    assert exc.value.code == 1
    assert target.read_bytes() == previous


def test_helper_fails_cleanly_for_unwritable_destination(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    import argparse

    parent_file = tmp_path / "not-directory"
    parent_file.write_text("prior", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        write_audit_text_or_exit(argparse.ArgumentParser(), parent_file / "report.json", "{}")
    assert exc.value.code == 1
    assert parent_file.read_text(encoding="utf-8") == "prior"
    assert "Audit report output:" in capsys.readouterr().err
