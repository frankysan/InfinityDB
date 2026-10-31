// Convert reviewed, source-cited ammunition facts into display-only rows.
// This is deliberately not a Saving Roll calculator or a precedence engine.
function rollLabel(count) {
  return `${count} Saving Roll${count === 1 ? "" : "s"}`;
}

function woundLabel(count) {
  return `${count} Wound${count === 1 ? "" : "s"}`;
}

export function ammunitionFactRows(facts = {}, stateNames = {}) {
  const rows = [];
  const resolution = facts.ammunitionResolution;
  if (resolution) {
    if (resolution.rollsPerHit != null) {
      rows.push(["Hit", `${rollLabel(resolution.rollsPerHit)} per hit`]);
    }
    if (resolution.defenseModifier?.operation === "halve") {
      rows.push(["Defense", `Halve ${resolution.defenseModifier.attributes.join(" or ")} (as applicable)`]);
    }
    if (resolution.savingRoll) {
      const roll = resolution.savingRoll;
      const modifier = roll.modifier < 0 ? `−${Math.abs(roll.modifier)}` : `+${roll.modifier}`;
      rows.push(["Saving Roll", `${roll.attribute}${modifier}${
        roll.missingAttribute === "no-effect" ? "; no effect if the target lacks this Attribute" : ""
      }`]);
    }
    if (resolution.woundsPerFailedSave) {
      const wounds = resolution.woundsPerFailedSave;
      rows.push(["Failed hit roll", `${woundLabel(wounds.hit)} per failed Saving Roll`]);
      if (wounds.criticalAdditionalRoll !== wounds.hit) {
        rows.push(["Failed extra Critical roll", `${woundLabel(wounds.criticalAdditionalRoll)} per failed Saving Roll`]);
      }
    }
    for (const state of resolution.stateEffects || []) {
      let condition = "On a failed Saving Roll";
      if (state.targetTypes?.length) condition += `; ${state.targetTypes.join(", ")} targets only`;
      if (state.targetAttribute) {
        condition += `; ${state.targetAttribute.name} ${state.targetAttribute.equals} only`;
      }
      if (state.application === "bypass-unconscious") condition += "; bypasses Unconscious";
      rows.push([stateNames[state.stateId] || state.stateId, condition, state.stateId]);
    }
    if (resolution.gutsEffect?.result === "automatic-failure") {
      rows.push(["Guts Roll", "Automatically failed after a failed Saving Roll; Courage or equivalent is exempt"]);
    }
    if (resolution.criticalAdditionalSavingRolls != null) {
      rows.push(["Critical", `${rollLabel(resolution.criticalAdditionalSavingRolls)} in addition to the hit (subject to applicable exceptions)`]);
    }
  }
  const zone = facts.visibilityZone;
  if (zone) {
    rows.push(["Effect", "Zero Visibility Zone"]);
    rows.push(["Area", `${zone.template === "circular" ? "Circular Template" : zone.template}; ${zone.height} height`]);
    if (zone.expires === "start-of-states-phase") {
      rows.push(["Duration", "Until the start of the States Phase"]);
    }
    rows.push(["Multispectral Visors", zone.multispectralVisor === "blocked"
      ? "Cannot draw LoF through this zone"
      : "Can draw LoF through this zone"]);
    const opposition = zone.opposition;
    if (opposition) {
      rows.push(["Opposing Attacks",
        "Face to Face only against enemy Attacks requiring a Roll and LoF crossing the zone",
        opposition.ruleId]);
      rows.push(["Visor Attacks", opposition.visorAttack === "normal-roll"
        ? "Normal Rolls against placement; Smoke does not oppose these Attacks"
        : "Qualifying rolled Attacks through Eclipse can be Face to Face"]);
      rows.push(["Enemy Dodge", "A Dodge inside the Template is a Normal Roll, unopposed by placement"]);
      rows.push(["Template remains",
        "Win every applicable Face to Face Roll, or pass the unopposed Normal Roll"]);
      rows.push(["Critical", "No additional effect; apply the Face to Face rules", opposition.ruleId]);
    }
  }
  return rows;
}
