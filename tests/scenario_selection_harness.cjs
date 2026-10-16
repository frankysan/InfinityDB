const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const scriptPath = process.argv[2];
if (!scriptPath) throw new Error("Expected scenario.js path");

class FakeElement extends EventTarget {
  constructor() {
    super();
    this.hidden = false;
    this.value = "";
    this.dataset = {};
    this.children = [];
    this.classList = { add() {} };
  }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
}
const elements = new Map();
const document = new EventTarget();
document.getElementById = (id) => {
  if (!elements.has(id)) elements.set(id, new FakeElement());
  return elements.get(id);
};
document.createElement = () => new FakeElement();
document.createTextNode = (text) => text;
document.title = "";
const window = new EventTarget();
window.location = { pathname: "/scenarios/domination" };
const requests = [];
const panels = [];
const renders = [];
const shares = [];
const context = vm.createContext({
  document,
  window,
  AbortController,
  URLSearchParams,
  Number,
  encodeURIComponent,
  getScenarios: async () => ({ items: [{
    slug: "domination", name: "Domination", supported_army_points: [150, 200, 300, 350],
  }] }),
  getScenario: (_slug, points, signal) => new Promise((resolve, reject) => {
    requests.push({ points, signal, resolve, reject });
  }),
  // The FAQ overlay is independent and immediately available in this race
  // harness. Only stale scenario responses may replace the active game size.
  fetchReviewedFaqRulings: async () => ({ items: [] }),
  readShareState: () => ({ params: new URLSearchParams(), source: "none" }),
  writeShareState: (_kind, params) => shares.push(params.army_points),
  appendMaintainedText(node, _tokens, raw) { node.append(raw); },
  distanceUnit: () => "in",
  createPanelSwitcher: () => (panel) => { panels.push(panel); },
});
const code = fs.readFileSync(scriptPath, "utf8").replace(/^import .*;$/gm, "");
vm.runInContext(code, context, { filename: scriptPath });
context.render = (item) => renders.push(item.selected_army_points);

setImmediate(async () => {
  // Shared renderer: inline mission rules must not disappear when there is no
  // canonical linked Rule object (e.g. ITS Battleground's six local rules).
  const inline = context.inlineScenarioRuleArticle({
    name: "Dominate Zone", paragraphs: ["Only eligible Troopers count.", "Null States do not."],
  });
  assert.equal(inline.className.includes("scenario-inline-rule"), true);
  assert.deepEqual(inline.children.map((child) => child.children.length), [1, 1, 1]);
  assert.equal(inline.children[0].children[0].children[0], "Dominate Zone");
  assert.equal(inline.children[1].children[0], "Only eligible Troopers count.");
  assert.equal(inline.children[2].children[0], "Null States do not.");
  const sector = context.conditionNode({
    kind: "dominated-region-comparison", comparison: "greater",
    elementIds: ["sector-center"], minimum: 1,
  });
  assert.equal(sector.textContent, "Dominate this Sector");
  const quadrants = context.conditionNode({
    kind: "dominated-region-comparison", comparison: "greater",
    elementIds: ["quadrant-1", "quadrant-2"],
  });
  assert.equal(quadrants.textContent, "Dominate more Quadrants than the opponent");

  assert.equal(requests.length, 1, "default game size must load");
  assert.equal(requests[0].points, 300);
  assert.deepEqual(shares, ["300"]);
  const pointsSelect = elements.get("scenario-army-points");
  pointsSelect.value = "200";
  pointsSelect.dispatchEvent(new Event("change"));
  assert.equal(requests[0].signal.aborted, true);
  assert.equal(requests[1].points, 200);
  assert.equal(panels.at(-1), elements.get("scenario-status"));
  pointsSelect.value = "350";
  pointsSelect.dispatchEvent(new Event("change"));
  assert.equal(requests[1].signal.aborted, true);
  assert.equal(requests[2].points, 350);

  // Simulate transports that ignore aborts, delivering stale success and failure.
  requests[0].resolve({ selected_army_points: 300 });
  requests[1].reject(new Error("Old failed request"));
  await Promise.resolve();
  await Promise.resolve();
  assert.deepEqual(renders, []);
  assert.equal(panels.at(-1), elements.get("scenario-status"));
  requests[2].resolve({ selected_army_points: 350 });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(renders, [350]);
  assert.deepEqual(shares, ["300", "200", "350"]);

  // Clearing a selection cancels any in-flight detail request as well.
  pointsSelect.value = "150";
  pointsSelect.dispatchEvent(new Event("change"));
  assert.equal(requests[3].points, 150);
  pointsSelect.value = "";
  pointsSelect.dispatchEvent(new Event("change"));
  assert.equal(requests[3].signal.aborted, true);
  assert.equal(panels.at(-1), elements.get("scenario-choice"));
  requests[3].resolve({ selected_army_points: 150 });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(renders, [350]);
  console.log("scenario selection race: passed");
});
