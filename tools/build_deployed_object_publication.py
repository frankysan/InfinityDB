"""Build the pinned deployed-object reference JSON for release packaging.

Developer/release build only. Production consumes the generated artifact
without reading the raw Army normalized tables or working-tree curated JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from infinity_db.deployed_object_builder import build_deployed_objects

ROOT = Path(__file__).resolve().parents[1]


def _digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def build_publication(
    army_db: Path,
    rules_db: Path,
    curated_source: Path,
    delivery_reviews: Path,
    candidate_reviews: Path,
) -> dict[str, Any]:
    """Project only validated review evidence; pin both shipped databases."""
    publication = build_deployed_objects(
        army_db, curated_source, delivery_reviews, candidate_reviews,
    )
    publication["sourceSnapshot"]["rulesDatabaseSha256"] = _digest(rules_db)
    return publication


def publication_bytes(publication: dict[str, Any]) -> bytes:
    return (json.dumps(
        publication, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ) + "\n").encode("utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=ROOT / "data/generated/infinity.db")
    parser.add_argument("--rules-db", type=Path, default=ROOT / "data/generated/rules.db")
    parser.add_argument(
        "--curated-source", type=Path,
        default=ROOT / "data/curated/rules/n5-core-v5.3.json",
    )
    parser.add_argument(
        "--delivery-reviews", type=Path,
        default=ROOT / "config/validation/deployed-object-delivery-reviews.json",
    )
    parser.add_argument(
        "--candidate-reviews", type=Path,
        default=ROOT / "config/validation/deployed-object-candidate-reviews.json",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data/generated/deployed-objects.json"
    )
    parser.add_argument("--check", action="store_true", help="Verify an existing artifact only")
    migration = parser.add_mutually_exclusive_group()
    migration.add_argument(
        "--stage-restrictions-v9", type=Path,
        help="Stage v9 rules.db and paired publication under ignored local/",
    )
    migration.add_argument(
        "--promote-restrictions-v9", type=Path,
        help="Promote a verified v9 pair with v8 recovery copies",
    )
    migration.add_argument(
        "--refresh-isolated-context-v9", action="store_true",
        help="Refresh the exact reviewed Isolated State contextual links in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-core-pdf-pin-v9", action="store_true",
        help="Pin the reviewed English N5.3 PDF in the matched v9 release pair",
    )
    migration.add_argument(
        "--refresh-pdf-source-pins-v9", action="store_true",
        help="Verify and publish missing byte pins for already-cataloged PDFs in a v9 pair",
    )
    migration.add_argument(
        "--refresh-variant-semantics-v9", nargs="+", metavar="RECORD_ID",
        help="Append reviewed occurrence metadata for explicit records in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-movement-distance-v9", action="store_true",
        help="Add verified Jump/Climb source links and distance metadata to a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-ecm-source-variants-v9", action="store_true",
        help="Promote exact Guided/Hacker ECM source variants in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-evo-trinity-v9", action="store_true",
        help="Promote exact EVO Trinity grant plus SR-2 in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-medikit-v9", action="store_true",
        help="Promote source-verified MediKit ranged +1B in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-medikit-target-ph-v9", action="store_true",
        help="Promote Skill-273 target PH replacements on canonical MediKit Equipment",
    )
    migration.add_argument(
        "--refresh-regeneration-v9", action="store_true",
        help="Promote Regeneration source-62 exact States Phase PH values",
    )
    migration.add_argument(
        "--refresh-chart-rerolls-v9", action="store_true",
        help="Promote exact Booty and MetaChemistry chart ReRoll signatures",
    )
    migration.add_argument(
        "--refresh-hacker-skill-v9", action="store_true",
        help="Promote source-1000 direct Hacker programs and exact upgrades",
    )
    migration.add_argument(
        "--refresh-vulnerability-viral-v9", action="store_true",
        help="Promote source-220 Viral weapon-name Immunity restriction",
    )
    migration.add_argument(
        "--refresh-decoy-v9", action="store_true",
        help="Promote exact Decoy source-215 additional replica counts",
    )
    migration.add_argument(
        "--refresh-ft-master-v9", action="store_true",
        help="Promote exact FT Master source-261 listed-Unit cancellation triggers",
    )
    migration.add_argument(
        "--refresh-tagcom-v9", action="store_true",
        help="Promote exact ordered TAGCom Dodge/GizmoKit recipient modifiers",
    )
    migration.add_argument(
        "--refresh-remdriver-v9", action="store_true",
        help="Promote exact RemDriver source-255 compound Attribute signatures",
    )
    migration.add_argument(
        "--refresh-impersonation-v9", action="store_true",
        help="Promote exact Impersonation IMP-2 Skill variant in matched v9 artifacts",
    )
    migration.add_argument(
        "--refresh-khd-v9", action="store_true",
        help="Promote exact KHD source variants in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-deactivator-v9", action="store_true",
        help="Promote exact Deactivator Burst and ReRoll source extras in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-gizmokit-target-ph-v9", action="store_true",
        help="Promote Skill-listed target PH replacements on canonical GizmoKit Equipment",
    )
    migration.add_argument(
        "--refresh-gizmokit-v9", action="store_true",
        help="Promote source-verified GizmoKit ranged +1B in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-bangbomb-skill-v9", action="store_true",
        help="Promote Skill-266 +4 via the existing restricted Bangbomb Equipment effect",
    )
    migration.add_argument(
        "--refresh-bangbomb-v9", action="store_true",
        help="Promote source-verified Bangbomb Dodge +4 extras in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-tinbot-firewall-v9", action="store_true",
        help="Promote exact TinBot Firewall Comms modifiers in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-tinbot-other-v9", action="store_true",
        help="Promote reviewed TinBot Discover/ECM Guided extras in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-hacking-program-grants-v9", action="store_true",
        help="Promote exact unmodified Hacking Device program grants in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-hacking-program-mods-v9", action="store_true",
        help="Promote exact Hacking Device B/PS/Special Die modifiers in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-hacking-saving-rolls-v9", action="store_true",
        help="Promote exact named-program Hacking Device SR modifiers in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-hacking-firewall-v9", action="store_true",
        help="Promote exact Hacking Device Firewall Comms-defense extras in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-hacking-trinity-access-v9", action="store_true",
        help="Add exact reviewed Trinity grants in a matched v9 pair",
    )
    migration.add_argument(
        "--refresh-hacking-combinations-v9", action="store_true",
        help="Promote only exact multi-extra Hacking Device signatures in a matched v9 pair",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if (
        args.stage_restrictions_v9 is not None
        or args.promote_restrictions_v9 is not None
        or args.refresh_isolated_context_v9
        or args.refresh_core_pdf_pin_v9
        or args.refresh_pdf_source_pins_v9
        or args.refresh_variant_semantics_v9 is not None
        or args.refresh_movement_distance_v9
        or args.refresh_tinbot_firewall_v9
        or args.refresh_bangbomb_v9
        or args.refresh_bangbomb_skill_v9
        or args.refresh_medikit_v9
        or args.refresh_medikit_target_ph_v9
        or args.refresh_gizmokit_v9
        or args.refresh_gizmokit_target_ph_v9
        or args.refresh_deactivator_v9
        or args.refresh_khd_v9
        or args.refresh_impersonation_v9
        or args.refresh_remdriver_v9
        or args.refresh_tagcom_v9
        or args.refresh_ft_master_v9
        or args.refresh_decoy_v9
        or args.refresh_vulnerability_viral_v9
        or args.refresh_hacker_skill_v9
        or args.refresh_chart_rerolls_v9
        or args.refresh_regeneration_v9
        or args.refresh_evo_trinity_v9
        or args.refresh_ecm_source_variants_v9
        or args.refresh_tinbot_other_v9
        or args.refresh_hacking_program_grants_v9
        or args.refresh_hacking_program_mods_v9
        or args.refresh_hacking_saving_rolls_v9
        or args.refresh_hacking_firewall_v9
        or args.refresh_hacking_combinations_v9
        or args.refresh_hacking_trinity_access_v9
    ):
        if args.check:
            raise ValueError("--check cannot be combined with v9 migration operations")
        from tools.restrictions_v9_release import (
            promote_restrictions_v9,
            refresh_bangbomb_skill_v9_release,
            refresh_bangbomb_v9_release,
            refresh_chart_rerolls_v9_release,
            refresh_core_pdf_pin_v9_release,
            refresh_deactivator_v9_release,
            refresh_decoy_v9_release,
            refresh_ecm_source_variants_v9_release,
            refresh_evo_trinity_v9_release,
            refresh_ft_master_v9_release,
            refresh_gizmokit_target_ph_v9_release,
            refresh_gizmokit_v9_release,
            refresh_hacker_skill_v9_release,
            refresh_hacking_combinations_v9_release,
            refresh_hacking_firewall_v9_release,
            refresh_hacking_program_grants_v9_release,
            refresh_hacking_program_mods_v9_release,
            refresh_hacking_saving_rolls_v9_release,
            refresh_hacking_trinity_access_v9_release,
            refresh_impersonation_v9_release,
            refresh_isolated_context_v9_release,
            refresh_killer_hacking_v9_release,
            refresh_medikit_target_ph_v9_release,
            refresh_medikit_v9_release,
            refresh_movement_distance_v9_release,
            refresh_pdf_source_pins_v9_release,
            refresh_regeneration_v9_release,
            refresh_remdriver_v9_release,
            refresh_tagcom_v9_release,
            refresh_tinbot_firewall_v9_release,
            refresh_tinbot_other_v9_release,
            refresh_variant_semantics_v9_release,
            refresh_vulnerability_viral_v9_release,
            stage_restrictions_v9,
        )

        if args.refresh_ecm_source_variants_v9:
            backup = refresh_ecm_source_variants_v9_release()
            print("Promoted two exact ECM source variants in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_evo_trinity_v9:
            backup = refresh_evo_trinity_v9_release()
            print("Refreshed exact EVO Trinity grant and SR-2 in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_medikit_target_ph_v9:
            backup = refresh_medikit_target_ph_v9_release()
            print("Refreshed Skill-273 target PH extras on MediKit Equipment in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_medikit_v9:
            backup = refresh_medikit_v9_release()
            print("Refreshed exact ranged MediKit Burst upgrade in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_regeneration_v9:
            backup = refresh_regeneration_v9_release()
            print("Refreshed exact Regeneration Skill-62 PH replacements in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_chart_rerolls_v9:
            backup = refresh_chart_rerolls_v9_release()
            print("Refreshed exact Booty/MetaChemistry ReRolls in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_hacker_skill_v9:
            backup = refresh_hacker_skill_v9_release()
            print("Refreshed exact Hacker Skill-1000 parameters in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_vulnerability_viral_v9:
            backup = refresh_vulnerability_viral_v9_release()
            print("Refreshed exact Viral Vulnerability source-220 variant in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_decoy_v9:
            backup = refresh_decoy_v9_release()
            print("Refreshed exact Decoy Skill-215 counts in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_ft_master_v9:
            backup = refresh_ft_master_v9_release()
            print("Refreshed exact FT Master Skill-261 source variants in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_tagcom_v9:
            backup = refresh_tagcom_v9_release()
            print("Refreshed exact TAGCom Skill-270 signatures in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_remdriver_v9:
            backup = refresh_remdriver_v9_release()
            print("Refreshed exact RemDriver compound signatures in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_impersonation_v9:
            backup = refresh_impersonation_v9_release()
            print("Refreshed exact Impersonation IMP-2 Skill variant in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_khd_v9:
            backup = refresh_killer_hacking_v9_release()
            print("Refreshed exact KHD upgrades in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_deactivator_v9:
            backup = refresh_deactivator_v9_release()
            print("Refreshed exact Deactivator Burst and ReRoll extras in matched v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_gizmokit_target_ph_v9:
            backup = refresh_gizmokit_target_ph_v9_release()
            print("Refreshed Skill-254 target PH extras on GizmoKit Equipment in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_gizmokit_v9:
            backup = refresh_gizmokit_v9_release()
            print("Refreshed exact ranged GizmoKit Burst upgrade in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_bangbomb_skill_v9:
            backup = refresh_bangbomb_skill_v9_release()
            print("Refreshed exact Skill-266 Bangbomb on canonical Equipment in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_bangbomb_v9:
            backup = refresh_bangbomb_v9_release()
            print("Refreshed exact Bangbomb Dodge +4 semantics in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_hacking_trinity_access_v9:
            backup = refresh_hacking_trinity_access_v9_release()
            print("Added exact Trinity program access to reviewed device variants.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_hacking_combinations_v9:
            backup = refresh_hacking_combinations_v9_release()
            print("Refreshed exact Hacking Device compound extras in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_hacking_firewall_v9:
            backup = refresh_hacking_firewall_v9_release()
            print("Refreshed reviewed Hacking Device Firewall extras in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_hacking_saving_rolls_v9:
            backup = refresh_hacking_saving_rolls_v9_release()
            print("Refreshed exact Hacking Device named-program SR modifiers in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_hacking_program_mods_v9:
            backup = refresh_hacking_program_mods_v9_release()
            print("Refreshed reviewed Hacking Device B/PS/Special Die upgrades in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_hacking_program_grants_v9:
            backup = refresh_hacking_program_grants_v9_release()
            print("Refreshed reviewed unmodified Hacking Device UPGRADE grants in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_tinbot_other_v9:
            backup = refresh_tinbot_other_v9_release()
            print("Refreshed reviewed TinBot Discover/ECM Guided extras in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_tinbot_firewall_v9:
            backup = refresh_tinbot_firewall_v9_release()
            print("Refreshed reviewed TinBot Firewall source modifiers in v9 artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_movement_distance_v9:
            backup = refresh_movement_distance_v9_release()
            print("Refreshed reviewed Jump/Climb distance metadata in v9 release artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_variant_semantics_v9 is not None:
            backup = refresh_variant_semantics_v9_release(set(args.refresh_variant_semantics_v9))
            print("Refreshed reviewed variant metadata in v9 release artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_pdf_source_pins_v9:
            backup = refresh_pdf_source_pins_v9_release()
            print("Refreshed verified PDF source pins in v9 release artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_core_pdf_pin_v9:
            backup = refresh_core_pdf_pin_v9_release()
            print("Refreshed the reviewed English N5.3 source pin in v9 release artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.refresh_isolated_context_v9:
            backup = refresh_isolated_context_v9_release()
            print("Refreshed the reviewed Isolated links in v9 release artifacts.")
            print(f"Original matched v9 release pair retained: {backup}")
            return 0
        if args.stage_restrictions_v9 is not None:
            report = stage_restrictions_v9(args.stage_restrictions_v9)
            print("Staged verified v9 rules database and paired deployed-object publication.")
            print(f"Staged rules SHA-256: {report['staged']['data/generated/rules.db']}")
            print(f"Staging report: {args.stage_restrictions_v9 / 'staging-report.json'}")
            print("No tracked artifacts were modified.")
            return 0
        if args.promote_restrictions_v9 is None:
            raise ValueError("Missing v9 promotion staging directory")
        backup = promote_restrictions_v9(args.promote_restrictions_v9)
        print("Promoted v9 rules database and matching deployed-object publication.")
        print(f"Original v8 release pair retained: {backup}")
        return 0
    publication = build_publication(
        args.army_db, args.rules_db, args.curated_source,
        args.delivery_reviews, args.candidate_reviews,
    )
    expected = publication_bytes(publication)
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != expected:
            raise SystemExit("Deployed-object publication missing or stale; rebuild it")
        print(f"Deployed-object publication verified: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(expected)
        print(f"Deployed-object publication built: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
