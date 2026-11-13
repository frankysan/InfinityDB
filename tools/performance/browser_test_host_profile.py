"""Host-local, opt-in Chromium test defaults; never committed or shipped.

The Linux worker's profile lives under ignored local/ and only changes the
maintained run_checks test stage. Windows and clean CI retain two slots.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROFILE_NAME = "linux-four-browser-slots"
PROFILE_FILENAME = "local/browser-test-profile.json"
ROOT = Path(__file__).resolve().parents[2]


def profile_path(root: Path = ROOT) -> Path:
    return root / PROFILE_FILENAME


def linux_four_slots_enabled(
    root: Path = ROOT, *, platform: str | None = None,
) -> bool:
    """Read only this explicit host-local profile. Unknown data fails closed."""
    platform = sys.platform if platform is None else platform
    if not platform.startswith("linux"):
        return False
    path = profile_path(root)
    if not path.exists() and not path.is_symlink():
        return False
    if path.is_symlink() or not path.is_file():
        raise ValueError("Browser test host profile must be a regular local file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Browser test host profile is unreadable or invalid") from exc
    if data != {"profile": PROFILE_NAME}:
        raise ValueError("Unknown browser test host profile; expected linux-four-browser-slots")
    return True


def set_linux_four_slots(
    enabled: bool, root: Path = ROOT, *, platform: str | None = None,
) -> None:
    """Opt in or revert on a Linux test worker; write only ignored local/."""
    platform = sys.platform if platform is None else platform
    if not platform.startswith("linux"):
        raise ValueError("Linux four-slot profile cannot be configured on this host")
    path = profile_path(root)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Browser test host profile must be a regular local file")
    if enabled:
        if path.exists():
            linux_four_slots_enabled(root, platform=platform)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"profile": PROFILE_NAME}, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
    elif path.exists():
        linux_four_slots_enabled(root, platform=platform)
        path.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("status", "enable", "disable"),
        help="Inspect, opt in, or revert the Linux-only test profile",
    )
    args = parser.parse_args(argv)
    if args.action == "enable":
        set_linux_four_slots(True)
    elif args.action == "disable":
        set_linux_four_slots(False)
    status = linux_four_slots_enabled()
    print(
        f"Browser test host profile: {'linux-four-browser-slots' if status else 'standard'}"
        " (Windows and clean CI: 2 slots)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
