from __future__ import annotations

from datetime import date

import pytest

from infinity_db.web.release_notes import (
    ReleaseNotesError,
    load_release_notes,
    parse_release_notes,
    render_release_notes_html,
)


def test_checked_in_changelog_parses_current_and_historical_releases() -> None:
    releases = load_release_notes()

    assert releases[0].version is None
    assert releases[0].released_on is None
    assert releases[0].sections[0].heading == "Player summary"
    assert any("What's changed" in item for item in releases[0].player_summary)
    assert [section.heading for section in releases[0].detail_sections] == [
        "Added",
        "Changed",
        "Fixed",
    ]
    assert all(release.sections[0].heading == "Player summary" for release in releases)

    release_091 = next(release for release in releases if release.version == "0.9.1")
    assert release_091.released_on == date(2026, 9, 30)
    assert [section.heading for section in release_091.detail_sections] == [
        "Changed",
        "Fixed",
        "Upgrade notes",
    ]


def test_release_notes_renderer_escapes_text_and_preserves_supported_inline_markup() -> None:
    releases = parse_release_notes(
        """# Changelog

## Unreleased

### Player summary

- Render `safe-code` and escape <script>alert(1)</script>.

### Added

- **Web frontend:** Detailed note.

## [1.2.3] - 2026-10-05

### Player summary

- Historical summary.

### Fixed

- Historical note.
"""
    )

    rendered = render_release_notes_html(releases)

    assert '<article class="surface changes-release changes-release--unreleased"' in rendered
    assert '<section class="changes-player-summary">' in rendered
    assert "<h3>For players</h3>" not in rendered
    assert "<code>safe-code</code>" in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "<script>alert(1)</script>" not in rendered
    assert '<details class="changes-details">' in rendered
    assert "<strong>Web frontend:</strong> Detailed note." in rendered
    assert 'datetime="2026-10-05">October 5, 2026</time>' in rendered


def test_release_notes_parser_requires_player_summary_first() -> None:
    with pytest.raises(ReleaseNotesError, match="must begin with a Player summary"):
        parse_release_notes(
            """# Changelog

## Unreleased

### Added

- Detailed note.
"""
        )


def test_release_notes_parser_rejects_unsupported_structure_inside_a_release() -> None:
    with pytest.raises(ReleaseNotesError, match="Unsupported changelog structure"):
        parse_release_notes(
            """# Changelog

## Unreleased

### Player summary

- Visible summary.

This paragraph would otherwise disappear from the browser page.
"""
        )
