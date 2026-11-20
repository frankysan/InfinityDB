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
const nodes = new Map();
const document = new EventTarget();
document.getElementById = (id) => {
  if (!nodes.has(id)) nodes.set(id, new Element());
  return nodes.get(id);
};
document.createElement = (tag) => new Element(tag);
document.createTextNode = (text) => text;
const window = new EventTarget();
window.location = { pathname: "/scenarios/double-bind" };
const context = vm.createContext({
  document, window, AbortController, URLSearchParams, encodeURIComponent,
  appendMaintainedText: (node, _tokens, fallback) => node.append(fallback),
  getScenarios: () => new Promise(() => {}),
  readShareState: () => ({ params: new URLSearchParams(), source: "none" }),
  createPanelSwitcher: () => () => {},
});
vm.runInContext(fs.readFileSync(source, "utf8").replace(/^import .*;$/gm, ""), context);

const objective = (id, name) => ({
  id, name, maximumPoints: 2, timing: "end-of-game",
  awards: [{ objectivePoints: 2, condition: { kind: "reviewed-prose", text: name } }],
});
context.item = {
  objectives: [
    objective("encryption-one", "Activate an Antenna"),
    objective("sabotage", "Destroy an Antenna"),
    objective("secure-vector-one", "Dominate the Zone"),
    objective("kill-more", "Kill more enemy points"),
  ],
  objective_selection: {
    firstChooser: "player-who-chose-deployment",
    selectionTiming: "when-deployment-is-chosen",
    distinctSetsRequired: true,
    sets: [
      { id: "encryption", name: "Encryption", objectiveIds: ["encryption-one"] },
      { id: "sabotage", name: "Sabotage", objectiveIds: ["sabotage"] },
      { id: "secure-vector", name: "Secure Vector", objectiveIds: ["secure-vector-one"] },
    ],
  },
};
const wrapper = vm.runInContext("objectivesSection(item)", context);
const select = wrapper.children[2].children[0];
const regions = wrapper.children[3].children;
const secondary = wrapper.children[5];
assert.equal(select.value, "", "Default should compare all Main Objective sets");
assert.equal(regions.length, 3);
assert(regions.every((region) => !region.hidden), "No Main Objective selected by default");
assert.equal(secondary.children.length, 1);
assert.equal(secondary.children[0].children[0].children[0].children[0], "Kill more enemy points");

select.value = "sabotage";
select.dispatchEvent(new Event("change"));
assert.equal(regions.filter((region) => !region.hidden).length, 1);
assert.equal(regions[1].hidden, false);
assert.equal(secondary.children.length, 1, "Secondary scoring must remain visible");

context.item = { objectives: [objective("alone", "Standard objective")] };
const ordinary = vm.runInContext("objectivesSection(item)", context);
assert.equal(ordinary.children.length, 2, "Ordinary scenarios use the unchanged objective layout");
fs.writeSync(1, "scenario Main Objective selection: passed\n");
