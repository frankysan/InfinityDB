const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const scriptPath = process.argv[2];
if (!scriptPath) throw new Error("Expected scenario.js path");

let distanceRefreshes = 0;
let mapSignal;
let summarySignal;
let resolveMapRequest;
let parses = 0;

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
document.getElementById = (id) => {
  if (!elements.has(id)) elements.set(id, new FakeElement());
  return elements.get(id);
};
document.createElement = (tag) => new FakeElement(tag);
const window = new EventTarget();
window.location = { pathname: "/scenarios/domination" };
const context = vm.createContext({
  document,
  window,
  AbortController,
  URLSearchParams,
  encodeURIComponent,
  URL,
  fetch: (_url, options) => {
    mapSignal = options.signal;
    return new Promise((resolve) => { resolveMapRequest = resolve; });
  },
  getScenarios: (signal) => {
    summarySignal = signal;
    return new Promise(() => {});
  },
  getScenario() { throw new Error("Unexpected detail request"); },
  distanceUnit: () => "in",
  createPanelSwitcher: () => () => {},
  DOMParser: class {
    parseFromString() {
      parses += 1;
      throw new Error("Stale map must never be parsed");
    }
  },
});
const code = fs.readFileSync(scriptPath, "utf8").replace(/^import .*;$/gm, "");
vm.runInContext(code, context, { filename: scriptPath });
assert(summarySignal && !summarySignal.aborted);

// Simulate a map SVG request that the underlying fetch ignores after navigation.
vm.runInContext('mapCard({ name: "Domination", slug: "domination", selected_army_points: 300 })', context);
assert(mapSignal && !mapSignal.aborted);
window.dispatchEvent(new Event("distanceunitchange"));
assert.equal(distanceRefreshes, 1);

document.dispatchEvent(new Event("infinity:beforenavigation"));
assert.equal(mapSignal.aborted, true, "pending map request must be aborted");
assert.equal(summarySignal.aborted, true, "pending catalog request must be aborted");
window.dispatchEvent(new Event("distanceunitchange"));
assert.equal(distanceRefreshes, 1, "inactive page must not receive distance changes");
resolveMapRequest({ ok: true, text: () => Promise.resolve("<svg/>") });

setImmediate(() => {
  assert.equal(parses, 0, "late fetch resolution must not mutate a navigated-away page");
  console.log("scenario navigation lifecycle: passed");
});
