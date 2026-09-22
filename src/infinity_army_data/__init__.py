"""Tools for importing and normalizing Infinity Army JSON data."""

from os import environ
from pathlib import Path
from subprocess import DEVNULL, PIPE, TimeoutExpired, run

__version__ = "0.6.3"


def _repository_root() -> Path | None:
    for directory in Path(__file__).resolve().parents:
        if (directory / ".git").exists():
            return directory
    return None


def _git_output(repository: Path, *arguments: str) -> str | None:
    try:
        result = run(
            ["git", *arguments],
            cwd=repository,
            stdout=PIPE,
            stderr=DEVNULL,
            text=True,
            check=False,
            timeout=1,
        )
    except (OSError, TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _has_commits_after_version_tag(repository: Path) -> bool:
    """Return whether HEAD is ahead of the current release tag."""
    count = _git_output(repository, "rev-list", "--count", f"v{__version__}..HEAD")
    return count is None or int(count) > 0


def _source_checkout_has_unreleased_changes() -> bool:
    """Return whether the source checkout differs from its release tag."""
    repository = _repository_root()
    if repository is None:
        return False

    status = _git_output(repository, "status", "--porcelain")
    if status is None:
        return False
    if status:
        return True
    return _has_commits_after_version_tag(repository)


def _display_version() -> str:
    configured = environ.get("INFINITY_DB_DISPLAY_VERSION", "").strip()
    if configured:
        return configured
    return f"{__version__}+dev" if _source_checkout_has_unreleased_changes() else __version__


__display_version__ = _display_version()
