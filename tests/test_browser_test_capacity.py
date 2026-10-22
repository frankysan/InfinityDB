"""Cross-process browser admission is bounded and releases on exit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tools.browser_test_capacity import browser_slot


def test_browser_slots_reject_invalid_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Browser slots"):
        with browser_slot(tmp_path, slots=0):
            pass
    with pytest.raises(ValueError, match="Browser slots"):
        with browser_slot(tmp_path, timeout_seconds=-1):
            pass


def test_browser_slot_is_exclusive_across_processes_and_reusable(tmp_path: Path) -> None:
    # Subprocesses use a separate OS lock owner (also on Windows, where the
    # multiprocessing start method differs from POSIX).
    probe = (
        "import sys\n"
        "from pathlib import Path\n"
        "from tools.browser_test_capacity import browser_slot\n"
        "try:\n"
        "    with browser_slot(Path(sys.argv[1]), slots=1, timeout_seconds=0.2):\n"
        "        pass\n"
        "except TimeoutError:\n"
        "    sys.exit(17)\n"
    )
    command = [sys.executable, "-c", probe, str(tmp_path)]
    with browser_slot(tmp_path, slots=1):
        blocked = subprocess.run(command, capture_output=True, text=True, timeout=10)
        assert blocked.returncode == 17, blocked.stderr
    released = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert released.returncode == 0, released.stderr


def test_browser_slots_admit_distinct_slots(tmp_path: Path) -> None:
    with browser_slot(tmp_path, slots=2) as first:
        with browser_slot(tmp_path, slots=2) as second:
            assert {first, second} == {0, 1}
