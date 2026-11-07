import { getScenarios } from "./api.js";
import { appendMaintainedText } from "./maintained-text.js";
import { createPanelSwitcher } from "./view-components.js";

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

function renderScenario(item) {
  const article = document.createElement("article");
  article.className = "surface surface--subtle surface--raised scenario-card";

  const header = document.createElement("header");
  header.className = "scenario-card-header";
  const identity = document.createElement("div");
  const eyebrow = document.createElement("p");
  eyebrow.className = "eyebrow";
  eyebrow.textContent = item.publication?.collection_title || "Scenario";
  const title = document.createElement("h3");
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
    params.set("revision", item.publication.revision);
  }
  link.href = `/scenarios/${encodeURIComponent(item.slug)}${params.size ? `?${params}` : ""}`;
  link.textContent = "Open scenario";
  footer.append(source, link);

  article.append(header, description, sizes, footer);
  return article;
}

function populateCollections(collections) {
  availableCollections = collections;
  const selected = selection.collection
    ? collections.findIndex((item) => item.id === selection.collection && item.revision === selection.revision)
    : collections.findIndex((item) => item.id === "n5-core");
  const options = collections.map((item, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${item.title} · ${item.revision} (${item.scenario_count})`;
    return option;
  });
  if (selected < 0) {
    const unavailable = document.createElement("option");
    unavailable.value = "";
    unavailable.textContent = selection.collection
      ? `Collection unavailable: ${selection.collection} · ${selection.revision}`
      : "No current core scenarios";
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
    params.set("revision", item.revision);
  }
  window.location.assign(`/scenarios${params.size ? `?${params}` : ""}`);
}

async function initialize() {
  show(elements.loading);
  try {
    const payload = await getScenarios(controller.signal, selection);
    populateCollections(payload.collections || []);
    const items = payload.items || [];
    elements.count.textContent = `${items.length} ${items.length === 1 ? "scenario" : "scenarios"}`;
    if (!items.length) return show(elements.empty);
    elements.grid.replaceChildren(...items.map(renderScenario));
    show(elements.grid);
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Could not load scenarios.";
    show(elements.error);
  }
}

elements.collection.addEventListener("change", changeCollection);
document.addEventListener("infinity:beforenavigation", () => controller.abort(), { once: true });
initialize();
