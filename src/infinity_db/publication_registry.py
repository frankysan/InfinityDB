"""Domain-aware, fail-closed N5/ITS publication resolution (P3.4).

This backend layer resolves explicit typed references without attaching SQLite
databases or inferring an ITS season from a scenario slug. It is deliberately
independent of the HTTP and browser layers.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .domain_slugs import require_domain_slug, validate_typed_domain_id
from .its_season_database import (
    inspect_its_database,
    select_its_policies,
    select_its_scenario,
)
from .rules_database import RulesDatabase


@dataclass(frozen=True)
class PublicationReference:
    """One explicitly owned record; ITS references always include a revision."""

    domain: str
    record_id: str
    revision: str | None = None

    def __post_init__(self) -> None:
        require_domain_slug(self.domain, context="publication domain")
        kind = self.record_id.partition(":")[0]
        if not kind or ":" not in self.record_id:
            raise ValueError("Publication reference requires a typed record ID")
        validate_typed_domain_id(
            self.record_id, expected_domain=kind, context="publication reference",
        )
        if self.domain == "rules-n5":
            if self.revision is not None:
                raise ValueError("Core N5 references do not take season revisions")
        elif self.domain.startswith("its-"):
            if kind != "scenario":
                raise ValueError("ITS references must identify a Scenario")
            if (
                not isinstance(self.revision, str)
                or not self.revision.strip()
                or self.revision.strip() != self.revision
            ):
                raise ValueError("ITS references require an exact season revision")
        else:
            raise ValueError(f"Unregistered publication domain: {self.domain}")


class PublicationRegistry:
    """Resolve typed N5 and ITS publications from independently stored SQLite files.

    The selected complete runtime registers independently owned ITS season
    databases and retains N5 core definitions in the Rules database.
    """

    def __init__(
        self, rules_database: RulesDatabase, season_databases: Mapping[str, Path],
    ) -> None:
        self.rules_database = rules_database
        self.core_revision = rules_database.current_core_scenario_revision()
        self._season_paths: dict[str, Path] = {}
        self._season_revisions: dict[str, str] = {}
        self._season_reports: dict[str, dict[str, Any]] = {}
        self._season_sources: dict[str, dict[str, dict[str, Any]]] = {}
        for registered, path in season_databases.items():
            season_id, separator, pinned_revision = registered.partition("@")
            require_domain_slug(season_id, context="registered ITS season")
            if not season_id.startswith("its-"):
                raise ValueError(f"Not an ITS publication domain: {season_id}")
            resolved = Path(path).resolve()
            report = inspect_its_database(resolved, core_revision=self.core_revision)
            identity = report["inputIdentity"]
            if season_id != identity["seasonId"] or (
                separator and pinned_revision != identity["seasonRevision"]
            ):
                raise ValueError(f"ITS filename/registration does not match {registered}")
            if registered in self._season_paths or any(
                key.partition("@")[0] == season_id
                and prior_revision == identity["seasonRevision"]
                for key, prior_revision in self._season_revisions.items()
            ):
                raise ValueError(f"Duplicate registered ITS season/revision: {registered}")
            self._season_paths[registered] = resolved
            self._season_revisions[registered] = identity["seasonRevision"]
            self._season_reports[registered] = report
            with closing(sqlite3.connect(resolved.as_uri() + "?mode=ro", uri=True)) as db:
                descriptors = [
                    json.loads(row[0])
                    for row in db.execute(
                        "SELECT descriptor_json FROM sources WHERE collection_id=?",
                        (identity["sourceCollectionId"],),
                    )
                ]
            self._season_sources[registered] = {
                descriptor["id"]: descriptor for descriptor in descriptors
            }

        # Validate cross-domain references at registration, before any HTTP read.
        # No policy is applied by default, but unresolved targets cannot be hosted.
        for report in self._season_reports.values():
            season_id = report["inputIdentity"]["seasonId"]
            revision = report["inputIdentity"]["seasonRevision"]
            for policy in report["policies"]:
                target = PublicationReference("rules-n5", policy["target"])
                if self.resolve(target) is None:
                    raise ValueError(
                        f"ITS policy {policy['id']!r} has unknown N5 target "
                        f"{policy['target']!r}"
                    )
            for scenario in report["scenarios"]:
                selected = self.resolve(PublicationReference(
                    season_id, scenario["id"], revision,
                ))
                if selected is None:
                    raise ValueError(f"Missing registered ITS scenario: {scenario['id']}")
                mission = selected["record"]["facts"]["mission"]
                for inclusion in mission["rules"]:
                    definition_id = inclusion.get("definitionId")
                    if definition_id is not None and self.resolve(
                        PublicationReference("rules-n5", definition_id)
                    ) is None:
                        raise ValueError(
                            f"ITS scenario {scenario['id']!r} has unknown N5 Rule "
                            f"{definition_id!r}"
                        )
                for skill_id in mission.get("skills", []):
                    if self.resolve(PublicationReference("rules-n5", skill_id)) is None:
                        raise ValueError(
                            f"ITS scenario {scenario['id']!r} has unknown N5 Skill "
                            f"{skill_id!r}"
                        )

    def season_skill_entries(self) -> list[dict[str, Any]]:
        """Return validated standalone Skills from the selected ITS publications."""
        entries: list[dict[str, Any]] = []
        for registered, report in self._season_reports.items():
            identity = report["inputIdentity"]
            season = identity["seasonId"]
            sources = self._season_sources[registered]
            with closing(sqlite3.connect(self._season_paths[registered].as_uri() + "?mode=ro",
                                         uri=True)) as connection:
                for (raw,) in connection.execute(
                    "SELECT payload_json FROM records WHERE collection_id=? AND kind='skill' "
                    "ORDER BY id", (identity["sourceCollectionId"],),
                ):
                    record = json.loads(raw)
                    citations = []
                    for pin in record["citations"]:
                        source = sources[pin["sourceId"]]
                        citations.append({
                            "source_id": source["id"],
                            "source_title": source["title"],
                            "source_version": source["version"],
                            "source_url": source.get("url"),
                            "page": pin.get("page"),
                            "section": pin.get("section"),
                        })
                    entries.append({
                        "record": record,
                        "citations": citations,
                        "collection": season,
                        "revision": identity["seasonRevision"],
                    })
        return entries


    def _registered_key(self, season_id: str, revision: str) -> str | None:
        """Resolve an exact season/revision; never substitute another revision."""
        explicit = f"{season_id}@{revision}"
        if self._season_revisions.get(explicit) == revision:
            return explicit
        if self._season_revisions.get(season_id) == revision:
            return season_id
        return None

    def resolve(self, reference: PublicationReference) -> dict[str, Any] | None:
        """Never search another owner or revision when the requested one is absent."""
        if reference.domain == "rules-n5":
            return self.rules_database.composed_record(reference.record_id)
        key = self._registered_key(reference.domain, reference.revision or "")
        if key is None:
            return None
        return select_its_scenario(
            self._season_paths[key], season_id=reference.domain,
            revision=reference.revision or "",
            scenario_id=reference.record_id,
        )

    def scenario_entries(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        """Return validated ITS scenarios in the existing catalog's read format.

        Selection is scoped by the registered owner and exact revision. Different
        seasons may publish the same scenario slug without overwriting each other.
        """
        entries: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for registered, report in self._season_reports.items():
            season_id = report["inputIdentity"]["seasonId"]
            for scenario in report["scenarios"]:
                selected = self.resolve(PublicationReference(
                    season_id, scenario["id"], self._season_revisions[registered],
                ))
                if selected is None:
                    raise ValueError(f"Missing ITS scenario: {scenario['id']}")
                record = deepcopy(selected["record"])
                published = selected["publication"]
                sources = {source["id"]: source for source in published["sources"]}
                record["citations"] = [
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
                    for citation in record["citations"]
                ]
                publication = {
                    "scenario_id": record["id"],
                    "name": record["name"],
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
                entries.append((record, publication))
        return entries

    def scenario_reference(self, record: dict[str, Any]) -> dict[str, Any]:
        """Resolve an ITS mission's reusable N5 definitions without shadowing."""
        mission = record["facts"]["mission"]
        rules = []
        for inclusion in mission["rules"]:
            definition_id = inclusion.get("definitionId")
            if definition_id is None:
                continue
            rule = self.rules_database.composed_record(
                definition_id, scenario_id=record["id"],
            )
            if rule is None:
                raise ValueError(f"Missing N5 scenario Rule {definition_id!r}")
            if "specialists" in inclusion:
                rule["facts"]["specialists"] = inclusion["specialists"]
            rules.append(rule)
        skills = []
        for skill_id in mission.get("skills", []):
            skill = self.rules_database.composed_record(
                skill_id, scenario_id=record["id"],
            )
            if skill is None:
                raise ValueError(f"Missing N5 scenario Skill {skill_id!r}")
            skills.append(skill)
        return {"scenario": record, "rules": rules, "skills": skills}

    def has_season(self, season_id: str, revision: str) -> bool:
        """Whether this exact season and revision are registered for serving."""
        return self._registered_key(season_id, revision) is not None

    def source_citation(
        self, *, season_id: str, source_id: str, page: int,
        revision: str | None = None,
    ) -> dict[str, Any] | None:
        """Resolve an external citation against a registered publication source.

        Source attribution does not transfer ownership of the citing N5 record.
        Do not infer a new season or substitute another source when the requested
        provenance is absent.
        """
        key = season_id if revision is None else self._registered_key(season_id, revision)
        source = self._season_sources.get(key or "", {}).get(source_id)
        if source is None:
            return None
        return {
            "source_id": source["id"],
            "source_title": source["title"],
            "source_version": source["version"],
            "source_url": source.get("url"),
            "page": page,
        }

    def season_contexts(self, *, season_id: str, revision: str) -> list[str]:
        """List authored play contexts without selecting or applying any policy."""
        require_domain_slug(season_id, context="ITS policy season")
        if not isinstance(revision, str) or not revision.strip() or revision.strip() != revision:
            raise ValueError("ITS policy selection requires an exact season revision")
        key = self._registered_key(season_id, revision)
        if key is None:
            return []
        return sorted({policy["context"] for policy in self._season_reports[key]["policies"]})

    def season_policies(
        self, *, season_id: str, revision: str, context: str,
        target_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return explicit-context policies with their resolved core references.

        No selection, unknown season/revision, or irrelevant context yields no
        policy. Never implicitly apply tournament policy to free play.
        """
        require_domain_slug(season_id, context="ITS policy season")
        require_domain_slug(context, context="ITS policy context")
        if not isinstance(revision, str) or not revision.strip() or revision.strip() != revision:
            raise ValueError("ITS policy selection requires an exact season revision")
        key = self._registered_key(season_id, revision)
        if key is None:
            return []
        path = self._season_paths[key]
        policies = select_its_policies(
            path, season_id=season_id, revision=revision, context=context,
            target_id=target_id,
        )
        result = []
        for policy in policies:
            target = self.resolve(PublicationReference(
                policy["target"]["domain"], policy["target"]["recordId"],
            ))
            if target is None:
                raise ValueError(f"ITS policy {policy['id']!r} has an unknown N5 target")
            published = deepcopy(policy)
            for citation in published["citations"]:
                source = self._season_sources[key].get(citation["sourceId"])
                if source is None:
                    raise ValueError(
                        f"ITS policy {policy['id']!r} has unknown source {citation['sourceId']!r}"
                    )
                citation.update({
                    "sourceTitle": source["title"],
                    "sourceVersion": source["version"],
                    "sourceUrl": source.get("url"),
                })
            result.append({"policy": published, "target": target})
        return result

    def season_manifest(self) -> dict[str, dict[str, Any]]:
        """Expose validated season identity and immutable bytes, not file paths."""
        return {
            season: {
                "revision": self._season_revisions[season],
                "sourceCollectionId": report["inputIdentity"]["sourceCollectionId"],
                "sourceSha256": report["inputIdentity"]["sourceSha256"],
                **({
                    "sharedScenarioLibrary": report["inputIdentity"]["sharedScenarioLibrary"]
                } if "sharedScenarioLibrary" in report["inputIdentity"] else {}),
                "requiredCoreRulesRevision": self.core_revision,
                "sha256": report["sha256"],
            }
            for season, report in self._season_reports.items()
        }
