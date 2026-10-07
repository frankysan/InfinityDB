import { getScenarios } from "./api.js";
import { appendMaintainedText } from "./maintained-text.js";
import { createPanelSwitcher } from "./view-components.js";

const byId = (id) => document.getElementById(id);
const elements = {
  count: byId("scenario-count"),
  results: byId("scenario-results"),
  loading: byId("scenario-loading"),
  error: byId("scenario-error"),
  errorMessage: byId("scenario-error-message"),
  empty: byId("scenario-empty"),
  grid: byId("scenario-grid"),
};
const controller = new AbortController();
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
  link.href = `/scenarios/${encodeURIComponent(item.slug)}`;
  link.textContent = "Open scenario";
  footer.append(source, link);

  article.append(header, description, sizes, footer);
  return article;
}

async function initialize() {
  show(elements.loading);
  try {
    const payload = await getScenarios(controller.signal);
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

document.addEventListener("infinity:beforenavigation", () => controller.abort(), { once: true });
initialize();
