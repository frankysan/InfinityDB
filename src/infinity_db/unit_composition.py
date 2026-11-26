"""Shared Unit presentation composition for serving and offline publication."""

from __future__ import annotations

from typing import Any

from .army_slugs import enrich_army_references
from .catalog_slugs import enrich_nested_catalog_slugs
from .database import Database
from .equipment_catalog import EquipmentCatalog
from .skill_catalog import SkillCatalog
from .skill_config import SkillSourceClassification
from .symbol_catalog import SymbolCatalog
from .unit_presentation import enrich_unit_presentation
from .unit_slugs import attach_public_unit_slug


def present_unit(
    unit: dict[str, Any], *, database: Database,
    skill_catalog: SkillCatalog, equipment_catalog: EquipmentCatalog,
    symbol_catalog: SymbolCatalog,
    source_skill_classifications: tuple[SkillSourceClassification, ...] | None,
    optional_filters: dict[str, bool], requested_army: str | None = None,
    general_only: bool = False,
    classify_general: bool = True,
    materialized_general_profiles: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Use identical composition semantics during publication and serving."""
    if general_only:
        # General profiles need occurrence data, not source notes, charts,
        # selection constraints, composite options or Army detail metadata.
        # Keep every Army's profiles for snapshot-wide symbol resolution,
        # including occurrences excluded by the current optional filters.
        unit = {
            **{key: unit[key] for key in ("id", "name", "isc", "slug") if key in unit},
            "armies": [
                {
                    "id": army["id"],
                    "availability_flags": army.get("availability_flags", []),
                    "profiles": [
                        {key: value for key, value in profile.items() if key in {
                            "profile_identity", "display_name", "name", "group_id",
                            "type", "classification", "move_1", "move_2", "cc", "bs",
                            "ph", "wip", "arm", "bts", "vitality", "silhouette",
                            "is_structure", "ava", "logo_urls", "skills", "equipment",
                            "characteristics",
                        }}
                        for profile in army.get("profiles", ())
                    ],
                    "loadouts": [
                        {key: value for key, value in loadout.items() if key in {
                            "group_id", "skills", "equipment", "weapons", "orders",
                        }}
                        for loadout in army.get("loadouts", ())
                    ],
                }
                for army in unit.get("armies", ())
            ],
        }
    # Skill enrichment detaches the cached repository payload. All further
    # enrichment owns this copy, so no intermediate deep copies are needed.
    unit = skill_catalog.enrich_unit(unit)
    unit = equipment_catalog.enrich_unit(unit, in_place=True)
    unit = enrich_nested_catalog_slugs(
        database, unit, frozenset({"equipment", "weapons"}), in_place=True,
    )
    if not general_only:
        attach_public_unit_slug(database, unit)
        unit = enrich_army_references(database, unit, in_place=True)
    symbol_catalog.enrich_unit(unit)
    return enrich_unit_presentation(
        unit, optional_filters=optional_filters, requested_army=requested_army,
        source_skill_classifications=source_skill_classifications,
        general_only=general_only, classify_general=classify_general,
        materialized_general_profiles=materialized_general_profiles,
    )
