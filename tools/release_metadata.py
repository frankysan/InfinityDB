"""Fail-fast consistency check for finalized InfinityDB releases."""

from __future__ import annotations

import argparse
import re
import tomllib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADING = re.compile(r"^## \[([^\]]+)\] - ([^\n]+)$", re.MULTILINE)
README = re.compile(
    r"^Current release: \*\*([^*]+)\*\* \(([^)]+)\)\.", re.MULTILINE,
)
MODULE_VERSION = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)


def metadata_errors(version: str, module: str, readme: str, changelog: str) -> list[str]:
    problems = []
    if module != version:
        problems.append("package and module versions differ")
    match = HEADING.search(changelog)
    if match is None:
        return problems + ["changelog has no version heading"]
    actual, published = match.groups()
    if actual != version:
        problems.append("latest changelog version differs from package")
    if published == "Unreleased":
        return problems + ["latest release is still Unreleased"]
    try:
        release_date = date.fromisoformat(published)
    except ValueError:
        return problems + ["invalid changelog release date"]
    readme_match = README.search(readme)
    if readme_match is None:
        return problems + ["README has no dated Current release statement"]
    if readme_match.groups() != (version, release_date.isoformat()):
        problems.append("README version/date differs from changelog")
    anchor = f"docs/CHANGELOG.md#{version.replace('.', '')}---{release_date.isoformat()}"
    if anchor not in readme:
        problems.append("README changelog link points to the wrong release")
    return problems


def check_repository(root: Path = ROOT) -> list[str]:
    with (root / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    init = (root / "src/infinity_army_data/__init__.py").read_text(encoding="utf-8")
    module_match = MODULE_VERSION.search(init)
    if module_match is None:
        return ["module version declaration missing"]
    return metadata_errors(
        version,
        module_match.group(1),
        (root / "README.md").read_text(encoding="utf-8"),
        (root / "docs/CHANGELOG.md").read_text(encoding="utf-8"),
    )


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    problems = check_repository()
    for problem in problems:
        print(f"RELEASE METADATA ERROR: {problem}")
    if problems:
        return 1
    print("Release metadata: finalized and consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
