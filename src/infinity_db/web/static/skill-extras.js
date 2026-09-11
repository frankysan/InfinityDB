import { initializeDistanceUnitToggle } from "./preferences.js";

const byId = (id) => document.getElementById(id);
const elements = {
  count: byId("modifier-count"), results: byId("modifier-results"), loading: byId("modifier-loading"),
  error: byId("modifier-error"), errorMessage: byId("modifier-error-message"), empty: byId("modifier-empty"),
  table: byId("modifier-table-container"), list: byId("modifier-list"),
};

function show(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.table]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

async function load() {
  show(elements.loading);
  try {
    const response = await fetch("/api/skill-extras");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Could not load skill modifiers.");
    elements.count.textContent = `${payload.items.length} combinations`;
    if (!payload.items.length) return show(elements.empty);
    const fragment = document.createDocumentFragment();
    for (const item of payload.items) {
      const row = document.createElement("tr");
      const skill = document.createElement("th");
      skill.scope = "row";
      skill.textContent = item.skill_name;
      const extra = document.createElement("td");
      extra.textContent = item.extra_name;
      row.append(skill, extra);
      fragment.append(row);
    }
    elements.list.replaceChildren(fragment);
    show(elements.table);
  } catch (error) {
    elements.errorMessage.textContent = error.message || "Could not load skill modifiers.";
    show(elements.error);
  }
}

initializeDistanceUnitToggle();
load();
