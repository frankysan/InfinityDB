import { getSearchResults } from "./api.js";
import { readShareState, shareStateHref, writeShareState } from "./share-state.js";
import { collectionLoadMessage, createPanelSwitcher } from "./view-components.js";

const byId = (id) => document.getElementById(id);
const elements = {
  form: byId("search-form"), query: byId("search-query"), count: byId("search-count"),
  results: byId("search-results"), prompt: byId("search-prompt"), loading: byId("search-loading"),
  error: byId("search-error"), errorMessage: byId("search-error-message"), empty: byId("search-empty"),
  list: byId("search-list"),
};
let controller;
let searchTimer;
let generation = 0;
const initialQuery = readShareState("search").params.get("q")?.trim().slice(0, 200) || "";

const show = createPanelSwitcher({
  container: elements.results,
  loading: elements.loading,
  panels: [
    elements.prompt,
    elements.loading,
    elements.error,
    elements.empty,
    elements.list,
  ],
});

function render(items) {
  elements.count.textContent = `${items.length.toLocaleString()} result${items.length === 1 ? "" : "s"}`;
  if (!items.length) return show(elements.empty);
  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const result = document.createElement("li");
    result.className = "search-result";
    const link = document.createElement("a");
    link.href = item.share_state
      ? shareStateHref(item.href, item.share_state.schema, item.share_state.values)
      : item.href;
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

function cancelSearch() {
  clearTimeout(searchTimer);
  controller?.abort();
  generation += 1;
}

async function search(query, requestGeneration) {
  const request = new AbortController();
  controller = request;
  show(elements.loading);
  try {
    const payload = await getSearchResults(query, request.signal);
    if (requestGeneration !== generation) return;
    render(payload.items);
  } catch (error) {
    if (requestGeneration !== generation || error.name === "AbortError") return;
    elements.errorMessage.textContent = collectionLoadMessage(error, "search results");
    console.error("Could not load search results", error);
    show(elements.error);
  }
}

function scheduleSearch({ immediate = false, composing = false } = {}) {
  cancelSearch();
  if (composing) return;
  const query = elements.query.value.trim().slice(0, 200);
  writeShareState("search", query ? { q: query } : {}, { replace: true });
  elements.count.textContent = "";
  if (!query) {
    show(elements.prompt);
    return;
  }
  show(elements.loading);
  const requestGeneration = generation;
  if (immediate) search(query, requestGeneration);
  else searchTimer = setTimeout(() => search(query, requestGeneration), 250);
}

elements.count.setAttribute("role", "status");
elements.query.value = initialQuery;
elements.query.addEventListener("input", (event) => scheduleSearch({ composing: event.isComposing }));
elements.query.addEventListener("compositionend", () => scheduleSearch());
elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  scheduleSearch({ immediate: true });
});
document.addEventListener("infinity:beforenavigation", cancelSearch, { once: true });
scheduleSearch({ immediate: true });
