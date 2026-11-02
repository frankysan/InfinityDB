"""Reconstruct Chromium admission and wait occupancy from timestamped JSONL records.

Usage: python -m tools.analyze_chromium_timeline local/benchmarks/chromium-RUN --slots 4
Only complete, timestamped slot records are supported; no timeline is inferred
from legacy duration-only files.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path, PureWindowsPath
from typing import Any

_TIME_FIELDS = (
    "request_monotonic_seconds",
    "acquired_monotonic_seconds",
    "released_monotonic_seconds",
)


def load_slot_records(
    directory: Path, *, slots: int, lock_directory: str | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    """Select one lock namespace before filtering its slots by capacity.

    Older metrics have no namespace identity and remain readable, but cannot
    distinguish independent locks. Ambiguous equally sized namespaces require
    explicit selection rather than silently combining unrelated test fixtures.
    """
    if slots < 1:
        raise ValueError("slots must be positive")
    paths = sorted(directory.glob("slot-*.jsonl"))
    if not paths:
        raise ValueError(f"No slot-*.jsonl files in {directory}")
    all_records: list[dict[str, Any]] = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                slot = record["slot"]
                if not isinstance(slot, int) or isinstance(slot, bool) or slot < 0:
                    raise ValueError("Invalid slot index")
                start, acquired, released = (float(record[key]) for key in _TIME_FIELDS)
                release_started = float(
                    record.get("release_started_monotonic_seconds", released)
                )
                if not (0 <= start <= acquired <= release_started <= released):
                    raise ValueError("Invalid monotonic timestamp ordering")
                if "lock_directory" in record and not (
                    isinstance(record["lock_directory"], str) and record["lock_directory"]
                ):
                    raise ValueError("Invalid lock directory")
                record["slot"] = slot
                record[_TIME_FIELDS[0]] = start
                record[_TIME_FIELDS[1]] = acquired
                record[_TIME_FIELDS[2]] = released
                record["release_started_monotonic_seconds"] = release_started
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path.name}:{line_number}: invalid or legacy slot metrics: {exc}"
                ) from exc
            all_records.append(record)
    if not all_records:
        raise ValueError("No timestamped slot records")
    namespaces = Counter(record.get("lock_directory") for record in all_records)
    if None in namespaces and len(namespaces) > 1:
        raise ValueError("Mixed namespace-aware and legacy slot metrics")
    primary_namespaces = [
        name for name in namespaces
        if name is not None
        and (PureWindowsPath(name) if "\\" in name else Path(name)).name
        == "infinitydb-chromium-slots"
    ]
    if lock_directory is not None:
        if lock_directory not in namespaces:
            raise ValueError(f"Lock directory not found in metrics: {lock_directory}")
        selected = lock_directory
    elif len(primary_namespaces) == 1:
        # Prefer the actual shared pytest-xdist browser lock, even when
        # capacity self-tests have more records than a small targeted run.
        selected = primary_namespaces[0]
    elif len(primary_namespaces) > 1:
        raise ValueError("Multiple browser lock directories; supply --lock-directory")
    else:
        most_common = namespaces.most_common()
        if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
            raise ValueError("Ambiguous lock directories; supply --lock-directory")
        selected = most_common[0][0]
    selected_records = [
        record for record in all_records if record.get("lock_directory") == selected
    ]
    records = [record for record in selected_records if record["slot"] < slots]
    if not records:
        raise ValueError("No timestamped slot records in configured capacity")
    return records, len(selected_records) - len(records), len(all_records) - len(selected_records)


def summarize_timeline(records: list[dict[str, Any]], *, slots: int) -> dict[str, Any]:
    """Integrate concurrent requests and occupied slots over the observed interval."""
    if slots < 1 or not records:
        raise ValueError("Need at least one record and one slot")
    # The sequence counter makes sorting deterministic for coincident timestamps.
    events: list[tuple[float, int, int, int]] = []
    module_totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    module_workers: dict[str, set[str]] = defaultdict(set)
    module_pids: dict[str, set[int]] = defaultdict(set)
    release_intervals: dict[int, list[tuple[float, float, float]]] = defaultdict(list)
    unlock_gap_seconds = 0.0
    for record in records:
        slot = int(record["slot"])
        start, acquired, released = (float(record[key]) for key in _TIME_FIELDS)
        release_started = float(
            record.get("release_started_monotonic_seconds", released)
        )
        if not (0 <= slot < slots and 0 <= start <= acquired <= release_started <= released):
            raise ValueError("Invalid slot record")
        # Occupancy uses the *lower bound* of release. The actual unlock occurs
        # between release_started and released, so short boundary overlaps are
        # inconclusive rather than proof that two processes held the same lock.
        events.extend((
            (start, 0, -1, 1),              # add one waiter
            (acquired, 1, slot, 1),         # acquire + remove waiting
            (release_started, 2, slot, -1),  # conservative release bound
        ))
        release_intervals[slot].append((acquired, release_started, released))
        unlock_gap_seconds += released - release_started
        label = str(record.get("label", "unspecified"))
        module = label.split("::", 1)[0].rsplit("/", 1)[-1]
        module_totals[module][0] += acquired - start
        module_totals[module][1] += released - acquired
        if record.get("worker"):
            module_workers[module].add(str(record["worker"]))
        if record.get("pid") is not None:
            module_pids[module].add(int(record["pid"]))
    possible_unlock_overlaps = 0
    for intervals in release_intervals.values():
        ordered = sorted(intervals)
        for previous, current in pairwise(ordered):
            if previous[1] <= current[0] < previous[2]:
                possible_unlock_overlaps += 1
    events.sort()
    waiting = 0
    occupancy = [0] * slots
    observed = 0.0
    idle_wait = 0.0
    fully_used = 0.0
    occupied_slot_seconds = 0.0
    max_waiting = 0
    max_occupied = 0
    same_slot_overlap = False
    previous = events[0][0]
    for instant, event_type, slot, delta in events:
        elapsed = instant - previous
        active = sum(count > 0 for count in occupancy)
        observed += elapsed
        occupied_slot_seconds += active * elapsed
        if active == slots:
            fully_used += elapsed
        if waiting > 0 and active < slots:
            idle_wait += elapsed
        previous = instant
        if elapsed > 0 and any(count > 1 for count in occupancy):
            same_slot_overlap = True
        if event_type == 0:
            waiting += 1
        elif event_type == 1:
            waiting -= 1
            occupancy[slot] += delta
        else:
            occupancy[slot] += delta
        if waiting < 0 or (slot >= 0 and occupancy[slot] < 0):
            raise ValueError("Unbalanced slot events")
        max_waiting = max(max_waiting, waiting)
        max_occupied = max(max_occupied, sum(count > 0 for count in occupancy))
    if waiting or any(occupancy):
        raise ValueError("Unbalanced slot events")
    return {
        "records": len(records),
        "observed_seconds": observed,
        "wait_seconds": sum(value[0] for value in module_totals.values()),
        "held_seconds": sum(value[1] for value in module_totals.values()),
        "occupied_slot_seconds": occupied_slot_seconds,
        "full_capacity_seconds": fully_used,
        "idle_with_waiters_seconds": idle_wait,
        "max_waiters": max_waiting,
        "max_occupied": max_occupied,
        "same_slot_overlap": same_slot_overlap,
        "possible_unlock_overlaps": possible_unlock_overlaps,
        "unlock_gap_seconds": unlock_gap_seconds,
        "module_workers": {key: sorted(value) for key, value in module_workers.items()},
        "module_pids": {key: len(value) for key, value in module_pids.items()},
        "module_totals": sorted(
            ((label, *times) for label, times in module_totals.items()),
            key=lambda row: row[2], reverse=True,
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directory containing slot-*.jsonl")
    parser.add_argument("--slots", type=int, required=True, help="Configured admission capacity")
    parser.add_argument(
        "--lock-directory", help="Exact lock directory for ambiguous multi-namespace traces",
    )
    args = parser.parse_args(argv)
    try:
        records, extra, other_namespaces = load_slot_records(
            args.directory, slots=args.slots, lock_directory=args.lock_directory,
        )
        summary = summarize_timeline(records, slots=args.slots)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Recorded admissions: {summary['records']} ({extra} above capacity excluded)")
    if records[0].get("lock_directory") is not None:
        print(f"Lock directory: {records[0]['lock_directory']}")
        print(f"Other lock namespaces excluded: {other_namespaces} records")
    else:
        print("Legacy metrics: lock namespaces unknown; overlaps cannot be verified.")
    print(f"Observation span: {summary['observed_seconds']:.2f}s")
    print(f"Waiting: {summary['wait_seconds']:.2f} worker-seconds")
    print(f"Held: {summary['held_seconds']:.2f} worker-seconds")
    print(f"Unique occupied slots: {summary['occupied_slot_seconds']:.2f} slot-seconds")
    print(f"All slots busy: {summary['full_capacity_seconds']:.2f}s")
    print(f"Free slot while requests waited: {summary['idle_with_waiters_seconds']:.2f}s")
    print(f"Peak occupied slots: {summary['max_occupied']}/{args.slots}")
    print(f"Peak queued admission requests: {summary['max_waiters']}")
    if summary["same_slot_overlap"]:
        print("WARNING: same-slot occupancy overlaps beyond unlock timestamp uncertainty.")
    if summary["possible_unlock_overlaps"]:
        print(
            f"Indeterminate overlaps within unlock windows: "
            f"{summary['possible_unlock_overlaps']} (not evidence of lock failure)."
        )
    if summary["unlock_gap_seconds"]:
        print(
            f"Summed unlock timestamp uncertainty: "
            f"{summary['unlock_gap_seconds']:.4f}s."
        )
    print("Longest module holds (waiting / held worker-seconds):")
    for module, wait, held in summary["module_totals"][:8]:
        workers = summary["module_workers"].get(module, [])
        worker_text = ", ".join(workers) if workers else "unavailable"
        pids = summary["module_pids"].get(module, 0)
        print(f"  {wait:9.2f} / {held:9.2f}  {module} "
              f"(workers: {worker_text}; PIDs: {pids})")
    print("Note: timestamps use one host monotonic clock; compare runs separately.")
    print("Slot occupancy uses the conservative release-start bound;")
    print("held time includes unlock latency.")
    print("Completed lock lifetimes only; interrupted holders cannot be reconstructed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
