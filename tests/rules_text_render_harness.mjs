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
assert.equal(note.textContent, "Source context: Army retains Throwing Weapon.");
assert.equal(note.children[0].className, "rules-provenance-label");
assert.ok(article.children.some((node) => (
  node.className === "rules-card-provenance"
  && node.textContent.includes("InfinityDB-maintained reference")
)));
assert.ok(note.children.some((node) => node.className === "maintained-reference-wrap"));
assert.ok(article.children.indexOf(note) > article.children.indexOf(paragraphs[2]));

const placeholder = {
  id: "rule:scenario:supply-boxes", name: "Supply Boxes",
  summary: "Rules for Supply Boxes.",
  summary_tokens: [{ type: "text", text: "Rules for Supply Boxes." }],
  facts: {
    effects: ["Only Models, not Markers, may carry a Supply Box."],
    sourceNotes: ["Reviewed in the N5.3 core scenario."],
  },
  citations: [{ source_title: "N5.3", page: 153 }],
  collection: { title: "N5 Core Scenarios" },
  scope: { game: "N5" },
};
const redundant = rulesReferenceSection([placeholder]).children.find(
  (node) => node.tag === "article"
);
assert.equal(redundant.id, "rule-rule-scenario-supply-boxes");
assert.equal(redundant.children.filter((node) => node.className === "detail-copy").length, 0);
assert.ok(redundant.textContent.includes("Supply Boxes"));
assert.ok(redundant.textContent.includes("Only Models, not Markers"));
assert.ok(redundant.textContent.includes("Reviewed in the N5.3 core scenario."));
assert.ok(redundant.textContent.includes("Sources: N5.3, p. 153"));
assert.ok(redundant.textContent.includes("N5 Core Scenarios"));
const cited = redundant.children.find((node) => node.className === "detail-source rules-source-citations");
assert.ok(cited);
assert.equal(cited.children[0].textContent, "Sources: ");

const meaningful = {
  ...placeholder,
  summary: "Supply Boxes can be carried by Specialist Troops.",
  summary_tokens: [{ type: "text", text: "Supply Boxes can be carried by Specialist Troops." }],
};
const meaningfulArticle = rulesReferenceSection([meaningful]).children.find(
  (node) => node.tag === "article"
);
assert.equal(meaningfulArticle.children.filter((node) => node.className === "detail-copy").length, 1);
assert.ok(meaningfulArticle.textContent.includes("can be carried by Specialist Troops"));

const linked = {
  ...placeholder,
  summary_tokens: [
    { type: "text", text: "Rules for " }, reference("Supply Boxes"),
    { type: "text", text: "." },
  ],
};
const linkedArticle = rulesReferenceSection([linked]).children.find(
  (node) => node.tag === "article"
);
assert.equal(linkedArticle.children.filter((node) => node.className === "detail-copy").length, 1);
assert.ok(linkedArticle.textContent.includes("Rules for Supply Boxes."));
const clarifications = rulesReferenceSection([{
  ...meaningful,
  facts: { clarifications: ["InfinityDB notes an interaction."] },
}]).children.find((node) => node.tag === "article");
const reviewed = clarifications.children.find((node) => (
  node.className === "detail-fact-group" && node.children.some((child) => (
    child.className === "rules-provenance-caption"
  ))
));
assert.ok(reviewed);
assert.equal(reviewed.children[0].textContent, "Clarifications and examples");
assert.ok(reviewed.children[1].textContent.includes("InfinityDB-reviewed explanation"));
assert.equal(reviewed.children[2].tag, "ul");

const { faqRulingsSection } = await import(
  "../src/infinity_db/web/static/faq-rulings.js"
);
const selectedFaq = {
  question: "Can this be done?", answer: "No.",
  selected_source: { version: "0.1", published_date: "2026-09-01" },
  original_publication: { version: "0.1" },
  citations: [{ source_id: "faq", page: 3, source_title: "N5 FAQ" }],
  selected_citation: { sourceId: "faq", page: 3 },
};
const FAQ = faqRulingsSection([
  selectedFaq,
  {
    ...selectedFaq,
    question: "Are the publications in agreement?",
    conflicting_citations: [{ sourceId: "faq", page: 3 }],
    selection_reason: "The publications differ in a material requirement.",
  },
]);
const dated = FAQ.children.find((node) => node.tag === "article");
assert.ok(dated.className.includes("faq-dated-clarification"));
assert.ok(dated.children.some((node) => (
  node.className === "detail-source faq-publication-source"
  && node.textContent.includes("source date anchor 2026-09-01")
)));
assert.ok(FAQ.children.some((node) => (
  node.className === "detail-source"
  && node.textContent.includes("not a verified PDF publication date")
)));
const carriedFaq = faqRulingsSection([{
  ...selectedFaq,
  original_publication: { version: "0.0", publishedDate: "2025-10-15" },
}]);
const carried = carriedFaq.children.find((node) => node.tag === "article");
assert.ok(carried.children.some((node) => (
  node.className === "detail-source faq-publication-source"
  && node.textContent.includes("first documented v0.0 (date anchor 2025-10-15)")
)));
const conflicted = FAQ.children.filter((node) => node.tag === "article")[1];
const warning = conflicted.children.find((node) => (
  node.className === "faq-source-discrepancy"
));
assert.ok(warning);
assert.equal(warning.children[0].textContent, "Source discrepancy — cited publications differ");
assert.ok(warning.children[1].textContent.includes("publications differ"));

console.log("4 paragraphs; bold links; separate source note; no literal markers; redundant summary omitted; explicit provenance roles");
