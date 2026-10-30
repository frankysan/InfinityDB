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
    : value === "explicit-n5.3-pdf-p96-example-3"
      ? "Explicit N5.3 p. 96, Example 3"
      : "Evidence classification unavailable";
const rollCount = (count) => `${count} Saving Roll${count === 1 ? "" : "s"}`;
const counts = (rolls) => `${rollCount(rolls.hitRolls)} on a hit (${rolls.criticalRolls} on a Critical)`;

function componentTokens(ids) {
  const labels = { normal: "N", em: "E/M" };
  return ids.flatMap((id, index) => {
    const slug = id.split(":")[1];
    return [
      ...(index ? [text(" + ")] : []),
      reference(id, labels[slug] || slug.toUpperCase()),
    ];
  });
}

export function immunityCaseRows(facts = {}) {
  const cases = facts.immunityInteraction;
  if (!cases) return [];
  const rows = [];
  for (const item of cases.reviewedWeaponCases || []) {
    if (item.when.weaponId === "weapon:flash-pulse") {
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
    } else if (item.when.weaponId === "weapon:e-mitter") {
      rows.push({
        title: [text(`Immunity (${item.when.immunity}) vs standalone `),
          reference(item.when.weaponId, "E/Mitter")],
        detail: [
          text(`The source's ${counts(item.withoutImmunity)} at ${item.withoutImmunity.savingAttribute} `),
          text(`become ${counts(item.withImmunity)} at ${item.withImmunity.savingAttribute}. `),
          reference("ammunition:em", "E/M"), text(" is treated as "),
          reference(item.ammunitionTreatedAs, "Normal"),
          text("; its Isolated/Immobilized-B effects are ignored. The "),
          reference("trait:non-lethal", "Non-Lethal"),
          text(" Trait still applies, so this weapon inflicts no Wounds. "),
          text("Only the source Weapon 25 non-Comms profile is reviewed; "),
          text("the Armed Turret E/Mitter discrepancy is not adjudicated."),
        ],
        evidence: evidence(item.evidence),
      });
    }
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
  for (const item of cases.reviewedSavingRollCases || []) {
    // Printed Plasma/Enhanced case is a Combined Saving Roll, not combined
    // Ammunition. These fixed source-reviewed rolls are not a calculator.
    if (item.when.weaponId !== "weapon:plasma-rifle") continue;
    const rolls = item.savingRolls.map(
      (roll) => `${roll.count} ${roll.attribute} Saving Roll${roll.count === 1 ? "" : "s"}`
    ).join(" and ");
    rows.push({
      title: [text(`Immunity (${item.when.immunity}) vs `),
        reference(item.when.weaponId, "Plasma Rifle")],
      detail: [
        text(`Still requires ${rolls}. `),
        reference(item.when.ammunitionId, "Normal Ammunition"),
        text(" is not a combined Ammunition type; treating it as Normal does not eliminate either Saving Roll Attribute. This is the exact printed example, not a general immunity calculation."),
      ],
      evidence: evidence(item.evidence),
    });
  }
  for (const item of cases.reviewedCombinedCases || []) {
    const partial = Array.isArray(item.withImmunity.ignoredComponents);
    const applied = item.withImmunity;
    rows.push({
      title: [
        text(`Immunity (${item.when.immunity}) vs `), ...componentTokens(item.components),
        ...(item.when.weaponId
          ? [text(" — "), reference(
              item.when.weaponId,
              ({
                "weapon:silenced-pistol": "Silenced Pistol",
                "weapon:ap-t2-cc-weapon": "AP+T2 CC Weapon",
                "weapon:e-m-cc-weapon": "E/M CC Weapon",
              })[item.when.weaponId] || "Reviewed Weapon"
            )] : []),
      ],
      detail: [
        text(`${counts(applied)} using ${applied.savingAttribute || item.when.savingAttribute}, rather than `),
        text(`${counts(item.withoutImmunity)}${item.withoutImmunity.savingAttribute
          ? ` using ${item.withoutImmunity.savingAttribute}` : ""}. `),
        ...(partial ? [text("The "), ...componentTokens(applied.ignoredComponents),
          text(" component is ignored; "), ...componentTokens(applied.remainingComponents),
          text(" still applies.")] : [text("The covered combined Ammunition counts as "),
          reference(applied.treatedAs, "Normal"), text(".")]),
        ...(item.when.weaponId === "weapon:silenced-pistol"
          ? [text(" On a failed Saving Roll, the "),
            reference("ammunition:shock", "Shock"),
            text(" effect still sends a VITA 1 target directly to "),
            reference("state:dead", "Dead"),
            text(" instead of Unconscious. The weapon's "),
            reference("trait:silent-x", "Silent (-6)"),
            text(" remains a separately conditional Trait.")] : []),
        ...(item.when.weaponId === "weapon:ap-t2-cc-weapon"
          ? [text(" A failed hit Saving Roll still inflicts "),
            text(`${applied.failedRollWounds.hit} Wounds`),
            text("; a failed additional Critical Saving Roll inflicts only "),
            text(`${applied.failedRollWounds.criticalAdditionalRoll} Wound`),
            text(". Identify which die is the hit roll and which is the extra Critical roll before rolling. The "),
            reference("trait:anti-materiel", "Anti-materiel"),
            text(" Trait remains a separate Weapon property.")] : []),
        text(" Applies to the reviewed non-Comms attack only."),
      ],
      evidence: evidence(item.evidence),
    });
  }
  return rows;
}
