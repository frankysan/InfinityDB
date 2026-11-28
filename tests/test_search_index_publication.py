"""Search projection parity against the canonical runtime catalog."""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from statistics import median
from time import perf_counter

import pytest

from infinity_db.catalog_projection import CatalogProjection
from infinity_db.database.repository import accent_insensitive_key
from infinity_db.database_set import SEASON_DATABASE_SOURCES
from infinity_db.rules_database import RulesDatabase
from infinity_db.search_catalog import rank_results
from infinity_db.search_index_storage import query_search_index, stage_search_index
from infinity_db.web.app import create_app

RELEASE = Path("data/generated")
SEASONS = {
    season: RELEASE / filename for season, (filename, _) in SEASON_DATABASE_SOURCES.items()
}


def test_search_projection_pilot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(
        RELEASE / "army.db", RELEASE / "rules_n5.db", season_databases=SEASONS,
    )
    catalog = app.api.search_catalog
    assert catalog.published_search is not None
    with monkeypatch.context() as context:
        context.setattr(CatalogProjection, "select", lambda path: None)
        legacy = create_app(
            RELEASE / "army.db", RELEASE / "rules_n5.db", season_databases=SEASONS,
        ).api.search_catalog
    path = tmp_path / "search.db"
    started = perf_counter()
    entries = list(legacy.entries())
    with closing(sqlite3.connect(path)) as db, db:
        stage_search_index(db, entries)
    build_seconds = perf_counter() - started

    # Compare every systematically selected term and substring to Python
    # matching, including collisions and stable ordering.
    terms = sorted({term for _, keys in entries for term in keys})
    assert len(entries) > 1000
    assert len(terms) > 1000
    generated = {term for term in terms[::7]}
    generated.update(term[len(term)//3:len(term)//3 + 4] for term in terms[::7])
    queries = [
        "mimetism", "activate console", "Dragões", "dragoes", "combi rifle",
        "spec-ops", "PanOceania", "breaker", "hacker", "casevac", "civevac",
        "armour", "martial arts", "MSV", "msv", "a", "!!!", "", "no-such-result-987654",
    ]
    legacy_times, indexed_times = [], []
    with (
        closing(sqlite3.connect(path)) as db,
        closing(sqlite3.connect(RELEASE / "rules_n5.db")) as published_db,
    ):
        for table, order in (
            ("search_index", "position"),
            ("search_index_terms", "position, term"),
        ):
            sql = f"SELECT * FROM {table} ORDER BY {order}"
            assert db.execute(sql).fetchall() == published_db.execute(sql).fetchall()
        for query in sorted(generated):
            needle = accent_insensitive_key(query)
            expected = rank_results([
                result for result, keys in entries if any(needle in key for key in keys)
            ], needle)
            assert query_search_index(published_db, query) == expected, query
        for query in queries + terms[::max(1, len(terms)//12)]:
            started = perf_counter()
            expected = legacy.search_composed(query)
            legacy_times.append(perf_counter() - started)
            started = perf_counter()
            actual = query_search_index(db, query)
            indexed_times.append(perf_counter() - started)
            assert actual == expected == catalog.search(query), query
    print(
        f"Search pilot: {len(entries)} entries; {len(terms)} distinct terms; "
        f"{len(generated)} systematic queries; {path.stat().st_size} bytes; "
        f"{build_seconds:.3f}s build; warm medians "
        f"{median(legacy_times)*1000:.2f}ms legacy / {median(indexed_times)*1000:.2f}ms indexed"
    )


@pytest.mark.parametrize(
    "mutation", ["DELETE FROM search_index_terms", "UPDATE search_index SET result='{}'"],
)
def test_damaged_search_projection_fails_closed(tmp_path: Path, mutation: str) -> None:
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(RELEASE / "rules_n5.db", path)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(mutation)
    with pytest.raises(ValueError, match="global search publication"):
        RulesDatabase(path).validate()


def test_explicit_partial_season_scope_uses_legacy_composer() -> None:
    app = create_app(
        RELEASE / "army.db", RELEASE / "rules_n5.db",
        season_databases={"its-18": SEASONS["its-18"]},
    )
    catalog = app.api.search_catalog
    assert catalog.published_search is None
    assert catalog.search("activate console") == catalog.search_composed("activate console")
