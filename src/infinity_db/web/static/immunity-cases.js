// Present only curated, source-reviewed Immunity cases. Never evaluate a new attack.
const catalogs = {
  ammunition: "ammunition", weapon: "weapons", state: "states", trait: "traits",
  skill: "skills",
};
const text = (value) => ({ type: "text", text: value });
const reference = (id, label) => {
  const [kind, slug] = id.split(":");
  return {
    type: "reference", target: id, label,
    public_reference: { catalog: catalogs[kind], id: slug },
  };
};
const evidence = (value) => value === "derived-from-pinned-general-rules"
  ? "Derived from reviewed general rules"
  : value === "explicit-pinned-wiki-example" ? "Explicit source example"
    : "Evidence classification unavailable";
const rollCount = (count) => `${count} Saving Roll${count === 1 ? "" : "s"}`;
const counts = (rolls) => `${rollCount(rolls.hitRolls)} on a hit (${rolls.criticalRolls} on a Critical)`;

function componentTokens(ids) {
  return ids.flatMap((id, index) => [
    ...(index ? [text(" + ")] : []), reference(id, id.split(":")[1].toUpperCase()),
  ]);
}

export function immunityCaseRows(facts = {}) {
  const cases = facts.immunityInteraction;
  if (!cases) return [];
  const rows = [];
  for (const item of cases.reviewedWeaponCases || []) {
    // The source currently reviews Flash Pulse, not arbitrary BTS weapons.
    if (item.when.weaponId !== "weapon:flash-pulse") continue;
    rows.push({
      title: [text(`Immunity (${item.when.immunity}) vs `),
        reference(item.when.weaponId, "Flash Pulse")],
      detail: [
        text(`A failed ${item.when.savingAttribute} Saving Roll still causes `),
        reference(item.stateEffect.stateId, "Stunned"),
        text(" without Wounds. "),
        reference("ammunition:stun", "STUN"),
        text(" counts as "), reference(item.ammunitionTreatedAs, "Normal"),
        text(`, but the Saving Roll remains ${item.when.savingAttribute}; the explicit `),
        reference("trait:non-lethal", "Non-Lethal"), text(" and "),
        reference("trait:state", "State: Stunned"),
        text(" Trait exceptions still apply (non-Comms attacks)."),
      ],
      evidence: evidence(item.evidence),
    });
  }
  for (const item of cases.reviewedVulnerabilityCases || []) {
    rows.push({
      title: [text(`Immunity (${item.when.immunity}) + `),
        reference("skill:vulnerability", `Vulnerability (${item.when.vulnerability})`)],
      detail: [text(`Immunity cannot apply against a weapon with “${item.when.weaponNameContains}” `),
        text("in its name. This is a weapon-name example, not a rule for individual Ammunition components.")],
      evidence: evidence(item.evidence),
    });
  }
  for (const item of cases.reviewedCombinedCases || []) {
    const partial = Array.isArray(item.withImmunity.ignoredComponents);
    const applied = item.withImmunity;
    rows.push({
      title: [text(`Immunity (${item.when.immunity}) vs `), ...componentTokens(item.components)],
      detail: [
        text(`${counts(applied)} using ${item.when.savingAttribute}, rather than `),
        text(`${counts(item.withoutImmunity)}. `),
        ...(partial ? [text("The "), ...componentTokens(applied.ignoredComponents),
          text(" component is ignored; "), ...componentTokens(applied.remainingComponents),
          text(" still applies.")] : [text("The covered combined Ammunition counts as "),
          reference(applied.treatedAs, "Normal"), text(".")]),
        text(" Applies to the reviewed non-Comms attack only."),
      ],
      evidence: evidence(item.evidence),
    });
  }
  return rows;
}
