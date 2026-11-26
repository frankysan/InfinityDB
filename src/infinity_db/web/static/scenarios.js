import { getScenarios } from "./api.js";
import { appendMaintainedText } from "./maintained-text.js";
import { collectionLoadMessage, createPanelSwitcher } from "./view-components.js";

// Source-reviewed overview grouping: ITS 17 V0.2 contents (p. 2) and
// ITS 18 2026.09.11 contents (p. 4) list the same five Direct Action missions.
// Keep the classification season-scoped: Core Annihilation is not Direct Action.
const GROUPED_ITS_COLLECTIONS = new Set(["its-17", "its-18"]);
const DIRECT_ACTION_SCENARIOS = new Set([
  "annihilation", "battleground", "cutthroat", "superiority", "uplink-center",
]);

const byId = (id) => document.getElementById(id);
const elements = {
  count: byId("scenario-count"),
  collection: byId("scenario-collection"),
  results: byId("scenario-results"),
  loading: byId("scenario-loading"),
  error: byId("scenario-error"),
  errorMessage: byId("scenario-error-message"),
  empty: byId("scenario-empty"),
  grid: byId("scenario-grid"),
};
const controller = new AbortController();
let availableCollections = [];
const selectedParams = new URLSearchParams(window.location.search);
const selection = {
  collection: selectedParams.get("collection") || "",
  revision: selectedParams.get("revision") || "",
};
const show = createPanelSwitcher({
  container: elements.results,
  loading: elements.loading,
  panels: [elements.loading, elements.error, elements.empty, elements.grid],
});

function supportedPointsLabel(points) {
  return (points || []).map((value) => `${value}`).join(" · ");
}

function renderScenario(item, headingTag = "h3") {
  const article = document.createElement("article");
  article.className = "surface surface--subtle surface--raised scenario-card";

  const header = document.createElement("header");
  header.className = "scenario-card-header";
  const identity = document.createElement("div");
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = item.publication?.collection_title || "Scenario";
  const title = document.createElement(headingTag);
  title.textContent = item.name;
  identity.append(eyebrow, title);
  const revision = document.createElement("span");
  revision.className = "detail-badge";
  revision.textContent = item.publication?.revision ? `v${item.publication.revision}` : "Current";
  header.append(identity, revision);

  const description = document.createElement("p");
  description.className = "detail-copy scenario-card-description";
  appendMaintainedText(description, item.description_tokens, item.description);

  const sizes = document.createElement("div");
  sizes.className = "scenario-card-sizes";
  const sizesLabel = document.createElement("span");
  sizesLabel.className = "small-label";
  sizesLabel.textContent = "Army Points";
  const sizesValue = document.createElement("strong");
  sizesValue.textContent = supportedPointsLabel(item.supported_army_points);
  sizes.append(sizesLabel, sizesValue);

  const footer = document.createElement("footer");
  footer.className = "scenario-card-footer";
  const source = document.createElement("span");
  source.className = "detail-source";
  source.textContent = item.publication?.source_title || "Current rules";
  const link = document.createElement("a");
  link.className = "button button-primary";
  const params = new URLSearchParams();
  if (item.publication?.collection_id !== "n5-core") {
    params.set("collection", item.publication.collection_id);
  }
  link.href = `/scenarios/${encodeURIComponent(item.slug)}${params.size ? `?${params}` : ""}`;
  link.textContent = "Open scenario";
  footer.append(source, link);

  article.append(header, description, sizes, footer);
  return article;
}

function scenarioGrid(items, headingTag = "h3") {
  const grid = document.createElement("div");
  grid.className = "scenario-grid";
  grid.append(...items.map((item) => renderScenario(item, headingTag)));
  return grid;
}

function scenarioSections(items) {
  const collection = items[0]?.publication?.collection_id;
  if (!GROUPED_ITS_COLLECTIONS.has(collection)
      || !items.every((item) => item.publication?.collection_id === collection)) {
    return [scenarioGrid(items)];
  }

  const groups = [
    ["standard", "Standard scenarios", items.filter((item) => !DIRECT_ACTION_SCENARIOS.has(item.slug))],
    ["direct-action", "Direct Action scenarios", items.filter((item) => DIRECT_ACTION_SCENARIOS.has(item.slug))],
  ];
  return groups.filter(([, , members]) => members.length).map(([id, title, members]) => {
    const section = document.createElement("section");
    section.className = "scenario-catalog-group";
    const heading = document.createElement("h3");
    heading.id = `scenario-group-${id}`;
    heading.className = "detail-heading";
    heading.textContent = title;
    section.setAttribute("aria-labelledby", heading.id);
    section.append(heading, scenarioGrid(members, "h4"));
    return section;
  });
}

function populateCollections(collections) {
  availableCollections = collections;
  const selected = selection.collection
    ? collections.findIndex((item) => item.id === selection.collection
      && (!selection.revision || item.revision === selection.revision))
    : collections.findIndex((item) => item.id === "n5-core");
  const options = collections.map((item, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${item.title} (${item.scenario_count})`;
    return option;
  });
  if (selected < 0) {
    const unavailable = document.createElement("option");
    unavailable.value = "";
    unavailable.textContent = selection.collection
      ? "Selected rules set or season unavailable"
      : "Core scenarios unavailable";
    unavailable.disabled = true;
    options.unshift(unavailable);
  }
  elements.collection.replaceChildren(...options);
  elements.collection.value = selected < 0 ? "" : String(selected);
  elements.collection.disabled = collections.length === 0;
}

function changeCollection() {
  if (!elements.collection.value) return;
  const item = availableCollections[Number(elements.collection.value)];
  if (!item) return;
  const params = new URLSearchParams();
  if (item.id !== "n5-core") {
    params.set("collection", item.id);
  }
  window.location.assign(`/scenarios${params.size ? `?${params}` : ""}`);
}

async function initialize() {
  show(elements.loading);
  try {
    const payload = await getScenarios(controller.signal, selection);
    populateCollections(payload.collections || []);
    const items = [...(payload.items || [])].sort((a, b) => a.name.localeCompare(b.name, "en"));
    elements.count.textContent = `${items.length} ${items.length === 1 ? "scenario" : "scenarios"}`;
    if (!items.length) return show(elements.empty);
    elements.grid.replaceChildren(...scenarioSections(items));
    show(elements.grid);
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.status === 400
      ? "This rules set, ITS season or rules revision is unavailable. Choose another from Scenarios."
      : collectionLoadMessage(error, "scenarios");
    console.error("Could not load scenarios", error);
    show(elements.error);
  }
}

elements.collection.addEventListener("change", changeCollection);
document.addEventListener("infinity:beforenavigation", () => controller.abort(), { once: true });
initialize();
