"""Compose Army Hacking Program profiles with curated rules semantics."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.domain_slugs import assign_domain_slugs, route_slug_from_typed_domain_id
from infinity_db.rules_database import RulesDatabase


class HackingProgramCatalog:
    """Expose Hacking Programs as first-class reference identities.

    Army's structured ``hack`` metadata remains authoritative for profile fields,
    targets, declaration types, baseline Device associations, and Upgrade-extra
    provenance. ``rules.db`` contributes reviewed semantic summaries and typed
    cross-rule relationships without duplicating that source matrix.
    """

    def __init__(self, database: Database, rules_database: RulesDatabase | None) -> None:
        self.database = database
        self.rules_database = rules_database

    def _programs(self) -> list[dict[str, Any]]:
        rows = deepcopy(self.database.list_hacking_programs())
        slugs = assign_domain_slugs(
            ((int(row["position"]), row["name"]) for row in rows),
            domain="hacking-programs",
        )
        records: dict[str, dict[str, Any]] = {}
        if self.rules_database is not None:
            for record in self.rules_database.composed_records_by_kind("hacking-program"):
                slug = route_slug_from_typed_domain_id(
                    record.get("id"),
                    expected_domain="hacking-program",
                    context="curated Hacking Program id",
                )
                records[slug] = record

        programs: list[dict[str, Any]] = []
        for row in rows:
            position = int(row["position"])
            slug = slugs[position]
            record = records.get(slug)
            item = {
                **row,
                "id": slug,
                "slug": slug,
                "description": record["summary"] if record is not None else row.get("special"),
            }
            if record is not None:
                item["rules"] = [record]
            programs.append(item)
        return programs

    def list_programs(self) -> list[dict[str, Any]]:
        """Return source-ordered first-class Hacking Program identities."""

        return self._programs()

    def get_program(self, program_ref: int | str) -> dict[str, Any] | None:
        """Return one Hacking Program by source position or public slug."""

        for program in self._programs():
            if isinstance(program_ref, int):
                if int(program["position"]) == program_ref:
                    return program
            elif program["slug"] == program_ref:
                return program
        return None

    def programs_for_equipment(self, equipment_ref: int | str) -> list[dict[str, Any]]:
        """Return baseline Programs explicitly associated with one Hacking Device."""

        application_id = self.database.application_catalog_id("equipment", equipment_ref)
        if application_id is None:
            return []
        result = []
        for program in self._programs():
            if not any(device.get("id") == application_id for device in program["devices"]):
                continue
            result.append(
                {
                    "id": program["id"],
                    "slug": program["slug"],
                    "name": program["name"],
                }
            )
        return result
