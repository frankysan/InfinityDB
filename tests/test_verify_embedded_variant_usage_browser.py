"""Reuse the exact-occurrence browser journey without a variant-usage sidecar."""

from __future__ import annotations

import pytest
from test_variant_usage_storage import embedded as embedded
from test_verify_variant_usage_publication_browser import (
    test_variant_usage_developer_browser_matches_real_source_groups as _verify_browser,
)

from infinity_db.web import create_app


@pytest.mark.parametrize("catalog", ("skills", "equipment"))
@pytest.mark.parametrize("width", (1440, 390, 320))
def test_embedded_exact_occurrences_preserve_browser_journey(
    embedded, catalog: str, width: int,
) -> None:
    directory, publication = embedded
    app = create_app(directory / "infinity.db", rules_database_path=directory / "rules.db")
    _verify_browser({"app": app, "publication": publication}, catalog, width)
