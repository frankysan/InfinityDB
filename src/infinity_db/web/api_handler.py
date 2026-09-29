"""JSON API request parsing and domain-response handling."""

from __future__ import annotations

import logging
import re
import sqlite3
from http import HTTPStatus
from urllib.parse import parse_qs

from infinity_db import __version__
from infinity_db.application_domains import public_rule_record_domain
from infinity_db.army_overview import (
    army_overview_description,
    army_overview_group,
    army_overview_out_of_catalog,
)
from infinity_db.army_slugs import attach_public_army_slug, enrich_army_references
from infinity_db.catalog_rules import CatalogRules
from infinity_db.catalog_slugs import attach_public_catalog_slug, enrich_nested_catalog_slugs
from infinity_db.database import ArmySelectionError, Database
from infinity_db.domain_references import (
    enrich_rule_relation_references,
    rule_record_public_reference,
)
from infinity_db.domain_slugs import require_domain_slug
from infinity_db.equipment_catalog import EquipmentCatalog
from infinity_db.fireteam_reference import fireteam_reference
from infinity_db.glossary_catalog import GlossaryCatalog
from infinity_db.hacking_program_catalog import HackingProgramCatalog
from infinity_db.legacy_armies import load_legacy_armies
from infinity_db.maintained_text_references import (
    enrich_maintained_text_references,
    maintained_text_tokens,
)
from infinity_db.reference_catalog import LabelCatalog, RulesRecordCatalog
from infinity_db.rules_database import RulesDatabase
from infinity_db.search_catalog import SearchCatalog
from infinity_db.skill_catalog import SkillCatalog
from infinity_db.state_catalog import StateCatalog
from infinity_db.symbol_catalog import SymbolCatalog
from infinity_db.trait_catalog import TraitCatalog
from infinity_db.unit_slugs import (
    attach_public_unit_slug,
    enrich_nested_unit_slugs,
    enrich_unit_items,
)
from infinity_db.web.response import WebResponse
from infinity_db.web.routes import (
    AMMUNITION_API_PATH,
    EQUIPMENT_API_PATH,
    HACKING_PROGRAM_API_PATH,
    LABEL_API_PATH,
    RULE_API_PATH,
    SKILL_API_PATH,
    STATE_API_PATH,
    TRAIT_API_PATH,
    UNIT_API_PATH,
    WEAPON_API_PATH,
)

LOGGER = logging.getLogger(__name__)
API_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=600"


def _public_reference_href(reference: dict[str, str] | None) -> str | None:
    if reference is None:
        return None
    if href := reference.get("href"):
        return href
    catalog = reference.get("catalog")
    identifier = reference.get("id")
    if not catalog or not identifier:
        return None
    return f"/{catalog}/{identifier}"


def _integer(params: dict, key: str, default: int | None, low: int, high: int) -> int | None:
    if key not in params:
        return default
    raw = params[key][0]
    if len(raw) > 19 or not re.fullmatch(r"[0-9]+", raw):
        raise ValueError(f"{key} must be an integer between {low} and {high}")
    value = int(raw)
    if not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}")
    return value


def _flag(params: dict, key: str) -> bool:
    if key not in params:
        return False
    if params[key][0] not in {"0", "1"}:
        raise ValueError(f"{key} must be 0 or 1")
    return params[key][0] == "1"


def _optional_integer(
    params: dict, key: str, low: int = 0, high: int = 2**63 - 1
) -> int | None:
    if key not in params or params[key][0] == "":
        return None
    return _integer(params, key, None, low, high)


def _optional_decimal(params: dict, key: str) -> float | None:
    if key not in params or params[key][0] == "":
        return None
    raw = params[key][0]
    if len(raw) > 32 or re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", raw) is None:
        raise ValueError(f"{key} must be a nonnegative decimal number")
    return float(raw)


def _ava_exact(params: dict) -> int | str | None:
    if "ava" not in params or params["ava"][0] == "":
        return None
    raw = params["ava"][0].strip().casefold()
    if raw in {"t", "total"}:
        return "total"
    if re.fullmatch(r"[0-9]+", raw) is None:
        raise ValueError("ava must be an integer from 0 to 99 or 'total'")
    value = int(raw)
    if not 0 <= value <= 99:
        raise ValueError("ava must be an integer from 0 to 99 or 'total'")
    return value


def _swc_exact(params: dict) -> str | None:
    if "swc" not in params or params["swc"][0] == "":
        return None
    raw = params["swc"][0].strip()
    if re.fullmatch(r"(?:\+)?(?:0|[1-9]\d*)(?:\.[0-9]+)?|-", raw) is None:
        raise ValueError("swc must be a numeric cost, +bonus, or '-'")
    return raw


def _domain_filter_identifier(params: dict, key: str) -> int | str | None:
    """Parse one domain filter as a numeric compatibility ID or public slug."""

    if key not in params or params[key][0] == "":
        return None
    raw = params[key][0]
    if raw.isdigit():
        if len(raw) > 19:
            raise ValueError(f"{key} must be a valid domain identifier")
        value = int(raw)
        if value > 2**63 - 1:
            raise ValueError(f"{key} must be a valid domain identifier")
        return value
    return require_domain_slug(raw, context=key)


def _unit_query(query: str) -> dict:
    params = parse_qs(query, keep_blank_values=True, max_num_fields=40)
    for key, values in params.items():
        if key not in {
            "army_id",
            "declared_faction_id",
            "search",
            "skill_id",
            "equipment_id",
            "weapon_id",
            "troop_type",
            "classification",
            "characteristic",
            "ava",
            "ava_min",
            "ava_max",
            "points",
            "points_min",
            "points_max",
            "swc",
            "swc_min",
            "swc_max",
            "limit",
            "offset",
            "mercs",
            "specops",
            "teamops",
            "reinforcement",
            "order",
            "extended",
            "cache_bust",
        }:
            raise ValueError(f"Unknown query parameter: {key}")
        if len(values) != 1:
            raise ValueError(f"Provide {key} only once")
    search = params.get("search", [""])[0].strip()
    if len(search) > 200:
        raise ValueError("search must be at most 200 characters")
    order = params.get("order", ["asc"])[0]
    if order not in {"asc", "desc"}:
        raise ValueError("order must be asc or desc")
    ava = _ava_exact(params)
    ava_min = _optional_integer(params, "ava_min", 0, 99)
    ava_max = _optional_integer(params, "ava_max", 0, 99)
    points = _optional_integer(params, "points")
    points_min = _optional_integer(params, "points_min")
    points_max = _optional_integer(params, "points_max")
    swc = _swc_exact(params)
    swc_min = _optional_decimal(params, "swc_min")
    swc_max = _optional_decimal(params, "swc_max")
    for name, exact, minimum, maximum in (
        ("ava", ava, ava_min, ava_max),
        ("points", points, points_min, points_max),
        ("swc", swc, swc_min, swc_max),
    ):
        if exact is not None and (minimum is not None or maximum is not None):
            raise ValueError(f"{name} exact value cannot be combined with a range")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError(f"{name}_min must be less than or equal to {name}_max")

    return {
        "army_id": _domain_filter_identifier(params, "army_id"),
        "declared_faction_id": _integer(
            params, "declared_faction_id", None, 0, 2**63 - 1
        ),
        "search": search,
        "skill_id": _domain_filter_identifier(params, "skill_id"),
        "equipment_id": _domain_filter_identifier(params, "equipment_id"),
        "weapon_id": _domain_filter_identifier(params, "weapon_id"),
        "troop_type": _domain_filter_identifier(params, "troop_type"),
        "classification": _domain_filter_identifier(params, "classification"),
        "characteristic": _domain_filter_identifier(params, "characteristic"),
        "ava": ava,
        "ava_min": ava_min,
        "ava_max": ava_max,
        "points": points,
        "points_min": points_min,
        "points_max": points_max,
        "swc": swc,
        "swc_min": swc_min,
        "swc_max": swc_max,
        "limit": _integer(params, "limit", 50, 1, 200),
        "offset": _integer(params, "offset", 0, 0, 2**63 - 1),
        "mercs": _flag(params, "mercs"),
        "specops": _flag(params, "specops"),
        "teamops": _flag(params, "teamops"),
        "reinforcement": _flag(params, "reinforcement"),
        "descending": order == "desc",
        "extended": _flag(params, "extended"),
    }


class ApiHandler:
    """Own JSON API validation, domain projection, and response payloads."""

    def __init__(
        self,
        database: Database,
        rules_database: RulesDatabase | None,
        *,
        static_revision: str,
        snapshot_revision: str,
    ) -> None:
        self.database = database
        self.rules_database = rules_database
        self.static_revision = static_revision
        self.snapshot_revision = snapshot_revision
        self.trait_catalog = TraitCatalog(database, rules_database)
        self.state_catalog = StateCatalog(rules_database)
        self.skill_catalog = SkillCatalog(database, rules_database)
        self.equipment_catalog = EquipmentCatalog(database, rules_database)
        self.hacking_program_catalog = HackingProgramCatalog(database, rules_database)
        self.ammunition_catalog = RulesRecordCatalog(rules_database, "ammunition")
        self.label_catalog = LabelCatalog(rules_database)
        self.general_rules_catalog = RulesRecordCatalog(rules_database, "rules")
        self.glossary_catalog = GlossaryCatalog(database, rules_database)
        self.search_catalog = SearchCatalog(
            database,
            self.skill_catalog,
            self.equipment_catalog,
            self.trait_catalog,
            self.state_catalog,
            self.hacking_program_catalog,
            self.ammunition_catalog,
            self.label_catalog,
            self.general_rules_catalog,
            self.glossary_catalog,
        )
        self.catalog_rules = CatalogRules(rules_database)
        self.symbol_catalog = SymbolCatalog()
        self.legacy_armies = load_legacy_armies()
        self.fireteam_rules_reference = fireteam_reference(rules_database)
        if self.fireteam_rules_reference is not None:
            self.fireteam_rules_reference = enrich_maintained_text_references(
                database, rules_database, self.fireteam_rules_reference
            )

    def validate_health(self) -> None:
        """Exercise the minimum database paths required by the health endpoint."""

        self.database.list_armies()
        if self.rules_database is not None:
            self.state_catalog.list_states()

    def handle(self, path: str, query_string: str) -> WebResponse | None:
        """Return an API response, or None when this handler does not own the path."""

        if not path.startswith("/api/"):
            return None

        status = HTTPStatus.OK
        cache_control = "no-cache"
        payload = None
        if path == "/api/version":
            payload = {
                "version": __version__,
                "static_revision": self.static_revision,
                "snapshot_revision": self.snapshot_revision,
            }
            cache_control = "no-store"
        elif path == "/api/search":
            cache_control = API_CACHE_CONTROL
            try:
                params = parse_qs(query_string, keep_blank_values=True)
                unknown = sorted(set(params) - {"q", "cache_bust"})
                if unknown:
                    raise ValueError(f"Unknown query parameter: {unknown[0]}")
                if len(params.get("q", [])) != 1:
                    raise ValueError("Provide q exactly once")
                query = params["q"][0].strip()
                if not query:
                    raise ValueError("q must not be empty")
                if len(query) > 200:
                    raise ValueError("q must be at most 200 characters")
                if len(params.get("cache_bust", [])) > 1:
                    raise ValueError("Provide cache_bust only once")
                payload = {"items": self.search_catalog.search(query)}
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not search the database")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "Search is unavailable. Please try again."}
        elif path == "/api/glossary":
            cache_control = API_CACHE_CONTROL
            try:
                items = self.glossary_catalog.entries()
                for item in items:
                    item["description_tokens"] = maintained_text_tokens(
                        self.database, self.rules_database, item["description"]
                    )
                payload = {"items": items}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read Glossary")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The Glossary is unavailable. Please try again."}
        elif path == "/api/fireteams":
            cache_control = API_CACHE_CONTROL
            try:
                params = parse_qs(query_string, keep_blank_values=True)
                army_ref = _domain_filter_identifier(params, "army_id")
                if army_ref is None:
                    items = [dict(item) for item in self.database.list_fireteam_armies()]
                    for item in items:
                        attach_public_army_slug(self.database, item)
                    payload = {"items": items, "reference": self.fireteam_rules_reference}
                else:
                    payload = self.database.get_fireteam_chart(army_ref)
                    if payload is None:
                        status = HTTPStatus.NOT_FOUND
                        payload = {"error": "Fireteam chart not found"}
                    else:
                        attach_public_army_slug(self.database, payload["army"])
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read Fireteam chart")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The Fireteam chart is unavailable. Please try again."}
        elif path == "/api/unit-profile-help":
            cache_control = API_CACHE_CONTROL
            try:
                items = (
                    self.rules_database.unit_profile_help()
                    if self.rules_database is not None
                    else []
                )
                attributes = [
                    item
                    for item in self.glossary_catalog.embedded_entries()
                    if item["domain_slug"] == "attributes"
                ]
                payload = {"items": items, "attributes": attributes}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read Unit Profile help")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {
                    "error": "Unit Profile help is unavailable. Please try again."
                }
        elif path == "/api/skill-extras":
            cache_control = API_CACHE_CONTROL
            try:
                payload = {"items": self.skill_catalog.list_skill_extras()}
                payload = enrich_nested_unit_slugs(self.database, payload)
                payload = enrich_army_references(self.database, payload)
                payload = self.symbol_catalog.enrich_nested_units(payload)
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read skill modifiers")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The skill modifiers are unavailable. Please try again."}
        elif path in {"/api/skills", "/api/equipment", "/api/weapons"}:
            cache_control = API_CACHE_CONTROL
            try:
                catalog = path.removeprefix("/api/")
                if catalog == "skills":
                    items = self.skill_catalog.list_skills()
                elif catalog == "equipment":
                    items = self.equipment_catalog.list_equipment()
                else:
                    items = self.database.list_catalog_items(catalog)
                    for item in items:
                        attach_public_catalog_slug(self.database, catalog, item)
                payload = {"items": items}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read catalog")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The catalog is unavailable. Please try again."}
        elif path == "/api/traits":
            cache_control = API_CACHE_CONTROL
            try:
                payload = {"items": self.trait_catalog.list_traits()}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read traits")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The traits are unavailable. Please try again."}
        elif path == "/api/states":
            cache_control = API_CACHE_CONTROL
            try:
                payload = {"items": self.state_catalog.list_states()}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read states")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The states are unavailable. Please try again."}
        elif path == "/api/hacking-programs":
            cache_control = API_CACHE_CONTROL
            try:
                payload = {"items": self.hacking_program_catalog.list_programs()}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read Hacking Programs")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The Hacking Programs are unavailable. Please try again."}
        elif path in {"/api/ammunition", "/api/labels", "/api/rules"}:
            cache_control = API_CACHE_CONTROL
            try:
                if path == "/api/ammunition":
                    catalog = self.ammunition_catalog
                elif path == "/api/labels":
                    catalog = self.label_catalog
                else:
                    catalog = self.general_rules_catalog
                payload = {"items": catalog.list_items()}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read rules-reference catalog")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {
                    "error": "The reference catalog is unavailable. Please try again."
                }
        elif match := SKILL_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                identifier = match.group("identifier")
                skill_ref = int(identifier) if identifier.isdigit() else identifier
                payload = self.skill_catalog.get_skill(skill_ref)
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Skill not found"}
                else:
                    payload = enrich_nested_unit_slugs(self.database, payload)
                    payload = enrich_army_references(self.database, payload)
                    payload = self.symbol_catalog.enrich_nested_units(payload)
                    payload = enrich_rule_relation_references(self.database, payload)
                    payload = enrich_maintained_text_references(
                        self.database, self.rules_database, payload
                    )
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read skill")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The skill is unavailable. Please try again."}
        elif match := EQUIPMENT_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                identifier = match.group("identifier")
                item_ref = int(identifier) if identifier.isdigit() else identifier
                payload = self.equipment_catalog.get_equipment(item_ref)
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Reference item not found"}
                else:
                    payload["hacking_programs"] = (
                        self.hacking_program_catalog.programs_for_equipment(
                            payload.get("slug") or payload["id"]
                        )
                    )
                    payload = self.trait_catalog.enrich_catalog_item(payload)
                    payload = self.catalog_rules.enrich_catalog_item("equipment", payload)
                    payload = enrich_nested_unit_slugs(self.database, payload)
                    payload = enrich_army_references(self.database, payload)
                    payload = self.symbol_catalog.enrich_nested_units(payload)
                    payload = enrich_rule_relation_references(self.database, payload)
                    payload = enrich_maintained_text_references(
                        self.database, self.rules_database, payload
                    )
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read reference item")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The reference item is unavailable. Please try again."}
        elif match := WEAPON_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                identifier = match.group("identifier")
                item_ref = int(identifier) if identifier.isdigit() else identifier
                payload = self.database.get_catalog_item("weapons", item_ref)
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Reference item not found"}
                else:
                    attach_public_catalog_slug(self.database, "weapons", payload)
                    payload = self.trait_catalog.enrich_catalog_item(payload)
                    payload = self.catalog_rules.enrich_catalog_item("weapons", payload)
                    payload = enrich_nested_unit_slugs(self.database, payload)
                    payload = enrich_army_references(self.database, payload)
                    payload = self.symbol_catalog.enrich_nested_units(payload)
                    payload = enrich_rule_relation_references(self.database, payload)
                    payload = enrich_maintained_text_references(
                        self.database, self.rules_database, payload
                    )
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read reference item")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The reference item is unavailable. Please try again."}
        elif match := TRAIT_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                payload = self.trait_catalog.get_trait(match.group("identifier"))
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Trait not found"}
                else:
                    payload = enrich_nested_unit_slugs(self.database, payload)
                    payload = enrich_army_references(self.database, payload)
                    payload = self.symbol_catalog.enrich_nested_units(payload)
                    payload = enrich_rule_relation_references(self.database, payload)
                    payload = enrich_maintained_text_references(
                        self.database, self.rules_database, payload
                    )
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read trait")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The trait is unavailable. Please try again."}
        elif match := STATE_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                payload = self.state_catalog.get_state(match.group("identifier"))
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "State not found"}
                else:
                    payload = enrich_rule_relation_references(self.database, payload)
                    payload = enrich_maintained_text_references(
                        self.database, self.rules_database, payload
                    )
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read state")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The state is unavailable. Please try again."}
        elif match := HACKING_PROGRAM_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                identifier = match.group("identifier")
                program_ref = int(identifier) if identifier.isdigit() else identifier
                payload = self.hacking_program_catalog.get_program(program_ref)
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Hacking Program not found"}
                else:
                    payload = enrich_rule_relation_references(self.database, payload)
                    payload = enrich_maintained_text_references(
                        self.database, self.rules_database, payload
                    )
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read Hacking Program")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The Hacking Program is unavailable. Please try again."}
        elif match := AMMUNITION_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                payload = self.ammunition_catalog.get_item(match.group("identifier"))
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Ammunition not found"}
                else:
                    payload = enrich_rule_relation_references(self.database, payload)
                    payload = enrich_maintained_text_references(
                        self.database, self.rules_database, payload
                    )
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read Ammunition")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {
                    "error": "The Ammunition reference is unavailable. Please try again."
                }
        elif match := RULE_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                payload = self.general_rules_catalog.get_item(match.group("identifier"))
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "General rule not found"}
                else:
                    payload = enrich_rule_relation_references(self.database, payload)
                    payload = enrich_maintained_text_references(
                        self.database, self.rules_database, payload
                    )
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read General Rule")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {
                    "error": "The General Rules reference is unavailable. Please try again."
                }
        elif match := LABEL_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                payload = self.label_catalog.get_item(match.group("identifier"))
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Label not found"}
                else:
                    payload["description_tokens"] = maintained_text_tokens(
                        self.database, self.rules_database, payload["description"]
                    )
                    used_by: list[dict[str, str]] = []
                    seen_hrefs: set[str] = set()
                    if self.rules_database is not None:
                        for record in self.rules_database.composed_records_using_label(
                            payload["id"]
                        ):
                            domain = public_rule_record_domain(record)
                            if domain is None:
                                continue
                            href = _public_reference_href(
                                rule_record_public_reference(self.database, record)
                            )
                            if href is None or href in seen_hrefs:
                                continue
                            seen_hrefs.add(href)
                            used_by.append(
                                {
                                    "catalog": domain.slug,
                                    "catalog_name": domain.plural_name,
                                    "name": str(record["name"]),
                                    "href": href,
                                }
                            )
                    payload["used_by"] = sorted(
                        used_by,
                        key=lambda item: (
                            item["catalog_name"].casefold(),
                            item["name"].casefold(),
                            item["href"],
                        ),
                    )
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read Label")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {
                    "error": "The Label reference is unavailable. Please try again."
                }
        elif path == "/api/armies":
            cache_control = API_CACHE_CONTROL
            try:
                items = [dict(item) for item in self.database.list_armies()]
                for item in items:
                    attach_public_army_slug(self.database, item)

                current_by_id = {item["id"]: item for item in items}
                for legacy_army in self.legacy_armies:
                    if legacy_army.id in current_by_id:
                        raise ValueError(
                            f"Legacy Army {legacy_army.id} overlaps a current Army identity"
                        )
                    items.append(legacy_army.as_api_item())

                items.sort(key=lambda item: int(item["id"]))
                armies_by_id = {item["id"]: item for item in items}
                for item in items:
                    item["out_of_catalog"] = army_overview_out_of_catalog(
                        item, armies_by_id=armies_by_id
                    )
                    item["overview_group"] = army_overview_group(
                        item, armies_by_id=armies_by_id
                    )
                    item["overview_description"] = army_overview_description(
                        item, armies_by_id=armies_by_id
                    )
                payload = enrich_army_references(self.database, {"items": items})
                self.symbol_catalog.enrich_armies(payload["items"])
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read armies")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The database is unavailable. Please try again."}
        elif path == "/api/visible-unit-ids":
            cache_control = API_CACHE_CONTROL
            try:
                filters = _unit_query(query_string)
                payload = {
                    "ids": self.database.visible_unit_ids(
                        mercs=filters["mercs"],
                        specops=filters["specops"],
                        teamops=filters["teamops"],
                        reinforcement=filters["reinforcement"],
                    )
                }
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read visible unit IDs")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The database is unavailable. Please try again."}
        elif path == "/api/unit-filters":
            cache_control = API_CACHE_CONTROL
            try:
                payload = self.database.list_unit_filter_values()
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read Unit filter values")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The database is unavailable. Please try again."}
        elif path == "/api/units":
            cache_control = API_CACHE_CONTROL
            try:
                query = _unit_query(query_string)
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            else:
                try:
                    logical_unit_ids = self.equipment_catalog.logical_unit_ids_for_filter(
                        query.get("equipment_id")
                    )
                    if logical_unit_ids is not None:
                        query["equipment_id"] = None
                        query["_logical_unit_ids"] = logical_unit_ids
                    payload = self.database.list_units(**query)
                    payload = {
                        **payload,
                        "items": enrich_unit_items(self.database, payload["items"]),
                    }
                    payload = enrich_army_references(self.database, payload)
                    self.symbol_catalog.enrich_units(payload["items"])
                except ArmySelectionError as exc:
                    status = HTTPStatus.BAD_REQUEST
                    payload = {"error": str(exc)}
                except (OSError, ValueError, sqlite3.Error):
                    LOGGER.exception("Could not read units")
                    status = HTTPStatus.SERVICE_UNAVAILABLE
                    payload = {"error": "The database is unavailable. Please try again."}
        elif match := UNIT_API_PATH.fullmatch(path):
            cache_control = API_CACHE_CONTROL
            try:
                identifier = match.group("identifier")
                unit_ref = int(identifier) if identifier.isdigit() else identifier
                payload = self.database.get_unit(unit_ref)
                if payload is not None:
                    payload = self.skill_catalog.enrich_unit(payload)
                    payload = self.equipment_catalog.enrich_unit(payload)
                    payload = enrich_nested_catalog_slugs(
                        self.database,
                        payload,
                        frozenset({"equipment", "weapons"}),
                    )
                    attach_public_unit_slug(self.database, payload)
                    payload = enrich_army_references(self.database, payload)
                    self.symbol_catalog.enrich_unit(payload)
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Unit not found"}
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read unit")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The database is unavailable. Please try again."}
        else:
            status = HTTPStatus.NOT_FOUND
            payload = {"error": "Resource not found"}

        return WebResponse.json(payload, status=status, cache_control=cache_control)
