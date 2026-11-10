"""Domain-aware, fail-closed N5/ITS publication resolution (P3.4).

This backend layer resolves explicit typed references without attaching SQLite
databases or inferring an ITS season from a scenario slug. It is deliberately
independent of the HTTP and browser layers.
"""

from __future__ import annotations

from collections.abc import Mapping
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

    This is the P3.4 backend foundation. The existing two-file HTTP runtime is
    unchanged until the integrated serving/build/packaging cutover.
    """

    def __init__(
        self, rules_database: RulesDatabase, season_databases: Mapping[str, Path],
    ) -> None:
        self.rules_database = rules_database
        self.core_revision = rules_database.current_core_scenario_revision()
        self._season_paths: dict[str, Path] = {}
        self._season_revisions: dict[str, str] = {}
        self._season_reports: dict[str, dict[str, Any]] = {}
        for season_id, path in season_databases.items():
            require_domain_slug(season_id, context="registered ITS season")
            if not season_id.startswith("its-"):
                raise ValueError(f"Not an ITS publication domain: {season_id}")
            resolved = Path(path).resolve()
            report = inspect_its_database(resolved, core_revision=self.core_revision)
            identity = report["inputIdentity"]
            if season_id != identity["seasonId"]:
                raise ValueError(f"ITS filename/registration does not match {season_id}")
            if season_id in self._season_paths:
                raise ValueError(f"Duplicate registered ITS season: {season_id}")
            self._season_paths[season_id] = resolved
            self._season_revisions[season_id] = identity["seasonRevision"]
            self._season_reports[season_id] = report

        # Validate cross-domain references at registration, before any HTTP read.
        # No policy is applied by default, but unresolved targets cannot be hosted.
        for season_id, report in self._season_reports.items():
            for policy in report["policies"]:
                target = PublicationReference("rules-n5", policy["target"])
                if self.resolve(target) is None:
                    raise ValueError(
                        f"ITS policy {policy['id']!r} has unknown N5 target "
                        f"{policy['target']!r}"
                    )
            for scenario in report["scenarios"]:
                selected = self.resolve(PublicationReference(
                    season_id, scenario["id"], self._season_revisions[season_id],
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

    def resolve(self, reference: PublicationReference) -> dict[str, Any] | None:
        """Never search another owner or revision when the requested one is absent."""
        if reference.domain == "rules-n5":
            return self.rules_database.composed_record(reference.record_id)
        path = self._season_paths.get(reference.domain)
        if path is None:
            return None
        return select_its_scenario(
            path, season_id=reference.domain,
            revision=reference.revision or "",
            scenario_id=reference.record_id,
        )

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
        path = self._season_paths.get(season_id)
        if path is None or revision != self._season_revisions[season_id]:
            return []
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
            result.append({"policy": policy, "target": target})
        return result

    def season_manifest(self) -> dict[str, dict[str, Any]]:
        """Expose validated season identity and immutable bytes, not file paths."""
        return {
            season: {
                "revision": self._season_revisions[season],
                "sourceCollectionId": report["inputIdentity"]["sourceCollectionId"],
                "requiredCoreRulesRevision": self.core_revision,
                "sha256": report["sha256"],
            }
            for season, report in self._season_reports.items()
        }
