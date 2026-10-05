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
    assert [section.heading for section in releases[0].sections] == ["Added", "Changed", "Fixed"]
    assert releases[0].sections[0].items[0].startswith(
        "**Web frontend + Project infrastructure:** Add a Changes page"
    )

    release_091 = next(release for release in releases if release.version == "0.9.1")
    assert release_091.released_on == date(2026, 9, 30)
    assert [section.heading for section in release_091.sections] == [
        "Changed",
        "Fixed",
        "Upgrade notes",
    ]


def test_release_notes_renderer_escapes_text_and_preserves_supported_inline_markup() -> None:
    releases = parse_release_notes(
        """# Changelog

## Unreleased

### Added

- **Web frontend:** Render `safe-code` and escape <script>alert(1)</script>.

## [1.2.3] - 2026-10-05

### Fixed

- Historical note.
"""
    )

    rendered = render_release_notes_html(releases)

    assert '<article class="surface changes-release changes-release--unreleased"' in rendered
    assert "<strong>Web frontend:</strong>" in rendered
    assert "<code>safe-code</code>" in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "<script>alert(1)</script>" not in rendered
    assert 'datetime="2026-10-05">October 5, 2026</time>' in rendered


def test_release_notes_parser_rejects_unsupported_structure_inside_a_release() -> None:
    with pytest.raises(ReleaseNotesError, match="Unsupported changelog structure"):
        parse_release_notes(
            """# Changelog

## Unreleased

This paragraph would otherwise disappear from the browser page.
"""
        )
