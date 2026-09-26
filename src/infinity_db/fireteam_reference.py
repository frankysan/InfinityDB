"""Project curated Fireteam general rules into the application API."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from infinity_db.rules_database import RulesDatabase

GENERAL_FIRETEAM_RULE_ID = "rule:fireteam-general"
FIRETEAM_LEVEL_RULE_ID = "rule:fireteam-level-bonuses"


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return the bounded rules payload needed by the Fireteam browser."""

    return {
        "id": record["id"],
        "name": record["name"],
        "summary": record["summary"],
        "aliases": list(record.get("aliases") or []),
        "facts": deepcopy(record.get("facts") or {}),
        "citations": [
            {
                key: citation[key]
                for key in (
                    "source_id",
                    "source_title",
                    "source_version",
                    "source_url",
                    "page",
                    "member",
                    "heading",
                    "section",
                )
                if citation.get(key) is not None
            }
            for citation in record.get("citations", [])
        ],
    }


def fireteam_reference(rules_database: RulesDatabase | None) -> dict[str, Any] | None:
    """Return the current general Fireteam reference, when the rules snapshot has it.

    The application database remains independently usable. Older compatible rules snapshots
    that predate the Fireteam records therefore yield no reference block rather than making the
    Army chart unavailable.
    """

    if rules_database is None:
        return None
    records = {
        record["id"]: record for record in rules_database.composed_records_by_kind("rule")
    }
    general = records.get(GENERAL_FIRETEAM_RULE_ID)
    levels = records.get(FIRETEAM_LEVEL_RULE_ID)
    if general is None or levels is None:
        return None
    return {
        "general": _public_record(general),
        "levels": _public_record(levels),
    }
