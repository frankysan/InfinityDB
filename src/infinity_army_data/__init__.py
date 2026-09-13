"""Tools for importing and normalizing Infinity Army JSON data."""

from pathlib import Path
from subprocess import DEVNULL, PIPE, TimeoutExpired, run

__version__ = "0.3.0"


def _working_tree_has_changes() -> bool:
    """Return whether this source checkout has unreleased changes."""
    for directory in Path(__file__).resolve().parents:
        if (directory / ".git").exists():
            try:
                status = run(
                    ["git", "status", "--porcelain"],
                    cwd=directory,
                    stdout=PIPE,
                    stderr=DEVNULL,
                    text=True,
                    check=False,
                    timeout=1,
                )
            except (OSError, TimeoutExpired):
                return False
            return status.returncode == 0 and bool(status.stdout.strip())
    return False


def _display_version() -> str:
    return f"{__version__}+dev" if _working_tree_has_changes() else __version__


__display_version__ = _display_version()
