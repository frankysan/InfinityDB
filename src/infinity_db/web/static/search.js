import { getSearchResults } from "./api.js";
import { initializeDistanceUnitToggle } from "./preferences.js";

const byId = (id) => document.getElementById(id);
const elements = {
  form: byId("search-form"), query: byId("search-query"), count: byId("search-count"),
  results: byId("search-results"), prompt: byId("search-prompt"), loading: byId("search-loading"),
  error: byId("search-error"), errorMessage: byId("search-error-message"), empty: byId("search-empty"),
  list: byId("search-list"),
};
const controller = new AbortController();
const query = new URLSearchParams(window.location.search).get("q")?.trim() || "";

function show(panel) {
  for (const element of [elements.prompt, elements.loading, elements.error, elements.empty, elements.list]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

function render(items) {
  elements.count.textContent = `${items.length.toLocaleString()} result${items.length === 1 ? "" : "s"}`;
  if (!items.length) return show(elements.empty);
  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const result = document.createElement("li");
    result.className = "search-result";
    const link = document.createElement("a");
    link.href = item.href;
    link.textContent = item.name;
    const domain = document.createElement("span");
    domain.className = "search-domain";
    domain.textContent = item.domain;
    result.append(link, domain);
    fragment.append(result);
  }
  elements.list.replaceChildren(fragment);
  show(elements.list);
}

async function search() {
  if (!query) return show(elements.prompt);
  show(elements.loading);
  try {
    const payload = await getSearchResults(query, controller.signal);
    render(payload.items);
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || "Please try again.";
    show(elements.error);
  }
}

elements.query.value = query;
document.addEventListener("infinity:beforenavigation", () => controller.abort(), { once: true });
initializeDistanceUnitToggle();
search();
