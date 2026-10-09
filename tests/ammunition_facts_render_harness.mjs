// Probe the shared reference renderer with every reviewed base Ammunition record.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

class Node {
  constructor(tag, value = "") {
    this.tag = tag;
    this.children = [];
    this.className = "";
    this.href = "";
    this.value = value;
  }
  append(...items) {
    for (const item of items) {
      if (typeof item === "string") this.children.push(new Node("#text", item));
      else if (item.tag === "#fragment") this.children.push(...item.children);
      else this.children.push(item);
    }
  }
  set textContent(value) { this.children = [new Node("#text", String(value))]; }
  get textContent() { return this.tag === "#text"
    ? this.value : this.children.map((child) => child.textContent).join(""); }
  setAttribute() {}
  addEventListener() {}
}

globalThis.window = {
  infinityThemeBootstrap: {
    preferenceKey: "test", normalizeSelection: (value) => value,
    applySelection: (value) => value,
  },
  addEventListener() {},
};
globalThis.document = {
  cookie: "", addEventListener() {},
  createElement: (tag) => new Node(tag),
  createTextNode: (text) => new Node("#text", text),
  createDocumentFragment: () => new Node("#fragment"),
};

const { rulesReferenceArticle } = await import(
  "../src/infinity_db/web/static/rules-reference.js"
);
const documentSource = JSON.parse(readFileSync(
  new URL("../data/curated/rules/n5-core-v5.3.json", import.meta.url), "utf8"
));
const ammunition = documentSource.records.filter((record) => record.kind === "ammunition");
assert.equal(ammunition.length, 11);

function descendants(element, predicate) {
  const result = [];
  for (const child of element.children) {
    if (predicate(child)) result.push(child);
    result.push(...descendants(child, predicate));
  }
  return result;
}

const rendered = new Map();
for (const record of ammunition) {
  const states = (record.relations || [])
    .filter((relation) => relation.type === "causes-state")
    .map((relation) => ({
      record: {
        id: relation.recordId, kind: "state",
        name: `${relation.recordId.split(":")[1]} State`,
        public_reference: {
          catalog: "states", id: relation.recordId.split(":")[1],
        },
      },
    }));
  const article = rulesReferenceArticle({ ...record, display_relations: states });
  const facts = descendants(article, (node) => node.className.split(" ").includes("ammunition-mechanics"));
  assert.equal(facts.length, 1, `${record.id} missing reviewed mechanics`);
  const list = descendants(facts[0], (node) => node.className === "ammunition-mechanics-list");
  assert.equal(list.length, 1);
  assert.ok(list[0].children.length >= 4);
  rendered.set(record.id, facts[0]);
}

const eclipse = rendered.get("ammunition:eclipse").textContent;
const smoke = rendered.get("ammunition:smoke").textContent;
assert.match(eclipse, /Multispectral VisorsCannot draw LoF/);
assert.match(smoke, /Multispectral VisorsCan draw LoF/);
for (const text of [eclipse, smoke]) assert.doesNotMatch(text, /Critical|Saving Roll/);

const t2 = rendered.get("ammunition:t2").textContent;
assert.match(t2, /2 Wounds per failed Saving Roll/);
assert.match(t2, /1 Wound per failed Saving Roll/);
const para = rendered.get("ammunition:para").textContent;
assert.match(para, /PH−6; no effect if the target lacks this Attribute/);
const em = rendered.get("ammunition:em");
const links = descendants(em, (node) => node.tag === "a");
assert.ok(links.some((link) => link.href === "/states/isolated"));
assert.ok(links.some((link) => link.href === "/states/immobilized-b"));
const shock = rendered.get("ammunition:shock").textContent;
assert.match(shock, /VITA 1 only; bypasses Unconscious/);
const stun = rendered.get("ammunition:stun").textContent;
assert.match(stun, /Courage or equivalent is exempt/);

const nonAmmunition = rulesReferenceArticle({
  id: "skill:test", kind: "skill", name: "Skill",
  summary: "Some rules", facts: { ammunitionResolution: { rollsPerHit: 2 } },
});
assert.equal(descendants(nonAmmunition,
  (node) => node.className.split(" ").includes("ammunition-mechanics")).length, 0);

console.log("11 ammunition cards; source conditions and linked states; no computed results");
