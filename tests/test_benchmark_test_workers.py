from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools import benchmark_test_workers


def _run(workers: str, repetition: int, duration: float, *, status: str = "PASS"):
    return benchmark_test_workers.BenchmarkRun(
        workers=workers,
        repetition=repetition,
        status=status,
        returncode=0 if status == "PASS" else 1,
        duration_seconds=duration,
    )


def test_normalize_workers_preserves_order_and_deduplicates() -> None:
    assert benchmark_test_workers.normalize_workers(["4", "04", "auto", "0", "auto"]) == (
        "4",
        "auto",
        "0",
    )

    with pytest.raises(ValueError, match="non-negative"):
        benchmark_test_workers.normalize_workers(["-1"])


def test_benchmark_order_balances_candidates_across_positions() -> None:
    assert benchmark_test_workers.benchmark_order(("6", "8", "auto"), 6) == (
        (1, "6"),
        (1, "8"),
        (1, "auto"),
        (2, "8"),
        (2, "auto"),
        (2, "6"),
        (3, "auto"),
        (3, "6"),
        (3, "8"),
        (4, "auto"),
        (4, "8"),
        (4, "6"),
        (5, "8"),
        (5, "6"),
        (5, "auto"),
        (6, "6"),
        (6, "auto"),
        (6, "8"),
    )


def test_parallel_benchmark_requires_xdist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        benchmark_test_workers.importlib.util,
        "find_spec",
        lambda name: None,
    )

    with pytest.raises(ValueError, match="pytest-xdist is required"):
        benchmark_test_workers.validate_parallel_support(("0", "4"))

    benchmark_test_workers.validate_parallel_support(("0",))


def test_benchmark_command_reuses_normal_check_runner_contract() -> None:
    command = benchmark_test_workers.benchmark_command(
        "6",
        sections=("model", "web"),
        assets="off",
        targets=("tests/test_database.py",),
    )

    assert command == (
        benchmark_test_workers.sys.executable,
        str(benchmark_test_workers.REPO_ROOT / "tools" / "run_checks.py"),
        "--stage",
        "test",
        "--assets",
        "off",
        "--test-workers",
        "6",
        "--test-section",
        "model",
        "--test-section",
        "web",
        "tests/test_database.py",
    )


def test_summaries_use_median_and_fastest_requires_complete_passes() -> None:
    runs = [
        _run("4", 1, 12.0),
        _run("8", 1, 10.0),
        _run("8", 2, 8.0),
        _run("4", 2, 9.0, status="FAIL"),
    ]
    summaries = benchmark_test_workers.summarize_runs(("4", "8"), runs)

    assert summaries[0].median_seconds == 12.0
    assert summaries[0].failed_runs == 1
    assert summaries[1].median_seconds == 9.0
    assert benchmark_test_workers.fastest_complete_summary(summaries, 2) == summaries[1]


def test_report_document_records_machine_selection_and_fastest(monkeypatch) -> None:
    monkeypatch.setattr(benchmark_test_workers, "git_value", lambda *args: "test-git")
    runs = [_run("0", 1, 20.0), _run("4", 1, 10.0)]
    summaries = benchmark_test_workers.summarize_runs(("0", "4"), runs)

    document = benchmark_test_workers.report_document(
        started_at=datetime(2026, 9, 28, 10, 0, tzinfo=UTC),
        workers=("0", "4"),
        repeat=1,
        sections=("model",),
        assets="off",
        targets=(),
        runs=runs,
        summaries=summaries,
    )

    assert document["commit"] == "test-git"
    assert document["sections"] == ["model"]
    assert document["fastestCompleteWorkers"] == "4"


def test_write_report_uses_stable_utf8_json(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    benchmark_test_workers.write_report(path, {"version": 1, "workers": ["4"]})

    assert path.read_bytes() == b'{\n  "version": 1,\n  "workers": [\n    "4"\n  ]\n}\n'


def test_report_writer_refuses_existing_file_without_changing_bytes(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    prior = b'{"run":"accepted earlier"}\n'
    path.write_bytes(prior)
    with pytest.raises(FileExistsError, match="already exists"):
        benchmark_test_workers.write_report(path, {"run": "new"})
    assert path.read_bytes() == prior


def test_report_writer_refuses_dangling_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "dangling.json"
    monkeypatch.setattr(
        Path, "is_symlink", lambda target: target == path,
    )
    with pytest.raises(FileExistsError, match="already exists"):
        benchmark_test_workers.require_new_report(path)
    assert not path.exists()


def test_report_writer_exclusive_creation_survives_post_check_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "report.json"
    prior = b'{"source":"competing-run"}\n'
    original_open = Path.open

    def concurrent_open(
        target: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ):
        if target == path and mode == "x":
            path.write_bytes(prior)
        return original_open(
            target, mode, buffering=buffering, encoding=encoding,
            errors=errors, newline=newline,
        )

    monkeypatch.setattr(Path, "open", concurrent_open)
    with pytest.raises(FileExistsError):
        benchmark_test_workers.write_report(path, {"source": "current"})
    assert path.read_bytes() == prior


@pytest.mark.parametrize("default_path", (False, True))
def test_benchmark_cli_rejects_occupied_report_before_test_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], default_path: bool,
) -> None:
    path = tmp_path / "old-benchmark.json"
    prior = b"completed benchmark measurements\n"
    path.write_bytes(prior)
    if default_path:
        monkeypatch.setattr(
            benchmark_test_workers, "report_path_for",
            lambda started, requested: path if requested is None else requested,
        )

    def no_run(*args: object, **kwargs: object) -> None:
        pytest.fail("Test subprocess must not run after an output collision")

    monkeypatch.setattr(benchmark_test_workers, "run_once", no_run)
    command = ["--workers", "0"]
    if not default_path:
        command.extend(["--report", str(path)])
    assert benchmark_test_workers.main(command) == benchmark_test_workers.EXIT_USAGE_ERROR
    assert "already exists" in capsys.readouterr().err
    assert path.read_bytes() == prior


@pytest.mark.parametrize("failed", (False, True))
def test_benchmark_cli_writes_new_report_and_keeps_failed_run_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], failed: bool,
) -> None:
    path = tmp_path / "new" / "test-workers.json"
    calls: list[tuple[str, int, dict[str, object]]] = []

    def single_run(
        workers: str, repetition: int, **kwargs: object,
    ) -> tuple[benchmark_test_workers.BenchmarkRun, str]:
        calls.append((workers, repetition, kwargs))
        return (
            _run(workers, repetition, 2.5, status="FAIL" if failed else "PASS"),
            "recorded runner output",
        )

    monkeypatch.setattr(benchmark_test_workers, "run_once", single_run)
    monkeypatch.setattr(benchmark_test_workers, "git_value", lambda *args: "revision")
    assert benchmark_test_workers.main([
        "--workers", "0", "--repeat", "1", "--report", str(path),
    ]) == (benchmark_test_workers.EXIT_BENCHMARK_FAILURE if failed else 0)
    assert calls == [("0", 1, {"sections": (), "assets": "off", "targets": ()})]
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["workers"] == ["0"]
    assert report["commit"] == "revision"
    assert report["runs"][0]["status"] == ("FAIL" if failed else "PASS")
    assert report["summaries"][0]["failed_runs"] == int(failed)
    assert path.read_bytes().endswith(b"\n")
    capture = capsys.readouterr()
    assert f"Report: {path}" in capture.out
    if failed:
        assert "recorded runner output" in capture.err


def test_benchmark_cli_catches_report_collision_after_test_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "report.json"
    prior = b"other job's receipt\n"

    def competing_run(
        workers: str, repetition: int, **kwargs: object,
    ) -> tuple[benchmark_test_workers.BenchmarkRun, str]:
        path.write_bytes(prior)
        return _run(workers, repetition, 1.0), ""

    monkeypatch.setattr(benchmark_test_workers, "run_once", competing_run)
    monkeypatch.setattr(benchmark_test_workers, "git_value", lambda *args: "revision")
    assert benchmark_test_workers.main([
        "--workers", "0", "--report", str(path),
    ]) == benchmark_test_workers.EXIT_USAGE_ERROR
    assert path.read_bytes() == prior
    assert "could not write benchmark report" in capsys.readouterr().err
