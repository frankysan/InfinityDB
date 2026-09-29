import { getCatalogItems } from "./api.js";
import { readCatalogSearchQuery, replaceCatalogSearchQuery } from "./catalog-search-state.js";
import { initializeDistanceUnitToggle } from "./preferences.js";

const { catalog, singular, plural } = document.body.dataset;
const pageController = new AbortController();
const byId = (id) => document.getElementById(id);
const elements = {
  count: byId("catalog-count"),
  results: byId("catalog-results"),
  loading: byId("catalog-loading"),
  error: byId("catalog-error"),
  errorMessage: byId("catalog-error-message"),
  empty: byId("catalog-empty"),
  table: byId("catalog-table-container"),
  list: byId("catalog-list"),
  search: byId("catalog-search"),
};
let items = [];
let searchTimer;

function show(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.table]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

function render() {
  const query = elements.search.value.trim().toLocaleLowerCase();
  const visible = query
    ? items.filter((item) => item.searchText.includes(query))
    : items;
  elements.count.textContent = `${visible.length} ${visible.length === 1 ? singular : plural}`;
  if (!visible.length) return show(elements.empty);

  const fragment = document.createDocumentFragment();
  for (const item of visible) {
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    name.className = "table-column--primary";
    const link = document.createElement("a");
    link.href = `/${catalog}/${encodeURIComponent(item.slug || item.id)}`;
    link.textContent = item.name;
    name.append(link);

    const id = document.createElement("td");
    id.className = "id-column table-column--technical";
    id.textContent = item.id;
    row.append(name, id);
    fragment.append(row);
  }
  elements.list.replaceChildren(fragment);
  show(elements.table);
}

async function load() {
  show(elements.loading);
  try {
    const payload = await getCatalogItems(catalog, pageController.signal);
    items = payload.items
      .map((item) => ({
        ...item,
        searchText: `${item.name}\u0000${item.description || ""}`.toLocaleLowerCase(),
      }))
      .sort((left, right) => left.name.localeCompare(right.name, undefined, { numeric: true }));
    render();
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.errorMessage.textContent = error.message || `Could not load ${plural}.`;
    show(elements.error);
  }
}

elements.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    replaceCatalogSearchQuery(elements.search.value);
    render();
  }, 150);
});
document.addEventListener("infinity:beforenavigation", () => {
  clearTimeout(searchTimer);
  pageController.abort();
}, { once: true });
elements.search.value = readCatalogSearchQuery();
replaceCatalogSearchQuery(elements.search.value);
initializeDistanceUnitToggle();
load();
