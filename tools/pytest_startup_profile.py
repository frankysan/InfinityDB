"""Controller-side pytest-xdist startup and collection timing diagnostics.

The standard pytest --durations report only covers test setup/call/teardown.
This plugin separately measures the worker startup/collection wall-clock interval
without creating persistent report artifacts or changing test distribution.
"""

from __future__ import annotations

import os
import re
import time
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import pytest

from tools.resource_waits import capture_resource_waits

_SETUP_WAITS: pytest.StashKey[list[tuple[str, float]]] = pytest.StashKey()
_WAIT_PROPERTY_PREFIX = "infinitydb_wait_"
_LANE_PROPERTY = "infinitydb_browser_lane"
_WORKER_PROPERTY = "infinitydb_browser_worker"


def incompatible_loadgroup_versions(pytest_version: str, xdist_version: str) -> bool:
    """pytest 9.2 node IDs break pytest-xdist 3.8.0 loadgroup scheduling."""
    def release(value: str) -> tuple[int, int, int] | None:
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value)
        if match is None:
            return None
        return int(match[1]), int(match[2]), int(match[3])

    pytest_release = release(pytest_version)
    xdist_release = release(xdist_version)
    return bool(
        pytest_release is not None and xdist_release is not None
        and pytest_release >= (9, 2, 0) and xdist_release <= (3, 8, 0)
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Reject a known silently broken loadgroup combination before collection."""
    if session.config.getoption("dist", default="no") != "loadgroup":
        return
    try:
        pytest_version = version("pytest")
        xdist_version = version("pytest-xdist")
    except PackageNotFoundError:
        return
    if incompatible_loadgroup_versions(pytest_version, xdist_version):
        raise pytest.UsageError(
            f"pytest {pytest_version} with pytest-xdist {xdist_version} "
            "silently ignores --dist loadgroup (pytest 9.2 node IDs). "
            "Install the compatible dev dependencies: "
            "python -m pip install 'pytest>=8.0,<9.2'."
        )


def _skip_reason(report: pytest.TestReport) -> str:
    detail = report.longrepr
    if isinstance(detail, tuple) and len(detail) >= 3:
        reason = str(detail[2])
    else:
        reason = str(detail or "Unspecified skip reason")
    return reason.removeprefix("Skipped: ").strip()


def summarized_skip_reasons(reports: Sequence[pytest.TestReport]) -> tuple[str, ...]:
    """Group actual pytest skip reports by reason without losing their counts."""
    reasons: Counter[str] = Counter()
    for report in reports:
        reasons[_skip_reason(report)] += 1
    if not reasons:
        return ()
    total = sum(reasons.values())
    test_word = "test" if total == 1 else "tests"
    reason_word = "reason" if len(reasons) == 1 else "reasons"
    lines = [f"Skipped: {total} {test_word}; {len(reasons)} distinct {reason_word}."]
    lines.extend(
        f"  {count:>4}  {reason}"
        for reason, count in sorted(reasons.items(), key=lambda entry: (-entry[1], entry[0]))
    )
    return tuple(lines)


def summarized_skip_details(reports: Sequence[pytest.TestReport]) -> tuple[str, ...]:
    """Expose exact skipped node IDs for optional cross-host coverage comparison."""
    if not reports:
        return ()
    return tuple(
        f"  {report.nodeid} :: {' '.join(_skip_reason(report).split())}"
        for report in sorted(reports, key=lambda item: (item.nodeid, _skip_reason(item)))
    )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--infinitydb-skip-summary", action="store_true", default=False,
        help="Print grouped pytest skip reasons in the final validation report.",
    )
    parser.addoption(
        "--infinitydb-skip-details", action="store_true", default=False,
        help="Print individual skipped test IDs and reasons for cross-host comparison.",
    )


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
    setup_waits: list[tuple[str, str, float, float]] = field(default_factory=list)
    lane_workers: dict[str, set[str]] = field(default_factory=dict)
    lane_cases: dict[str, int] = field(default_factory=dict)

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
        self.setup_waits.clear()
        self.lane_workers.clear()
        self.lane_cases.clear()

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
        return lane if lane in ("chromium-a", "chromium-b", "chromium-c", "chromium-d") else None

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

    def record_setup_wait(self, report: pytest.TestReport) -> None:
        """Retain measured resource waiting transported by pytest/xdist."""
        for key, value in report.user_properties:
            if (key.startswith(_WAIT_PROPERTY_PREFIX)
                    and isinstance(value, (int, float)) and value >= 0.05):
                self.setup_waits.append((
                    report.nodeid, key[len(_WAIT_PROPERTY_PREFIX):],
                    float(value), report.duration,
                ))

    def record_lane_worker(self, report: pytest.TestReport) -> None:
        """Track actual group-to-worker placements across xdist test reports."""
        properties = dict(report.user_properties)
        lane = properties.get(_LANE_PROPERTY)
        worker = properties.get(_WORKER_PROPERTY)
        if not isinstance(lane, str) or not isinstance(worker, str):
            return
        self.lane_workers.setdefault(lane, set()).add(worker)
        self.lane_cases[lane] = self.lane_cases.get(lane, 0) + 1

    def lane_violations(self) -> tuple[str, ...]:
        return tuple(
            f"{lane}: {', '.join(sorted(workers))}"
            for lane, workers in sorted(self.lane_workers.items())
            if len(workers) > 1
        )

    def lane_summary_lines(self) -> tuple[str, ...]:
        if not self.lane_workers:
            return ("No Chromium lane assignments observed.",)
        lines = [
            f"  {lane}: {', '.join(sorted(workers))} "
            f"({self.lane_cases[lane]} setup events)"
            for lane, workers in sorted(self.lane_workers.items())
        ]
        if self.lane_violations():
            lines.append("FAIL: one or more grouped browser lanes ran on multiple workers.")
        else:
            lines.append("PASS: each observed browser lane used one worker.")
        return tuple(lines)

    def wait_summary_lines(self) -> tuple[str, ...]:
        if not self.setup_waits:
            return ()
        total = sum(wait for _, _, wait, _ in self.setup_waits)
        lines = [
            f"Measured resource waiting during setup: {total:.2f}s across "
            f"{len(self.setup_waits)} test setup events (summed worker time; not wall time).",
            "Largest setup waits (waiting / remaining setup / original pytest setup):",
        ]
        for nodeid, resource, wait, duration in sorted(
            self.setup_waits, key=lambda record: record[2], reverse=True,
        )[:10]:
            lines.append(
                f"  {resource}: {wait:.2f}s / {max(0.0, duration - wait):.2f}s / "
                f"{duration:.2f}s  {nodeid}"
            )
        lines.append(
            "Remaining setup can include other unmeasured waits; waiting is already "
            "included in pytest setup (do not add the two)."
        )
        return tuple(lines)

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
            for lane in sorted(self.browser_lane_started_at):
                started = self.browser_lane_started_at[lane]
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


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> Iterator[None]:
    """Observe resource blocking without changing pytest's native setup phase."""
    with capture_resource_waits() as waits:
        yield
    item.stash[_SETUP_WAITS] = waits


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> Iterator[None]:
    """Attach setup waits to the report for transmission to the xdist controller."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "setup":
        return
    by_resource: dict[str, float] = {}
    for resource, seconds in item.stash.get(_SETUP_WAITS, []):
        by_resource[resource] = by_resource.get(resource, 0.0) + seconds
    for resource, seconds in sorted(by_resource.items()):
        report.user_properties.append((_WAIT_PROPERTY_PREFIX + resource, seconds))
    if item.config.getoption("--browser-lanes"):
        for marker in item.iter_markers("xdist_group"):
            lane = marker.kwargs.get("name", marker.args[0] if marker.args else None)
            if isinstance(lane, str) and lane.startswith("chromium-"):
                report.user_properties.append((_LANE_PROPERTY, lane))
                report.user_properties.append((
                    _WORKER_PROPERTY, os.environ.get("PYTEST_XDIST_WORKER", "main"),
                ))
                break


def pytest_runtest_logstart(nodeid: str, location: tuple[str, int, str]) -> None:
    """Track when Chromium lanes and ordinary tests first start."""
    _PROFILE.test_started(nodeid, time.perf_counter())


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Track the last teardown observed per Chromium scheduling lane."""
    if report.when == "teardown":
        _PROFILE.test_finished(report.nodeid, time.perf_counter())
    elif report.when == "setup":
        _PROFILE.record_setup_wait(report)
        _PROFILE.record_lane_worker(report)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Reject silently dispersed opt-in browser lanes on the xdist controller."""
    config = session.config
    if config.getoption("--browser-lanes") and _PROFILE.lane_violations():
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter: Any) -> None:
    lines = _PROFILE.summary_lines()
    if lines:
        terminalreporter.write_sep("=", "xdist startup and collection timings")
        for line in lines:
            terminalreporter.write_line(line)
    if terminalreporter.config.getoption("--browser-lanes"):
        terminalreporter.write_sep("=", "chromium lane worker assignment")
        for line in _PROFILE.lane_summary_lines():
            terminalreporter.write_line(line)
    waits = _PROFILE.wait_summary_lines()
    if waits:
        terminalreporter.write_sep("=", "resource waiting versus pytest setup")
        for line in waits:
            terminalreporter.write_line(line)
    if terminalreporter.config.getoption("--infinitydb-skip-summary"):
        skipped = summarized_skip_reasons(terminalreporter.stats.get("skipped", []))
        if skipped:
            terminalreporter.write_sep("=", "grouped skip reasons")
            for line in skipped:
                terminalreporter.write_line(line)
    if terminalreporter.config.getoption("--infinitydb-skip-details"):
        details = summarized_skip_details(terminalreporter.stats.get("skipped", []))
        if details:
            terminalreporter.write_sep("=", "skipped test identities")
            for line in details:
                terminalreporter.write_line(line)
