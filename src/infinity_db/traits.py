"""Shared Infinity rules-trait labels and concise rules summaries."""
# ruff: noqa: E501

from __future__ import annotations

TRAIT_DESCRIPTIONS = {
    "Anti-materiel": "Its Special Ammunition can affect structures and scenery.",
    "ARM = 0": "Reduces the target's ARM Attribute to 0 for Saving Rolls.",
    "ARO": "Only usable in ARO.",
    "BioWeapon": "Applies DA+Shock Special Ammunition against targets with VITA.",
    "Boost": "Applies the Boost rule when an enemy declares or executes an Order or ARO in its Zone of Control.",
    "BS Weapon (PH)": "Makes BS Attacks using PH instead of BS; BS rules and MODs affect PH instead.",
    "BS Weapon (WIP)": "Makes BS Attacks using WIP instead of BS; BS rules and MODs affect WIP instead.",
    "BTS = 0": "Reduces the target's BTS Attribute to 0 for Saving Rolls.",
    "Burst: Single Target": "All shots in the Burst must choose one target.",
    "CC": "Can be used to make CC Attacks.",
    "Concealed": "Uses the effects of Camouflaged State; its concealing marker has Silhouette 2.",
    "Continuous Damage": "After a failed Saving Roll, the target keeps making Saving Rolls until one succeeds or it enters Dead State.",
    "Deployable": "May be deployed as an independent battlefield element with its own profile and Attributes.",
    "Direct Template": "Uses Direct Template rules, firing the indicated Template.",
    "Disposable (X)": "Has limited uses. Each use is expended when declared, and all modes share the available uses.",
    "Double Shot": "In the Active Turn, may apply +1 Burst; with Disposable (2), this spends both uses.",
    "Impact Template": "Places the indicated Template at the point of impact.",
    "Improvised": "Imposes a -6 MOD to the user's relevant Attribute.",
    "Indiscriminate": "May be used or deployed despite Camouflage and Hiding Markers in its Area of Effect.",
    "Intuitive Attack": "Can be used to make Intuitive Attacks.",
    "Non-Lethal": "Never inflicts Wounds or requires Saving Rolls, regardless of ammunition added by other rules.",
    "Non-Reloadable": "Its expended Disposable uses cannot be regained.",
    "Perimeter": "When placed, applies Deployable and Perimeter, placing it completely inside the user's Zone of Control.",
    "Prior Deployment": "Must be placed during the Deployment Phase.",
    "Reflective": "Also affects Troopers with Marksmanship, Multispectral Visors, or specified equivalent Equipment.",
    "Silent (X)": "When used inside the target's Zone of Control but outside LoF, applies its bracketed MOD to Face to Face Dodge Rolls.",
    "Speculative Attack": "Can be used to make Speculative Attacks.",
    "State": "Causes the target to enter the Game State indicated in its profile.",
    "Suppressive Fire (SF)": "Allows the user to enter Suppressive Fire State and use its SF Mode profile.",
    "Target (Attribute)": "Only affects targets with the indicated VITA or STR Attribute.",
    "Targetless": "Can fire without designating an enemy target; in the Reactive Turn it requires LoF to the Active Trooper.",
    "Zone of Control (ZC)": "Its range is the user's Zone of Control (8 inches).",
}


def canonical_trait_name(value: object) -> str:
    """Map profile-specific trait values to their rules-reference identity."""
    name = str(value or "").strip()
    if name.startswith("["):
        return ""
    if name == "Suppressive Fire":
        return "Suppressive Fire (SF)"
    for prefix, canonical in (
        ("Disposable (", "Disposable (X)"),
        ("Direct Template (", "Direct Template"),
        ("Impact Template (", "Impact Template"),
        ("Silent (", "Silent (X)"),
        ("State:", "State"),
        ("Target (", "Target (Attribute)"),
        ("Bioweapon", "BioWeapon"),
        ("Continous Damage", "Continuous Damage"),
    ):
        if name.startswith(prefix):
            return canonical
    return name
