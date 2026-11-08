const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const scriptPath = process.argv[2];
if (!scriptPath) throw new Error("Expected scenario.js path");

let distanceRefreshes = 0;
let summarySignal;
let mapImage;
let mapFetches = 0;

class FakeElement extends EventTarget {
  constructor(tagName = "div") {
    super();
    this.localName = tagName;
    this.hidden = false;
    this.dataset = {};
    this.isConnected = true;
    this.classList = { add() {} };
  }
  append() {}
  querySelector(selector) {
    if (this === elements.get("scenario-content") && selector === ".scenario-table-size") {
      distanceRefreshes += 1;
    }
    return null;
  }
}

const elements = new Map();
const document = new EventTarget();
document.documentElement = { dataset: { theme: "dark" } };
document.getElementById = (id) => {
  if (!elements.has(id)) elements.set(id, new FakeElement());
  return elements.get(id);
};
document.createElement = (tag) => {
  const element = new FakeElement(tag);
  if (tag === "img") mapImage = element;
  return element;
};
const window = new EventTarget();
window.location = { pathname: "/scenarios/domination" };
const context = vm.createContext({
  document,
  window,
  AbortController,
  URLSearchParams,
  encodeURIComponent,
  URL,
  fetch: () => { mapFetches += 1; throw new Error("Map must remain a native image"); },
  getScenarios: (signal) => {
    summarySignal = signal;
    return new Promise(() => {});
  },
  getScenario() { throw new Error("Unexpected detail request"); },
  distanceUnit: () => "in",
  readShareState: () => ({ params: new URLSearchParams(), source: "none" }),
  createPanelSwitcher: () => () => {},
});
const code = fs.readFileSync(scriptPath, "utf8").replace(/^import .*;$/gm, "");
vm.runInContext(code, context, { filename: scriptPath });
assert(summarySignal && !summarySignal.aborted);

vm.runInContext('mapCard({ name: "Domination", slug: "domination", selected_army_points: 300 })', context);
assert.equal(mapImage.localName, "img");
assert(mapImage.src.includes("/api/scenarios/domination/map.svg?"));
assert(mapImage.src.includes("army_points=300"));
assert(mapImage.src.includes("theme=dark"));
assert.equal(mapFetches, 0, "Map rendering must not fetch and inline SVG");

window.dispatchEvent(new Event("distanceunitchange"));
assert.equal(distanceRefreshes, 1);

document.dispatchEvent(new Event("infinity:beforenavigation"));
assert.equal(summarySignal.aborted, true, "pending catalog request must be aborted");
window.dispatchEvent(new Event("distanceunitchange"));
window.dispatchEvent(new Event("themechange"));
assert.equal(distanceRefreshes, 1, "inactive page must not receive preference changes");

fs.writeSync(1, "scenario navigation lifecycle: passed\n");
process.exit(0);
