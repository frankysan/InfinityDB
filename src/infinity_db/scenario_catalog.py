"""Compose current scenario publications into player-facing list/detail read models."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.domain_slugs import require_domain_slug, route_slug_from_typed_domain_id
from infinity_db.publication_registry import PublicationRegistry
from infinity_db.rules_database import RulesDatabase
from infinity_db.scenario_geometry import MarkerElement, marker_diameter_mm, parse_scenario_geometry


def _scenario_slug(record: dict[str, Any]) -> str:
    return route_slug_from_typed_domain_id(
        record.get("id"),
        expected_domain="scenario",
        context="curated Scenario id",
    )


def _publication_model(publication: dict[str, Any]) -> dict[str, Any]:
    return {
        "collection_id": publication["collection"],
        "collection_title": publication["collection_title"],
        "revision": publication["revision"],
        "source_collection_id": publication["publication_revision"],
        "source_title": publication["publication_title"],
        "content_sha256": publication["content_sha256"],
        "status": publication["status"],
        "effective_from": publication["effective_from"],
        "authority": publication["authority"],
        "sources": deepcopy(publication["sources"]),
    }


def _mission(record: dict[str, Any]) -> dict[str, Any]:
    facts = record.get("facts")
    mission = facts.get("mission") if isinstance(facts, dict) else None
    if not isinstance(mission, dict):
        raise ValueError(f"Scenario {record.get('id')!r} has no composed mission")
    return mission


def _configurations(record: dict[str, Any]) -> list[dict[str, Any]]:
    facts = record.get("facts")
    configurations = facts.get("configurations") if isinstance(facts, dict) else None
    if not isinstance(configurations, list) or not configurations:
        raise ValueError(f"Scenario {record.get('id')!r} has no composed configurations")
    return configurations


def _supported_army_points(record: dict[str, Any]) -> list[int]:
    game_sizes = _mission(record).get("gameSizes")
    if not isinstance(game_sizes, list) or not game_sizes:
        raise ValueError(f"Scenario {record.get('id')!r} has no game-size rows")
    points: list[int] = []
    for row in game_sizes:
        if not isinstance(row, dict):
            raise ValueError(f"Scenario {record.get('id')!r} has invalid game-size rows")
        point = row.get("armyPoints")
        if type(point) is not int:
            raise ValueError(f"Scenario {record.get('id')!r} has invalid game-size rows")
        points.append(point)
    if len(points) != len(set(points)):
        raise ValueError(f"Scenario {record.get('id')!r} has duplicate game-size rows")
    return points


# Legacy/core-only catalog fallback. The selected three-file runtime resolves
# this external measurement source from the ITS 18 publication registry.
# Core N5.3 pp. 151/153 identify Console A and Supply Box markers but do not
# print their physical diameters; ITS 18 p. 17 is explicit measurement evidence,
# not ownership of the core scenario definitions.
_MARKER_SIZE_CITATION = {
    "source_id": "its-season-18-en-pdf",
    "source_title": "ITS Season 18: Overheat (English)",
    "source_version": "2026.09.01",
    "source_url": "https://experience.corvusbelli.com/en/infinity/its-rules",
    "page": 17,
}
_MARKER_LABELS = {
    "console": "Console A Marker",
    "supply-box": "Supply Box Marker",
}


def _marker_dimensions(
    geometry: dict[str, Any], source_citation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Project marker counts and *physical* footprints from canonical geometry."""
    parsed = parse_scenario_geometry(geometry)
    counts: dict[str, int] = {}
    for element in parsed.elements:
        if isinstance(element, MarkerElement):
            counts[element.marker_type] = counts.get(element.marker_type, 0) + 1
    result: list[dict[str, Any]] = []
    for marker_type, count in counts.items():
        diameter = marker_diameter_mm(marker_type)
        label = _MARKER_LABELS.get(marker_type)
        if diameter is None or label is None:
            raise ValueError(f"Missing reviewed marker dimensions for {marker_type!r}")
        result.append({
            "marker_type": marker_type,
            "name": label,
            "count": count,
            "diameter_mm": diameter,
            "citation": dict(source_citation),
        })
    return result


class ScenarioCatalog:
    """Expose current scenario publications as explicit configuration-aware read models."""

    def __init__(
        self, rules_database: RulesDatabase | None,
        publication_registry: PublicationRegistry | None = None,
    ) -> None:
        self.rules_database = rules_database
        self.publication_registry = publication_registry
        self._records_cache: list[tuple[dict[str, Any], dict[str, Any]]] | None = None

    def _marker_size_source(self) -> dict[str, Any]:
        """Source attribution for shared marker sizes, not mission ownership."""
        if self.publication_registry is not None:
            citation = self.publication_registry.source_citation(
                season_id="its-18", source_id="its-season-18-en-pdf", page=17,
            )
            if citation is not None:
                return citation
            if self.publication_registry.has_season("its-18", "2026.09.01"):
                raise ValueError("Registered ITS 18 marker size source is unavailable")
        # Isolated Rules-only research fixtures (or a future set without ITS 18)
        # retain the pinned external measurement provenance.
        return dict(_MARKER_SIZE_CITATION)

    def _records(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        if self._records_cache is not None:
            return self._records_cache
        if self.rules_database is None:
            self._records_cache = []
            return self._records_cache

        records: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for record in self.rules_database.composed_records_by_kind("scenario"):
            publication = self.rules_database.resolve_scenario_publication(str(record["id"]))
            if publication is None:
                raise ValueError(
                    f"Current Scenario {record['id']!r} has no current publication membership"
                )
            records.append((record, publication))

        if self.publication_registry is not None:
            records.extend(self.publication_registry.scenario_entries())

        seen: set[tuple[str, str, str]] = set()
        for record, publication in records:
            key = (
                str(publication["collection"]), str(publication["revision"]),
                _scenario_slug(record),
            )
            if key in seen:
                raise ValueError(f"Scenario catalog contains duplicate publication {key!r}")
            seen.add(key)

        records.sort(
            key=lambda item: (
                str(item[1]["collection"]),
                int(item[1]["position"]),
                _scenario_slug(item[0]),
            )
        )
        self._records_cache = records
        return records

    def _selected_records(
        self, *, collection: str | None, revision: str | None
    ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Select one exact published set without falling back to Core or another season."""
        if (collection is None) != (revision is None):
            raise ValueError("Scenario collection and revision must be provided together")
        if collection is not None:
            require_domain_slug(collection, context="scenario collection")
        if revision is not None and (
            not isinstance(revision, str) or not revision.strip() or revision != revision.strip()
        ):
            raise ValueError("scenario revision must be a non-empty trimmed string")
        return [
            (record, publication)
            for record, publication in self._records()
            if (
                publication["collection"] == "n5-core"
                if collection is None
                else (
                    publication["collection"] == collection
                    and publication["revision"] == revision
                )
            )
        ]

    def list_collections(self) -> list[dict[str, Any]]:
        """Return only current scenario sets with readable published missions."""
        collections: dict[tuple[str, str], dict[str, Any]] = {}
        for _record, publication in self._records():
            key = (publication["collection"], publication["revision"])
            if key not in collections:
                collections[key] = {
                    "id": key[0],
                    "revision": key[1],
                    "title": publication["collection_title"],
                    "scenario_count": 0,
                }
            collections[key]["scenario_count"] += 1
        return sorted(
            collections.values(),
            key=lambda item: (item["id"] != "n5-core", item["title"], item["revision"]),
        )

    def list_scenarios(
        self, *, collection: str | None = None, revision: str | None = None
    ) -> list[dict[str, Any]]:
        """Return current scenarios; explicit selection never falls back to another set."""

        return [
            {
                "id": _scenario_slug(record),
                "slug": _scenario_slug(record),
                "name": record["name"],
                "description": record["summary"],
                "supported_army_points": _supported_army_points(record),
                "publication": _publication_model(publication),
            }
            for record, publication in self._selected_records(
                collection=collection, revision=revision
            )
        ]

    def get_scenario(
        self, slug: str, *, army_points: int,
        collection: str | None = None, revision: str | None = None,
    ) -> dict[str, Any] | None:
        """Return one current scenario projected to one exact supported Army Points value."""

        rules_database = self.rules_database
        if rules_database is None:
            return None

        selected: tuple[dict[str, Any], dict[str, Any]] | None = None
        for record, publication in self._selected_records(
            collection=collection, revision=revision
        ):
            if _scenario_slug(record) == slug:
                selected = (record, publication)
                break
        if selected is None:
            return None
        if type(army_points) is not int or army_points <= 0:
            raise ValueError("scenario army_points must be a positive integer")

        record, publication = selected
        supported = _supported_army_points(record)
        if army_points not in supported:
            raise ValueError(
                f"Scenario {record['id']!r} does not support {army_points} Army Points; "
                f"supported values: {supported}"
            )

        mission = _mission(record)
        game_size_rows = [
            row
            for row in mission["gameSizes"]
            if isinstance(row, dict) and row.get("armyPoints") == army_points
        ]
        if len(game_size_rows) != 1:
            raise ValueError(
                f"Scenario {record['id']!r} does not have exactly one game-size row for "
                f"{army_points} Army Points"
            )
        game_size = deepcopy(game_size_rows[0])
        configuration_id = game_size.get("configurationId")

        configurations = [
            configuration
            for configuration in _configurations(record)
            if isinstance(configuration, dict) and configuration.get("id") == configuration_id
        ]
        if len(configurations) != 1:
            raise ValueError(
                f"Scenario {record['id']!r} does not have exactly one configuration "
                f"{configuration_id!r}"
            )
        configuration = configurations[0]
        configuration_points = configuration.get("armyPoints")
        if not isinstance(configuration_points, list) or army_points not in configuration_points:
            raise ValueError(
                f"Scenario {record['id']!r} configuration {configuration_id!r} does not cover "
                f"{army_points} Army Points"
            )

        objectives: list[dict[str, Any]] = []
        for objective in mission["objectives"]:
            item = deepcopy(objective)
            item["awards"] = [
                deepcopy(award)
                for award in objective["awards"]
                if army_points in award["armyPoints"]
            ]
            for award in item["awards"]:
                award["armyPoints"] = [army_points]
            if item["awards"]:
                objectives.append(item)

        reference = (
            self.publication_registry.scenario_reference(record)
            if self.publication_registry is not None
            and publication["collection"] != "n5-core"
            else rules_database.scenario_reference(str(record["id"]))
        )
        if reference is None:
            raise ValueError(f"Scenario {record['id']!r} has no composed rules reference")
        rules_by_id = {str(rule["id"]): rule for rule in reference["rules"]}
        special_rules: list[dict[str, Any]] = []
        for inclusion in mission["rules"]:
            item = deepcopy(inclusion)
            definition_id = item.get("definitionId")
            if definition_id is not None:
                rule = rules_by_id.get(str(definition_id))
                if rule is None:
                    raise ValueError(
                        f"Scenario {record['id']!r} is missing composed Rule {definition_id!r}"
                    )
                item["rule"] = deepcopy(rule)
            special_rules.append(item)

        source_issues = [
            deepcopy(issue)
            for issue in mission["sourceIssues"]
            if army_points in issue["armyPoints"]
        ]

        return {
            "id": slug,
            "slug": slug,
            "name": record["name"],
            "description": record["summary"],
            "supported_army_points": supported,
            "selected_army_points": army_points,
            "publication": _publication_model(publication),
            "setup": {
                "sides": deepcopy(mission["sides"]),
                "game_size": game_size,
            },
            "placement": {
                "configuration_id": configuration_id,
                "configuration_army_points": deepcopy(configuration_points),
                "geometry": deepcopy(configuration["geometry"]),
                "marker_dimensions": _marker_dimensions(
                    configuration["geometry"], self._marker_size_source(),
                ),
            },
            "objectives": objectives,
            "special_rules": special_rules,
            "skills": deepcopy(reference["skills"]),
            "end_conditions": deepcopy(mission["endConditions"]),
            "source_issues": source_issues,
            "citations": deepcopy(record["citations"]),
        }
