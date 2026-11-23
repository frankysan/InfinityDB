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
    "source_version": "2026.09.11",
    "source_url": "https://experience.corvusbelli.com/en/infinity/its-rules",
    "page": 18,
}
_MARKER_LABELS = {
    "console": "Console A Marker",
    "supply-box": "Supply Box Marker",
    "antenna": "Transmission Antenna Token",
    "tech-coffin": "Tech-Coffin Token",
    "hyperthermal-tech": "Hyperthermal Tech Token",
    "prototype": "Prototype (Objective Token)",
    "panoply": "Panoply (Objective Token)",
    "beacon": "Beacon Token",
    "tracking-beacon": "Tracking Beacon Token",
    "civilian": "Civilian Model or Token",
    "defensive-turret": "Defensive Turret Token or S2 Model",
    "objective": "Objective Token",
    "player-a-b": "Player A/B Token",
    "data-pack": "Data Pack Token",
    "civevac": "CivEvac Token",
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
        if label is None or (
            diameter is None
            and marker_type != "tracking-beacon"
        ):
            raise ValueError(f"Missing reviewed marker dimensions for {marker_type!r}")
        entry = {
            "marker_type": marker_type,
            "name": label,
            "count": count,
            "diameter_mm": diameter,
            "citation": dict(source_citation) if diameter is not None else None,
        }
        if marker_type == "tracking-beacon":
            # EN p. 60: 40 mm; ES p. 59: 25 mm. No agreed physical footprint.
            entry["size_status"] = "source-conflict"
        elif marker_type == "defensive-turret":
            # The cited 25 mm is the token option; the mission also permits an S2 Model.
            entry["size_status"] = "token-or-model"
        result.append(entry)
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
        self._season_rules_cache: list[dict[str, Any]] | None = None
        self._scenario_skills_cache: list[dict[str, Any]] | None = None
        self._scenario_skill_aliases: dict[str, dict[str, Any]] = {}

    def _marker_size_source(
        self, *, season_id: str = "its-18", revision: str | None = None,
    ) -> dict[str, Any]:
        """Source attribution for marker sizes in the selected ITS publication."""
        if self.publication_registry is not None:
            if season_id == "its-17" and revision != "0.2":
                # Synthetic/historical fixtures predate this source-verified
                # publication; do not fabricate a V0.2 source citation.
                return dict(_MARKER_SIZE_CITATION)
            if season_id == "its-17":
                chart_page, source_id = 13, "its-season-17-v0.2-en-pdf"
            else:
                # ITS 18 hotfix moved the chart from p.17 to p.18.
                chart_page = 17 if revision == "2026.09.01" else 18
                source_id = "its-season-18-en-pdf"
            citation = self.publication_registry.source_citation(
                season_id=season_id, source_id=source_id,
                page=chart_page, revision=revision,
            )
            if citation is not None:
                return citation
            if season_id in self.publication_registry.season_manifest():
                raise ValueError(f"Registered {season_id} marker size source is unavailable")
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
        if collection is None and revision is not None:
            raise ValueError("Scenario revision requires a collection")
        if collection is not None:
            require_domain_slug(collection, context="scenario collection")
        if revision is not None and (
            not isinstance(revision, str) or not revision.strip() or revision != revision.strip()
        ):
            raise ValueError("scenario revision must be a non-empty trimmed string")
        records = self._records()
        if collection is not None and revision is None:
            # The normal player selection is a season, not a publication date.
            # Exactly one revision per registered season is currently supported.
            available = {
                publication["revision"] for _record, publication in records
                if publication["collection"] == collection
            }
            if len(available) > 1:
                raise ValueError("Ambiguous current scenario collection revision")
            revision = next(iter(available), None)
        return [
            (record, publication)
            for record, publication in records
            if (
                publication["collection"] == "n5-core"
                if collection is None
                else (
                    publication["collection"] == collection
                    and publication["revision"] == revision
                )
            )
        ]

    def scenario_skill_items(self) -> list[dict[str, Any]]:
        """Project explicitly typed ITS actions as normal, scenario-scoped Skills."""
        if self._scenario_skills_cache is None:
            items: list[dict[str, Any]] = []
            known_labels = {
                label["name"]: label for label in (
                    self.rules_database.current_labels() if self.rules_database else []
                )
            }

            def source_labels(names: list[str]) -> list[dict[str, Any]]:
                # ITS-only qualifiers (such as Scenario) stay visible but unlinked
                # unless a matching canonical Rules Label exists.
                return [
                    {key: known_labels[name][key] for key in ("id", "name", "description")}
                    if name in known_labels else {"name": name}
                    for name in names
                ]

            for record, publication in self._records():
                scenario_slug = _scenario_slug(record)
                if publication["collection"] == "n5-core":
                    if self.rules_database is None:
                        raise ValueError("Core scenario Skills require the Rules database")
                    reference = self.rules_database.scenario_reference(str(record["id"]))
                    if reference is None:
                        raise ValueError(f"Missing Core scenario {record['id']!r}")
                    for skill in reference["skills"]:
                        if skill.get("facts", {}).get("category") != "scenario-skill":
                            continue
                        slug = skill["id"].removeprefix("skill:")
                        items.append({
                            "id": slug,
                            "slug": slug,
                            "name": skill["name"],
                            "use_count": 0,
                            "category": "Scenario-specific Skills",
                            "categories": [
                                {
                                    "id": category["id"],
                                    "name": category.get("category_name", category["name"]),
                                    "source": None,
                                    "page": None,
                                }
                                for category in skill.get("skill_types", [])
                            ],
                            "scenario": {
                                "id": record["id"],
                                "slug": scenario_slug,
                                "name": record["name"],
                                "collection": publication["collection"],
                                "revision": publication["revision"],
                            },
                            "rules": [deepcopy(skill)],
                            "variants": [],
                        })
                    continue
                for rule in _mission(record)["rules"]:
                    skill_types = rule.get("skillTypeIds", [])
                    if not skill_types:
                        continue
                    slug = f"{publication['collection']}-{scenario_slug}-{rule['id']}"
                    # The typed Skill category is displayed separately from its name.
                    skill_name = rule["name"].removesuffix(" (Short Skill)").removesuffix(
                        " (Long Skill)"
                    )
                    citations = []
                    by_source: dict[str, list[int]] = {}
                    mission_pins: set[tuple[str, int]] = set()
                    for citation in record.get("citations", []):
                        source_id = citation.get("source_id") or citation.get("sourceId")
                        if isinstance(citation.get("page"), int):
                            by_source.setdefault(source_id, []).append(citation["page"])
                            mission_pins.add((source_id, citation["page"]))
                    action_pins = rule.get("skillCitations", [])
                    if action_pins and any(
                        (pin["sourceId"], pin["page"]) not in mission_pins
                        for pin in action_pins
                    ):
                        raise ValueError(
                            f"Scenario Skill {rule['id']!r} cites outside its mission source"
                        )
                    if "sharedSkill" in rule:
                        shared_id = rule["sharedSkill"]["id"]
                        component_sources = [
                            component["citations"]
                            for component in record["facts"].get("componentSources", [])
                            if component["id"] == shared_id
                        ]
                        if len(component_sources) != 1:
                            raise ValueError(
                                f"Shared Skill {shared_id!r} requires exact publication citations"
                            )
                        bound_pins = [
                            {"sourceId": citation["sourceId"], "page": citation["page"]}
                            for citation in component_sources[0]
                        ]
                        if action_pins and "origin" in rule["sharedSkill"] and any(
                            pin not in bound_pins for pin in action_pins
                        ):
                            raise ValueError(
                                f"Shared Skill {shared_id!r} has unbound action citations"
                            )
                        if not action_pins and any(
                            (pin["sourceId"], pin["page"]) not in mission_pins
                            for pin in bound_pins
                        ):
                            raise ValueError(
                                f"Shared Skill {shared_id!r} cites outside its mission source"
                            )
                        action_pins = action_pins or bound_pins
                    if action_pins:
                        by_source = {}
                        for pin in action_pins:
                            by_source.setdefault(pin["sourceId"], []).append(pin["page"])
                    for source_id, pages in by_source.items():
                        if self.publication_registry is None:
                            raise ValueError(
                                "ITS scenario Skill requires registered source provenance"
                            )
                        for page in pages if action_pins else [min(pages)]:
                            source = self.publication_registry.source_citation(
                                season_id=publication["collection"],
                                revision=publication["revision"],
                                source_id=source_id,
                                page=page,
                            )
                            if source is None:
                                raise ValueError(f"Missing ITS Skill source {source_id!r}")
                            if action_pins:
                                source["section"] = f"{record['name']} — {skill_name}"
                            else:
                                # An unpinned citation covers the mission, not a skill page.
                                source["page"] = None
                                page_range = str(min(pages)) if min(pages) == max(pages) else (
                                    f"{min(pages)}–{max(pages)}"
                                )
                                source["section"] = f"{record['name']}, pp. {page_range}"
                            citations.append(source)
                    categories = [
                        {"id": category, "name": "Short Skill" if category == "short-skill"
                         else "Long Skill", "source": None, "page": None}
                        for category in skill_types
                    ]
                    skill_rule = {
                        "id": f"skill:{slug}",
                        "kind": "skill",
                        "name": skill_name,
                        "summary": (
                            "" if rule.get("skillFacts")
                            else "\n\n".join(rule["paragraphs"])
                        ),
                        "facts": {
                            "category": "scenario-skill",
                            **deepcopy(rule.get("skillFacts", {})),
                        },
                        "skill_types": [
                            {"id": category["id"], "name": category["name"]}
                            for category in categories
                        ],
                        "labels": source_labels(rule.get("sourceLabels", [])),
                        "scope": {
                            "game": "N5",
                            "seasons": [publication["collection"]],
                            "scenarios": [record["id"]],
                        },
                        "applicable_scenarios": [{"id": record["id"], "name": record["name"]}],
                        "citations": citations,
                        **({"sharedSkill": deepcopy(rule["sharedSkill"])}
                           if "sharedSkill" in rule else {}),
                    }
                    items.append({
                        "id": slug,
                        "slug": slug,
                        "name": skill_name,
                        "use_count": 0,
                        "category": "Scenario-specific Skills",
                        "categories": categories,
                        "scenario": {
                            "id": record["id"],
                            "slug": scenario_slug,
                            "name": record["name"],
                            "collection": publication["collection"],
                            "revision": publication["revision"],
                        },
                        "rules": [skill_rule],
                        "variants": [],
                    })
            self._scenario_skill_aliases = {item["slug"]: deepcopy(item) for item in items}
            shared: dict[str, list[dict[str, Any]]] = {}
            published: list[dict[str, Any]] = []
            for item in items:
                identity = item["rules"][0].get("sharedSkill")
                if identity is None or identity.get("overriddenFields"):
                    published.append(item)
                else:
                    shared.setdefault(identity["id"], []).append(item)
            legacy_slugs = set(self._scenario_skill_aliases)
            for identifier, uses in shared.items():
                slug = identifier.removeprefix("skill:")
                if slug in legacy_slugs or any(item["slug"] == slug for item in published):
                    raise ValueError(f"Shared scenario Skill {identifier!r} conflicts with a route")
                first = uses[0]
                first_rule = first["rules"][0]
                version = first_rule["sharedSkill"]["version"]
                for use in uses[1:]:
                    rule = use["rules"][0]
                    if (
                        rule["sharedSkill"]["version"] != version
                        or use["name"] != first["name"]
                        or rule["facts"] != first_rule["facts"]
                        or rule["skill_types"] != first_rule["skill_types"]
                        or rule["labels"] != first_rule["labels"]
                        or rule["sharedSkill"].get("origin")
                        != first_rule["sharedSkill"].get("origin")
                    ):
                        raise ValueError(
                            f"Conflicting facts for pinned shared scenario Skill {identifier!r}"
                        )
                canonical = deepcopy(first)
                canonical["id"] = slug
                canonical["slug"] = slug
                canonical.pop("scenario", None)
                canonical["scenarios"] = [deepcopy(use["scenario"]) for use in uses]
                canonical["aliases"] = [use["slug"] for use in uses]
                merged_rule = canonical["rules"][0]
                merged_rule["id"] = identifier
                merged_rule["scope"]["seasons"] = list(dict.fromkeys(
                    use["scenario"]["collection"] for use in uses
                ))
                merged_rule["scope"]["scenarios"] = list(dict.fromkeys(
                    use["scenario"]["id"] for use in uses
                ))
                merged_rule["applicable_scenarios"] = [
                    deepcopy(use["scenario"]) for use in uses
                ]
                merged_rule["citations"] = []
                seen_citations: set[tuple[str, str, str, int | None]] = set()
                for use in uses:
                    for citation in use["rules"][0]["citations"]:
                        key = (
                            use["scenario"]["collection"], use["scenario"]["revision"],
                            str(citation["source_id"]), citation.get("page"),
                        )
                        if key not in seen_citations:
                            seen_citations.add(key)
                            merged_rule["citations"].append(deepcopy(citation))
                published.append(canonical)
            if self.publication_registry is not None:
                season_skills: dict[str, dict[str, Any]] = {}
                by_identity: dict[str, list[dict[str, Any]]] = {}

                def season_sort_key(entry: dict[str, Any]) -> tuple[int, str]:
                    number = entry["collection"].removeprefix("its-")
                    return (int(number) if number.isdecimal() else -1, entry["revision"])

                # The newest season retains the established unqualified route.
                for entry in sorted(
                    self.publication_registry.season_skill_entries(),
                    key=season_sort_key, reverse=True,
                ):
                    record = entry["record"]
                    slug = record["id"].removeprefix("skill:")
                    if slug in legacy_slugs or any(
                        item["slug"] == slug for item in published
                    ):
                        raise ValueError(f"ITS season Skill {slug!r} conflicts with a Skill route")
                    types = [
                        {
                            "id": kind,
                            "name": {
                                "basic-short-skill": "Basic Short Skill",
                                "short-skill": "Short Skill",
                                "short-movement-skill": "Short Movement Skill",
                                "automatic": "Automatic Skill",
                            }[kind],
                            "source": None,
                            "page": None,
                        }
                        for kind in record["facts"]["typeIds"]
                    ]
                    rule = deepcopy(record)
                    rule["citations"] = deepcopy(entry["citations"])
                    rule["skill_types"] = [
                        {"id": kind["id"], "name": kind["name"]} for kind in types
                    ]
                    rule["labels"] = source_labels(record["facts"].get("sourceLabels", []))
                    category = ("Common Skills" if record["facts"]["category"] == "common-skill"
                                else "Special Skills")
                    season_use = {
                        "collection": entry["collection"],
                        "revision": entry["revision"],
                        "context": record["facts"]["applicability"]["context"],
                    }
                    groups = by_identity.setdefault(slug, [])
                    if any(use["collection"] == season_use["collection"]
                           for group in groups for use in group["seasons"]):
                        raise ValueError(
                            f"Conflicting ITS season Skill registration: {slug!r}"
                        )
                    # Source-local season Skills have no shared identity. Keep
                    # distinct editions separate rather than merging two None keys.
                    shared_identity = rule.get("sharedSkill")
                    existing = next(
                        (group for group in groups
                         if shared_identity is not None
                         and group["rules"][0].get("sharedSkill") == shared_identity),
                        None,
                    )
                    if existing is None:
                        if groups:
                            previous = groups[0]["rules"][0].get("sharedSkill")
                            shared = rule.get("sharedSkill")
                            if (
                                # Independently curated editions do not claim
                                # shared identity and use season-qualified routes.
                                previous is None and shared is None
                            ):
                                pass
                            elif (
                                not previous or not shared
                                or previous["id"] != shared["id"]
                                or previous["origin"] != shared["origin"]
                                or previous["version"] == shared["version"]
                            ):
                                raise ValueError(
                                    "Conflicting ITS season Skill facts or unpinned reuse: "
                                    f"{slug!r}"
                                )
                        # A different pinned version gets its own season route.
                        # Never silently replace the latest season's Skill facts.
                        route = slug if not groups else f"{entry['collection']}-{slug}"
                        if route in legacy_slugs or route in season_skills or any(
                            item["slug"] == route for item in published
                        ):
                            raise ValueError(
                                f"ITS season Skill {route!r} conflicts with a Skill route"
                            )
                        item = {
                            "id": route,
                            "slug": route,
                            "name": record["name"],
                            "use_count": 0,
                            "category": category,
                            "categories": types,
                            "applicability": deepcopy(record["facts"]["applicability"]),
                            "seasons": [season_use],
                            "rules": [rule],
                            "variants": [],
                        }
                        season_skills[route] = item
                        groups.append(item)
                        continue
                    prior_rule = existing["rules"][0]
                    prior_facts = {
                        key: value for key, value in prior_rule["facts"].items()
                        if key != "applicability"
                    }
                    new_facts = {
                        key: value for key, value in rule["facts"].items()
                        if key != "applicability"
                    }
                    if (
                        not prior_rule.get("sharedSkill")
                        or existing["name"] != record["name"]
                        or existing["category"] != category
                        or prior_rule["summary"] != record["summary"]
                        or prior_rule["skill_types"] != rule["skill_types"]
                        or prior_rule["labels"] != rule["labels"]
                        or prior_facts != new_facts
                        or existing["applicability"]["context"] != season_use["context"]
                        or season_use in existing["seasons"]
                    ):
                        raise ValueError(
                            f"Conflicting ITS season Skill facts or unpinned reuse: {slug!r}"
                        )
                    existing["seasons"].append(season_use)
                    existing["applicability"] = {
                        "context": season_use["context"],
                        "revisions": [use["revision"] for use in existing["seasons"]],
                    }
                    prior_rule["scope"]["seasons"].append(entry["collection"])
                    prior_rule["facts"]["applicability"] = {
                        "context": season_use["context"],
                        "revisions": [use["revision"] for use in existing["seasons"]],
                    }
                    seen_pins = {
                        (cite["source_id"], cite["source_version"], cite["page"],
                         cite.get("section")) for cite in prior_rule["citations"]
                    }
                    for cite in rule["citations"]:
                        key = (cite["source_id"], cite["source_version"], cite["page"],
                               cite.get("section"))
                        if key not in seen_pins:
                            seen_pins.add(key)
                            prior_rule["citations"].append(cite)
                published.extend(season_skills.values())
            self._scenario_skills_cache = published
        return deepcopy(self._scenario_skills_cache)

    def get_scenario_skill(self, slug: str) -> dict[str, Any] | None:
        items = self.scenario_skill_items()
        if slug in self._scenario_skill_aliases:
            return deepcopy(self._scenario_skill_aliases[slug])
        return next((item for item in items if item["slug"] == slug), None)

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
            if item.get("skillTypeIds"):
                skill_slug = f"{publication['collection']}-{slug}-{item['id']}"
                scenario_skill = self.get_scenario_skill(skill_slug)
                if scenario_skill is None:
                    raise ValueError(f"Missing scenario Skill {skill_slug!r}")
                item["skill"] = deepcopy(scenario_skill["rules"][0])
            definition_id = item.get("definitionId")
            if definition_id is not None:
                rule = rules_by_id.get(str(definition_id))
                if rule is None:
                    raise ValueError(
                        f"Scenario {record['id']!r} is missing composed Rule {definition_id!r}"
                    )
                item["rule"] = deepcopy(rule)
            special_rules.append(item)

        tactical_support = None
        if record["facts"].get("eventContext", {}).get("tacticalSupportOptions", 0) > 0:
            if self._season_rules_cache is None:
                self._season_rules_cache = (
                    self.publication_registry.season_rule_entries()
                    if self.publication_registry is not None else []
                )
            support = next((
                entry for entry in self._season_rules_cache
                if entry["record"]["id"] == "rule:tactical-support"
                and entry["collection"] == publication["collection"]
                and entry["revision"] == publication["revision"]
            ), None)
            if support is None:
                raise ValueError("Scenario requires a published Tactical Support rule")
            tactical_support = {
                "name": support["record"]["name"],
                **deepcopy(support["record"]["facts"]),
                "citations": deepcopy(support["citations"]),
            }

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
                **({"play_requirements": deepcopy(record["facts"]["playRequirements"])}
                   if "playRequirements" in record["facts"] else {}),
                **({"event_context": deepcopy(record["facts"]["eventContext"])}
                   if "eventContext" in record["facts"] else {}),
            },
            "placement": {
                "configuration_id": configuration_id,
                "configuration_army_points": deepcopy(configuration_points),
                "geometry": deepcopy(configuration["geometry"]),
                "marker_dimensions": _marker_dimensions(
                    configuration["geometry"],
                    self._marker_size_source(
                        season_id=(publication["collection"]
                                   if publication["collection"] in {"its-17", "its-18"}
                                   else "its-18"),
                        revision=(str(publication["revision"])
                                  if publication["collection"] in {"its-17", "its-18"}
                                  else None),
                    ),
                ),
            },
            "objectives": objectives,
            **({"tactical_support": tactical_support} if tactical_support else {}),
            **({"objective_selection": deepcopy(mission["objectiveSelection"])}
               if "objectiveSelection" in mission else {}),
            "special_rules": special_rules,
            "skills": deepcopy(reference["skills"]),
            "end_conditions": deepcopy(mission["endConditions"]),
            "source_issues": source_issues,
            "citations": deepcopy(record["citations"]),
        }
