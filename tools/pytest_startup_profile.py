"""Controller-side pytest-xdist startup and collection timing diagnostics.

The standard pytest --durations report only covers test setup/call/teardown.
This plugin separately measures the worker startup/collection wall-clock interval
without creating persistent report artifacts or changing test distribution.
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class XdistStartupProfile:
    """Monotonic controller-side timestamps for one distributed pytest run."""

    started_at: float | None = None
    launch_at: float | None = None
    expected_workers: int = 0
    ready_at: dict[str, float] = field(default_factory=dict)
    collected_at: dict[str, float] = field(default_factory=dict)
    first_test_at: float | None = None
    first_ordinary_test_at: float | None = None
    browser_lane_started_at: dict[str, float] = field(default_factory=dict)
    browser_lane_finished_at: dict[str, float] = field(default_factory=dict)

    def start(self, workers: int, now: float, *, launch_at: float | None = None) -> None:
        self.started_at = now
        self.launch_at = launch_at if launch_at is not None and 0 <= launch_at <= now else None
        self.expected_workers = workers
        self.ready_at.clear()
        self.collected_at.clear()
        self.first_test_at = None
        self.first_ordinary_test_at = None
        self.browser_lane_started_at.clear()
        self.browser_lane_finished_at.clear()

    def ready(self, worker: str, now: float) -> None:
        if self.started_at is not None:
            self.ready_at.setdefault(worker, now)

    def collected(self, worker: str, now: float) -> None:
        if self.started_at is not None:
            self.collected_at.setdefault(worker, now)

    def first_test(self, now: float) -> None:
        if self.started_at is not None and self.first_test_at is None:
            self.first_test_at = now

    @staticmethod
    def _browser_lane(nodeid: str) -> str | None:
        lane = nodeid.rpartition("@")[2]
        return lane if lane in ("chromium-a", "chromium-b") else None

    def test_started(self, nodeid: str, now: float) -> None:
        if self.started_at is None:
            return
        self.first_test(now)
        lane = self._browser_lane(nodeid)
        if lane is not None:
            self.browser_lane_started_at.setdefault(lane, now)
        elif self.first_ordinary_test_at is None:
            self.first_ordinary_test_at = now

    def test_finished(self, nodeid: str, now: float) -> None:
        if self.started_at is None:
            return
        lane = self._browser_lane(nodeid)
        if lane is not None:
            self.browser_lane_finished_at[lane] = now

    def summary_lines(self) -> tuple[str, ...]:
        start = self.started_at
        if start is None:
            return ()

        def elapsed(value: float) -> str:
            return f"{max(0.0, value - start):.2f}s"

        ready = len(self.ready_at)
        collected = len(self.collected_at)
        lines = [
            f"Workers ready: {ready}/{self.expected_workers}"
            + (
                f"; first +{elapsed(min(self.ready_at.values()))}, "
                f"last +{elapsed(max(self.ready_at.values()))}"
                if self.ready_at else ""
            ),
            f"Collections complete: {collected}/{self.expected_workers}"
            + (
                f"; first +{elapsed(min(self.collected_at.values()))}, "
                f"last +{elapsed(max(self.collected_at.values()))}"
                if self.collected_at else ""
            ),
            "First test started: "
            + (
                f"+{elapsed(self.first_test_at)}"
                if self.first_test_at is not None else "not observed"
            ),
        ]
        if self.launch_at is not None:
            lines.append(
                "Runner process launch to xdist worker spawn: "
                f"{start - self.launch_at:.2f}s"
            )
            if self.first_test_at is not None:
                lines.append(
                    f"Runner process launch to first test: "
                    f"{self.first_test_at - self.launch_at:.2f}s"
                )
        else:
            lines.append(
                "Runner process launch to worker spawn: unavailable "
                "(run through tools/run_checks.py)"
            )
        if self.browser_lane_started_at:
            if self.first_ordinary_test_at is not None:
                lines.append(
                    f"First non-lane test started: +{elapsed(self.first_ordinary_test_at)}"
                )
            for lane in ("chromium-a", "chromium-b"):
                started = self.browser_lane_started_at.get(lane)
                if started is None:
                    continue
                finished = self.browser_lane_finished_at.get(lane)
                lines.append(
                    f"Browser lane {lane}: first +{elapsed(started)}"
                    + (f", last teardown +{elapsed(finished)}" if finished is not None else "")
                )
        lines.append(
            "Worker times are relative to xdist spawn; startup and collection overlap."
        )
        return tuple(lines)


_PROFILE = XdistStartupProfile()


def _runner_launch_timestamp() -> float | None:
    """Read the inherited cross-process perf-counter value if supplied."""
    raw = os.environ.get("INFINITYDB_PYTEST_LAUNCH_PERF_COUNTER")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_setupnodes(specs: Sequence[Any]) -> None:
    """Called on the controller immediately before xdist starts its workers."""
    _PROFILE.start(
        len(specs), time.perf_counter(), launch_at=_runner_launch_timestamp()
    )


@pytest.hookimpl(optionalhook=True)
def pytest_testnodeready(node: Any) -> None:
    """Record when a worker is ready to collect."""
    _PROFILE.ready(str(node.gateway.id), time.perf_counter())


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_node_collection_finished(node: Any, ids: Sequence[str]) -> None:
    """Record completion of each worker's independent test collection."""
    _PROFILE.collected(str(node.gateway.id), time.perf_counter())


def pytest_runtest_logstart(nodeid: str, location: tuple[str, int, str]) -> None:
    """Track when Chromium lanes and ordinary tests first start."""
    _PROFILE.test_started(nodeid, time.perf_counter())


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Track the last teardown observed per Chromium scheduling lane."""
    if report.when == "teardown":
        _PROFILE.test_finished(report.nodeid, time.perf_counter())


def pytest_terminal_summary(terminalreporter: Any) -> None:
    lines = _PROFILE.summary_lines()
    if not lines:
        return
    terminalreporter.write_sep("=", "xdist startup and collection timings")
    for line in lines:
        terminalreporter.write_line(line)
