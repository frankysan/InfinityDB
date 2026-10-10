// Minimal DOM probe of the real maintained-text and shared rules-card modules.
import assert from "node:assert/strict";

class Node {
  constructor(tag, text = "") {
    this.tag = tag;
    this.children = [];
    this.className = "";
    this.value = text;
  }
  append(...children) {
    for (const child of children) {
      if (typeof child === "string") this.children.push(new Node("#text", child));
      else if (child.tag === "#fragment") this.children.push(...child.children);
      else this.children.push(child);
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
  cookie: "",
  addEventListener() {},
  createElement: (tag) => new Node(tag),
  createTextNode: (text) => new Node("#text", text),
  createDocumentFragment: () => new Node("#fragment"),
};

const { maintainedTextFragment } = await import(
  "../src/infinity_db/web/static/maintained-text.js"
);
const literalMarker = maintainedTextFragment([{ type: "text", text: "Army [**] marker." }]);
assert.equal(literalMarker.textContent, "Army [**] marker.");
assert.ok(!literalMarker.children.some((node) => node.tag === "strong"));

const { rulesReferenceSection } = await import(
  "../src/infinity_db/web/static/rules-reference.js"
);

const reference = (label) => ({
  type: "reference", label,
  public_reference: { catalog: "traits", id: "deployable" },
});
const rule = {
  id: "weapon:drop-bears", name: "Drop Bears",
  summary: "Intro.\n\n**Deployable Mode:** Place it.\n\n**BS Mode:** Throw it.\n\nRestrictions.",
  summary_tokens: [
    { type: "text", text: "Intro.\n\n**" },
    reference("Deployable"),
    { type: "text", text: " Mode:** Place it.\n\n**BS Mode:** Throw it.\n\nRestrictions." },
  ],
  facts: { sourceNotes: ["Army retains Throwing Weapon."] },
  fact_tokens: { sourceNotes: [[
    { type: "text", text: "Army retains " },
    reference("Throwing Weapon"),
    { type: "text", text: "." },
  ]] },
};
const section = rulesReferenceSection([rule]);
const article = section.children.find((node) => node.tag === "article");
const paragraphs = article.children.filter((node) => node.className === "detail-copy");
assert.equal(paragraphs.length, 4);
assert.equal(paragraphs[0].textContent, "Intro.");
assert.equal(paragraphs[1].textContent, "Deployable Mode: Place it.");
assert.equal(paragraphs[2].textContent, "BS Mode: Throw it.");
assert.equal(paragraphs[3].textContent, "Restrictions.");
assert.ok(paragraphs[1].children.some((node) => node.tag === "strong"));
const bold = paragraphs[1].children.find((node) => node.tag === "strong");
assert.ok(bold.children.some((node) => node.className === "maintained-reference-wrap"));
assert.ok(paragraphs[2].children.some((node) => node.tag === "strong"));
assert.ok(!paragraphs.some((node) => node.textContent.includes("**")));
const note = article.children.find((node) => node.className === "rules-source-note");
assert.ok(note);
assert.equal(note.textContent, "Army retains Throwing Weapon.");
assert.ok(note.children.some((node) => node.className === "maintained-reference-wrap"));
assert.ok(article.children.indexOf(note) > article.children.indexOf(paragraphs[2]));
console.log("4 paragraphs; bold links; separate source note; no literal markers");
