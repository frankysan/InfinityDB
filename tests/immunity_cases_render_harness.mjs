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
assert.equal(descendants(clarifications, (node) => node.tag === "li").length, 3);
assert.match(clarifications.textContent, /Printed Example 2/);
assert.match(clarifications.textContent, /The printed \[\[weapon:flash-pulse\|Flash Pulse\]\] example/);
const groups = descendants(article, (node) => node.className === "detail-fact-group immunity-reviewed-cases");
assert.equal(groups.length, 1);
const group = groups[0];
const cases = descendants(group, (node) => node.tag === "li");
assert.equal(cases.length, 14);
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
]);
assert.match(cases[0].textContent, /non-Comms attacks/);
for (const item of cases.slice(8)) {
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
const combined = cases.map((node) => node.textContent);
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
assert.match(combined[8], /1 Saving Roll on a hit \(2 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
assert.match(combined[9], /1 Saving Roll on a hit \(2 on a Critical\).*3 Saving Rolls on a hit \(4 on a Critical\)/);
assert.match(combined[10], /2 Saving Rolls on a hit \(3 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
assert.match(combined[10], /AP component is ignored; DA still applies/);
assert.match(combined[11], /Immunity \(AP\) vs AP \+ SHOCK.*Silenced Pistol/);
assert.match(combined[11], /1 Saving Roll on a hit \(2 on a Critical\) using BTS, rather than 1 Saving Roll on a hit \(2 on a Critical\) using BTS\/2/);
assert.match(combined[11], /Shock effect still sends a VITA 1 target directly to Dead/);
assert.match(combined[11], /Silent \(-6\) remains a separately conditional Trait/);
assert.match(combined[12], /Immunity \(AP\) vs AP \+ T2.*AP\+T2 CC Weapon/);
assert.match(combined[12], /1 Saving Roll on a hit \(2 on a Critical\) using ARM, rather than 1 Saving Roll on a hit \(2 on a Critical\) using ARM\/2/);
assert.match(combined[12], /failed hit Saving Roll still inflicts 2 Wounds/);
assert.match(combined[12], /failed additional Critical Saving Roll inflicts only 1 Wound/);
assert.match(combined[12], /Identify which die is the hit roll/);
assert.match(combined[12], /Anti-materiel Trait remains a separate Weapon property/);
assert.match(combined[13], /Immunity \(BTS\) vs N \+ E\/M.*E\/M CC Weapon/);
assert.match(combined[13], /1 Saving Roll on a hit \(2 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
for (const item of cases.slice(8)) assert.match(item.textContent, /Derived from reviewed general rules/);
assert.match(group.textContent, /Critical counts assume no Immunity \(Critical\)/);
const links = descendants(group, (node) => node.tag === "a");
for (const url of ["/weapons/flash-pulse", "/weapons/e-mitter", "/weapons/plasma-rifle",
  "/weapons/silenced-pistol", "/ammunition/shock", "/traits/silent-x", "/states/dead", "/skills/vulnerability", "/ammunition/ap",
  "/ammunition/da", "/ammunition/exp", "/ammunition/normal", "/ammunition/em",
  "/weapons/e-m-cc-weapon", "/weapons/ap-t2-cc-weapon", "/ammunition/t2",
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
console.log("14 reviewed Immunity cases, conditions, evidence labels and semantic links; ordered sections");
