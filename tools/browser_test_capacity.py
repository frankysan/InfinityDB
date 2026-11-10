"""Bound concurrent Chromium acceptance without reducing pytest workers.

A single pytest-xdist run shares the parent of every worker's basetemp.
OS-managed advisory locks free slots even if a worker exits unexpectedly.
This limits browser tests, not ordinary test parallelism or CI capability.
"""

from __future__ import annotations

import errno
import hashlib
import importlib
import json
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

from tools.resource_waits import record_resource_wait

CHROMIUM_SCHEDULING_LANES = {
    # Stable, opt-in xdist groups prevent workers waiting on the two-slot lock.
    "test_verify_unit_skill_presentation_browser": "chromium-a",
    "test_verify_scenario_faq_browser": "chromium-a",
    "test_verify_fireteam_context_browser": "chromium-a",
    "test_verify_contextual_state_fireteam_browser": "chromium-a",
    "test_verify_release_candidate_browser": "chromium-a",
    "test_verify_orders_aros_browser": "chromium-a",
    "test_verify_aro_deployment_browser": "chromium-a",
    "test_verify_movement_browser": "chromium-a",
    "test_combat_attack_reference": "chromium-a",
    "test_hacking_source_followup": "chromium-a",
    "test_verify_turn_sequence_browser": "chromium-a",
    "test_verify_accessible_navigation_browser": "chromium-a",
    "test_verify_immunity_plasma_browser": "chromium-b",
    "test_verify_ammunition_publication_browser": "chromium-b",
    "test_template_reference": "chromium-b",
    "test_verify_weapon_source_cards_browser": "chromium-b",
    "test_verify_army_overview_browser": "chromium-b",
    "test_verify_reinforcements_optional_browser": "chromium-b",
    "test_verify_sidebar_density_browser": "chromium-b",
    "test_verify_fireteam_fto_browser": "chromium-b",
    "test_verify_page_footer_browser": "chromium-b",
    "test_reference_player_errors_browser": "chromium-b",
    "test_verify_deployed_object_publication_browser": "chromium-b",
    "test_verify_variant_usage_publication_browser": "chromium-b",
    "test_verify_embedded_variant_usage_browser": "chromium-b",
}


# Experimental splits retain the original two-lane assignments as the default.
# Rebalance them against measured per-module execution before choosing a new default.
_EXTRA_BROWSER_LANES: dict[int, tuple[tuple[str, ...], ...]] = {
    3: (
        ("test_verify_scenario_faq_browser", "test_verify_release_candidate_browser",
         "test_verify_accessible_navigation_browser",
         "test_verify_orders_aros_browser", "test_verify_aro_deployment_browser",
         "test_verify_turn_sequence_browser", "test_verify_movement_browser",
         "test_combat_attack_reference"),
        ("test_verify_weapon_source_cards_browser", "test_verify_army_overview_browser",
         "test_verify_fireteam_fto_browser", "test_verify_deployed_object_publication_browser",
         "test_verify_reinforcements_optional_browser", "test_template_reference",
         "test_verify_variant_usage_publication_browser",
         "test_verify_embedded_variant_usage_browser"),
        ("test_verify_unit_skill_presentation_browser", "test_verify_fireteam_context_browser",
         "test_verify_immunity_plasma_browser", "test_verify_ammunition_publication_browser",
         "test_verify_sidebar_density_browser", "test_verify_page_footer_browser",
         "test_reference_player_errors_browser", "test_hacking_source_followup",
         "test_verify_contextual_state_fireteam_browser"),
    ),
    4: (
        ("test_verify_scenario_faq_browser", "test_verify_release_candidate_browser"),
        ("test_verify_weapon_source_cards_browser", "test_verify_ammunition_publication_browser",
         "test_verify_sidebar_density_browser", "test_template_reference"),
        ("test_verify_unit_skill_presentation_browser", "test_verify_orders_aros_browser",
         "test_verify_accessible_navigation_browser",
         "test_verify_aro_deployment_browser", "test_verify_turn_sequence_browser",
         "test_verify_movement_browser",
         "test_verify_fireteam_context_browser", "test_combat_attack_reference",
         "test_verify_contextual_state_fireteam_browser"),
        ("test_verify_army_overview_browser", "test_verify_fireteam_fto_browser",
         "test_verify_reinforcements_optional_browser",
         "test_verify_deployed_object_publication_browser", "test_verify_immunity_plasma_browser",
         "test_verify_page_footer_browser", "test_reference_player_errors_browser",
         "test_hacking_source_followup", "test_verify_variant_usage_publication_browser",
         "test_verify_embedded_variant_usage_browser"),
    ),
}


def browser_lane_groups(count: int = 2) -> dict[str, str]:
    """Return deterministic module-to-group assignments for a configured lane count."""
    if count == 2:
        return dict(CHROMIUM_SCHEDULING_LANES)
    if count not in _EXTRA_BROWSER_LANES:
        raise ValueError("Browser lane count must be 2, 3 or 4")
    groups = {
        module: f"chromium-{chr(ord('a') + index)}"
        for index, modules in enumerate(_EXTRA_BROWSER_LANES[count])
        for module in modules
    }
    if set(groups) != set(CHROMIUM_SCHEDULING_LANES):
        raise ValueError("Experimental Chromium lane registry is incomplete")
    return groups


def scenario_faq_split_lane(nodeid: str) -> str:
    """Divide Scenario FAQ cases deterministically across lanes A and D.

    This is only used by the opt-in four-lane benchmark. Each worker
    retains its own module-scoped Chromium and WSGI fixtures.
    """
    partition = hashlib.sha256(nodeid.encode("utf-8")).digest()[0] & 1
    return ("chromium-a", "chromium-d")[partition]


def _lock(handle: BinaryIO) -> bool:
    if os.name == "nt":
        msvcrt = importlib.import_module("msvcrt")

        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                return False
            raise
    else:
        fcntl = importlib.import_module("fcntl")

        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                return False
            raise
    return True


def _unlock(handle: BinaryIO) -> None:
    if os.name == "nt":
        msvcrt = importlib.import_module("msvcrt")

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl = importlib.import_module("fcntl")

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def browser_slot(
    directory: Path, *, slots: int = 2, timeout_seconds: float = 900,
    label: str = "",
) -> Iterator[int]:
    """Admit at most the specified browser cases across workers in one test run."""
    if slots < 1 or timeout_seconds < 0:
        raise ValueError("Browser slots and timeout must be positive")
    directory.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    while True:
        for index in range(slots):
            handle = (directory / f"chromium-{index}.lock").open("a+b")
            try:
                acquired = _lock(handle)
            except BaseException:
                handle.close()
                raise
            if not acquired:
                handle.close()
                continue
            acquired_at = time.monotonic()
            record_resource_wait("chromium", acquired_at - start)
            try:
                yield index
            finally:
                release_started_at = time.monotonic()
                try:
                    _unlock(handle)
                    released_at = time.monotonic()
                finally:
                    handle.close()
                metrics_path = os.environ.get("INFINITYDB_BROWSER_METRICS_DIRECTORY")
                if metrics_path:
                    metrics_dir = Path(metrics_path)
                    metrics_dir.mkdir(parents=True, exist_ok=True)
                    record = {
                        "pid": os.getpid(), "label": label, "slot": index,
                        "worker": os.environ.get("PYTEST_XDIST_WORKER", "main"),
                        "lock_directory": str(directory.resolve()),
                        "wait_seconds": acquired_at - start,
                        "hold_seconds": released_at - acquired_at,
                        "request_monotonic_seconds": start,
                        "acquired_monotonic_seconds": acquired_at,
                        "release_started_monotonic_seconds": release_started_at,
                        "released_monotonic_seconds": released_at,
                    }
                    with (metrics_dir / f"slot-{os.getpid()}.jsonl").open(
                        "a", encoding="utf-8"
                    ) as output:
                        output.write(json.dumps(record, sort_keys=True) + "\n")
            return
        if time.monotonic() - start >= timeout_seconds:
            record_resource_wait("chromium", time.monotonic() - start)
            raise TimeoutError(
                f"No Chromium acceptance slot available within {timeout_seconds}s"
            )
        time.sleep(0.1)
