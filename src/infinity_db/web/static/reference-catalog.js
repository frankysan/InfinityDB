import { getCatalogItems, getRestrictionsReference } from "./api.js";
import { restrictionsSection } from "./restrictions-reference.js";
import { readCatalogSearchQuery, replaceCatalogSearchQuery } from "./catalog-search-state.js";
import { createPanelSwitcher } from "./view-components.js";

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

const show = createPanelSwitcher({
  container: elements.results,
  loading: elements.loading,
  panels: [elements.loading, elements.error, elements.empty, elements.table],
});

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
load();

async function loadRestrictionsReference() {
  if (catalog !== "rules") return;
  try {
    const data = await getRestrictionsReference(pageController.signal);
    const section = restrictionsSection(data);
    const listing = document.querySelector(".modifier-explorer");
    listing.after(section);
    const jump = document.createElement("p");
    jump.className = "intro-copy";
    const anchor = document.createElement("a");
    anchor.href = "/rules#restrictions";
    anchor.textContent = "View N5.3 Restrictions chart";
    jump.append(anchor);
    document.querySelector(".intro > div")?.append(jump);
    if (window.location.hash === "#restrictions") {
      requestAnimationFrame(() => section.scrollIntoView({ block: "start" }));
    }
  } catch (error) {
    if (error.name === "AbortError") return;
    const note = document.createElement("p");
    note.className = "detail-copy";
    note.textContent = "Restrictions chart unavailable. Other General Rules remain accessible.";
    document.querySelector(".modifier-explorer")?.after(note);
    console.error("Could not load Restrictions reference", error);
  }
}
loadRestrictionsReference();
