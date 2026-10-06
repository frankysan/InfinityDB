"""Parse and render the maintained InfinityDB changelog for browser presentation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from html import escape

from infinity_army_data.project_resources import maintained_documentation_path

_RELEASE_HEADING = re.compile(
    r"^## \[(?P<version>[A-Za-z0-9.-]+)\] - (?P<date>\d{4}-\d{2}-\d{2})$"
)
_INLINE_MARKUP = re.compile(r"`(?P<code>[^`]+)`|\*\*(?P<strong>[^*]+)\*\*")


class ReleaseNotesError(ValueError):
    """Raised when the maintained changelog no longer matches its publication contract."""


@dataclass(frozen=True, slots=True)
class ReleaseNoteSection:
    """One player-summary or detailed section in a release."""

    heading: str
    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReleaseNote:
    """One current or historical release parsed from the canonical changelog."""

    version: str | None
    released_on: date | None
    sections: tuple[ReleaseNoteSection, ...]

    @property
    def label(self) -> str:
        return "Unreleased" if self.version is None else self.version

    @property
    def player_summary(self) -> tuple[str, ...]:
        return self.sections[0].items

    @property
    def detail_sections(self) -> tuple[ReleaseNoteSection, ...]:
        return self.sections[1:]


def parse_release_notes(markdown: str) -> tuple[ReleaseNote, ...]:
    """Parse the release-note subset used by ``docs/CHANGELOG.md``.

    The introductory changelog prose is intentionally not published as release content. Once the
    first ``##`` release heading is reached, fail closed on unsupported structure so a future
    changelog-format change cannot silently disappear from the browser page.
    """

    releases: list[ReleaseNote] = []
    current_version: str | None = None
    current_date: date | None = None
    current_sections: list[ReleaseNoteSection] = []
    current_heading: str | None = None
    current_items: list[str] = []
    started = False

    def flush_section() -> None:
        nonlocal current_heading, current_items
        if current_heading is None:
            return
        if not current_items:
            raise ReleaseNotesError(f"Release-note section {current_heading!r} has no items")
        current_sections.append(ReleaseNoteSection(current_heading, tuple(current_items)))
        current_heading = None
        current_items = []

    def flush_release() -> None:
        nonlocal current_sections
        if not started:
            return
        flush_section()
        if not current_sections:
            raise ReleaseNotesError("Release has no release-note sections")
        if current_sections[0].heading != "Player summary":
            raise ReleaseNotesError("Release must begin with a Player summary section")
        if any(section.heading == "Player summary" for section in current_sections[1:]):
            raise ReleaseNotesError("Release contains more than one Player summary section")
        releases.append(ReleaseNote(current_version, current_date, tuple(current_sections)))
        current_sections = []

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        if line == "## Unreleased":
            flush_release()
            if started:
                raise ReleaseNotesError("Unreleased must be the first release heading")
            started = True
            current_version = None
            current_date = None
            continue

        release_match = _RELEASE_HEADING.fullmatch(line)
        if release_match:
            flush_release()
            started = True
            current_version = release_match.group("version")
            try:
                current_date = date.fromisoformat(release_match.group("date"))
            except ValueError as exc:
                raise ReleaseNotesError(
                    f"Invalid release date on changelog line {line_number}"
                ) from exc
            continue

        if not started:
            continue
        if not line:
            continue
        if line.startswith("### "):
            flush_section()
            current_heading = line.removeprefix("### ").strip()
            if not current_heading:
                raise ReleaseNotesError(
                    f"Empty release-note section heading on changelog line {line_number}"
                )
            continue
        if line.startswith("- "):
            if current_heading is None:
                raise ReleaseNotesError(
                    f"Release-note item has no section on changelog line {line_number}"
                )
            current_items.append(line.removeprefix("- ").strip())
            continue
        if line.startswith("  ") and current_items:
            current_items[-1] = f"{current_items[-1]} {line.strip()}"
            continue
        raise ReleaseNotesError(f"Unsupported changelog structure on line {line_number}: {line!r}")

    flush_release()
    if not releases:
        raise ReleaseNotesError("Changelog contains no release headings")
    return tuple(releases)


def load_release_notes() -> tuple[ReleaseNote, ...]:
    """Load release notes from the canonical source/install changelog resource."""

    path = maintained_documentation_path("CHANGELOG.md")
    return parse_release_notes(path.read_text(encoding="utf-8"))


def _render_inline(text: str) -> str:
    rendered: list[str] = []
    offset = 0
    for match in _INLINE_MARKUP.finditer(text):
        rendered.append(escape(text[offset : match.start()]))
        if match.group("code") is not None:
            rendered.append(f"<code>{escape(match.group('code'))}</code>")
        else:
            rendered.append(f"<strong>{escape(match.group('strong'))}</strong>")
        offset = match.end()
    rendered.append(escape(text[offset:]))
    return "".join(rendered)


def _release_anchor(release: ReleaseNote) -> str:
    if release.version is None:
        return "changes-unreleased"
    return "changes-" + re.sub(r"[^a-z0-9]+", "-", release.version.lower()).strip("-")


def render_release_notes_html(releases: tuple[ReleaseNote, ...]) -> str:
    """Render parsed release notes as escaped, presentation-ready HTML."""

    rendered: list[str] = []
    for release in releases:
        classes = "surface changes-release"
        if release.version is None:
            classes += " changes-release--unreleased"
            date_markup = '<span class="changes-release-date">Next release</span>'
            heading = "Unreleased"
        else:
            assert release.released_on is not None
            date_text = (
                f"{release.released_on:%B} {release.released_on.day}, "
                f"{release.released_on.year}"
            )
            date_markup = (
                f'<time class="changes-release-date" '
                f'datetime="{release.released_on.isoformat()}">{escape(date_text)}</time>'
            )
            heading = f"Version {release.version}"

        summary_items = "".join(
            f"<li>{_render_inline(item)}</li>" for item in release.player_summary
        )
        detail_sections = []
        for section in release.detail_sections:
            items = "".join(f"<li>{_render_inline(item)}</li>" for item in section.items)
            detail_sections.append(
                '<section class="changes-category">'
                f"<h3>{escape(section.heading)}</h3>"
                f"<ul>{items}</ul>"
                "</section>"
            )

        details_markup = ""
        if detail_sections:
            details_markup = (
                '<details class="changes-details">'
                '<summary><span class="changes-details-title">Detailed changes</span>'
                '<span class="changes-details-hint">Full release notes</span>'
                "</summary>"
                f'<div class="changes-details-body">{"".join(detail_sections)}</div>'
                "</details>"
            )

        rendered.append(
            f'<article class="{classes}" id="{_release_anchor(release)}">'
            '<header class="surface-titlebar surface-titlebar--subtle '
            'surface-titlebar--ruled changes-release-header">'
            f"<h2>{escape(heading)}</h2>{date_markup}"
            "</header>"
            '<div class="changes-release-body">'
            '<section class="changes-player-summary">'
            f"<ul>{summary_items}</ul>"
            "</section>"
            f"{details_markup}"
            "</div>"
            "</article>"
        )
    return "".join(rendered)


def render_current_release_notes_html() -> str:
    """Load and render the canonical changelog for the What's changed page."""

    return render_release_notes_html(load_release_notes())
