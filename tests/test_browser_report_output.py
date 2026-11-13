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
    verify_hacking_programs_browser,
    verify_labels_browser,
    verify_non_skill_army_browser,
    verify_rule_fragment_browser,
    verify_states_browser,
    verify_traits_catalog_browser,
    verify_unit_skill_presentation_browser,
)
from tools.browser.report_output import require_new_browser_report, write_browser_report

MODULES = (
    verify_ammunition_browser,
    verify_general_rules_browser,
    verify_labels_browser,
    verify_states_browser,
    verify_traits_catalog_browser,
)
SPECIALIZED_MODULES = (
    verify_hacking_programs_browser,
    verify_non_skill_army_browser,
)
PRESENTATION_MODULES = (
    verify_unit_skill_presentation_browser,
    verify_rule_fragment_browser,
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


@pytest.mark.parametrize(
    "module", SPECIALIZED_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
def test_specialized_cli_rejects_existing_output_before_any_browser_work(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "existing.json"
    prior = b"previous browser evidence\n"
    output.write_bytes(prior)

    def no_browser(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Occupied output must block browser verification")

    monkeypatch.setattr(module, "verify", no_browser)
    if module is verify_hacking_programs_browser:
        monkeypatch.setattr(module, "verify_local", no_browser)
    with pytest.raises(SystemExit) as exc:
        module.main(["--output", str(output)])
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == prior


@pytest.mark.parametrize(
    "module", SPECIALIZED_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
@pytest.mark.parametrize("passed", (True, False))
def test_specialized_cli_keeps_json_format_and_failure_exit(
    module: Any, passed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "new-run" / "browser.json"
    identity_key = (
        "slug" if module is verify_hacking_programs_browser else "unit"
    )
    report = {
        "format": "bounded browser acceptance",
        "total": 1,
        "passed": int(passed),
        "results": [{
            "width": 390,
            identity_key: "example",
            "status": "passed" if passed else "failed",
            **({} if passed else {"error": "observed browser failure"}),
        }],
    }
    monkeypatch.setattr(module, "verify", lambda *args, **kwargs: report)
    assert module.main(["--output", str(output)]) == (0 if passed else 1)
    assert output.read_bytes() == (
        json.dumps(report, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    output_text = capsys.readouterr().out
    assert ("1/1 passed" if passed else "0/1 passed") in output_text
    if not passed:
        assert "observed browser failure" in output_text


@pytest.mark.parametrize(
    "module", SPECIALIZED_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
def test_specialized_cli_still_supports_stdout_without_output(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        module, "verify",
        lambda *args, **kwargs: {"passed": 0, "total": 0, "results": []},
    )
    assert module.main([]) == 0
    assert list(tmp_path.iterdir()) == []


def test_hacking_cli_keeps_self_host_and_base_url_mutual_exclusion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "already.json"
    output.write_text("original", encoding="utf-8")

    def no_browser(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Invalid CLI combination must not reach browser startup")

    monkeypatch.setattr(verify_hacking_programs_browser, "verify", no_browser)
    monkeypatch.setattr(verify_hacking_programs_browser, "verify_local", no_browser)
    with pytest.raises(SystemExit) as exc:
        verify_hacking_programs_browser.main([
            "--self-host", "--base-url", "http://localhost:8001",
            "--output", str(output),
        ])
    assert exc.value.code == 2
    assert "--self-host cannot be combined" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "original"


def test_hacking_self_host_output_collision_blocks_server_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "existing.json"
    output.write_text("prior receipt", encoding="utf-8")

    def no_local_server(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Occupied output must block local server startup")

    monkeypatch.setattr(
        verify_hacking_programs_browser, "verify_local", no_local_server,
    )
    with pytest.raises(SystemExit) as exc:
        verify_hacking_programs_browser.main([
            "--self-host", "--output", str(output),
        ])
    assert exc.value.code == 1
    assert output.read_text(encoding="utf-8") == "prior receipt"


def test_hacking_self_host_output_calls_original_local_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = {"passed": 0, "total": 0, "results": []}
    called: list[bool] = []
    monkeypatch.setattr(
        verify_hacking_programs_browser, "verify_local",
        lambda *, headed: (called.append(headed), report)[1],
    )

    def no_remote(*args: Any, **kwargs: Any) -> None:
        pytest.fail("--self-host should not use an external server")

    monkeypatch.setattr(verify_hacking_programs_browser, "verify", no_remote)
    output = tmp_path / "local.json"
    assert verify_hacking_programs_browser.main([
        "--self-host", "--headed", "--output", str(output),
    ]) == 0
    assert called == [True]
    assert json.loads(output.read_text(encoding="utf-8")) == report


@pytest.mark.parametrize(
    "module", SPECIALIZED_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
def test_specialized_cli_does_not_replace_report_created_during_verification(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "candidate.json"
    prior = b"another run's receipt\n"

    def competing_verification(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output.write_bytes(prior)
        return {"total": 0, "passed": 0, "results": []}

    monkeypatch.setattr(module, "verify", competing_verification)
    with pytest.raises(SystemExit) as exc:
        module.main(["--output", str(output)])
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == prior


@pytest.mark.parametrize(
    "module", SPECIALIZED_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
def test_specialized_cli_keeps_exception_from_verifier_without_new_receipt(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "new" / "browser.json"

    def broken_verification(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("preflight browser failure")

    monkeypatch.setattr(module, "verify", broken_verification)
    with pytest.raises(RuntimeError, match="preflight browser failure"):
        module.main(["--output", str(output)])
    assert not output.exists()
    assert not output.parent.exists()


@pytest.mark.parametrize(
    "module", PRESENTATION_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
def test_presentation_cli_rejects_prior_report_before_verification(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "previous.json"
    previous = b"accepted evidence\n"
    output.write_bytes(previous)

    def no_browser(*args: Any, **kwargs: Any) -> None:
        pytest.fail("An occupied report must prevent browser startup")

    monkeypatch.setattr(module, "verify", no_browser)
    if module is verify_rule_fragment_browser:
        monkeypatch.setattr(module, "verify_local", no_browser)
    with pytest.raises(SystemExit) as exc:
        module.main(["--output", str(output)])
    assert exc.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == previous


@pytest.mark.parametrize(
    "module", PRESENTATION_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
@pytest.mark.parametrize("passed", (True, False))
def test_presentation_cli_preserves_json_and_failure_exit(
    module: Any, passed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "new-run" / "receipt.json"
    report = {
        "format": "pinned browser report",
        "passed": int(passed),
        "total": 1,
        "results": [{
            "status": "passed" if passed else "failed", "width": 320,
            "unit" if module is verify_unit_skill_presentation_browser else "href":
                "sample" if module is verify_unit_skill_presentation_browser else "#rule-weapon",
            **({} if passed else {"error": "observed failure"}),
        }],
    }
    monkeypatch.setattr(module, "verify", lambda *args, **kwargs: report)
    assert module.main(["--output", str(output)]) == (0 if passed else 1)
    assert output.read_bytes() == (
        json.dumps(report, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    stdout = capsys.readouterr().out
    assert ("1/1 passed" if passed else "0/1 passed") in stdout
    if not passed:
        assert "observed failure" in stdout


@pytest.mark.parametrize(
    "module", PRESENTATION_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
def test_presentation_cli_still_prints_without_output(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        module, "verify",
        lambda *args, **kwargs: {"passed": 0, "total": 0, "results": []},
    )
    assert module.main([]) == 0
    assert "0/0 passed" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "module", PRESENTATION_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
def test_presentation_cli_does_not_overwrite_late_arrival(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "candidate.json"
    earlier = b"another process arrived\n"

    def late_report(*args: Any, **kwargs: Any) -> dict[str, Any]:
        output.write_bytes(earlier)
        return {"passed": 0, "total": 0, "results": []}

    monkeypatch.setattr(module, "verify", late_report)
    with pytest.raises(SystemExit) as exc:
        module.main(["--output", str(output)])
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    assert "browser acceptance:" not in captured.out
    assert output.read_bytes() == earlier


@pytest.mark.parametrize(
    "module", PRESENTATION_MODULES, ids=lambda module: module.__name__.split(".")[-1],
)
def test_presentation_cli_preserves_verification_exception_without_receipt(
    module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "new-run" / "report.json"

    def fail_browser(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("browser unavailable")

    monkeypatch.setattr(module, "verify", fail_browser)
    with pytest.raises(RuntimeError, match="browser unavailable"):
        module.main(["--output", str(output)])
    assert not output.exists()
    assert not output.parent.exists()


def test_unit_skill_cli_forwards_selected_profiles_and_viewports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, dict[str, Any]]] = []
    report = {"passed": 0, "total": 0, "results": []}

    def verify_unit(base_url: str, **kwargs: Any) -> dict[str, Any]:
        captured.append((base_url, kwargs))
        return report

    monkeypatch.setattr(verify_unit_skill_presentation_browser, "verify", verify_unit)
    output = tmp_path / "unit.json"
    assert verify_unit_skill_presentation_browser.main([
        "--base-url", "http://127.0.0.1:8080",
        "--slug", "raoul-spector", "--slug", "dragoes",
        "--exclude-optional", "mercs", "--exclude-optional", "teamops",
        "--distance-unit", "cm",
        "--width", "390", "--width", "320",
        "--headed", "--channel", "chrome", "--output", str(output),
    ]) == 0
    assert captured == [(
        "http://127.0.0.1:8080",
        {
            "slugs": ("raoul-spector", "dragoes"),
            "headed": True,
            "channel": "chrome",
            "optional_filters": {"mercs": False, "teamops": False},
            "distance_unit": "cm",
            "widths": (390, 320),
        },
    )]
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_rule_fragment_cli_retains_self_host_and_base_url_exclusion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "occupied.json"
    output.write_text("existing", encoding="utf-8")

    def unexpected(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Invalid argument combination must not start a browser or server")

    monkeypatch.setattr(verify_rule_fragment_browser, "verify", unexpected)
    monkeypatch.setattr(verify_rule_fragment_browser, "verify_local", unexpected)
    with pytest.raises(SystemExit) as exc:
        verify_rule_fragment_browser.main([
            "--self-host", "--base-url", "http://localhost:8800",
            "--output", str(output),
        ])
    assert exc.value.code == 2
    assert "--self-host cannot be combined" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "existing"


def test_rule_fragment_cli_self_host_refuses_existing_before_wsgi_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "occupied.json"
    output.write_text("previous", encoding="utf-8")

    def unexpected(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Existing report should block WSGI server startup")

    monkeypatch.setattr(verify_rule_fragment_browser, "verify_local", unexpected)
    with pytest.raises(SystemExit) as exc:
        verify_rule_fragment_browser.main(["--self-host", "--output", str(output)])
    assert exc.value.code == 1
    assert output.read_text(encoding="utf-8") == "previous"


def test_rule_fragment_cli_self_host_runs_original_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[bool] = []
    report = {"passed": 0, "total": 0, "results": []}

    def verify_local(*, headed: bool) -> dict[str, Any]:
        called.append(headed)
        return report

    def unexpected(*args: Any, **kwargs: Any) -> None:
        pytest.fail("--self-host must not use external-server verification")

    monkeypatch.setattr(verify_rule_fragment_browser, "verify_local", verify_local)
    monkeypatch.setattr(verify_rule_fragment_browser, "verify", unexpected)
    output = tmp_path / "fresh.json"
    assert verify_rule_fragment_browser.main([
        "--self-host", "--headed", "--output", str(output),
    ]) == 0
    assert called == [True]
    assert json.loads(output.read_text(encoding="utf-8")) == report
