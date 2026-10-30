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
assert.equal(cases.length, 7);
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
  "Explicit source example", "Explicit source example",
  "Explicit N5.3 p. 96, Example 3",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
  "Derived from reviewed general rules", "Derived from reviewed general rules",
]);
assert.match(cases[0].textContent, /non-Comms attacks/);
for (const item of cases.slice(3)) {
  assert.match(item.textContent, /Applies to the reviewed non-Comms attack only/);
}
assert.match(cases[2].textContent, /Immunity \(Enhanced\) vs Plasma Rifle/);
assert.match(cases[2].textContent, /1 ARM Saving Roll and 1 BTS Saving Roll/);
assert.doesNotMatch(cases[2].textContent, /Critical/);
const combined = cases.map((node) => node.textContent);
assert.match(combined[0], /failed BTS Saving Roll still causes Stunned without Wounds/);
assert.match(combined[0], /the Saving Roll remains BTS/);
assert.match(combined[0], /Explicit source example/);
assert.match(combined[1], /weapon with “Viral” in its name/);
assert.match(combined[1], /not a rule for individual Ammunition components/);
assert.match(combined[3], /1 Saving Roll on a hit \(2 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
assert.match(combined[4], /1 Saving Roll on a hit \(2 on a Critical\).*3 Saving Rolls on a hit \(4 on a Critical\)/);
assert.match(combined[5], /2 Saving Rolls on a hit \(3 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
assert.match(combined[5], /AP component is ignored; DA still applies/);
assert.match(combined[6], /Immunity \(BTS\) vs N \+ E\/M.*E\/M CC Weapon/);
assert.match(combined[6], /1 Saving Roll on a hit \(2 on a Critical\).*2 Saving Rolls on a hit \(3 on a Critical\)/);
for (const item of cases.slice(3)) assert.match(item.textContent, /Derived from reviewed general rules/);
assert.match(group.textContent, /Critical counts assume no Immunity \(Critical\)/);
const links = descendants(group, (node) => node.tag === "a");
for (const url of ["/weapons/flash-pulse", "/weapons/plasma-rifle", "/skills/vulnerability", "/ammunition/ap",
  "/ammunition/da", "/ammunition/exp", "/ammunition/normal", "/ammunition/em",
  "/weapons/e-m-cc-weapon", "/states/stunned",
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
console.log("7 reviewed Immunity cases, conditions, evidence labels and semantic links; ordered sections");
