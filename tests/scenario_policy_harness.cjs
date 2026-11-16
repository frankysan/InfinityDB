const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = process.argv[2];
if (!source) throw new Error("Missing scenario script");
class Element extends EventTarget {
  constructor(tag = "div") {
    super();
    this.tag = tag;
    this.children = [];
    this.value = "";
    this.hidden = false;
    this.dataset = {};
    this.classList = { add() {} };
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
}
const elements = new Map();
const document = new EventTarget();
document.getElementById = (id) => {
  if (!elements.has(id)) elements.set(id, new Element());
  return elements.get(id);
};
document.createElement = (tag) => new Element(tag);
document.createTextNode = (text) => text;
const window = new EventTarget();
window.location = { pathname: "/scenarios/battleground" };
const requests = [];
const context = vm.createContext({
  document,
  window,
  AbortController,
  URLSearchParams,
  encodeURIComponent,
  getScenarios: () => new Promise(() => {}),
  getSeasonPolicies: (season, revision, mode, signal) => new Promise((resolve) => {
    requests.push({ season, revision, mode, signal, resolve });
  }),
  readShareState: () => ({ params: new URLSearchParams(), source: "none" }),
  createPanelSwitcher: () => () => {},
});
vm.runInContext(fs.readFileSync(source, "utf8").replace(/^import .*;$/gm, ""), context);

const controller = new AbortController();
context.item = {
  publication: {
    collection_id: "its-18", revision: "2026.09.01",
    collection_title: "ITS Season 18: Overheat",
  },
};
context.availableContexts = ["official-tournament", "team-ops-extra"];
context.controller = controller;
const section = vm.runInContext(
  "seasonPolicySection(item, availableContexts, controller)", context,
);
assert(section, "Season page must offer an explicit context selector");
const select = section.children[2].children[0];
const results = section.children[3];
assert.equal(select.value, "", "Unselected season must not opt into tournament rules");
assert.equal(requests.length, 0, "Unselected context must not fetch or apply policies");

select.value = "official-tournament";
select.dispatchEvent(new Event("change"));
assert.equal(requests.length, 1);
assert.equal(requests[0].season, "its-18");
assert.equal(requests[0].revision, "2026.09.01");
assert.equal(requests[0].mode, "official-tournament");

select.value = "";
select.dispatchEvent(new Event("change"));
assert.equal(results.children.length, 0);
requests[0].resolve({ items: [{
  id: "its18-spec-ops-tournament",
  title: "Season 18 restriction",
  target: { recordId: "skill:infinity-spec-ops", name: "Infinity Spec-Ops" },
  effect: { text: "Prohibited in tournament play" },
  citations: [{
    sourceId: "its-season-18-en-pdf", page: 26, section: "Spec-Ops",
    sourceTitle: "ITS Season 18: Overheat (English)",
    sourceUrl: "https://experience.corvusbelli.com/en/infinity/its-rules",
  }],
}] });
setImmediate(() => {
  assert.equal(results.children.length, 0, "Late result may not reapply a cleared context");
  assert.equal(requests.length, 1, "Clearing an opt-in never fetches a policy");
  select.value = "team-ops-extra";
  select.dispatchEvent(new Event("change"));
  assert.equal(requests.length, 2);
  controller.abort();
  requests[1].resolve({ items: [] });
  setImmediate(() => {
    assert.notEqual(results.children[0]?.textContent,
      "No additional ITS policy is published for this play context.",
      "Aborted navigation may not render a late policy");
    assert.equal(vm.runInContext("seasonPolicySection({publication:{collection_id:'n5-core'}}, availableContexts, controller)", context),
      null, "Core page may not offer ITS policy selection");
    fs.writeSync(1, "scenario ITS context selection: passed\\n");
  });
});
