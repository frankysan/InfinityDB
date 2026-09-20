import { getCatalogItems } from "./api.js";
import { initializeDistanceUnitToggle } from "./preferences.js";

const page = document.body.dataset.catalog;
const title = page === "traits" ? "traits" : page;
const byId = (id) => document.getElementById(id);
const elements = {
  count: byId("catalog-count"), results: byId("catalog-results"), loading: byId("catalog-loading"),
  error: byId("catalog-error"), errorMessage: byId("catalog-error-message"), empty: byId("catalog-empty"),
  table: byId("catalog-table-container"), list: byId("catalog-list"), search: byId("catalog-search"),
};
let items = [];
let searchTimer;

function searchableItem(item) {
  return {
    ...item,
    searchText: Object.values(item).map((value) => String(value || "").toLocaleLowerCase()).join("\u0000"),
    categoryName: item.category || "Uncategorized",
  };
}

function show(panel) {
  for (const element of [elements.loading, elements.error, elements.empty, elements.table]) {
    element.hidden = element !== panel;
  }
  elements.results.setAttribute("aria-busy", String(panel === elements.loading));
}

function render() {
  const query = elements.search.value.trim().toLocaleLowerCase();
  const visible = query ? items.filter((item) => item.searchText.includes(query)) : items;
  elements.count.textContent = page === "traits"
    ? `${visible.length} trait${visible.length === 1 ? "" : "s"}`
    : `${visible.length} ${title}${visible.length === 1 ? "" : " entries"}`;
  if (!visible.length) return show(elements.empty);
  const fragment = document.createDocumentFragment();
  let category;
  for (const item of visible) {
    const itemCategory = item.categoryName;
    if (page === "weapons" && itemCategory !== category) {
      category = itemCategory;
      const categoryRow = document.createElement("tr");
      categoryRow.className = "catalog-category-row";
      const categoryCell = document.createElement("th");
      categoryCell.colSpan = 3;
      categoryCell.scope = "rowgroup";
      categoryCell.textContent = category;
      categoryRow.append(categoryCell);
      fragment.append(categoryRow);
    }
    const row = document.createElement("tr");
    const name = document.createElement("th");
    name.scope = "row";
    if (["skills", "equipment", "weapons", "traits"].includes(page)) {
      const link = document.createElement("a");
      const routeId = page === "skills" && item.slug ? item.slug : item.id;
      link.href = `/${page}/${encodeURIComponent(routeId)}`;
      link.textContent = item.name;
      name.append(link);
    } else {
      name.textContent = item.name;
    }
    const useCount = document.createElement("td");
    useCount.textContent = Number(item.use_count || 0).toLocaleString();
    const id = document.createElement("td");
    id.className = "id-column unit-id";
    id.textContent = item.id;
    row.append(name, useCount, id);
    fragment.append(row);
  }
  elements.list.replaceChildren(fragment);
  show(elements.table);
}

async function load() {
  show(elements.loading);
  try {
    const payload = await getCatalogItems(page);
    items = payload.items.map(searchableItem).sort((left, right) => (
      `${left.categoryName}\u0000${left.name}`.localeCompare(
        `${right.categoryName}\u0000${right.name}`, undefined, { numeric: true },
      )
    ));
    render();
  } catch (error) {
    elements.errorMessage.textContent = error.message || `Could not load ${title}.`;
    show(elements.error);
  }
}

elements.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(render, 150);
});
initializeDistanceUnitToggle();
load();
