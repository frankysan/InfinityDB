"""Compose current scenario publications into player-facing list/detail read models."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.domain_slugs import route_slug_from_typed_domain_id
from infinity_db.rules_database import RulesDatabase


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


class ScenarioCatalog:
    """Expose current scenario publications as explicit configuration-aware read models."""

    def __init__(self, rules_database: RulesDatabase | None) -> None:
        self.rules_database = rules_database
        self._records_cache: list[tuple[dict[str, Any], dict[str, Any]]] | None = None

    def _records(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        if self._records_cache is not None:
            return self._records_cache
        if self.rules_database is None:
            self._records_cache = []
            return self._records_cache

        records: list[tuple[dict[str, Any], dict[str, Any]]] = []
        seen_slugs: set[str] = set()
        for record in self.rules_database.composed_records_by_kind("scenario"):
            slug = _scenario_slug(record)
            if slug in seen_slugs:
                raise ValueError(f"Scenario catalog contains duplicate route slug {slug!r}")
            seen_slugs.add(slug)
            publication = self.rules_database.resolve_scenario_publication(str(record["id"]))
            if publication is None:
                raise ValueError(
                    f"Current Scenario {record['id']!r} has no current publication membership"
                )
            records.append((record, publication))

        records.sort(
            key=lambda item: (
                str(item[1]["collection"]),
                int(item[1]["position"]),
                _scenario_slug(item[0]),
            )
        )
        self._records_cache = records
        return records

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return current scenario identities in maintained collection order."""

        return [
            {
                "id": _scenario_slug(record),
                "slug": _scenario_slug(record),
                "name": record["name"],
                "description": record["summary"],
                "supported_army_points": _supported_army_points(record),
                "publication": _publication_model(publication),
            }
            for record, publication in self._records()
        ]

    def get_scenario(self, slug: str, *, army_points: int) -> dict[str, Any] | None:
        """Return one current scenario projected to one exact supported Army Points value."""

        rules_database = self.rules_database
        if rules_database is None:
            return None

        selected: tuple[dict[str, Any], dict[str, Any]] | None = None
        for record, publication in self._records():
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

        reference = rules_database.scenario_reference(str(record["id"]))
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
            },
            "objectives": objectives,
            "special_rules": special_rules,
            "skills": deepcopy(reference["skills"]),
            "end_conditions": deepcopy(mission["endConditions"]),
            "source_issues": source_issues,
            "citations": deepcopy(record["citations"]),
        }
