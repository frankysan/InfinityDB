import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import vm from "node:vm";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const code = readFileSync(path.join(root, "src/infinity_db/web/static/catalog-detail.js"), "utf8");
const start = code.indexOf("function ruleReferenceHref(reference) {");
const end = code.indexOf("function traitDescription(description) {", start);
assert(start >= 0 && end > start);

function fragment() {
  return { children: [], append(...children) { this.children.push(...children); } };
}
const document = {
  createDocumentFragment: fragment,
  createElement(tag) {
    return { tag, textContent: "", className: "", href: "" };
  },
};
const render = vm.runInNewContext(
  `${code.slice(start, end)}\nweaponTraitLinks`, { document, encodeURIComponent },
);
const output = render([
  { label: "Comms. Attack", name: "Comms Attack", slug: null,
    source_alias: true, public_reference: { catalog: "labels", id: "comms-attack" } },
  { label: "No LoF", name: "No LoF", slug: null,
    public_reference: { catalog: "labels", id: "no-lof" } },
  { label: "CC Attack (+3)", name: "CC Attack (+3)", slug: null,
    public_reference: { catalog: "labels", id: "cc-attack" } },
  { label: "State: Stunned / Immbolized-B", name: "State: Stunned / Immobilized-B",
    slug: null, source_alias: true, state_references: [
      { label: "Stunned", public_reference: { catalog: "states", id: "stunned" } },
      { label: "Immobilized-B", public_reference: { catalog: "states", id: "immobilized-b" } },
    ] },
  { label: "State: Unknown / Stunned", name: "State: Unknown / Stunned", slug: null },
]);
const links = output.children.filter((item) => typeof item !== "string" && item.tag === "a");
assert.deepEqual(links.map((item) => [item.textContent, item.href]), [
  ["Comms Attack", "/labels/comms-attack"],
  ["No LoF", "/labels/no-lof"],
  ["CC Attack (+3)", "/labels/cc-attack"],
  ["Stunned", "/states/stunned"],
  ["Immobilized-B", "/states/immobilized-b"],
]);
const aliases = output.children.filter((item) => item?.className === "developer-only weapon-trait-source-alias");
assert.equal(aliases.length, 2);
assert(aliases[0].textContent.includes("Comms. Attack"));
assert(aliases[1].textContent.includes("Immbolized-B"));
assert(output.children.includes("State: Unknown / Stunned"));
console.log("weapon trait and label navigation passed");
