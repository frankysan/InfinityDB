"""Bound concurrent Chromium acceptance without reducing pytest workers.

A single pytest-xdist run shares the parent of every worker's basetemp.
OS-managed advisory locks free slots even if a worker exits unexpectedly.
This limits browser tests, not ordinary test parallelism or CI capability.
"""

from __future__ import annotations

import errno
import importlib
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

CHROMIUM_SCHEDULING_LANES = {
    # Stable, opt-in xdist groups prevent workers waiting on the two-slot lock.
    "test_verify_unit_skill_presentation_browser": "chromium-a",
    "test_verify_scenario_faq_browser": "chromium-a",
    "test_verify_release_candidate_browser": "chromium-a",
    "test_verify_weapon_source_cards_browser": "chromium-b",
    "test_verify_army_overview_browser": "chromium-b",
    "test_verify_sidebar_density_browser": "chromium-b",
    "test_verify_fireteam_fto_browser": "chromium-b",
    "test_verify_page_footer_browser": "chromium-b",
    "test_verify_deployed_object_publication_browser": "chromium-b",
}


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
    directory: Path, *, slots: int = 2, timeout_seconds: float = 900
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
            try:
                yield index
            finally:
                try:
                    _unlock(handle)
                finally:
                    handle.close()
            return
        if time.monotonic() - start >= timeout_seconds:
            raise TimeoutError(
                f"No Chromium acceptance slot available within {timeout_seconds}s"
            )
        time.sleep(0.1)
