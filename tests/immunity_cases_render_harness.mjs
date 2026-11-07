// Exercise the real shared rules-card renderer; no browser dependency.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

class Node {
  constructor(tag, value = "") {
    this.tag = tag;
    this.value = value;
    this.children = [];
    this.className = "";
    this.href = "";
  }
  append(...items) {
    for (const item of items) {
      if (typeof item === "string") this.children.push(new Node("#text", item));
      else if (item.tag === "#fragment") this.children.push(...item.children);
      else this.children.push(item);
    }
  }
  set textContent(value) { this.children = [new Node("#text", String(value))]; }
  get textContent() {
    return this.tag === "#text" ? this.value
      : this.children.map((child) => child.textContent).join("");
  }
  setAttribute() {}
  addEventListener() {}
}
globalThis.window = {
  infinityThemeBootstrap: { preferenceKey: "test", normalizeSelection: (v) => v,
    applySelection: (v) => v }, addEventListener() {},
};
globalThis.document = {
  cookie: "", addEventListener() {}, createElement: (tag) => new Node(tag),
  createTextNode: (value) => new Node("#text", value),
  createDocumentFragment: () => new Node("#fragment"),
};
const { rulesReferenceArticle } = await import(
  "../src/infinity_db/web/static/rules-reference.js"
);
const source = JSON.parse(readFileSync(
  new URL("../data/curated/rules/n5-core-v5.3.json", import.meta.url), "utf8"
));
const immunity = source.records.find((record) => record.id === "skill:immunity");
function descendants(node, predicate) {
  return node.children.flatMap((child) => [
    ...(predicate(child) ? [child] : []), ...descendants(child, predicate),
  ]);
}
const article = rulesReferenceArticle(immunity);
const headings = descendants(article, (node) => node.className === "detail-fact-heading")
  .map((node) => node.textContent);
assert.deepEqual(headings.slice(0, 5), [
  "Requirements", "Effects", "Restrictions", "Clarifications and examples", "Reviewed interactions",
]);
const allGroups = descendants(article, (node) => node.className === "detail-fact-group");
const effects = allGroups.find((node) => descendants(node, (c) => c.className === "detail-fact-heading")
  .some((heading) => heading.textContent === "Effects"));
assert.ok(effects);
assert.doesNotMatch(effects.textContent, /Printed Example 2|The printed Flash Pulse example/);
const clarifications = allGroups.find((node) => descendants(node, (c) => c.className === "detail-fact-heading")
  .some((heading) => heading.textContent === "Clarifications and examples"));
assert.ok(clarifications);
assert.equal(descendants(clarifications, (node) => node.tag === "li").length, 4);
assert.match(clarifications.textContent, /Printed Example 2/);
assert.match(clarifications.textContent, /The printed \[\[weapon:flash-pulse\|Flash Pulse\]\] example/);
const groups = descendants(article, (node) => node.className === "detail-fact-group immunity-reviewed-cases");
assert.equal(groups.length, 1);
const group = groups[0];
const allCases = descendants(group, (node) => node.tag === "li");
assert.equal(allCases.length, 23);
const grenade = allCases[4];
assert.match(grenade.textContent, /Immunity \(BTS\) vs E\/M Grenade Launcher/);
assert.match(grenade.textContent, /2 Saving Rolls on a hit \(3 on a Critical\) using BTS\/2/);
assert.match(grenade.textContent, /1 Saving Roll on a hit \(2 on a Critical\) using full BTS/);
assert.match(grenade.textContent, /Non-Lethal still applies, preventing Wounds/);
assert.match(grenade.textContent, /Isolated and conditional Immobilized-B State effects are ignored/);
assert.match(grenade.textContent, /Circular Impact Template and Speculative Attack/);
assert.match(grenade.textContent, /not Comms Attacks or arbitrary E\/M weapons/);
const comms = allCases[5];
assert.match(comms.textContent, /Comms exception: Oblivion vs Immunity \(BTS \/ State: Isolated\)/);
assert.match(comms.textContent, /Immunity \(BTS\) does not apply to Comms Attacks/);
assert.match(comms.textContent, /neither removes the AP BTS reduction nor prevents Isolated/);
assert.match(comms.textContent, /Immunity \(State: Isolated\) does apply and prevents entry into Isolated/);
assert.match(comms.textContent, /without cancelling the underlying Saving Roll/);
assert.match(comms.textContent, /Burst 2 counts attack dice, not Saving Rolls/);
assert.match(comms.textContent, /not all hacking or Comms effects/);
const cases = [...allCases.slice(0, 4), ...allCases.slice(6)];
assert.equal(cases.length, 21);
// Every reviewed case uses the same semantic list-item structure with
// a navigable title, an outcome, and its own source-evidence classification.
for (const item of cases) {
  assert.equal(descendants(item, (node) => node.tag === "strong").length, 1);
  assert.equal(descendants(item, (node) => node.className === "detail-copy").length, 1);
  assert.equal(descendants(item, (node) => node.className === "detail-source").length, 1);
}
const labels = cases.map((item) => descendants(item,
  (node) => node.className === "detail-source")[0].textContent);
assert.deepEqual(labels, [
  "Explicit N5.3 p. 96, Example 4", "Derived from reviewed general rules",
  "Explicit N5.3 p. 96, Example 1",
  "Explicit N5.3 p. 96, Example 2",
  "Explicit source example", "Explicit N5.3 p. 96, Example 3",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
  "Derived from reviewed general rules",
]);
assert.match(cases[0].textContent, /non-Comms attacks/);
for (const item of cases.slice(12)) {
  assert.match(item.textContent, /Applies to the reviewed non-Comms attack only/);
}
assert.match(cases[2].textContent, /Immunity \(ARM\) vs Missile Launcher \(Blast Mode\)/);
assert.match(cases[2].textContent, /3 Saving Rolls using ARM on a hit/);
assert.match(cases[2].textContent, /1 Saving Roll using full ARM on a hit or 2 Saving Rolls on a Critical/);
assert.match(cases[2].textContent, /Hit Mode uses AP\+EXP with ARM\/2 instead/);
assert.match(cases[3].textContent, /Immunity \(ARM\) vs Monofilament CC Weapon/);
assert.match(cases[3].textContent, /full ARM for 1 Saving Roll on a hit or 2 Saving Rolls on a Critical/);
assert.match(cases[3].textContent, /State: Dead is also ignored/);
assert.match(cases[3].textContent, /Ordinary failed Normal Ammunition Saving Rolls are not cancelled/);
assert.match(cases[5].textContent, /Immunity \(Enhanced\) vs Plasma Rifle/);
assert.match(cases[5].textContent, /1 ARM Saving Roll and 1 BTS Saving Roll/);
assert.doesNotMatch(cases[5].textContent, /Critical/);
assert.match(cases[6].textContent, /Immunity \(Critical\) vs Plasma Rifle/);
assert.match(cases[6].textContent, /2 ARM Saving Rolls and 1 BTS Saving Roll/);
assert.match(cases[6].textContent, /removes only the additional ARM Saving Roll/);
assert.match(cases[6].textContent, /leaving 1 ARM Saving Roll and 1 BTS Saving Roll/);
assert.match(cases[6].textContent, /not a printed Immunity example/);
assert.match(cases[7].textContent, /Immunity \(Critical\) vs AP\+T2 CC Weapon/);
assert.match(cases[7].textContent, /2 Saving Rolls using ARM\/2/);
assert.match(cases[7].textContent, /1 Saving Roll using ARM\/2 remains/);
assert.match(cases[7].textContent, /2 Wounds from T2/);
assert.match(cases[7].textContent, /1 Wound on failure/);
assert.match(cases[7].textContent, /AP still halves ARM/);
assert.match(cases[8].textContent, /Immunity \(Critical\) vs AP\+DA CC Weapon/);
assert.match(cases[8].textContent, /A hit requires 2 Saving Rolls using ARM\/2/);
assert.match(cases[8].textContent, /a Critical normally requires 3 Saving Rolls/);
assert.match(cases[8].textContent, /2 Saving Rolls using ARM\/2 remain because DA/);
assert.match(cases[8].textContent, /AP still halves ARM/);
assert.match(cases[8].textContent, /Anti-materiel remains a separate Weapon Trait/);
const combined = cases.map((node) => node.textContent);
assert.match(combined[9], /Immunity \(Critical\) vs AP\+EXP CC Weapon/);
assert.match(combined[9], /a Critical normally requires 4 Saving Rolls/);
assert.match(combined[9], /3 Saving Rolls using ARM\/2 remain because EXP/);
assert.match(combined[9], /AP still halves ARM/);
assert.match(combined[10], /Immunity \(Critical\) vs Silenced Pistol/);
assert.match(combined[10], /2 Saving Rolls using BTS\/2/);
assert.match(combined[10], /leaving 1 Saving Roll using BTS\/2/);
assert.match(combined[10], /Shock still inflicts 1 Wound per failed Saving Roll/);
assert.match(combined[10], /VITA 1 target directly to Dead on failure/);
assert.match(combined[10], /not adjudicated by this Saving Roll example/);
assert.match(combined[11], /Immunity \(Critical\) vs E\/M CC Weapon/);
assert.match(combined[11], /3 Saving Rolls using BTS\/2/);
assert.match(combined[11], /leaving 2 Saving Rolls using BTS\/2/);
assert.match(combined[11], /Normal still inflicts 1 Wound per failed Saving Roll/);
assert.match(combined[11], /Immobilized-B for HI, TAG, REM or VH targets/);
assert.match(combined[11], /There is no additional ARM Saving Roll/);

assert.match(combined[0], /failed BTS Saving Roll still causes Stunned without Wounds/);
assert.match(combined[0], /the Saving Roll remains BTS/);
assert.match(combined[0], /Explicit N5\.3 p\. 96, Example 4/);
assert.match(combined[1], /Immunity \(BTS\) vs standalone E\/Mitter/);
assert.match(combined[1], /2 Saving Rolls on a hit \(3 on a Critical\) at BTS\/2/);
assert.match(combined[1], /1 Saving Roll on a hit \(2 on a Critical\) at BTS/);
assert.match(combined[1], /Non-Lethal.*inflicts no Wounds/);
assert.match(combined[1], /Armed Turret E\/Mitter discrepancy is not adjudicated/);
assert.match(combined[4], /weapon with “Viral” in its name/);
assert.match(combined[4], /not a rule for individual Ammunition components/);
assert.match(combined[12], /1 Saving Roll on a hit \(2 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
assert.match(combined[13], /1 Saving Roll on a hit \(2 on a Critical\).*3 Saving Rolls on a hit \(4 on a Critical\)/);
assert.match(combined[14], /2 Saving Rolls on a hit \(3 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
assert.match(combined[14], /AP component is ignored; DA still applies/);
assert.match(combined[15], /Immunity \(AP\) vs AP \+ SHOCK.*Silenced Pistol/);
assert.match(combined[15], /1 Saving Roll on a hit \(2 on a Critical\) using BTS, rather than 1 Saving Roll on a hit \(2 on a Critical\) using BTS\/2/);
assert.match(combined[15], /Shock effect still sends a VITA 1 target directly to Dead/);
assert.match(combined[15], /Silent \(-6\) remains a separately conditional Trait/);
assert.match(combined[16], /Immunity \(AP\) vs AP \+ T2.*AP\+T2 CC Weapon/);
assert.match(combined[16], /1 Saving Roll on a hit \(2 on a Critical\) using ARM, rather than 1 Saving Roll on a hit \(2 on a Critical\) using ARM\/2/);
assert.match(combined[16], /failed hit Saving Roll still inflicts 2 Wounds/);
assert.match(combined[16], /failed additional Critical Saving Roll inflicts only 1 Wound/);
assert.match(combined[16], /Identify which die is the hit roll/);
assert.match(combined[16], /Anti-materiel Trait remains a separate Weapon property/);
assert.match(combined[17], /Immunity \(BTS\) vs N \+ E\/M.*E\/M CC Weapon/);
assert.match(combined[17], /1 Saving Roll on a hit \(2 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
assert.match(combined[18], /Immunity \(BTS\) vs AP \+ SHOCK.*Silenced Pistol/);
assert.match(combined[18], /1 Saving Roll on a hit \(2 on a Critical\) using BTS, rather than 1 Saving Roll on a hit \(2 on a Critical\) using BTS\/2/);
assert.match(combined[18], /Both AP and Shock special effects are ignored/);
assert.match(combined[18], /failed Normal Saving Roll can still inflict a Wound/);
assert.match(combined[18], /Silent \(-6\) concerns conditional Face to Face Dodge Rolls/);
assert.match(combined[18], /does not adjudicate its interaction with Immunity/);
assert.doesNotMatch(combined[18], /Shock effect still sends/);
assert.match(combined[19], /Immunity \(Shock\) vs AP \+ SHOCK.*Silenced Pistol/);
assert.match(combined[19], /1 Saving Roll on a hit \(2 on a Critical\) using BTS\/2/);
assert.match(combined[19], /SHOCK component is ignored; AP still applies/);
assert.match(combined[19], /VITA 1 direct-to-Dead effect is ignored/);
assert.match(combined[19], /AP still halves BTS/);
assert.match(combined[19], /each failed Saving Roll can still inflict 1 Wound/);
assert.doesNotMatch(combined[19], /Both AP and Shock special effects are ignored/);
assert.match(combined[20], /Immunity \(E\/M\) vs N \+ E\/M.*E\/M CC Weapon/);
assert.match(combined[20], /1 Saving Roll on a hit \(2 on a Critical\) using BTS, rather than 2 Saving Rolls on a hit \(3 on a Critical\) using BTS\/2/);
assert.match(combined[20], /E\/M component is ignored; N still applies/);
assert.match(combined[20], /Isolated \/ Immobilized-B effects/);
assert.match(combined[20], /additional Saving Roll per hit/);
assert.match(combined[20], /each failed Saving Roll can still inflict 1 Wound/);
assert.match(combined[20], /no additional ARM roll/);
assert.match(combined[20], /unless Immunity \(Critical\) also applies/);
for (const item of cases.slice(9)) assert.match(item.textContent, /Derived from reviewed general rules/);
assert.match(group.textContent, /Critical counts assume no Immunity \(Critical\)/);
const links = descendants(group, (node) => node.tag === "a");
for (const url of ["/weapons/flash-pulse", "/weapons/e-mitter", "/weapons/plasma-rifle",
  "/weapons/silenced-pistol", "/ammunition/shock", "/traits/silent-x", "/states/dead", "/skills/vulnerability", "/ammunition/ap",
  "/ammunition/da", "/ammunition/exp", "/ammunition/normal", "/ammunition/em",
  "/hacking-programs/oblivion", "/states/isolated",
  "/weapons/e-m-cc-weapon", "/weapons/e-m-grenade-launcher",
  "/traits/speculative-attack", "/weapons/ap-t2-cc-weapon",
  "/weapons/ap-da-cc-weapon", "/weapons/ap-exp-cc-weapon", "/ammunition/t2",
  "/states/immobilized-b", "/states/unconscious",
  "/weapons/missile-launcher", "/traits/impact-template",
  "/weapons/monofilament-cc-weapon", "/traits/arm-0",
  "/traits/anti-materiel", "/states/stunned",
  "/traits/non-lethal", "/traits/state"]) {
  assert.ok(links.some((link) => link.href === url), `Missing link ${url}`);
}
const other = rulesReferenceArticle({ id: "skill:unrelated", name: "Other",
  facts: { immunityInteraction: immunity.facts.immunityInteraction } });
assert.equal(descendants(other, (node) => node.className === "detail-fact-group immunity-reviewed-cases").length, 0);
const generic = rulesReferenceArticle({ id: "skill:example", name: "Example",
  facts: { requirements: ["A requirement"], effects: ["An effect"],
    restrictions: ["A restriction"], clarifications: ["An illustrated case"] } });
assert.deepEqual(descendants(generic, (node) => node.className === "detail-fact-heading")
  .map((node) => node.textContent), [
  "Requirements", "Effects", "Restrictions", "Clarifications and examples",
]);
console.log("23 reviewed Immunity cases, conditions, evidence labels and semantic links; ordered sections");
