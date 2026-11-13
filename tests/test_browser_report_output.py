"""Non-overwriting report contracts shared by optional catalog browser verifiers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from tools import (
    verify_ammunition_browser,
    verify_general_rules_browser,
    verify_labels_browser,
    verify_states_browser,
    verify_traits_catalog_browser,
)
from tools.browser.report_output import require_new_browser_report, write_browser_report

MODULES = (
    verify_ammunition_browser,
    verify_general_rules_browser,
    verify_labels_browser,
    verify_states_browser,
    verify_traits_catalog_browser,
)


def _stub_sources(module: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    if module is verify_general_rules_browser:
        monkeypatch.setattr(
            module, "source_rules", lambda: {"example": ("rule:example", "Example")}
        )
    elif module is verify_labels_browser:
        monkeypatch.setattr(module, "source_names", lambda: {"example": "Example"})
    elif module is verify_states_browser:
        monkeypatch.setattr(module, "source_states", lambda: {"example": "Example"})
    elif module is verify_traits_catalog_browser:
        monkeypatch.setattr(module, "source_traits", lambda: {"example": "Example"})
        monkeypatch.setattr(
            module, "load_trait_wiki_references",
            lambda: {"trait:example": {"url": "https://example.org/example"}},
        )

        class StubDatabase:
            def __init__(self, path: Path) -> None:
                self.path = path

            def list_traits(self) -> list[dict[str, str]]:
                return [{"slug": "example"}]

        monkeypatch.setattr(module, "Database", StubDatabase)


@pytest.mark.parametrize("module", MODULES, ids=lambda module: module.__name__.split(".")[-1])
def test_catalog_cli_rejects_existing_report_before_browser(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "evidence.json"
    prior = b'{"accepted":"previous-run"}\n'
    output.write_bytes(prior)

    def no_browser(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Browser must not launch after a report collision")

    monkeypatch.setattr(module, "verify", no_browser)
    with pytest.raises(SystemExit) as exc:
        module.main(["--output", str(output)])
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == prior


@pytest.mark.parametrize("module", MODULES, ids=lambda module: module.__name__.split(".")[-1])
@pytest.mark.parametrize("passed", (True, False))
def test_catalog_cli_preserves_report_format_and_failure_status(
    module: Any, passed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "new" / "evidence.json"
    report = {
        "format": "sample",
        "total": 1,
        "passed": 1 if passed else 0,
        "results": [
            {"status": "passed" if passed else "failed", "slug": "example",
             "width": 390, **({} if passed else {"error": "sample failure"})}
        ],
    }
    _stub_sources(module, monkeypatch)
    monkeypatch.setattr(module, "verify", lambda *args, **kwargs: report)
    assert module.main(["--output", str(output)]) == (0 if passed else 1)
    assert output.read_bytes() == (
        json.dumps(report, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    assert "navigation:" in capsys.readouterr().out


@pytest.mark.parametrize("module", MODULES, ids=lambda module: module.__name__.split(".")[-1])
def test_catalog_cli_without_output_remains_stdout_only(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = {"total": 0, "passed": 0, "results": []}
    _stub_sources(module, monkeypatch)
    monkeypatch.setattr(module, "verify", lambda *args, **kwargs: report)
    assert module.main([]) == 0
    assert list(tmp_path.iterdir()) == []


def test_report_helper_rejects_dangling_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "evidence.json"
    parser = argparse.ArgumentParser()
    monkeypatch.setattr(type(output), "is_symlink", lambda path: path == output)
    with pytest.raises(SystemExit) as exc:
        require_new_browser_report(parser, output)
    assert exc.value.code == 1


def test_report_helper_preserves_report_if_created_after_browser(
    tmp_path: Path,
) -> None:
    output = tmp_path / "evidence.json"
    parser = argparse.ArgumentParser()
    require_new_browser_report(parser, output)
    earlier = b"other job's report\n"
    output.write_bytes(earlier)
    with pytest.raises(SystemExit) as exc:
        write_browser_report(parser, output, {"passed": 1, "total": 1})
    assert exc.value.code == 1
    assert output.read_bytes() == earlier


def test_report_helper_handles_unwritable_path_as_failure(
    tmp_path: Path,
) -> None:
    parser = argparse.ArgumentParser()
    occupied_parent = tmp_path / "parent-file"
    occupied_parent.write_text("not a directory", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        write_browser_report(parser, occupied_parent / "evidence.json", {"passed": 1})
    assert exc.value.code == 1
    assert occupied_parent.read_text(encoding="utf-8") == "not a directory"


def test_report_helper_preserves_existing_report_after_success(
    tmp_path: Path,
) -> None:
    parser = argparse.ArgumentParser()
    output = tmp_path / "browser.json"
    report = {"é": "Ö", "passed": 0, "total": 1, "results": []}
    write_browser_report(parser, output, report)
    first = output.read_bytes()
    assert first == (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with pytest.raises(SystemExit) as exc:
        write_browser_report(parser, output, {"passed": 1})
    assert exc.value.code == 1
    assert output.read_bytes() == first
