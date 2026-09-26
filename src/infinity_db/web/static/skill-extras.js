import { getSkillExtras } from "./api.js";
import { formatSkillDistanceExtra, initializeDistanceUnitToggle } from "./preferences.js";

const byId = (id) => document.getElementById(id);
const elements = {
  count: byId("modifier-count"), results: byId("modifier-results"), loading: byId("modifier-loading"),
  error: byId("modifier-error"), errorMessage: byId("modifier-error-message"), empty: byId("modifier-empty"),
  table: byId("modifier-table-container"), list: byId("modifier-list"),
};
let items = [];
const pageController = new AbortController();

function show(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.table]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

function renderItems(items) {
  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const row = document.createElement("tr");
    const skill = document.createElement("th");
    skill.scope = "row";
    skill.textContent = item.skill_name;
    const extra = document.createElement("td");
    extra.textContent = item.is_distance
      ? formatSkillDistanceExtra(item.extra_name, item.parameter_semantics)
      : item.extra_name;
    const units = document.createElement("td");
    units.className = "modifier-unit-links";
    for (const [index, unit] of (item.units || []).entries()) {
      if (index) units.append(", ");
      const link = document.createElement("a");
      link.href = `/units/${unit.public_slug || unit.id}`;
      link.textContent = unit.name;
      units.append(link);
    }
    row.append(skill, extra, units);
    fragment.append(row);
  }
  elements.list.replaceChildren(fragment);
}

async function load() {
  show(elements.loading);
  try {
    const payload = await getSkillExtras(pageController.signal);
    items = payload.items;
    elements.count.textContent = `${items.length} combinations`;
    if (!items.length) return show(elements.empty);
    renderItems(items);
    show(elements.table);
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Could not load skill modifiers.";
    show(elements.error);
  }
}

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
initializeDistanceUnitToggle();
load();
window.addEventListener("distanceunitchange", () => {
  if (!elements.table.hidden) renderItems(items);
}, { signal: pageController.signal });
