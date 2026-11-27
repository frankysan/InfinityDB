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
  rulesReferenceArticle: (rule) => {
    const card = new Element("article");
    card.textContent = rule.name;
    return card;
  },
});
vm.runInContext(fs.readFileSync(source, "utf8").replace(/^import .*;$/gm, ""), context);

const item = {
  publication: {
    collection_id: "its-18", revision: "2026.09.11",
    collection_title: "ITS Season 18: Overheat",
  },
};
const settle = () => new Promise((resolve) => setImmediate(resolve));
const policy = (title) => ({
  title,
  target: { recordId: "skill:infinity-spec-ops", name: "Infinity Spec-Ops" },
  effect: { text: "Prohibited in this play context" },
  citations: [{
    page: 27, section: "Spec-Ops",
    sourceUrl: "https://experience.corvusbelli.com/en/infinity/its-rules",
  }],
});

async function run() {
  context.item = item;
  context.controller = new AbortController();
  const section = vm.runInContext("seasonPolicySection(item, controller)", context);
  assert.equal(section.hidden, true);
  assert.equal(requests[0].mode, "");
  requests[0].resolve({ contexts: ["official-tournament", "team-ops-extra", "empty-extra"] });
  await settle();
  assert.deepEqual(requests.slice(1).map(({ mode }) => mode),
    ["official-tournament", "team-ops-extra", "empty-extra"]);
  for (const request of requests) {
    assert.equal(request.season, "its-18");
    assert.equal(request.revision, "2026.09.11");
    assert.equal(request.signal, context.controller.signal);
  }

  requests[1].resolve({ items: [policy("Tournament restriction"), policy("Second tournament rule")] });
  requests[2].resolve({ items: [policy("TEAM-OPS restriction")] });
  requests[3].resolve({ items: [] });
  await settle();
  assert.equal(section.hidden, false);
  const [heading, tournament, extra] = section.children;
  assert.equal(heading.textContent, "ITS tournament and Extra rules");
  assert.equal(section.children.length, 3, "Only populated contexts get cards");
  assert.equal(tournament.tag, "article");
  assert.equal(tournament.children[0].textContent, "Official Tournament");
  const tournamentBody = tournament.children[1];
  assert.equal(tournamentBody.className, "surface-body");
  assert.equal(tournamentBody.children[0].children[0].textContent, "Tournament restriction");
  assert.equal(tournamentBody.children[1].children[0].textContent, "Second tournament rule");
  assert.equal(extra.tag, "article");
  assert.equal(extra.children[0].textContent, "TEAM-OPS Extra");
  const extraBody = extra.children[1];
  assert.equal(extraBody.className, "surface-body");
  const [extraPolicy] = extraBody.children;
  assert.equal(extraPolicy.children[0].textContent, "TEAM-OPS restriction");
  assert.equal(extraPolicy.children[2].children[1].href, "/skills/infinity-spec-ops");
  assert.match(extraPolicy.children[3].children[1].textContent, /p\. 27/);

  context.controller = new AbortController();
  const abandoned = vm.runInContext("seasonPolicySection(item, controller)", context);
  requests[4].resolve({ contexts: ["team-ops-extra"] });
  await settle();
  context.controller.abort();
  requests[5].resolve({ items: [policy("Late restriction")] });
  await settle();
  assert.equal(abandoned.hidden, true);
  assert.equal(abandoned.children.length, 1);
  assert.equal(vm.runInContext(
    "seasonPolicySection({publication:{collection_id:'n5-core'}}, controller)", context,
  ), null);
  assert.equal(requests.length, 6);

  context.controller = new AbortController();
  context.item = {
    ...item,
    season_rules: [
      { name: "Casevac", facts: { applicability: { context: "season" } } },
      { name: "Team-Ops", facts: { applicability: { context: "team-ops-extra" } } },
    ],
  };
  const disclosure = vm.runInContext("seasonRulesSection(item, controller)", context);
  assert.equal(disclosure.tag, "details");
  assert.equal(Boolean(disclosure.open), false);
  const [summary, body] = disclosure.children;
  assert.equal(summary.tag, "summary");
  assert.equal(summary.children[0].textContent, "Season Rules");
  assert.equal(body.children[1].children[0].textContent, "General season rules");
  assert.equal(body.children[1].children[1].textContent, "Casevac");
  assert.equal(body.children[2].children[0].textContent, "TEAM-OPS Extra");
  assert.equal(body.children[2].children[1].textContent, "Team-Ops");
  requests[6].resolve({ contexts: [] });
  await settle();
  assert.equal(vm.runInContext(
    "seasonRulesSection({publication:{collection_id:'n5-core'}}, controller)", context,
  ), null);
  fs.writeSync(1, "scenario ITS context cards: passed\n");
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
