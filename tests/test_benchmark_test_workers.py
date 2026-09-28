from __future__ import annotations

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


def test_benchmark_order_reverses_even_repetitions() -> None:
    assert benchmark_test_workers.benchmark_order(("0", "4", "auto"), 2) == (
        (1, "0"),
        (1, "4"),
        (1, "auto"),
        (2, "auto"),
        (2, "4"),
        (2, "0"),
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
