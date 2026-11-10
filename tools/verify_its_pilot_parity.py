"""P3.3 acceptance: ITS-owned Battleground versus the currently served Rules publication.

Uses the same ScenarioCatalog and deterministic SVG renderer on both inputs.
The ITS adapter below is diagnostic only; runtime registration belongs to P3.4.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from infinity_db.database import Database
from infinity_db.its_season_database import build_its_database, select_its_scenario
from infinity_db.rules_database import RulesDatabase
from infinity_db.scenario_catalog import ScenarioCatalog
from infinity_db.scenario_geometry import parse_scenario_geometry
from infinity_db.scenario_map_svg import render_scenario_map_svg
from infinity_db.web import create_app_from_database_set
from infinity_db.web.api_handler import _enrich_scenario_api_item
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/curated/rules/n5-its-season-18-2026.09.01.json"
DATABASE_SET = ROOT / "data/generated"
SEASON = "its-18"
REVISION = "2026.09.01"
SCENARIO = "scenario:battleground"
POINTS = (150, 200, 250, 300, 350, 400)
ORIGIN = "http://its-pilot-parity.test"


class _StandalonePilotSource:
    """Narrow diagnostic adapter to exercise the unchanged ScenarioCatalog.

    Rejects external scenario rules rather than silently reading the legacy
    rules copy; future cross-DB rule resolution is explicitly P3.4 work.
    """

    def __init__(self, item: dict[str, Any]):
        self.record = deepcopy(item["record"])
        published = item["publication"]
        sources = {source["id"]: source for source in published["sources"]}
        self.record["citations"] = [
            {
                "source_id": citation["sourceId"],
                "source_title": sources[citation["sourceId"]]["title"],
                "source_version": sources[citation["sourceId"]]["version"],
                "source_url": sources[citation["sourceId"]].get("url"),
                "page": citation.get("page"),
                "member": citation.get("member"),
                "heading": citation.get("heading"),
                "section": citation.get("section"),
            }
            for citation in self.record["citations"]
        ]
        if self.record["id"] != SCENARIO:
            raise ValueError("Selected ITS record is not the Battleground pilot")
        mission = self.record["facts"]["mission"]
        if any(rule.get("definitionId") for rule in mission["rules"]) or mission.get("skills"):
            raise ValueError("ITS pilot now requires cross-domain rule resolution")
        self.publication = {
            "scenario_id": self.record["id"],
            "name": self.record["name"],
            "collection": published["collectionId"],
            "collection_title": published["title"],
            "revision": published["revision"],
            "position": published["position"],
            "publication_revision": published["sourceCollectionId"],
            "publication_title": published["sourceCollectionTitle"],
            "content_sha256": published["contentSha256"],
            "status": published["status"],
            "effective_from": published["effectiveFrom"],
            "authority": published["authority"],
            "sources": [
                {
                    "id": source["id"],
                    "kind": source["kind"],
                    "title": source["title"],
                    "version": source["version"],
                    "published_date": source.get("publishedDate"),
                    "retrieved_date": source.get("retrievedDate"),
                    "language": source.get("language"),
                    "authority": source["authority"],
                }
                for source in published["sources"]
            ],
        }

    def composed_records_by_kind(self, kind: str) -> list[dict[str, Any]]:
        return [self.record] if kind == "scenario" else []

    def resolve_scenario_publication(self, reference: str) -> dict[str, Any] | None:
        return self.publication if reference == self.record["id"] else None

    def scenario_reference(self, reference: str) -> dict[str, Any] | None:
        if reference != self.record["id"]:
            return None
        return {"scenario": self.record, "rules": [], "skills": []}


def verify_pilot(
    *,
    source: Path = SOURCE,
    database_set: Path = DATABASE_SET,
) -> dict[str, Any]:
    """Compare full scenario HTTP JSON, all geometry and map SVG bytes."""
    source, database_set = source.resolve(), database_set.resolve()
    root = ROOT / "local"
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="its-p33-", dir=root) as directory:
        output = Path(directory) / "its_18.db"
        built = build_its_database(source, output)
        season = select_its_scenario(
            output, season_id=SEASON, revision=REVISION, scenario_id=SCENARIO,
        )
        if season is None:
            raise ValueError("Built ITS publication does not contain Battleground")
        old_database = RulesDatabase(database_set / "rules_n5.db")
        old_record = old_database.composed_record(SCENARIO)
        if old_record is None:
            raise ValueError("Current Rules publication has no Battleground baseline")
        for key in ("id", "kind", "name", "summary", "facts"):
            if old_record[key] != season["record"][key]:
                raise ValueError(f"ITS record differs from current Rules baseline: {key}")
        legacy = ScenarioCatalog(old_database)
        # Exercise ScenarioCatalog unchanged with an ITS-owned record. The
        # explicit diagnostic adapter is not a production multi-DB resolver.
        adapter = _StandalonePilotSource(season)
        if old_record["citations"] != adapter.record["citations"]:
            raise ValueError("ITS citations differ from current Rules baseline")
        standalone = ScenarioCatalog(cast(RulesDatabase, cast(object, adapter)))
        if legacy.list_scenarios(collection=SEASON, revision=REVISION) != (
            standalone.list_scenarios(collection=SEASON, revision=REVISION)
        ):
            raise ValueError("ITS scenario list differs from current Rules baseline")
        if standalone.list_scenarios() != []:
            raise ValueError("Standalone ITS scenario leaked into default core selection")
        app = create_app_from_database_set(database_set)
        army_database = Database(database_set / "army.db")
        geometry_count = 0
        svg_count = 0
        for points in POINTS:
            path = (
                f"/api/scenarios/battleground?army_points={points}"
                f"&collection={SEASON}&revision={REVISION}"
            )
            legacy_detail = legacy.get_scenario(
                "battleground", army_points=points, collection=SEASON, revision=REVISION,
            )
            candidate_detail = standalone.get_scenario(
                "battleground", army_points=points, collection=SEASON, revision=REVISION,
            )
            if (
                legacy_detail is None or candidate_detail is None
                or candidate_detail != legacy_detail
            ):
                raise ValueError(f"ITS projection differs for {points} points")
            status, _, body = wsgi_response(app, ORIGIN + path)
            enriched_candidate = _enrich_scenario_api_item(
                army_database, old_database, candidate_detail,
            )
            if status != 200 or json.loads(body) != enriched_candidate:
                raise ValueError(f"ITS HTTP JSON differs for {points} points")
            geometry_count += 1
            for theme in ("light", "dark"):
                for unit in ("in", "cm"):
                    svg_path = (
                        "/api/scenarios/battleground/map.svg?"
                        f"army_points={points}&collection={SEASON}&revision={REVISION}"
                        f"&theme={theme}&distance_unit={unit}"
                    )
                    geometry = parse_scenario_geometry(candidate_detail["placement"]["geometry"])
                    svg = render_scenario_map_svg(
                        geometry, distance_unit=unit, theme=theme,
                    ).encode("utf-8")
                    status, _, body = wsgi_response(app, ORIGIN + svg_path)
                    if status != 200 or body != svg:
                        raise ValueError(
                            f"ITS SVG bytes differ for {points} points, {theme}, {unit}"
                        )
                    svg_count += 1
        return {
            "result": "PASS",
            "season": f"{SEASON}@{REVISION}",
            "sourceCollection": season["publication"]["sourceCollectionId"],
            "publicationSha256": season["publication"]["contentSha256"],
            "databaseSha256": built["sha256"],
            "apiJsonComparisons": geometry_count,
            "svgByteComparisons": svg_count,
            "sourceCitations": len(season["record"]["citations"]),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--db-dir", type=Path, default=DATABASE_SET)
    args = parser.parse_args(argv)
    try:
        result = verify_pilot(source=args.source, database_set=args.db_dir)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"P3.3 parity FAIL: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
