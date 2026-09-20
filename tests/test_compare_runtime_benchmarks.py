from __future__ import annotations

import json
from pathlib import Path

from tools.benchmark_runtime import FORMAT as BENCHMARK_FORMAT
from tools.benchmark_runtime import FORMAT_VERSION as BENCHMARK_FORMAT_VERSION
from tools.compare_runtime_benchmarks import compare_reports, main


def _report(*, size: int = 1000, cold: int = 20, warm: int = 200) -> dict:
    return {
        "format": BENCHMARK_FORMAT,
        "formatVersion": BENCHMARK_FORMAT_VERSION,
        "database": "data/generated/infinity.db",
        "databaseBytes": size,
        "coldIterations": cold,
        "warmIterations": warm,
        "cases": [
            {
                "name": "units",
                "cold": {"medianMs": 100.0, "p95Ms": 120.0},
                "warm": {"medianMs": 1.0, "p95Ms": 1.2},
            },
            {
                "name": "armies",
                "cold": {"medianMs": 10.0, "p95Ms": 12.0},
                "warm": {"medianMs": 0.5, "p95Ms": 0.6},
            },
        ],
    }


def test_compare_reports_calculates_timing_and_size_deltas() -> None:
    before = _report(size=1000)
    after = _report(size=900)
    after["cases"][0]["cold"]["medianMs"] = 80.0
    after["cases"][0]["cold"]["p95Ms"] = 108.0

    report = compare_reports(
        before,
        after,
        before_source="before.json",
        after_source="after.json",
    )

    assert report["databaseSize"] == {"deltaBytes": -100, "deltaPercent": -10.0}
    units = report["cases"][0]
    assert units["cold"]["medianMs"] == {
        "beforeMs": 100.0,
        "afterMs": 80.0,
        "deltaMs": -20.0,
        "deltaPercent": -20.0,
    }
    assert units["cold"]["p95Ms"]["deltaPercent"] == -10.0


def test_compare_main_rejects_different_case_sets_without_traceback(
    tmp_path: Path, capsys
) -> None:
    before = _report()
    after = _report()
    after["cases"].pop()
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    before_path.write_text(json.dumps(before), encoding="utf-8")
    after_path.write_text(json.dumps(after), encoding="utf-8")

    assert main([str(before_path), str(after_path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("ERROR: Benchmark reports contain different cases")
    assert "Traceback" not in captured.err


def test_compare_main_rejects_different_iteration_counts(
    tmp_path: Path, capsys
) -> None:
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    before_path.write_text(json.dumps(_report()), encoding="utf-8")
    after_path.write_text(json.dumps(_report(cold=10)), encoding="utf-8")

    assert main([str(before_path), str(after_path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "different iteration counts" in captured.err
